# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Windows 10/11 - Fully Self-Contained

import os
import sys
from PyInstaller.utils.hooks import collect_all, collect_data_files

puresnmp_datas, puresnmp_binaries, puresnmp_hiddenimports = collect_all('puresnmp')
x690_datas, x690_binaries, x690_hiddenimports = collect_all('x690')
plugins_datas, plugins_binaries, plugins_hiddenimports = collect_all('puresnmp_plugins')

# Collect net-snmp binaries if they exist in tools/ directory
binaries = []
tools_dir = os.path.join(SPECPATH, 'tools')
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
    binaries=binaries + puresnmp_binaries + x690_binaries + plugins_binaries,
    datas=puresnmp_datas + x690_datas + plugins_datas,
    hiddenimports=puresnmp_hiddenimports + x690_hiddenimports + plugins_hiddenimports + [
        'matplotlib.backends.backend_tkagg',
        'matplotlib.backends.backend_agg',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'asyncio',
        'asyncio.selector_events',
        'puresnmp_plugins',
        'puresnmp_plugins.mpm',
        'puresnmp_plugins.mpm.v1',
        'puresnmp_plugins.mpm.v2c',
        'puresnmp_plugins.mpm.v2x',
        'puresnmp_plugins.mpm.v3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    upx=False,
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
