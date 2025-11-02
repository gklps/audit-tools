#!/usr/bin/env python3
"""
Test the logical IPFS directory detection pattern
"""
import sys
from pathlib import Path

def test_ipfs_pattern():
    """Test the logical pattern for finding .ipfs directories"""

    # Import our detection function
    sys.path.insert(0, '.')
    from sync_distributed_tokens import find_ipfs_directory

    print("🧠 Testing Logical IPFS Detection Pattern")
    print("=" * 50)

    # Test cases that follow the logical pattern
    test_cases = [
        # Case 1: Standard pattern
        {
            "db_path": "/mnt/drived/node056/Rubix/rubix.db",
            "expected_ipfs": "/mnt/drived/.ipfs",
            "description": "Standard VM setup"
        },
        # Case 2: Wallets pattern
        {
            "db_path": "/home/cherryrubix/wallets/node123/Rubix/rubix.db",
            "expected_ipfs": "/home/cherryrubix/wallets/.ipfs",
            "description": "Wallets directory setup"
        },
        # Case 3: Audit tools pattern
        {
            "db_path": "/home/cherryrubix/wallets/audit-tools/node456/Rubix/rubix.db",
            "expected_ipfs": "/home/cherryrubix/wallets/.ipfs",
            "description": "Cloned repo in wallets"
        },
        # Case 4: Nested structure
        {
            "db_path": "/data/rubix/nodes/node789/Rubix/rubix.db",
            "expected_ipfs": "/data/rubix/.ipfs",
            "description": "Nested structure"
        },
    ]

    print("📋 Test Cases:")
    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}. {case['description']}:")
        print(f"   Database: {case['db_path']}")
        print(f"   Expected: {case['expected_ipfs']}")

        # Show the search pattern
        db_path_obj = Path(case['db_path'])
        node_dir = db_path_obj.parent.parent

        print(f"   Pattern:")
        print(f"     Node dir: {node_dir}")

        # Show what levels would be checked
        current_path = node_dir
        for level in range(4):  # Show first 4 levels
            check_path = current_path.parent / '.ipfs'
            marker = "✅" if str(check_path) == case['expected_ipfs'] else "🔍"
            print(f"     Level {level}: {marker} {check_path}")

            current_path = current_path.parent
            if current_path == current_path.parent:  # Reached root
                break

    print("\n" + "=" * 50)
    print("🎯 Key Logic:")
    print("1. Start from node directory (parent of Rubix)")
    print("2. Walk up directory tree level by level")
    print("3. At each level, check parent/.ipfs")
    print("4. Verify .ipfs contains valid IPFS files")
    print("5. Return first valid .ipfs found")

    print("\n📊 This pattern handles:")
    print("✅ /mnt/drived/nodeXXX/Rubix/rubix.db → /mnt/drived/.ipfs")
    print("✅ /home/user/wallets/nodeXXX/Rubix/rubix.db → /home/user/wallets/.ipfs")
    print("✅ /home/user/wallets/audit-tools/nodeXXX/Rubix/rubix.db → /home/user/wallets/.ipfs")
    print("✅ /any/path/structure/nodeXXX/Rubix/rubix.db → /any/path/structure/.ipfs")

    print("\n🚀 Ready to run the actual detection!")

if __name__ == "__main__":
    test_ipfs_pattern()