# Simple Bandwidth Monitor

A Python tkinter-based SNMP bandwidth monitoring application.

## Requirements

- Python 3.14
- tkinter (installed via `brew install python-tk@3.14`)
- pysnmp
- matplotlib

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

Or use the convenience script:
```bash
chmod +x run.sh
./run.sh
```

## Features

- Add devices manually by IP address
- Real-time bandwidth monitoring with graphs
- Traffic data visualization (In/Out bandwidth)
- Support for custom SNMP community strings
- Interface selection per device
- Multiple time ranges (15m/30m/1h/3h/6h)
- Unit conversion (Kbps/Mbps/Gbps)

## Usage

1. Enter IP address of SNMP-enabled device
2. Change community string if needed (default: "public")
3. Click "Add Device" to add it to the monitor
4. Select device from list to view its bandwidth graph
5. Choose interface and time range to inspect
6. Click "Start" to begin monitoring

## Notes

- Requires SNMP to be enabled on target devices
- Default community string: "public"
- Application requires explicit IP address entry (no automatic discovery)
- Default interface monitored: interface 1
- Requires network access to specified SNMP device IP addresses only
