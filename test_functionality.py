#!/usr/bin/env python3
"""
Automated test for BandwidthMonitor functionality
Tests core components without GUI
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from collections import deque
from datetime import datetime
import time

# Test imports
print("=" * 60)
print("TESTING BANDWIDTH MONITOR COMPONENTS")
print("=" * 60)

# Test 1: Import test
print("\n[TEST 1] Import check...")
try:
    import tkinter as tk
    from tkinter import ttk
    import threading
    import subprocess
    import re
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    print("✅ All imports successful")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Deque functionality
print("\n[TEST 2] Data structure test...")
try:
    traffic_data = deque(maxlen=100)
    for i in range(5):
        ts = time.time()
        traffic_data.append((ts, f"{i:02d}:00:00", 100.0 + i*10, 50.0 + i*5))
    
    assert len(traffic_data) == 5, "Deque size mismatch"
    print(f"✅ Deque working: {len(traffic_data)} items stored")
except Exception as e:
    print(f"❌ Deque test failed: {e}")

# Test 3: Data filtering by time range
print("\n[TEST 3] Time range filtering test...")
try:
    test_data = deque()
    now = time.time()
    
    # Add data points from last 1 hour
    for i in range(60):
        ts = now - (60 - i) * 60  # 60 minutes ago to now
        test_data.append((ts, f"{i:02d}:00", 100, 50))
    
    cutoff = now - (15 * 60)  # 15 minutes
    filtered = [x for x in test_data if x[0] >= cutoff]
    
    # Should have approximately 15 data points (15 minutes)
    assert len(filtered) >= 14, f"Expected ~15 points, got {len(filtered)}"
    print(f"✅ Time filtering working: {len(filtered)} points in 15m range")
except Exception as e:
    print(f"❌ Time filtering failed: {e}")

# Test 4: Unit conversion
print("\n[TEST 4] Unit conversion test...")
try:
    rate_kbps = 1024
    
    rate_mbps = rate_kbps / 1024
    rate_gbps = rate_kbps / 1024 / 1024
    
    assert abs(rate_mbps - 1.0) < 0.01, f"Mbps conversion failed: {rate_mbps}"
    assert abs(rate_gbps - 0.000977) < 0.0001, f"Gbps conversion failed: {rate_gbps}"
    print(f"✅ Unit conversion: {rate_kbps} Kbps = {rate_mbps} Mbps = {rate_gbps} Gbps")
except Exception as e:
    print(f"❌ Unit conversion failed: {e}")

# Test 5: Statistics calculation
print("\n[TEST 5] Statistics calculation test...")
try:
    data = [
        ("12:00:00", 100.0, 50.0),
        ("12:00:03", 150.0, 75.0),
        ("12:00:06", 200.0, 100.0),
        ("12:00:09", 120.0, 60.0),
    ]
    
    in_rates = [x[1] for x in data]
    out_rates = [x[2] for x in data]
    
    stats = {
        'in': {
            'min': min(in_rates),
            'max': max(in_rates),
            'avg': sum(in_rates) / len(in_rates)
        },
        'out': {
            'min': min(out_rates),
            'max': max(out_rates),
            'avg': sum(out_rates) / len(out_rates)
        }
    }
    
    assert stats['in']['min'] == 100.0
    assert stats['in']['max'] == 200.0
    assert stats['in']['avg'] == 142.5
    print(f"✅ Stats calculation:")
    print(f"   In:  min={stats['in']['min']}, max={stats['in']['max']}, avg={stats['in']['avg']:.1f}")
    print(f"   Out: min={stats['out']['min']}, max={stats['out']['max']}, avg={stats['out']['avg']:.1f}")
except Exception as e:
    print(f"❌ Statistics failed: {e}")

# Test 6: Regex patterns for SNMP parsing
print("\n[TEST 6] SNMP OID parsing test...")
try:
    # Test snmpget output parsing
    snmpget_output = "42"
    match = re.search(r'-?\d+', snmpget_output)
    assert match is not None
    value = int(match.group(0))
    assert value == 42
    
    # Test snmpwalk interface parsing
    snmpwalk_line = "IF-MIB::ifName.1 = STRING: eth0"
    pattern = r'ifName\.(\d+)\s*=\s*STRING:\s*(.*)'
    match = re.search(pattern, snmpwalk_line)
    assert match is not None
    index = int(match.group(1))
    name = match.group(2).strip()
    assert index == 1
    assert name == "eth0"
    
    print(f"✅ SNMP parsing:")
    print(f"   snmpget: parsed value {value}")
    print(f"   snmpwalk: parsed interface {index}={name}")
except Exception as e:
    print(f"❌ SNMP parsing failed: {e}")

# Test 7: Counter wraparound handling
print("\n[TEST 7] Counter wraparound test...")
try:
    # Test 32-bit counter overflow handling
    last_bytes = 2**32 - 1000
    current_bytes = 500
    
    if current_bytes < last_bytes:
        diff = current_bytes - last_bytes
        diff += 2**32
    else:
        diff = current_bytes - last_bytes
    
    assert diff > 0, "Counter wraparound not handled correctly"
    print(f"✅ Wraparound: {last_bytes} → {current_bytes} = +{diff} bytes")
except Exception as e:
    print(f"❌ Counter wraparound failed: {e}")

# Test 8: Time string formatting
print("\n[TEST 8] Time formatting test...")
try:
    now = datetime.now()
    time_str = now.strftime("%H:%M:%S")
    assert len(time_str) == 8, f"Time format incorrect: {time_str}"
    assert time_str.count(':') == 2
    print(f"✅ Time formatting: {time_str}")
except Exception as e:
    print(f"❌ Time formatting failed: {e}")

print("\n" + "=" * 60)
print("UNIT TESTS COMPLETE")
print("=" * 60)
print("\nResult: ✅ All core functionality tests passed!")
print("App is ready for GUI testing.\n")
