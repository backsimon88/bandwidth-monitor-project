# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Windows 10/11 - Fully Self-Contained

import os
import sys

# Collect net-snmp binaries if they exist in tools/ directory
binaries = []
tools_dir = os.path.join(os.path.dirname(__file__), 'tools')
if os.path.exists(tools_dir):
    # If tools are bundled locally, include them
    for tool in ['snmpget.exe', 'snmpwalk.exe', 'snmpcmd.exe']:
        tool_path = os.path.join(tools_dir, tool)
        if os.path.exists(tool_path):
            binaries.append((tool_path, 'tools'))
else:
    # If system-wide net-snmp is available, bundle it
    try:
        import shutil
        snmp_path = shutil.which('snmpget')
        if snmp_path:
            snmp_dir = os.path.dirname(snmp_path)
            for tool in ['snmpget.exe', 'snmpwalk.exe', 'snmpcmd.exe']:
                full_path = os.path.join(snmp_dir, tool)
                if os.path.exists(full_path):
                    binaries.append((full_path, 'tools'))
    except:
        pass

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='BandwidthMonitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
