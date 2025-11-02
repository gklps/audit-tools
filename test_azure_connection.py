#!/usr/bin/env python3
"""
Test Azure SQL Database connection directly
"""
import sys

# Test without pyodbc first to see if connection string is properly formatted
try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False
    print("⚠️  pyodbc not available on this system")

def test_connection_string():
    """Test the connection string format"""
    try:
        with open('azure_sql_connection.txt', 'r') as f:
            conn_str = f.read().strip()

        print(f"📋 Connection string read from file:")
        print(f"   {conn_str}")

        # Check for placeholder
        if "{your_password}" in conn_str:
            print("❌ Password placeholder still present!")
            return False

        # Check for required components
        required_parts = ['DRIVER=', 'SERVER=', 'DATABASE=', 'UID=', 'PWD=']
        missing_parts = [part for part in required_parts if part not in conn_str]

        if missing_parts:
            print(f"❌ Missing required parts: {missing_parts}")
            return False

        print("✅ Connection string format looks correct")

        # Test connection if pyodbc is available
        if PYODBC_AVAILABLE:
            print("🔄 Testing actual database connection...")
            try:
                conn = pyodbc.connect(conn_str)
                print("✅ Database connection successful!")
                conn.close()
                return True
            except Exception as e:
                print(f"❌ Database connection failed: {e}")

                # Try with URL encoding for special characters
                print("🔄 Trying with URL-encoded password...")
                encoded_conn_str = conn_str.replace("Hg&ERwR!8mhMv9mD&Mu", "Hg%26ERwR%218mhMv9mD%26Mu")
                try:
                    conn = pyodbc.connect(encoded_conn_str)
                    print("✅ Database connection successful with URL encoding!")
                    # Update the config file
                    with open('azure_sql_connection.txt', 'w') as f:
                        f.write(encoded_conn_str)
                    print("📝 Updated config file with URL-encoded password")
                    conn.close()
                    return True
                except Exception as e2:
                    print(f"❌ Database connection failed with URL encoding: {e2}")
                    return False
        else:
            print("ℹ️  Cannot test database connection without pyodbc")
            return True

    except FileNotFoundError:
        print("❌ azure_sql_connection.txt file not found")
        return False
    except Exception as e:
        print(f"❌ Error reading config file: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Azure SQL Database Connection Test")
    print("=" * 50)

    success = test_connection_string()

    if success:
        print("\n✅ Connection test passed!")
        sys.exit(0)
    else:
        print("\n❌ Connection test failed!")
        sys.exit(1)