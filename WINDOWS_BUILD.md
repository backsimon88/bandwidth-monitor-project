# Building BandwidthMonitor for Windows 10/11

This guide explains how to build the Windows executable for BandwidthMonitor.

## Two Build Options

### ✅ Option 1: Fully Self-Contained (Recommended)
**Single executable with everything bundled inside - no installation needed**

### Option 2: Standard Build
**Requires net-snmp installation separately**

---

## Option 1: Fully Self-Contained Build (Just Double-Click!)

### Prerequisites

1. **Python 3.10+** - Download from https://www.python.org/
   - ✅ Check "Add Python to PATH" during installation
   - ✅ Check "Install pip" during installation

2. **Net-SNMP for Windows** - Download from http://www.snmp.com/
   - Or install via Chocolatey: `choco install net-snmp`

### Setup Instructions

#### Step 1: Clone/Download the Project
```cmd
git clone <repository-url>
cd bandwidth-monitor-project
```

#### Step 2: Create Virtual Environment
```cmd
python -m venv venv
venv\Scripts\activate
```

You should see `(venv)` in your command prompt.

#### Step 3: Install Dependencies
```cmd
pip install -r requirements.txt
pip install pyinstaller
```

#### Step 4: Bundle SNMP Tools
```cmd
python bundle_windows_snmp.py
```

This script will automatically find and copy net-snmp tools into the `tools/` directory.

**Expected output:**
```
✅ Copied snmpget from C:\Program Files\Net-SNMP\bin
✅ Copied snmpwalk from C:\Program Files\Net-SNMP\bin
✅ All SNMP tools bundled successfully!
```

#### Step 5: Build the Self-Contained Executable
```cmd
pyinstaller BandwidthMonitor_Windows.spec -y
```

The build process will:
- Bundle Python interpreter
- Bundle all dependencies (matplotlib, pysnmp, etc.)
- Bundle net-snmp tools (snmpget, snmpwalk)
- Create a single standalone executable

**Result:** `dist/BandwidthMonitor.exe`

#### Step 6: Test the App
Simply run:
```cmd
dist\BandwidthMonitor.exe
```

✅ No installation needed - it just works!

#### Step 7: Deploy
- Copy `dist/BandwidthMonitor.exe` anywhere (Desktop, Program Files, USB drive, etc.)
- It will work on any Windows 10/11 machine without any setup

---

## Option 2: Standard Build (Requires User to Install SNMP Tools)

### Setup Instructions

#### Step 1-3: Same as Above
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
```

#### Step 4: Build the Executable
```cmd
pyinstaller BandwidthMonitor_Windows.spec -y
```

**Result:** `dist/BandwidthMonitor.exe`

#### Step 5: Deploy with Instructions
The user needs to:
1. Install net-snmp (via Chocolatey: `choco install net-snmp`)
2. Run `BandwidthMonitor.exe`

---

## Using the App

### First Time Setup (Self-Contained Build)
1. Double-click `BandwidthMonitor.exe`
2. Add device IP (e.g., 192.168.1.1)
3. Enter Community string (default: "public")
4. Click "Add Device"
5. Monitor bandwidth in real-time

### First Time Setup (Standard Build)
1. Install net-snmp (one-time): `choco install net-snmp`
2. Then same as above

### Monitoring a Device
1. Select a device from the list
2. Choose an interface from the dropdown
3. Click "Start" to begin monitoring
4. Watch real-time bandwidth usage
5. Change time range and units as needed

---

## Troubleshooting

### "SNMP Tools Not Found" Error (Standard Build Only)

**Solution:**
1. Open Command Prompt
2. Install net-snmp:
   ```cmd
   choco install net-snmp
   ```
   Or download from: http://www.snmp.com/

3. Verify installation:
   ```cmd
   snmpget -V
   ```

### "Bundle Script Fails" (Self-Contained Build)

**If `bundle_windows_snmp.py` can't find net-snmp:**
1. Verify net-snmp is installed: `snmpget -V`
2. If not installed, install via Chocolatey:
   ```cmd
   choco install net-snmp
   ```
3. If already installed but script can't find it:
   - Copy net-snmp tools manually to `tools/` folder:
     ```
     tools/snmpget.exe
     tools/snmpwalk.exe
     ```
   - Then run: `pyinstaller BandwidthMonitor_Windows.spec -y`

### Python Not Found

**Solution:**
- Download and install Python from https://www.python.org/
- During installation, CHECK "Add Python to PATH"
- Restart Command Prompt after installation

### Device Not Responding

**Common causes:**
- Device IP is incorrect
- Device doesn't have SNMP enabled
- Firewall is blocking SNMP (port 161 UDP)
- Community string is wrong (usually "public")

**To verify device:**
```cmd
snmpget -v2c -c public 192.168.1.1 1.3.6.1.2.1.1.1.0
```

If this returns info, then SNMP is working and the device is accessible.

---

## System Requirements

- **Windows 10** (version 21H2 or later)
- **Windows 11** (all versions)
- **RAM:** 512MB minimum (200MB for app + 300MB system)
- **Disk:** 200MB free space
- **Network:** Access to devices with SNMP enabled

---

## Building on Different Machines

### Self-Contained Build is Platform-Specific

The `.exe` built on Windows can be copied to other Windows machines. However:
- Build on **same** Windows version if possible (10 or 11)
- Build on **same** architecture (32-bit or 64-bit)
- For 64-bit (recommended): Ensure Python 3.10+ 64-bit is installed

### Generic Guidance
- **Windows 10 + Windows 11:** executables built on Windows 10 usually work on Windows 11 (or vice versa)
- **Different PCs:** Just copy `BandwidthMonitor.exe` to any Windows 10/11 machine

---

## Development

### Rebuilding After Code Changes

1. Update `app.py`
2. Verify syntax:
   ```cmd
   python -m py_compile app.py
   ```
3. Rebuild executable:
   ```cmd
   pyinstaller BandwidthMonitor_Windows.spec -y
   ```

### Package Size Comparison

- **Self-Contained:** ~250-300 MB (includes everything)
- **Standard:** ~180-200 MB (no SNMP tools)

The extra size is worth it for zero-installation convenience!

---

## Support

For issues:
1. Check device configuration (SNMP enabled?)
