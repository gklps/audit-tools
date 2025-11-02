#!/usr/bin/env python3
"""
Test Azure SQL Database operations step by step
"""
import sys
import os

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False
    print("❌ pyodbc not available. Run: pip3 install pyodbc")
    sys.exit(1)

def load_connection_string():
    """Load connection string from config file"""
    if not os.path.exists('azure_sql_connection.txt'):
        print("❌ azure_sql_connection.txt not found")
        print("📋 Create it with:")
        print('echo "DRIVER={ODBC Driver 17 for SQL Server};SERVER=tcp:rauditser.database.windows.net,1433;DATABASE=rauditd;UID=rubix;PWD=YOUR_PASSWORD;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;" > azure_sql_connection.txt')
        return None

    with open('azure_sql_connection.txt', 'r') as f:
        conn_str = f.read().strip()

    if '{your_password}' in conn_str:
        print("❌ Password placeholder still in config file")
        return None

    return conn_str

def test_basic_connection():
    """Test basic database connection"""
    print("🔄 Testing basic database connection...")

    conn_str = load_connection_string()
    if not conn_str:
        return False

    try:
        conn = pyodbc.connect(conn_str)
        print("✅ Database connection successful!")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_query_permissions():
    """Test basic query permissions"""
    print("🔄 Testing query permissions...")

    conn_str = load_connection_string()
    if not conn_str:
        return False

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Test basic SELECT
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        print(f"✅ Basic query successful: {result[0]}")

        # Test database info
        cursor.execute("SELECT DB_NAME() as current_db")
        result = cursor.fetchone()
        print(f"✅ Current database: {result[0]}")

        # Test user info
        cursor.execute("SELECT USER_NAME() as current_user")
        result = cursor.fetchone()
        print(f"✅ Current user: {result[0]}")

        conn.close()
        return True
    except Exception as e:
        print(f"❌ Query test failed: {e}")
        return False

def test_table_permissions():
    """Test table creation and operations"""
    print("🔄 Testing table creation permissions...")

    conn_str = load_connection_string()
    if not conn_str:
        return False

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Try to create a test table
        test_table_sql = """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='test_table' AND xtype='U')
        CREATE TABLE test_table (
            id INT IDENTITY(1,1) PRIMARY KEY,
            test_data NVARCHAR(50),
            created_at DATETIME2 DEFAULT GETDATE()
        )
        """

        cursor.execute(test_table_sql)
        print("✅ Test table creation successful!")

        # Test INSERT
        cursor.execute("INSERT INTO test_table (test_data) VALUES (?)", "test_value")
        conn.commit()
        print("✅ Insert operation successful!")

        # Test SELECT
        cursor.execute("SELECT * FROM test_table")
        rows = cursor.fetchall()
        print(f"✅ Select operation successful! Found {len(rows)} rows")

        # Test UPDATE
        cursor.execute("UPDATE test_table SET test_data = ? WHERE id = 1", "updated_value")
        conn.commit()
        print("✅ Update operation successful!")

        # Test DELETE
        cursor.execute("DELETE FROM test_table WHERE id = 1")
        conn.commit()
        print("✅ Delete operation successful!")

        # Clean up - drop test table
        cursor.execute("DROP TABLE test_table")
        conn.commit()
        print("✅ Drop table successful!")

        conn.close()
        return True
    except Exception as e:
        print(f"❌ Table operations failed: {e}")
        return False

def test_token_table_creation():
    """Test creating the actual TokenRecords table"""
    print("🔄 Testing TokenRecords table creation...")

    conn_str = load_connection_string()
    if not conn_str:
        return False

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Create TokenRecords table (same as in the main app)
        create_table_sql = """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='TokenRecords' AND xtype='U')
        CREATE TABLE TokenRecords (
            id INT IDENTITY(1,1) PRIMARY KEY,
            source_ip NVARCHAR(45) NOT NULL,
            node_name NVARCHAR(255) NOT NULL,
            did NVARCHAR(500),
            token_id NVARCHAR(500),
            ipfs_data NTEXT,
            ipfs_fetched BIT DEFAULT 0,
            db_path NVARCHAR(1000) NOT NULL,
            synced_at DATETIME2 DEFAULT GETDATE(),
            created_at DATETIME2 DEFAULT GETDATE(),
            updated_at DATETIME2 DEFAULT GETDATE()
        )
        """

        cursor.execute(create_table_sql)
        conn.commit()
        print("✅ TokenRecords table created successfully!")

        # Create indexes
        indexes = [
            "CREATE NONCLUSTERED INDEX idx_token_id ON TokenRecords(token_id)",
            "CREATE NONCLUSTERED INDEX idx_node_name ON TokenRecords(node_name)",
            "CREATE NONCLUSTERED INDEX idx_source_ip ON TokenRecords(source_ip)",
            "CREATE NONCLUSTERED INDEX idx_synced_at ON TokenRecords(synced_at)",
            "CREATE NONCLUSTERED INDEX idx_ipfs_fetched ON TokenRecords(ipfs_fetched)",
            "CREATE NONCLUSTERED INDEX idx_did ON TokenRecords(did)"
        ]

        for idx_sql in indexes:
            try:
                cursor.execute(idx_sql)
                conn.commit()
                print(f"✅ Index created: {idx_sql.split()[2]}")
            except Exception as e:
                if "already exists" in str(e) or "duplicate" in str(e).lower():
                    print(f"ℹ️  Index already exists: {idx_sql.split()[2]}")
                else:
                    print(f"⚠️  Index creation warning: {e}")

        # Test inserting a sample record
        sample_insert = """
        INSERT INTO TokenRecords (source_ip, node_name, did, token_id, ipfs_data, ipfs_fetched, db_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        cursor.execute(sample_insert,
                      "127.0.0.1",
                      "test-node",
                      "test-did",
                      "test-token-id",
                      "test-ipfs-data",
                      1,
                      "/test/path")
        conn.commit()
        print("✅ Sample record inserted successfully!")

        # Test querying the table
        cursor.execute("SELECT COUNT(*) FROM TokenRecords")
        count = cursor.fetchone()[0]
        print(f"✅ TokenRecords table query successful! Records: {count}")

        # Clean up test record
        cursor.execute("DELETE FROM TokenRecords WHERE node_name = 'test-node'")
        conn.commit()
        print("✅ Test record cleaned up!")

        conn.close()
        return True
    except Exception as e:
        print(f"❌ TokenRecords table test failed: {e}")
        return False

def main():
    """Run all database tests"""
    print("🧪 Azure SQL Database Operations Test")
    print("=" * 60)

    tests = [
        ("Basic Connection", test_basic_connection),
        ("Query Permissions", test_query_permissions),
        ("Table Operations", test_table_permissions),
        ("TokenRecords Table", test_token_table_creation)
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        success = test_func()
        results.append((test_name, success))
        print("")

    print("=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if not success:
            all_passed = False

    if all_passed:
        print("\n🎉 All tests passed! Azure SQL Database is ready for sync operations.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())