#!/usr/bin/env python3
"""
Helper script to bundle net-snmp tools for Windows standalone build
Run this on Windows after installing net-snmp tools
"""

import os
import shutil
import sys
import platform

def create_tools_directory():
    """Create tools directory and copy SNMP binaries"""
    
    if platform.system() != "Windows":
        print("❌ This script must be run on Windows")
        sys.exit(1)
    
    # Create tools directory
    tools_dir = os.path.join(os.path.dirname(__file__), 'tools')
    os.makedirs(tools_dir, exist_ok=True)
    print(f"📁 Tools directory: {tools_dir}")
    
    # Common locations for net-snmp on Windows
    possible_locations = [
        r"C:\Program Files\Net-SNMP\bin",
        r"C:\Program Files (x86)\Net-SNMP\bin",
        r"C:\net-snmp\bin",
        r"C:\usr\bin",
    ]
    
    # Try to find snmpget
    snmpget_found = False
    snmpwalk_found = False
    
    for location in possible_locations:
        snmpget = os.path.join(location, "snmpget.exe")
        snmpwalk = os.path.join(location, "snmpwalk.exe")
        
        if os.path.exists(snmpget):
            try:
                shutil.copy2(snmpget, os.path.join(tools_dir, "snmpget.exe"))
                print(f"✅ Copied snmpget from {location}")
                snmpget_found = True
            except Exception as e:
                print(f"⚠️  Failed to copy snmpget: {e}")
        
        if os.path.exists(snmpwalk):
            try:
                shutil.copy2(snmpwalk, os.path.join(tools_dir, "snmpwalk.exe"))
                print(f"✅ Copied snmpwalk from {location}")
                snmpwalk_found = True
            except Exception as e:
                print(f"⚠️  Failed to copy snmpwalk: {e}")
        
        if snmpget_found and snmpwalk_found:
            break
    
    # Try using 'where' command if not found
    if not snmpget_found:
        try:
            snmpget_path = shutil.which("snmpget.exe") or shutil.which("snmpget")
            if snmpget_path:
                shutil.copy2(snmpget_path, os.path.join(tools_dir, "snmpget.exe"))
                print(f"✅ Copied snmpget from {snmpget_path}")
                snmpget_found = True
        except:
            pass
    
    if not snmpwalk_found:
        try:
            snmpwalk_path = shutil.which("snmpwalk.exe") or shutil.which("snmpwalk")
            if snmpwalk_path:
                shutil.copy2(snmpwalk_path, os.path.join(tools_dir, "snmpwalk.exe"))
                print(f"✅ Copied snmpwalk from {snmpwalk_path}")
                snmpwalk_found = True
        except:
            pass
    
    if not snmpget_found or not snmpwalk_found:
        print("\n⚠️  Could not find all SNMP tools")
        print("Please ensure net-snmp is installed:")
        print("  1. Via Chocolatey: choco install net-snmp")
        print("  2. Or download from: http://www.snmp.com/")
        print("\nThen either:")
        print("  A. Add net-snmp bin folder to PATH and try again")
        print("  B. Manually copy snmpget.exe and snmpwalk.exe to:", tools_dir)
        return False
    
    print("\n✅ All SNMP tools bundled successfully!")
    print(f"   Tools location: {tools_dir}")
    print("\nNow you can build the standalone app:")
    print("  pyinstaller BandwidthMonitor_Windows.spec -y")
    
    return True

if __name__ == "__main__":
    create_tools_directory()
