# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Specification File for Rubix Token Sync
Cross-platform executable build configuration
"""

import os
import sys
from pathlib import Path

# Build configuration
block_cipher = None
current_dir = Path('.').absolute()

# Application info
app_name = 'RubixTokenSync'
app_version = '1.0.0'
app_description = 'Rubix Distributed Token Synchronization Tool'
app_author = 'Rubix Network'

# Entry point
main_script = 'rubix_sync_main.py'

# Core Python files to include
core_modules = [
    'rubix_sync_main.py',
    'rubix_launcher.py',
    'config_manager.py',
    'system_checker.py',
    'sync_distributed_tokens.py'
]

# Optional modules (include if present)
optional_modules = [
    'telegram_notifier.py',
    'log_analyzer.py'
]

# Data files to include
data_files = []

# Configuration templates
config_templates = [
    'azure_sql_connection_template.txt',
    'telegram_config_template.json'
]

# Add existing config templates
for template in config_templates:
    template_path = current_dir / template
    if template_path.exists():
        data_files.append((str(template_path), '.'))

# Documentation files
doc_files = [
    'requirements.txt',
    'requirements-minimal.txt'
]

for doc in doc_files:
    doc_path = current_dir / doc
    if doc_path.exists():
        data_files.append((str(doc_path), '.'))

# Test files (include for completeness)
test_files = [
    'test_per_node_ipfs.py',
    'test_ipfs_locks.py',
    'test_ipfs_mapping.py'
]

for test in test_files:
    test_path = current_dir / test
    if test_path.exists():
        data_files.append((str(test_path), 'tests'))

# Hidden imports - packages that PyInstaller might miss
hidden_imports = [
    # Core database dependencies
    'pyodbc',
    'sqlite3',

    # Network and requests
    'requests',
    'requests.adapters',
    'requests.packages',
    'requests.packages.urllib3',

    # System monitoring
    'psutil',
    'psutil._psutil_windows' if sys.platform == 'win32' else 'psutil._psutil_posix',

    # JSON and data handling
    'json',
    'uuid',
    'datetime',
    'threading',
    'multiprocessing',
    'multiprocessing.pool',
    'concurrent.futures',

    # Logging
    'logging',
    'logging.handlers',

    # Optional dependencies (include if available)
    'pandas',
    'sqlalchemy',

    # Telegram (optional)
    'telegram',
    'telegram.ext',

    # Platform specific
    'platform',
    'socket',
    'subprocess',
    'tempfile',
    'stat',
    'shutil',
    'getpass'
]

# Add platform-specific hidden imports
if sys.platform == 'win32':
    hidden_imports.extend([
        'ctypes',
        'ctypes.wintypes',
        'winreg'
    ])
elif sys.platform.startswith('linux'):
    hidden_imports.extend([
        'pwd',
        'grp'
    ])

# Binary dependencies to exclude (let system provide these)
excludes = [
    'matplotlib',
    'scipy',
    'numpy.distutils',
    'setuptools',
    'pkg_resources.py2_warn',
    'PIL',
    'tkinter',
    'tkinter.ttk',
    '_tkinter'
]

# Collect all Python source files
python_sources = []
for module in core_modules:
    module_path = current_dir / module
    if module_path.exists():
        python_sources.append(str(module_path))

for module in optional_modules:
    module_path = current_dir / module
    if module_path.exists():
        python_sources.append(str(module_path))

# Analysis phase - discover all dependencies
a = Analysis(
    [main_script],
    pathex=[str(current_dir)],
    binaries=[],
    datas=data_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove duplicate entries
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Create executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress executable
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Console application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Could add an icon file here
    version=None  # Could add version info here
)

# For debugging - create app bundle on macOS
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name=f'{app_name}.app',
        icon=None,
        bundle_identifier=f'com.rubixnetwork.{app_name.lower()}',
        info_plist={
            'CFBundleDisplayName': app_name,
            'CFBundleVersion': app_version,
            'CFBundleShortVersionString': app_version,
            'NSHighResolutionCapable': True,
            'LSApplicationCategoryType': 'public.app-category.developer-tools',
            'CFBundleDocumentTypes': []
        }
    )