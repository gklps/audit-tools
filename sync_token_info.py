#!/usr/bin/env python3
"""
Rubix Token Info Sync Service - Parallel Version

High-performance parallel sync of token information from SQLite to Postgres.
Optimized for processing millions of tokens using multiprocessing and batch operations.
"""

import sqlite3
import subprocess
import logging
import sys
from typing import Optional, Tuple, List
from multiprocessing import Pool, cpu_count
from functools import partial
import psycopg2
from psycopg2.extras import execute_batch
import time

# Configuration
SQLITE_DB_PATH = '/datadrive/Rubix/Node/creator/Rubix/rubix.db'
IPFS_COMMAND = './ipfs'
POSTGRES_CONNECTION_STRING = 'postgresql://neondb_owner:npg_Pa$206d@ep-wandering-sky-a1s81o40-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'

# Performance tuning
NUM_WORKERS = cpu_count() * 2  # Use 2x CPU cores for I/O bound tasks
BATCH_SIZE = 1000  # Insert records in batches of 1000
IPFS_TIMEOUT = 15  # Reduced timeout for faster failure detection

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sync_token_info.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def get_token_ids_from_sqlite() -> List[str]:
    """
    Connect to SQLite database and retrieve all token_id values from FTTokenTable.

    Returns:
        list: List of token_id strings
    """
    try:
        logger.info(f"Connecting to SQLite database at {SQLITE_DB_PATH}")
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT token_id FROM FTTokenTable")
        token_ids = [row[0] for row in cursor.fetchall()]

        conn.close()
        logger.info(f"Retrieved {len(token_ids)} token IDs from SQLite")
        return token_ids

    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error reading from SQLite: {e}")
        raise


def fetch_and_parse_token(token_id: str) -> Optional[Tuple[str, str, int, str]]:
    """
    Fetch token data from IPFS and parse it.
    This function is designed to be run in parallel.

    Args:
        token_id: The IPFS token ID

    Returns:
        tuple: (token_id, token_name, token_number, creator_did) or None if failed
    """
    try:
        # Fetch from IPFS
        result = subprocess.run(
            [IPFS_COMMAND, 'cat', token_id],
            capture_output=True,
            text=True,
            timeout=IPFS_TIMEOUT,
            check=True
        )
        ipfs_data = result.stdout.strip()

        # Parse data
        parts = ipfs_data.split()
        if len(parts) != 3:
            logger.error(f"Invalid format for {token_id}: {ipfs_data}")
            return None

        token_name = parts[0]
        token_number = int(parts[1])
        creator_did = parts[2]

        return (token_id, token_name, token_number, creator_did)

    except subprocess.TimeoutExpired:
        logger.warning(f"IPFS timeout: {token_id}")
        return None
    except subprocess.CalledProcessError as e:
        logger.warning(f"IPFS failed for {token_id}: {e.stderr.strip() if e.stderr else 'unknown error'}")
        return None
    except ValueError as e:
        logger.error(f"Parse error for {token_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error for {token_id}: {e}")
        return None


def create_postgres_table(conn):
    """
    Create TokenInfo table in Postgres if it doesn't exist.
    Also creates an index for better query performance.

    Args:
        conn: psycopg2 connection object
    """
    try:
        cursor = conn.cursor()

        # Create table
        create_table_query = """
        CREATE TABLE IF NOT EXISTS TokenInfo (
            token_id TEXT PRIMARY KEY,
            token_name TEXT,
            token_number INTEGER,
            creator_did TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        cursor.execute(create_table_query)

        # Add last_updated column if it doesn't exist (for existing tables)
        cursor.execute("""
            DO $$
            BEGIN
                BEGIN
                    ALTER TABLE TokenInfo ADD COLUMN last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                EXCEPTION
                    WHEN duplicate_column THEN
                        -- Column already exists, do nothing
                        NULL;
                END;
            END $$;
        """)

        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_token_name ON TokenInfo(token_name)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_creator_did ON TokenInfo(creator_did)
        """)

        conn.commit()
        cursor.close()
        logger.info("TokenInfo table and indexes created or already exist")

    except psycopg2.Error as e:
        logger.error(f"Error creating Postgres table: {e}")
        raise


def batch_insert_tokens(conn, token_data_batch: List[Tuple[str, str, int, str]]):
    """
    Insert a batch of tokens into Postgres using execute_batch for performance.

    Args:
        conn: psycopg2 connection object
        token_data_batch: List of tuples (token_id, token_name, token_number, creator_did)
    """
    try:
        cursor = conn.cursor()
        insert_query = """
        INSERT INTO TokenInfo (token_id, token_name, token_number, creator_did, last_updated)
        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (token_id)
        DO UPDATE SET
            token_name = EXCLUDED.token_name,
            token_number = EXCLUDED.token_number,
            creator_did = EXCLUDED.creator_did,
            last_updated = CURRENT_TIMESTAMP
        """

        # Use execute_batch for better performance with large batches
        execute_batch(cursor, insert_query, token_data_batch, page_size=BATCH_SIZE)
        conn.commit()
        cursor.close()

        logger.info(f"Successfully inserted/updated batch of {len(token_data_batch)} tokens")

    except psycopg2.Error as e:
        logger.error(f"Error inserting batch: {e}")
        conn.rollback()
        raise


def process_batch_parallel(token_ids_batch: List[str], worker_pool: Pool) -> List[Tuple[str, str, int, str]]:
    """
    Process a batch of token IDs in parallel using multiprocessing.

    Args:
        token_ids_batch: List of token IDs to process
        worker_pool: Multiprocessing pool

    Returns:
        List of successfully parsed token data
    """
    # Process all tokens in parallel
    results = worker_pool.map(fetch_and_parse_token, token_ids_batch)

    # Filter out None results (failed fetches)
    successful_results = [r for r in results if r is not None]

    return successful_results


def main():
    """
    Main function to orchestrate the parallel token sync process.
    """
    logger.info("=" * 80)
    logger.info(f"Starting PARALLEL Token Info Sync Service (Workers: {NUM_WORKERS})")
    logger.info("=" * 80)

    start_time = time.time()
    postgres_conn = None
    success_count = 0
    error_count = 0

    try:
        # Step 1: Get all token IDs from SQLite
        token_ids = get_token_ids_from_sqlite()

        if not token_ids:
            logger.warning("No token IDs found in SQLite database")
            return

        total_tokens = len(token_ids)
        logger.info(f"Processing {total_tokens:,} tokens with {NUM_WORKERS} parallel workers")

        # Step 2: Connect to Postgres
        logger.info("Connecting to Postgres database")
        postgres_conn = psycopg2.connect(POSTGRES_CONNECTION_STRING)

        # Step 3: Create table if not exists
        create_postgres_table(postgres_conn)

        # Step 4: Process tokens in parallel batches
        logger.info(f"Starting parallel processing in batches of {BATCH_SIZE}")

        # Create worker pool
        with Pool(processes=NUM_WORKERS) as pool:
            # Process in chunks for better memory management
            for batch_start in range(0, total_tokens, BATCH_SIZE):
                batch_end = min(batch_start + BATCH_SIZE, total_tokens)
                token_ids_batch = token_ids[batch_start:batch_end]

                batch_num = (batch_start // BATCH_SIZE) + 1
                total_batches = (total_tokens + BATCH_SIZE - 1) // BATCH_SIZE

                logger.info(f"Processing batch {batch_num}/{total_batches} "
                           f"(tokens {batch_start+1:,} to {batch_end:,})")

                # Process batch in parallel
                batch_start_time = time.time()
                successful_tokens = process_batch_parallel(token_ids_batch, pool)
                batch_process_time = time.time() - batch_start_time

                # Calculate statistics for this batch
                batch_success = len(successful_tokens)
                batch_errors = len(token_ids_batch) - batch_success
                success_count += batch_success
                error_count += batch_errors

                logger.info(f"Batch {batch_num} processed in {batch_process_time:.2f}s: "
                           f"{batch_success} succeeded, {batch_errors} failed")

                # Insert successful tokens into Postgres
                if successful_tokens:
                    try:
                        batch_insert_tokens(postgres_conn, successful_tokens)
                    except Exception as e:
                        logger.error(f"Failed to insert batch {batch_num}: {e}")
                        # Continue processing other batches

                # Progress update
                progress_pct = (batch_end / total_tokens) * 100
                elapsed = time.time() - start_time
                tokens_per_sec = batch_end / elapsed
                eta_seconds = (total_tokens - batch_end) / tokens_per_sec if tokens_per_sec > 0 else 0

                logger.info(f"Progress: {progress_pct:.1f}% | "
                           f"Speed: {tokens_per_sec:.1f} tokens/sec | "
                           f"ETA: {eta_seconds/60:.1f} minutes")

        # Final summary
        total_time = time.time() - start_time
        logger.info("=" * 80)
        logger.info(f"Sync completed in {total_time:.2f} seconds ({total_time/60:.1f} minutes)")
        logger.info(f"Total: {total_tokens:,} tokens")
        logger.info(f"Success: {success_count:,} ({success_count/total_tokens*100:.1f}%)")
        logger.info(f"Errors: {error_count:,} ({error_count/total_tokens*100:.1f}%)")
        logger.info(f"Average speed: {total_tokens/total_time:.1f} tokens/second")
        logger.info("=" * 80)

    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error in main process: {e}")
        sys.exit(1)
    finally:
        # Clean up
        if postgres_conn:
            postgres_conn.close()
            logger.info("Postgres connection closed")


if __name__ == "__main__":
    main()
