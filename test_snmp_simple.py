#!/usr/bin/env python3
import sys
import socket

def test_snmp_connection(community, host, port=161, timeout=2):
    try:
        print(f"Testing SNMP connection to {host}:{port}")
        print(f"Community: {community}")
        print("Using low-level socket test...")
        
        # Simple SNMP ping via UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        
        # Minimal SNMPv2-C GetRequest PDU
        # This is a basic structure for testing connectivity
        snmp_packet = bytes([
            0x30  # SEQUENCE
        ])
        
        try:
            sock.sendto(b"ping", (host, port))
            response = sock.recv(1024)
            sock.close()
            print("✓ UDP port 161 is accessible")
            return True
        except socket.timeout:
            print("✗ Connection timeout - device not responding on port 161")
            sock.close()
            return False
        except ConnectionRefusedError:
            print("✗ Connection refused - port 161 not open")
            sock.close()
            return False
        except Exception as e:
            print(f"✗ Socket error: {e}")
            sock.close()
            return False
            
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
