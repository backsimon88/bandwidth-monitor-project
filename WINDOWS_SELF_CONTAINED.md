# BandwidthMonitor - Self-Contained Windows Build Guide

## Overview

This guide explains how to create a **fully self-contained** Windows executable that requires **ZERO additional installations** - just double-click and run!

Unlike the macOS version (which requires `brew install net-snmp`), the Windows version can be built with everything bundled inside a single `.exe` file.

## What's Different from macOS?

| Feature | macOS | Windows Self-Contained |
|---------|-------|------------------------|
| Installation | `brew install net-snmp` + run app | Just run `.exe` |
| Size | ~185 MB | ~250-300 MB |
| Setup time | ~5 minutes | ~1 minute |
| User experience | "Install tools, then run" | "Just run" |

## How It Works

The Windows build process:
1. **Detects installed net-snmp tools** on your build machine
2. **Optionally copies them** into the app bundle
3. **Creates single executable** with everything inside
4. **User just runs** - app finds tools automatically

## Build Process (For Developers)

### On Windows Build Machine

#### Step 1: Prepare Development Environment
```cmd
# Install Python 3.10+, then:
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
```

#### Step 2: Install net-snmp (One-time)
```cmd
# Via Chocolatey (easiest):
choco install net-snmp

# OR download from: http://www.snmp.com/
# Then add to PATH or copy binaries manually
```

#### Step 3: Bundle SNMP Tools
```cmd
# This finds and copies net-snmp tools into the app package
python bundle_windows_snmp.py
```

**Expected Output:**
```
✅ Copied snmpget from C:\Program Files\Net-SNMP\bin
✅ Copied snmpwalk from C:\Program Files\Net-SNMP\bin
✅ All SNMP tools bundled successfully!
```

#### Step 4: Build the Executable
```cmd
# Creates single self-contained .exe
pyinstaller BandwidthMonitor_Windows.spec -y
```

**Output Location:** `dist/BandwidthMonitor.exe`

### Testing on Any Windows 10/11 Machine

```cmd
# Just run - no installation needed!
BandwidthMonitor.exe
```

## How the App Finds Tools

The built-in app logic (in `app.py`):

```python
def get_snmp_tool_path(self, tool_name):
    # 1. Check bundled tools first (inside app)
    if tool found in app:
        return bundled_tool_path
    
    # 2. Fall back to system PATH
    if tool found in PATH:
        return system_tool_path
    
    # 3. If nowhere, let user know
    return tool_name  # Let subprocess search PATH
```

This means:
- ✅ Bundled tools work on any machine
- ✅ Falls back to system tools if available
- ✅ Doesn't require any environment setup

## File Structure

After building, you'll have:
```
dist/
  BandwidthMonitor.exe          ← Single executable
_internal/                       (Inside the exe)
  ├─ tools/
  │  ├─ snmpget.exe
  │  └─ snmpwalk.exe
  ├─ matplotlib/
  ├─ tkinter/
  └─ ...other dependencies...
```

## Distribution

### Option A: Direct Distribution
Just copy `BandwidthMonitor.exe`:
- Email to users
- Upload to website
- Share via USB drive
- Any Windows 10/11 machine can run it

### Option B: Create Installer
```cmd
# Optional: Create installer using NSIS or WiX
# But for personal use, just copy the .exe
```

## Troubleshooting Build

### Issue: `bundle_windows_snmp.py` Can't Find net-snmp

**Solution:**
```cmd
# Check if net-snmp is installed
snmpget -V

# If not found, install it:
choco install net-snmp

# Then try bundling again:
python bundle_windows_snmp.py
```

### Issue: Build Fails with Missing Modules

**Solution:**
```cmd
# Make sure all dependencies installed
pip install -r requirements.txt

# Then rebuild:
pyinstaller BandwidthMonitor_Windows.spec -y
```

### Issue: Built Exe Fails to Run on Another Machine

**Possible Causes:**
1. Different Windows version (build on target OS version)
2. Missing visual C++ runtime (install: Visual C++ Redistributable)
3. 32-bit/64-bit mismatch

**Solution:**
```cmd
# Build on Windows 10 or 11 matching your target
# Ensure 64-bit Python is installed (preferred)
python -c "import struct; print(f'{struct.calcsize(\"P\") * 8}-bit')"
```

## Advanced: Customizing the Build

### Add Custom Icon
Edit `BandwidthMonitor_Windows.spec`:
```python
exe = EXE(
    ...
    icon='path/to/icon.ico',  # Add this line
)
```

### Reduce Executable Size
Edit spec file:
```python
a = Analysis(
    ...
    excludes=['tkinter'],  # Or other unused modules
)
```

### Change App Name or Version
Modify spec file name or create new spec with custom settings.

## Comparison: Self-Contained vs Standard

| Aspect | Self-Contained | Standard |
|--------|---|---|
| **User Installation** | Copy `.exe` | Copy `.exe` + install net-snmp |
| **Distribution** | 1 file (300 MB) | 1 file (180 MB) |
| **Setup Time** | Instant | 5 minutes |
| **Portability** | Very high (works everywhere) | Medium (requires prerequisites) |
| **Recommended** | Yes (better UX) | No (requires user setup) |

## Future Improvements

Possible enhancements:
1. **Multi-file packaging** - Separate tools/libs for faster distribution
2. **Auto-update** - Built-in update checker
3. **Installer (.msi)** - Proper Windows installation experience
4. **Code signing** - Trusted certificate for Windows SmartScreen

## Questions?

Check these files for more info:
- [WINDOWS_BUILD.md](WINDOWS_BUILD.md) - Detailed build instructions
- [README.md](README.md) - General app documentation
- [app.py](app.py) - Source code comments

---

**Next Steps:**
1. Ensure net-snmp is installed
2. Run `python bundle_windows_snmp.py`
3. Run `pyinstaller BandwidthMonitor_Windows.spec -y`
4. Test with `dist/BandwidthMonitor.exe`
5. Distribute the `.exe` file!

**Happy Building! 🎉**
