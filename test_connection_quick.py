#!/usr/bin/env python3
"""
Quick Azure SQL Connection Test
Tests both original and URL-encoded password formats
"""

import pyodbc
import urllib.parse

def test_azure_connection():
    """Test Azure SQL connection with URL encoding"""

    # Original connection string from your config
    original_password = "Hg&ERwR!8mhMv9mD&Mu"
    base_conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=tcp:rauditser.database.windows.net,1433;DATABASE=rauditd;UID=rubix;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

    print("🔍 Testing Azure SQL Database Connection")
    print("=" * 50)

    # Test 1: Original password (likely to fail)
    print("\n1️⃣ Testing with original password...")
    original_conn_str = base_conn_str + f"PWD={original_password};"

    try:
        conn = pyodbc.connect(original_conn_str)
        print("✅ Original password works!")
        conn.close()
        return original_conn_str
    except Exception as e:
        print(f"❌ Original password failed: {e}")

    # Test 2: URL-encoded password
    print("\n2️⃣ Testing with URL-encoded password...")
    # URL encode the special characters
    encoded_password = original_password.replace("&", "%26").replace("!", "%21")
    encoded_conn_str = base_conn_str + f"PWD={encoded_password};"

    try:
        conn = pyodbc.connect(encoded_conn_str)
        print("✅ URL-encoded password works!")
        print(f"Working connection string: {encoded_conn_str}")
        conn.close()
        return encoded_conn_str
    except Exception as e:
        print(f"❌ URL-encoded password failed: {e}")

    # Test 3: Fully URL encode the password
    print("\n3️⃣ Testing with fully URL-encoded password...")
    fully_encoded = urllib.parse.quote(original_password, safe='')
    fully_encoded_conn_str = base_conn_str + f"PWD={fully_encoded};"

    try:
        conn = pyodbc.connect(fully_encoded_conn_str)
        print("✅ Fully URL-encoded password works!")
        print(f"Working connection string: {fully_encoded_conn_str}")
        conn.close()
        return fully_encoded_conn_str
    except Exception as e:
        print(f"❌ Fully URL-encoded password failed: {e}")

    # Test 4: Try without special character encoding (sometimes works)
    print("\n4️⃣ Testing basic connection without encoding...")
    try:
        conn = pyodbc.connect(original_conn_str)
        print("✅ Basic connection works!")
        conn.close()
        return original_conn_str
    except Exception as e:
        print(f"❌ Basic connection failed: {e}")

    print("\n❌ All connection attempts failed!")
    print("\n🔧 Troubleshooting suggestions:")
    print("1. Verify ODBC Driver 17 is installed: `odbcinst -q -d`")
    print("2. Check network connectivity to Azure")
    print("3. Verify credentials in Azure portal")
    print("4. Try connecting from Azure portal query editor")

    return None

def update_config_file(working_conn_str):
    """Update the azure_sql_connection.txt with working connection string"""
    if working_conn_str:
        try:
            with open('azure_sql_connection.txt', 'w') as f:
                f.write(working_conn_str)
            print(f"\n✅ Updated azure_sql_connection.txt with working connection string")
        except Exception as e:
            print(f"\n❌ Failed to update config file: {e}")

if __name__ == "__main__":
    working_conn_str = test_azure_connection()

    if working_conn_str:
        print(f"\n🎉 SUCCESS! Working connection string found.")
        response = input("\nUpdate azure_sql_connection.txt with working connection? (y/n): ")
        if response.lower().startswith('y'):
            update_config_file(working_conn_str)
    else:
        print(f"\n💥 FAILED! No working connection found.")