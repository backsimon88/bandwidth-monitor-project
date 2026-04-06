#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from pysnmp.hlapi import *

def test_snmp_connection(community, host, port=161, timeout=2):
    try:
        print(f"Testing SNMP connection to {host}:{port}")
        print(f"Community: {community}")
        
        engine = SnmpEngine()
        iterator = getCmd(
            engine,
            CommunityData(community),
            UdpTransportTarget((host, port), timeout=timeout),
            ContextData(),
            '1.3.6.1.2.1.1.1.0'
        )
        
        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
        
        if errorIndication:
            print(f"✗ SNMP Error: {errorIndication}")
            return False
        elif errorStatus:
            print(f"✗ SNMP Status Error: {errorStatus.prettyPrint()}")
            return False
        else:
            print("✓ SNMP connection successful!")
            for varBind in varBinds:
                print(f"  System Description: {varBind[1]}")
            return True
            
    except Exception as e:
        print(f"✗ Exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    community = "Snet@2022"
    host = "172.28.30.250"
    
    success = test_snmp_connection(community, host)
    sys.exit(0 if success else 1)
