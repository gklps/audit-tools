-- ============================================================
-- Azure SQL Database Cleanup Script
-- Removes duplicate records and resets database state
-- ============================================================

-- Step 1: Check current database state
SELECT
    'Current State' as Status,
    COUNT(*) AS TotalRows,
    COUNT(DISTINCT token_id) AS UniqueTokenIDs,
    COUNT(*) - COUNT(DISTINCT token_id) AS DuplicateRows
FROM [dbo].[TokenRecords];

-- Step 2: Show duplicate record details
SELECT
    token_id,
    source_ip,
    node_name,
    COUNT(*) as duplicate_count
FROM [dbo].[TokenRecords]
GROUP BY token_id, source_ip, node_name
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;

-- Step 3: Clean up duplicate records (keep only the latest ones)
WITH DuplicateTokens AS (
    SELECT
        id,
        token_id,
        source_ip,
        node_name,
        synced_at,
        ROW_NUMBER() OVER (
            PARTITION BY token_id, source_ip, node_name
            ORDER BY synced_at DESC, id DESC
        ) as row_num
    FROM [dbo].[TokenRecords]
)
DELETE FROM [dbo].[TokenRecords]
WHERE id IN (
    SELECT id
    FROM DuplicateTokens
    WHERE row_num > 1
);

-- Step 4: Reset processed database tracking (forces fresh sync)
DELETE FROM [dbo].[ProcessedDatabases];

-- Step 5: Clean up sync session tracking
DELETE FROM [dbo].[SyncSessions]
WHERE status IN ('INTERRUPTED', 'FAILED');

-- Step 6: Verify cleanup results
SELECT
    'After Cleanup' as Status,
    COUNT(*) AS TotalRows,
    COUNT(DISTINCT token_id) AS UniqueTokenIDs,
    COUNT(*) - COUNT(DISTINCT token_id) AS DuplicateRows
FROM [dbo].[TokenRecords];

-- Step 7: Show records by node after cleanup
SELECT
    node_name,
    COUNT(*) as record_count,
    COUNT(DISTINCT token_id) as unique_tokens,
    MIN(synced_at) as first_sync,
    MAX(synced_at) as last_sync
FROM [dbo].[TokenRecords]
GROUP BY node_name
ORDER BY node_name;

-- Step 8: Optional - Complete database reset (UNCOMMENT IF NEEDED)
-- WARNING: This will delete ALL data and start completely fresh
/*
TRUNCATE TABLE [dbo].[TokenRecords];
DELETE FROM [dbo].[ProcessedDatabases];
DELETE FROM [dbo].[SyncSessions];
SELECT 'Database completely reset' as Status;
*/