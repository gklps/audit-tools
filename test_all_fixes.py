#!/usr/bin/env python3
"""
Test all the fixes before running the full sync
"""
import os
import sys
from pathlib import Path

# Test 1: IPFS binary detection
print("🧪 Test 1: IPFS Binary Detection")
print("=" * 40)
try:
    # Import our IPFS detection
    sys.path.insert(0, '.')
    from sync_distributed_tokens import find_ipfs_binary

    ipfs_cmd = find_ipfs_binary()
    print(f"IPFS Command: {ipfs_cmd}")

    # Test if it works
    import subprocess
    try:
        result = subprocess.run([ipfs_cmd, 'version'], capture_output=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ IPFS binary works: {result.stdout.decode().strip()}")
        else:
            print(f"❌ IPFS binary failed: {result.stderr.decode()}")
    except Exception as e:
        print(f"❌ IPFS test error: {e}")

except Exception as e:
    print(f"❌ IPFS binary detection failed: {e}")

print()

# Test 2: .ipfs directory detection
print("🧪 Test 2: .ipfs Directory Detection")
print("=" * 40)
try:
    from sync_distributed_tokens import find_ipfs_directory

    # Test with realistic database paths from the actual structure
    test_paths = [
        str(Path.cwd() / "node123" / "Rubix" / "rubix.db"),  # Simulated node in audit-tools
        "/home/cherryrubix/wallets/node456/Rubix/rubix.db",   # Real structure
    ]

    # Also check if .ipfs exists in expected locations
    possible_ipfs_locations = [
        "/home/cherryrubix/wallets/.ipfs",
        str(Path.cwd().parent / ".ipfs"),
        str(Path.cwd() / ".ipfs")
    ]

    print("🔍 Checking for .ipfs directories:")
    for location in possible_ipfs_locations:
        if Path(location).exists():
            print(f"✅ Found .ipfs at: {location}")
        else:
            print(f"❌ No .ipfs at: {location}")

    for test_path in test_paths:
        ipfs_dir = find_ipfs_directory(test_path)
        if ipfs_dir:
            print(f"✅ Found .ipfs for {test_path}: {ipfs_dir}")
        else:
            print(f"⚠️  No .ipfs found for {test_path}")

except Exception as e:
    print(f"❌ .ipfs directory detection failed: {e}")

print()

# Test 3: SQLite schema compatibility
print("🧪 Test 3: SQLite Schema Compatibility")
print("=" * 40)
try:
    from sync_distributed_tokens import safe_str, safe_timestamp

    # Test safe_str with "c not found"
    test_values = ["normal_value", "c not found", None, "", "  "]
    for val in test_values:
        result = safe_str(val)
        print(f"safe_str('{val}') = '{result}'")

    print()

    # Test safe_timestamp with "c not found"
    test_timestamps = ["2023-01-01 12:00:00", "c not found", None, "", 1672574400]
    for val in test_timestamps:
        result = safe_timestamp(val)
        print(f"safe_timestamp('{val}') = '{result}'")

except Exception as e:
    print(f"❌ Schema compatibility test failed: {e}")

print()

# Test 4: Azure SQL connection
print("🧪 Test 4: Azure SQL Connection")
print("=" * 40)
try:
    from sync_distributed_tokens import get_azure_sql_connection_string

    conn_str = get_azure_sql_connection_string()
    if conn_str:
        print("✅ Connection string loaded successfully")
        # Test basic connection
        import pyodbc
        try:
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            print(f"✅ Azure SQL connection works: {result[0]}")
            conn.close()
        except Exception as e:
            print(f"❌ Azure SQL connection failed: {e}")
    else:
        print("❌ Could not load connection string")

except Exception as e:
    print(f"❌ Azure SQL test failed: {e}")

print()

# Test 5: Command line arguments
print("🧪 Test 5: Command Line Arguments")
print("=" * 40)
print("Available options:")
print("  python3 sync_distributed_tokens.py --clear     # Clear all records")
print("  python3 sync_distributed_tokens.py --force-ipfs # Force IPFS fetch")
print("  python3 sync_distributed_tokens.py --clear --force-ipfs # Both")

print()
print("🎯 All tests completed!")
print("Ready to run: python3 sync_distributed_tokens.py --clear --force-ipfs")