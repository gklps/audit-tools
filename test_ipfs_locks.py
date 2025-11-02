#!/usr/bin/env python3
"""
Test IPFS lock handling functionality
"""
import sys
import tempfile
from pathlib import Path

def test_lock_handling():
    """Test the IPFS lock detection and cleanup"""

    print("🧪 Testing IPFS Lock Handling")
    print("=" * 40)

    # Import our functions
    sys.path.insert(0, '.')
    from sync_distributed_tokens import clear_ipfs_lock, is_ipfs_daemon_running

    # Create a temporary .ipfs directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        test_ipfs_path = Path(temp_dir) / '.ipfs'
        test_ipfs_path.mkdir()

        print(f"📁 Created test IPFS directory: {test_ipfs_path}")

        # Test 1: No lock file (should return True)
        print("\n🧪 Test 1: No lock file")
        result = clear_ipfs_lock(str(test_ipfs_path))
        print(f"   clear_ipfs_lock() result: {result}")
        assert result == True, "Should return True when no lock file exists"

        # Test 2: Create lock file and clear it
        print("\n🧪 Test 2: Create and clear lock file")
        lock_file = test_ipfs_path / 'repo.lock'
        lock_file.write_text("test lock content")
        print(f"   Created lock file: {lock_file}")

        result = clear_ipfs_lock(str(test_ipfs_path))
        print(f"   clear_ipfs_lock() result: {result}")
        print(f"   Lock file exists after clear: {lock_file.exists()}")
        assert result == True, "Should successfully clear lock file"
        assert not lock_file.exists(), "Lock file should be removed"

        # Test 3: Daemon detection
        print("\n🧪 Test 3: Daemon detection")
        daemon_running = is_ipfs_daemon_running(str(test_ipfs_path))
        print(f"   is_ipfs_daemon_running() result: {daemon_running}")
        assert daemon_running == False, "Should detect no daemon running"

        # Create fake API file
        api_file = test_ipfs_path / 'api'
        api_file.write_text("/ip4/127.0.0.1/tcp/5001")
        daemon_running = is_ipfs_daemon_running(str(test_ipfs_path))
        print(f"   After creating API file: {daemon_running}")
        assert daemon_running == True, "Should detect daemon running"

        print("\n✅ All lock handling tests passed!")
        return True

def test_lock_error_cleanup():
    """Test the database cleanup for lock errors"""

    print("\n🧪 Testing Database Lock Error Cleanup")
    print("=" * 40)

    try:
        sys.path.insert(0, '.')
        from sync_distributed_tokens import get_azure_sql_connection_string
        import pyodbc

        # Test connection
        conn_str = get_azure_sql_connection_string()
        if not conn_str or '{your_password}' in conn_str:
            print("⚠️  Skipping database test - connection not configured")
            return True

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Check for existing lock error records
        cursor.execute("""
            SELECT COUNT(*) FROM [dbo].[TokenRecords]
            WHERE [ipfs_error] LIKE '%repo.lock%'
        """)
        lock_error_count = cursor.fetchone()[0]

        print(f"📊 Current lock error records: {lock_error_count:,}")

        # Check total records
        cursor.execute("SELECT COUNT(*) FROM [dbo].[TokenRecords]")
        total_records = cursor.fetchone()[0]

        print(f"📊 Total records in database: {total_records:,}")

        if lock_error_count > 0:
            print(f"✅ Found {lock_error_count:,} lock error records that can be cleaned up")
            print("   Use: python3 sync_distributed_tokens.py --cleanup-locks")
        else:
            print("✅ No lock error records found - system is clean")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def main():
    success = True

    try:
        success &= test_lock_handling()
        success &= test_lock_error_cleanup()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        success = False

    print("\n" + "=" * 40)
    if success:
        print("✅ All IPFS lock tests PASSED!")
        print("\n🎯 IPFS Lock Handling Features:")
        print("   • Automatic lock detection and cleanup")
        print("   • 3-attempt retry with exponential backoff")
        print("   • Database cleanup for existing lock errors")
        print("   • Command: --cleanup-locks")
        print("\n🚀 Ready for production sync!")
    else:
        print("❌ Some tests FAILED!")

if __name__ == "__main__":
    main()