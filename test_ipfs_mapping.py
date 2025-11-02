#!/usr/bin/env python3
"""
Test the new IPFS path mapping functionality
"""
import sys
from pathlib import Path

def test_ipfs_mapping():
    """Test the IPFS mapping functionality"""

    print("🗂️ Testing IPFS Path Mapping")
    print("=" * 50)

    # Import our functions
    sys.path.insert(0, '.')
    from sync_distributed_tokens import find_rubix_databases, build_ipfs_path_mapping

    print("🔍 Step 1: Finding all rubix.db files...")
    try:
        # Search for databases (adjust path as needed)
        search_path = '..'  # Search in parent directory
        databases = find_rubix_databases(search_path)

        print(f"📊 Found {len(databases)} database files")

        if len(databases) > 10:
            print("   Showing first 10:")
            for i, (db_path, modified) in enumerate(databases[:10]):
                node_name = Path(db_path).parent.parent.name
                print(f"   {i+1:3d}. {node_name}: {db_path}")
            print(f"   ... and {len(databases) - 10} more")
        else:
            for i, (db_path, modified) in enumerate(databases):
                node_name = Path(db_path).parent.parent.name
                print(f"   {i+1:3d}. {node_name}: {db_path}")

    except Exception as e:
        print(f"❌ Error finding databases: {e}")
        return False

    if not databases:
        print("❌ No databases found to test mapping")
        return False

    print(f"\n🗂️ Step 2: Building IPFS path mapping...")
    try:
        ipfs_mapping = build_ipfs_path_mapping(databases)

        print(f"\n📊 Mapping Results:")
        valid_paths = sum(1 for path in ipfs_mapping.values() if path is not None)
        total_paths = len(ipfs_mapping)

        print(f"   Total databases: {total_paths}")
        print(f"   Valid .ipfs paths: {valid_paths}")
        print(f"   Missing .ipfs paths: {total_paths - valid_paths}")

        # Show unique .ipfs directories
        unique_ipfs_dirs = set(path for path in ipfs_mapping.values() if path is not None)
        print(f"   Unique .ipfs directories: {len(unique_ipfs_dirs)}")

        for ipfs_dir in sorted(unique_ipfs_dirs):
            node_count = sum(1 for path in ipfs_mapping.values() if path == ipfs_dir)
            print(f"     {ipfs_dir} (used by {node_count} nodes)")

        # Show examples of successful mappings
        print(f"\n🎯 Example Mappings:")
        examples = 0
        for db_path, ipfs_path in ipfs_mapping.items():
            if ipfs_path and examples < 5:
                node_name = Path(db_path).parent.parent.name
                print(f"   {node_name}:")
                print(f"     DB:   {db_path}")
                print(f"     IPFS: {ipfs_path}")
                examples += 1

        # Show examples of missing mappings
        missing_examples = [(db, ipfs) for db, ipfs in ipfs_mapping.items() if ipfs is None]
        if missing_examples:
            print(f"\n⚠️  Examples with Missing .ipfs:")
            for i, (db_path, _) in enumerate(missing_examples[:3]):
                node_name = Path(db_path).parent.parent.name
                print(f"   {node_name}: {db_path}")

        return True

    except Exception as e:
        print(f"❌ Error building IPFS mapping: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    success = test_ipfs_mapping()

    print("\n" + "=" * 50)
    if success:
        print("✅ IPFS Mapping Test PASSED!")
        print("\n🎯 Benefits of pre-mapping:")
        print("   • Faster processing (no repeated .ipfs discovery)")
        print("   • Clear visibility of IPFS availability")
        print("   • Better error handling for missing .ipfs directories")
        print("   • Detailed statistics and reporting")
        print("\n🚀 Ready for production sync!")
    else:
        print("❌ IPFS Mapping Test FAILED!")

if __name__ == "__main__":
    main()