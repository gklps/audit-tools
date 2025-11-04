#!/usr/bin/env python3
"""
System Checker for Rubix Token Sync
Cross-platform system information, dependency checking, and compatibility validation
"""

import os
import sys
import platform
import subprocess
import psutil
import shutil
import socket
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import json
import requests

@dataclass
class SystemInfo:
    """Container for system information"""
    hostname: str
    platform_system: str
    platform_release: str
    platform_version: str
    architecture: str
    processor: str
    python_version: str
    python_executable: str
    working_directory: str
    total_memory_gb: float
    available_memory_gb: float
    total_disk_gb: float
    available_disk_gb: float
    public_ip: Optional[str]
    local_ip: Optional[str]
    cpu_count: int
    is_admin: bool

@dataclass
class DependencyStatus:
    """Container for dependency status"""
    name: str
    required: bool
    available: bool
    version: Optional[str] = None
    error: Optional[str] = None

class SystemChecker:
    """Cross-platform system checker and dependency validator"""

    def __init__(self):
        self.required_dependencies = [
            "pyodbc",
            "requests",
        ]
        self.optional_dependencies = [
            "pandas",
            "sqlalchemy",
            "python-telegram-bot"
        ]

    def get_system_info(self) -> SystemInfo:
        """Gather comprehensive system information"""

        # Basic platform info
        hostname = platform.node() or "Unknown"
        platform_system = platform.system()
        platform_release = platform.release()
        platform_version = platform.version()
        architecture = platform.machine()
        processor = platform.processor() or "Unknown"

        # Python info
        python_version = sys.version.split()[0]
        python_executable = sys.executable
        working_directory = str(Path.cwd())

        # Memory info
        memory = psutil.virtual_memory()
        total_memory_gb = memory.total / (1024**3)
        available_memory_gb = memory.available / (1024**3)

        # Disk info
        disk = psutil.disk_usage(Path.cwd())
        total_disk_gb = disk.total / (1024**3)
        available_disk_gb = disk.free / (1024**3)

        # Network info
        public_ip = self._get_public_ip()
        local_ip = self._get_local_ip()

        # CPU info
        cpu_count = psutil.cpu_count() or 1

        # Admin privileges
        is_admin = self._check_admin_privileges()

        return SystemInfo(
            hostname=hostname,
            platform_system=platform_system,
            platform_release=platform_release,
            platform_version=platform_version,
            architecture=architecture,
            processor=processor,
            python_version=python_version,
            python_executable=python_executable,
            working_directory=working_directory,
            total_memory_gb=total_memory_gb,
            available_memory_gb=available_memory_gb,
            total_disk_gb=total_disk_gb,
            available_disk_gb=available_disk_gb,
            public_ip=public_ip,
            local_ip=local_ip,
            cpu_count=cpu_count,
            is_admin=is_admin
        )

    def _get_public_ip(self) -> Optional[str]:
        """Get public IP address"""
        try:
            # Try multiple services for reliability
            services = [
                "https://ifconfig.me/ip",
                "https://api.ipify.org",
                "https://checkip.amazonaws.com",
                "https://ipecho.net/plain"
            ]

            for service in services:
                try:
                    response = requests.get(service, timeout=5)
                    if response.status_code == 200:
                        return response.text.strip()
                except:
                    continue

            return None
        except:
            return None

    def _get_local_ip(self) -> Optional[str]:
        """Get local IP address"""
        try:
            # Create a socket and connect to a remote server to get local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except:
            return None

    def _check_admin_privileges(self) -> bool:
        """Check if running with administrator privileges"""
        try:
            if platform.system() == "Windows":
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            else:
                return os.geteuid() == 0
        except:
            return False

    def check_python_compatibility(self) -> Tuple[bool, str]:
        """Check if Python version is compatible"""
        major, minor = sys.version_info[:2]

        if major < 3:
            return False, f"Python 3.x required, found Python {major}.{minor}"

        if major == 3 and minor < 8:
            return False, f"Python 3.8+ required for full compatibility, found Python {major}.{minor}"

        return True, f"Python {major}.{minor} is compatible"

    def check_dependency(self, package_name: str) -> DependencyStatus:
        """Check if a Python package is available"""
        try:
            # Try to import the package
            __import__(package_name.replace('-', '_'))

            # Try to get version
            try:
                import importlib.metadata
                version = importlib.metadata.version(package_name)
            except:
                # Fallback for older Python versions or packages without metadata
                try:
                    module = __import__(package_name.replace('-', '_'))
                    version = getattr(module, '__version__', 'Unknown')
                except:
                    version = 'Available'

            return DependencyStatus(
                name=package_name,
                required=package_name in self.required_dependencies,
                available=True,
                version=version
            )

        except (ImportError, ValueError, Exception) as e:
            # Handle import errors, version incompatibilities, etc.
            error_msg = str(e)
            if "binary incompatibility" in error_msg.lower():
                error_msg = "Version incompatibility detected"

            return DependencyStatus(
                name=package_name,
                required=package_name in self.required_dependencies,
                available=False,
                error=error_msg
            )

    def check_all_dependencies(self) -> Dict[str, DependencyStatus]:
        """Check all required and optional dependencies"""
        results = {}

        all_deps = self.required_dependencies + self.optional_dependencies

        for dep in all_deps:
            results[dep] = self.check_dependency(dep)

        return results

    def check_odbc_drivers(self) -> List[str]:
        """Check available ODBC drivers"""
        available_drivers = []

        try:
            import pyodbc
            drivers = pyodbc.drivers()

            # Look for SQL Server drivers
            sql_server_drivers = [
                driver for driver in drivers
                if 'SQL Server' in driver or 'ODBC Driver' in driver
            ]

            available_drivers.extend(sql_server_drivers)

        except ImportError:
            pass
        except Exception:
            pass

        return available_drivers

    def check_network_connectivity(self) -> Dict[str, bool]:
        """Check network connectivity to required services"""
        endpoints = {
            "internet": "8.8.8.8",
            "azure_sql": "rauditser.database.windows.net",
            "telegram": "api.telegram.org"
        }

        results = {}

        for name, endpoint in endpoints.items():
            try:
                socket.create_connection((endpoint, 443 if name != "internet" else 53), timeout=5)
                results[name] = True
            except:
                results[name] = False

        return results

    def check_disk_space_requirements(self, required_gb: float = 1.0) -> Tuple[bool, str]:
        """Check if sufficient disk space is available"""
        try:
            disk = psutil.disk_usage(Path.cwd())
            available_gb = disk.free / (1024**3)

            if available_gb >= required_gb:
                return True, f"{available_gb:.1f} GB available (requirement: {required_gb} GB)"
            else:
                return False, f"Only {available_gb:.1f} GB available (requirement: {required_gb} GB)"
        except:
            return False, "Unable to check disk space"

    def check_memory_requirements(self, required_gb: float = 2.0) -> Tuple[bool, str]:
        """Check if sufficient memory is available"""
        try:
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)

            if available_gb >= required_gb:
                return True, f"{available_gb:.1f} GB available (requirement: {required_gb} GB)"
            else:
                return False, f"Only {available_gb:.1f} GB available (requirement: {required_gb} GB)"
        except:
            return False, "Unable to check memory"

    def check_ipfs_availability(self, search_paths: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
        """Check if IPFS binary is available"""
        if search_paths is None:
            search_paths = []

        # Add common locations
        common_paths = [
            "ipfs",  # In PATH
            "./ipfs",  # Current directory
            "../ipfs",  # Parent directory
            "/usr/local/bin/ipfs",  # Common Unix location
            "/usr/bin/ipfs",  # System Unix location
            str(Path.home() / "ipfs"),  # User home
            str(Path.home() / "bin" / "ipfs"),  # User bin
        ]

        all_paths = search_paths + common_paths

        for ipfs_path in all_paths:
            try:
                result = subprocess.run([ipfs_path, "version"],
                                      capture_output=True, timeout=5)
                if result.returncode == 0:
                    return True, ipfs_path
            except:
                continue

        return False, None

    def generate_system_report(self) -> Dict[str, Any]:
        """Generate comprehensive system compatibility report"""
        report = {
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "system_info": {},
            "compatibility": {},
            "dependencies": {},
            "network": {},
            "resources": {},
            "recommendations": []
        }

        # System information
        sys_info = self.get_system_info()
        report["system_info"] = {
            "hostname": sys_info.hostname,
            "platform": f"{sys_info.platform_system} {sys_info.platform_release}",
            "architecture": sys_info.architecture,
            "python_version": sys_info.python_version,
            "cpu_count": sys_info.cpu_count,
            "memory_total_gb": round(sys_info.total_memory_gb, 1),
            "memory_available_gb": round(sys_info.available_memory_gb, 1),
            "disk_total_gb": round(sys_info.total_disk_gb, 1),
            "disk_available_gb": round(sys_info.available_disk_gb, 1),
            "public_ip": sys_info.public_ip,
            "local_ip": sys_info.local_ip,
            "is_admin": sys_info.is_admin
        }

        # Compatibility checks
        python_ok, python_msg = self.check_python_compatibility()
        disk_ok, disk_msg = self.check_disk_space_requirements()
        memory_ok, memory_msg = self.check_memory_requirements()

        report["compatibility"] = {
            "python": {"status": python_ok, "message": python_msg},
            "disk_space": {"status": disk_ok, "message": disk_msg},
            "memory": {"status": memory_ok, "message": memory_msg}
        }

        # Dependencies
        deps = self.check_all_dependencies()
        report["dependencies"] = {
            name: {
                "available": dep.available,
                "version": dep.version,
                "required": dep.required,
                "error": dep.error
            }
            for name, dep in deps.items()
        }

        # ODBC drivers
        odbc_drivers = self.check_odbc_drivers()
        report["dependencies"]["odbc_drivers"] = odbc_drivers

        # Network connectivity
        report["network"] = self.check_network_connectivity()

        # IPFS availability
        ipfs_available, ipfs_path = self.check_ipfs_availability()
        report["ipfs"] = {
            "available": ipfs_available,
            "path": ipfs_path
        }

        # Generate recommendations
        recommendations = []

        if not python_ok:
            recommendations.append("Upgrade Python to version 3.8 or higher")

        if not disk_ok:
            recommendations.append("Free up disk space before running sync")

        if not memory_ok:
            recommendations.append("Close other applications to free up memory")

        missing_required = [name for name, dep in deps.items()
                          if dep.required and not dep.available]
        if missing_required:
            recommendations.append(f"Install required packages: {', '.join(missing_required)}")

        if not odbc_drivers:
            recommendations.append("Install Microsoft ODBC Driver for SQL Server")

        if not report["network"]["internet"]:
            recommendations.append("Check internet connection")

        if not report["network"]["azure_sql"]:
            recommendations.append("Check firewall settings for Azure SQL access")

        if not ipfs_available:
            recommendations.append("Install or configure IPFS binary in system PATH")

        report["recommendations"] = recommendations

        return report

    def print_system_report(self, detailed: bool = True):
        """Print formatted system report"""
        report = self.generate_system_report()

        print("🖥️  System Compatibility Report")
        print("=" * 50)

        # System info
        sys_info = report["system_info"]
        print(f"Hostname: {sys_info['hostname']}")
        print(f"Platform: {sys_info['platform']}")
        print(f"Architecture: {sys_info['architecture']}")
        print(f"Python: {sys_info['python_version']}")
        print(f"CPU Cores: {sys_info['cpu_count']}")
        print(f"Memory: {sys_info['memory_available_gb']:.1f} GB available / {sys_info['memory_total_gb']:.1f} GB total")
        print(f"Disk: {sys_info['disk_available_gb']:.1f} GB available / {sys_info['disk_total_gb']:.1f} GB total")

        if sys_info['public_ip']:
            print(f"Public IP: {sys_info['public_ip']}")
        if sys_info['local_ip']:
            print(f"Local IP: {sys_info['local_ip']}")

        print()

        # Compatibility
        print("✅ Compatibility Checks:")
        for check, result in report["compatibility"].items():
            status = "✅" if result["status"] else "❌"
            print(f"   {status} {check.replace('_', ' ').title()}: {result['message']}")
        print()

        # Dependencies
        print("📦 Dependencies:")
        for name, dep in report["dependencies"].items():
            if name == "odbc_drivers":
                if dep:
                    print(f"   ✅ ODBC Drivers: {', '.join(dep)}")
                else:
                    print(f"   ❌ ODBC Drivers: None found")
                continue

            status = "✅" if dep["available"] else "❌"
            required = " (required)" if dep["required"] else " (optional)"
            version = f" v{dep['version']}" if dep["version"] else ""
            print(f"   {status} {name}{version}{required}")
        print()

        # Network
        print("🌐 Network Connectivity:")
        for service, available in report["network"].items():
            status = "✅" if available else "❌"
            print(f"   {status} {service.replace('_', ' ').title()}")
        print()

        # IPFS
        ipfs_info = report["ipfs"]
        ipfs_status = "✅" if ipfs_info["available"] else "❌"
        ipfs_path = f" ({ipfs_info['path']})" if ipfs_info["path"] else ""
        print(f"🗂️  IPFS: {ipfs_status} {'Available' if ipfs_info['available'] else 'Not found'}{ipfs_path}")
        print()

        # Recommendations
        if report["recommendations"]:
            print("💡 Recommendations:")
            for i, rec in enumerate(report["recommendations"], 1):
                print(f"   {i}. {rec}")
            print()

        # Overall status
        critical_issues = [
            not report["compatibility"]["python"]["status"],
            not report["compatibility"]["disk_space"]["status"],
            any(not dep["available"] for dep in report["dependencies"].values()
                if isinstance(dep, dict) and dep.get("required", False))
        ]

        if any(critical_issues):
            print("🚨 Critical issues found - please address before running sync")
        else:
            print("🎉 System is ready for Rubix Token Sync!")

def main():
    """Test the SystemChecker functionality"""
    checker = SystemChecker()

    print("Testing SystemChecker...")
    print()

    # Print full system report
    checker.print_system_report()

if __name__ == "__main__":
    main()