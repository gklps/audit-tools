#!/usr/bin/env python3
"""
Test different Azure SQL connection string formats to find what works
"""
import pyodbc
import sys

def test_connection_format(description, conn_str):
    """Test a specific connection string format"""
    print(f"\n🔄 Testing: {description}")
    print(f"Connection string: {conn_str}")

    try:
        conn = pyodbc.connect(conn_str)
        print("✅ SUCCESS!")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def main():
    print("🧪 Azure SQL Connection Format Testing")
    print("=" * 60)

    server = "tcp:rauditser.database.windows.net,1433"
    database = "rauditd"
    username = "rubix"
    password = "Hg&ERwR!8mhMv9mD&Mu"

    # Test different formats
    formats = [
        # Format 1: Current format with URL encoding
        ("Current format (URL encoded)",
         f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD=Hg%26ERwR%218mhMv9mD%26Mu;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"),

        # Format 2: Original password without encoding
        ("Original password (no encoding)",
         f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"),

        # Format 3: Password in braces
        ("Password in braces",
         f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={{{password}}};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"),

        # Format 4: Quoted password
        ("Quoted password",
         f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD=\"{password}\";Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"),

        # Format 5: Standard SQL Server format
        ("Standard SQL Server format",
         f"DRIVER={{ODBC Driver 17 for SQL Server}};Server={server};Database={database};Uid={username};Pwd={password};Encrypt=yes;TrustServerCertificate=no;"),

        # Format 6: Azure Data Studio style
        ("Azure Data Studio style",
         f"Driver={{ODBC Driver 17 for SQL Server}};Server={server};Database={database};User Id={username};Password={password};Encrypt=True;Connection Timeout=30;"),

        # Format 7: Connection with escaped characters
        ("Escaped special characters",
         f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD=Hg\\&ERwR\\!8mhMv9mD\\&Mu;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"),

        # Format 8: Minimal connection string
        ("Minimal format",
         f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};"),

        # Format 9: Try with SQLCMD auth (like Azure Data Studio)
        ("SQLCMD style authentication",
         f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Authentication=SqlPassword;UID={username};PWD={password};Encrypt=yes;"),

        # Format 10: Try without port in server
        ("Server without port",
         f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER=rauditser.database.windows.net;DATABASE={database};UID={username};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"),
    ]

    successful_formats = []

    for description, conn_str in formats:
        if test_connection_format(description, conn_str):
            successful_formats.append((description, conn_str))

    print("\n" + "=" * 60)
    print("📊 RESULTS SUMMARY")
    print("=" * 60)

    if successful_formats:
        print(f"✅ {len(successful_formats)} format(s) worked:")
        for i, (desc, conn_str) in enumerate(successful_formats, 1):
            print(f"\n{i}. {desc}")
            print(f"   {conn_str}")

            # Save the first working format to config file
            if i == 1:
                with open('azure_sql_connection.txt', 'w') as f:
                    f.write(conn_str)
                print(f"   ✅ Saved to azure_sql_connection.txt")
    else:
        print("❌ No formats worked. Possible issues:")
        print("   • Check if user 'rubix' exists in Azure SQL Database")
        print("   • Verify password is correct")
        print("   • Check if database 'rauditd' exists")
        print("   • Verify firewall allows connections")

        # Provide troubleshooting
        print("\n🔧 Troubleshooting steps:")
        print("1. Try connecting to master database:")
        print(f"   DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE=master;UID={username};PWD={password};")
        print("2. Check available drivers:")
        print("   python3 -c \"import pyodbc; print(pyodbc.drivers())\"")
        print("3. Test basic connectivity:")
        print(f"   telnet rauditser.database.windows.net 1433")

if __name__ == "__main__":
    main()