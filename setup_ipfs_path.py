#!/usr/bin/env python3
"""
Setup and test IPFS_PATH environment variable
"""
import os
import subprocess
from pathlib import Path

def find_and_set_ipfs_path():
    """Find the correct .ipfs directory and set IPFS_PATH"""

    print("🔍 Searching for .ipfs directories...")

    # Search locations in order of preference
    search_locations = [
        Path.cwd().parent / '.ipfs',      # /home/cherryrubix/wallets/.ipfs
        Path.cwd() / '.ipfs',             # /home/cherryrubix/wallets/audit-tools/.ipfs
        Path.home() / '.ipfs',            # /home/cherryrubix/.ipfs
        Path('/var/lib/ipfs'),            # System location
        Path('/opt/ipfs/.ipfs'),          # Custom location
    ]

    valid_ipfs_dirs = []

    for location in search_locations:
        if location.exists() and location.is_dir():
            # Check if it's a valid IPFS directory
            indicators = ['config', 'datastore', 'blocks', 'keystore', 'version']
            if any((location / indicator).exists() for indicator in indicators):
                valid_ipfs_dirs.append(str(location))
                print(f"✅ Found valid .ipfs: {location}")
            else:
                print(f"📂 Found directory but not valid IPFS: {location}")
        else:
            print(f"❌ Not found: {location}")

    if not valid_ipfs_dirs:
        print("❌ No valid .ipfs directories found!")
        return None

    # Use the first (highest priority) valid directory
    chosen_ipfs_path = valid_ipfs_dirs[0]

    print(f"\n🎯 Setting IPFS_PATH to: {chosen_ipfs_path}")

    # Set environment variable for current session
    os.environ['IPFS_PATH'] = chosen_ipfs_path

    return chosen_ipfs_path

def test_ipfs_with_path(ipfs_path):
    """Test IPFS commands with the set path"""

    print(f"\n🧪 Testing IPFS with IPFS_PATH={ipfs_path}")

    # Find IPFS binary
    ipfs_binary_locations = [
        Path.cwd().parent / 'ipfs',       # /home/cherryrubix/wallets/ipfs
        Path.cwd() / 'ipfs',              # Local to audit-tools
        Path('/usr/local/bin/ipfs'),      # System install
        Path('/usr/bin/ipfs'),            # System install
        'ipfs'                            # PATH
    ]

    ipfs_cmd = None
    for location in ipfs_binary_locations:
        try:
            if str(location) == 'ipfs':
                test_cmd = 'ipfs'
            else:
                if location.exists():
                    test_cmd = str(location)
                else:
                    continue

            result = subprocess.run([test_cmd, 'version'],
                                  capture_output=True, timeout=5)
            if result.returncode == 0:
                ipfs_cmd = test_cmd
                print(f"✅ Found IPFS binary: {ipfs_cmd}")
                break
        except:
            continue

    if not ipfs_cmd:
        print("❌ No working IPFS binary found!")
        return False

    # Test IPFS commands with the environment
    env = os.environ.copy()
    env['IPFS_PATH'] = ipfs_path

    try:
        # Test IPFS repo stat
        print(f"🔄 Testing: {ipfs_cmd} repo stat")
        result = subprocess.run([ipfs_cmd, 'repo', 'stat'],
                              env=env, capture_output=True,
                              text=True, timeout=10)

        if result.returncode == 0:
            print("✅ IPFS repo stat successful!")
            print(f"   Repo info: {result.stdout.split()[0]} (first line)")
        else:
            print(f"⚠️  IPFS repo stat failed: {result.stderr}")

        # Test IPFS swarm peers
        print(f"🔄 Testing: {ipfs_cmd} swarm peers")
        result = subprocess.run([ipfs_cmd, 'swarm', 'peers'],
                              env=env, capture_output=True,
                              text=True, timeout=10)

        if result.returncode == 0:
            peer_count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
            print(f"✅ IPFS swarm peers: {peer_count} connected")
        else:
            print(f"⚠️  IPFS swarm peers failed: {result.stderr}")

        return True

    except Exception as e:
        print(f"❌ IPFS test failed: {e}")
        return False

def main():
    print("🚀 IPFS_PATH Setup and Test")
    print("=" * 50)

    # Find and set IPFS_PATH
    ipfs_path = find_and_set_ipfs_path()

    if ipfs_path:
        # Test IPFS with the set path
        success = test_ipfs_with_path(ipfs_path)

        if success:
            print(f"\n✅ SUCCESS! IPFS is working with IPFS_PATH={ipfs_path}")
            print(f"\n📋 To use this in your session:")
            print(f"export IPFS_PATH='{ipfs_path}'")
            print(f"\n🚀 Now you can run:")
            print("python3 sync_distributed_tokens.py --clear --force-ipfs")
        else:
            print(f"\n⚠️  IPFS_PATH found but IPFS not working properly")
    else:
        print(f"\n❌ Could not find valid .ipfs directory")

if __name__ == "__main__":
    main()