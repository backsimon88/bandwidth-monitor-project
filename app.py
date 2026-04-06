import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import subprocess
import re
import sys
import os
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from collections import deque
from datetime import datetime

class SNMPBandwidthMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple Bandwidth Monitor - SNMP")
        self.root.geometry("900x700")
        
        self.devices = {}
        self.traffic_data = {}  # {ip: deque((timestamp, in_kbps, out_kbps))}
        self.last_counters = {}  # {(ip, if_index): {'ts': float, 'in_bytes': int, 'out_bytes': int}}
        self.community = "public"
        self.current_device = None
        self.current_interface = 1  # Default interface
        self.interfaces = {}  # {ip: {index: name}}
        self.unit = "Kbps"
        self.unit_options = ["Kbps", "Mbps", "Gbps"]
        self.range_keys = ["15m", "30m", "1h", "3h", "6h"]
        self.range_labels = {"15m": "15m", "30m": "30m", "1h": "1h", "3h": "3h", "6h": "6h"}
        self.range_seconds = {"15m": 15 * 60, "30m": 30 * 60, "1h": 60 * 60, "3h": 3 * 60 * 60, "6h": 6 * 60 * 60}
        self.selected_range = "15m"
        self.poll_interval = 3  # seconds; longer interval avoids noisy 1s polling and counter jitter
        self.max_range_seconds = self.range_seconds["6h"]
        self.max_points = int(self.max_range_seconds / self.poll_interval) + 1
        self.polling = False
        self.monitoring = False
        
        self.setup_ui()
        self.bring_window_front()
        
        # Check for SNMP tools
        if not self.check_snmp_tools():
            self.show_snmp_installation_guide()
            self.info_label.config(text="⚠️  SNMP tools not found - see error message")
        else:
            self.info_label.config(text="Ready - Add devices manually")
        
    def bring_window_front(self):
        try:
            self.root.update_idletasks()
            self.root.deiconify()
            self.root.lift()
            self.root.attributes('-topmost', True)
            self.root.focus_force()
            self.root.after(200, lambda: self.root.attributes('-topmost', False))
        except Exception:
            pass
        
    def setup_ui(self):
        # Control panel
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(control_frame, text="Community:").pack(side=tk.LEFT, padx=5)
        self.community_entry = ttk.Entry(control_frame, width=15)
        self.community_entry.pack(side=tk.LEFT, padx=5)
        self.community_entry.insert(0, "public")
        self.community_entry.bind('<KeyRelease>', self.on_community_changed)
        
        ttk.Label(control_frame, text="IP Address:").pack(side=tk.LEFT, padx=5)
        self.ip_entry = ttk.Entry(control_frame, width=20)
        self.ip_entry.pack(side=tk.LEFT, padx=5)
        self.ip_entry.insert(0, "192.168.1.1")
        
        ttk.Button(control_frame, text="Add Device", command=self.add_device).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Refresh", command=self.refresh_current).pack(side=tk.LEFT, padx=5)
        ttk.Label(control_frame, text="Unit:").pack(side=tk.LEFT, padx=5)
        self.unit_var = tk.StringVar(value=self.unit)
        self.unit_combobox = ttk.Combobox(control_frame, textvariable=self.unit_var, values=self.unit_options, state="readonly", width=7)
        self.unit_combobox.pack(side=tk.LEFT, padx=5)
        self.unit_combobox.bind('<<ComboboxSelected>>', self.on_unit_changed)
        ttk.Label(control_frame, text="Range:").pack(side=tk.LEFT, padx=5)
        self.range_var = tk.StringVar(value=self.selected_range)
        self.range_combobox = ttk.Combobox(control_frame, textvariable=self.range_var, values=[self.range_labels[k] for k in self.range_keys], state="readonly", width=6)
        self.range_combobox.pack(side=tk.LEFT, padx=5)
        self.range_combobox.bind('<<ComboboxSelected>>', self.on_range_changed)
        ttk.Button(control_frame, text="Start", command=self.start_monitoring).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Stop", command=self.stop_monitoring).pack(side=tk.LEFT, padx=5)
        
        # Device list (left side)
        self.device_frame = ttk.Frame(self.root)
        self.device_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=10, pady=10)
        
        ttk.Label(self.device_frame, text="Connected Devices:").pack()
        self.device_listbox = tk.Listbox(self.device_frame, height=10, width=25)
        self.device_listbox.pack(fill=tk.BOTH, expand=False)
        self.device_listbox.bind('<<ListboxSelect>>', self.on_device_select)
        
        # Interface selector
        ttk.Label(self.device_frame, text="Interfaces:").pack(pady=(10,0))
        self.interface_var = tk.StringVar()
        self.interface_combobox = ttk.Combobox(self.device_frame, textvariable=self.interface_var, state="readonly", width=22)
        self.interface_combobox.pack(fill=tk.X, expand=False)
        self.interface_combobox.bind('<<ComboboxSelected>>', self.on_interface_select)
        
        # Graph (right side)
        self.info_frame = ttk.Frame(self.root)
        self.info_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(self.info_frame, text="Bandwidth Graph:").pack()
        self.canvas_frame = ttk.Frame(self.info_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.fig = Figure(figsize=(7, 3.5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.line_in, = self.ax.plot([], [], label="Traffic In", color="#1f77b4", marker='o')
        self.line_out, = self.ax.plot([], [], label="Traffic Out", color="#2ca02c", marker='s')
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel(f"Bandwidth ({self.unit_label()})")
        self.ax.set_title("Bandwidth Monitor")
        self.ax.grid(True, alpha=0.3)
        self.ax.legend(loc='upper left')

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.canvas_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.stats_frame = ttk.Frame(self.info_frame)
        self.stats_frame.pack(fill=tk.X, pady=(5, 0))
        self.stats_in_label = ttk.Label(self.stats_frame, text="In: min 0.0, max 0.0, avg 0.0")
        self.stats_in_label.pack(fill=tk.X)
        self.stats_out_label = ttk.Label(self.stats_frame, text="Out: min 0.0, max 0.0, avg 0.0")
        self.stats_out_label.pack(fill=tk.X)

        self.info_label = ttk.Label(self.info_frame, text="Ready", anchor="w")
        self.info_label.pack(fill=tk.X, pady=(5, 0))
        
    def on_community_changed(self, event):
        self.community = self.community_entry.get() or "public"
        self.info_label.config(text=f"Community changed to: {self.community}")

    def on_unit_changed(self, event):
        self.unit = self.unit_var.get()
        unit_name = self.unit
        self.info_label.config(text=f"Display unit set to: {unit_name}")
        if self.current_device:
            self.refresh_current()

    def on_range_changed(self, event):
        selected = self.range_var.get()
        for key, label in self.range_labels.items():
            if label == selected:
                self.selected_range = key
                break
        if self.current_device:
            self.refresh_current()

    def format_rate(self, rate_kbps):
        if self.unit == "Mbps":
            return rate_kbps / 1024
        if self.unit == "Gbps":
            return rate_kbps / 1024 / 1024
        return rate_kbps

    def unit_label(self):
        return self.unit

    def get_current_range_seconds(self):
        return self.range_seconds.get(self.selected_range, self.range_seconds["15m"])

    def get_display_data(self, ip):
        data = list(self.traffic_data.get(ip, deque()))
        if not data:
            return []
        cutoff = time.time() - self.get_current_range_seconds()
        filtered = [(label, in_rate, out_rate) for ts, label, in_rate, out_rate in data if ts >= cutoff]
        if not filtered:
            filtered = [(data[-1][1], data[-1][2], data[-1][3])]
        max_plot_points = 180
        if len(filtered) <= max_plot_points:
            return filtered
        step = max(1, len(filtered) // max_plot_points)
        sampled = filtered[::step]
        if sampled[-1] != filtered[-1]:
            sampled.append(filtered[-1])
        return sampled

    def get_range_stats(self, data):
        if not data:
            return None
        in_rates = [self.format_rate(item[1]) for item in data]
        out_rates = [self.format_rate(item[2]) for item in data]
        return {
            'in': {
                'min': min(in_rates),
                'max': max(in_rates),
                'avg': sum(in_rates) / len(in_rates) if in_rates else 0.0
            },
            'out': {
                'min': min(out_rates),
                'max': max(out_rates),
                'avg': sum(out_rates) / len(out_rates) if out_rates else 0.0
            }
        }
        
    def add_device(self):
        ip = self.ip_entry.get()
        if ip and ip not in self.devices:
            self.devices[ip] = {"status": "added", "in": 0, "out": 0}
            self.traffic_data[ip] = deque(maxlen=self.max_points)
            self.device_listbox.insert(tk.END, ip)
            self.info_label.config(text=f"Device added: {ip}")
        elif ip in self.devices:
            self.info_label.config(text=f"Device already in list: {ip}")
        else:
            self.info_label.config(text="Please enter a valid IP address")

    def get_snmp_tool_path(self, tool_name):
        """Get path to SNMP tool, preferring bundled version"""
        import platform
        
        # Try bundled tools first (in _internal/tools for PyInstaller single-file)
        if hasattr(sys, '_MEIPASS'):
            # Running as PyInstaller bundle
            bundled_tools = os.path.join(sys._MEIPASS, 'tools')
            tool_exe = f"{tool_name}.exe" if platform.system() == "Windows" else tool_name
            tool_path = os.path.join(bundled_tools, tool_exe)
            if os.path.exists(tool_path):
                return tool_path
        
        # Fall back to system PATH
        import shutil
        tool_exe = f"{tool_name}.exe" if platform.system() == "Windows" else tool_name
        system_path = shutil.which(tool_exe)
        if system_path:
            return system_path
        
        # Return tool name and let subprocess search PATH
        return tool_exe
    
    def check_snmp_tools(self):
        """Check if SNMP tools are available"""
        import platform
        try:
            # Try to find snmpget - prefer bundled, then system
            snmpget_path = self.get_snmp_tool_path('snmpget')
            result = subprocess.run([snmpget_path, '-V'], capture_output=True, timeout=2)
            return result.returncode == 0
        except:
            return False
    
    def show_snmp_installation_guide(self):
        """Show installation guide for SNMP tools"""
        import platform
        os_name = platform.system()
        
        if os_name == "Darwin":  # macOS
            guide = """SNMP Tools Required

Please install net-snmp using Homebrew:
  brew install net-snmp

After installation, restart the app."""
        elif os_name == "Linux":
            guide = """SNMP Tools Required

For Ubuntu/Debian:
  sudo apt-get install snmp

For RedHat/CentOS:
  sudo yum install net-snmp-utils

After installation, restart the app."""
        else:  # Windows
            guide = """SNMP Tools Required (Windows 10/11)

1. Install via Chocolatey (recommended):
   - Open Command Prompt as Administrator
   - Run: choco install net-snmp
   - Restart the app

2. Or download manually:
   - Visit: http://www.snmp.com/
   - Download Net-SNMP for Windows
   - Install and add to PATH

3. Verify installation:
   - Open Command Prompt
   - Type: snmpget -V
   - Should show version info

After installation, restart the app."""
        
        messagebox.showerror("SNMP Tools Not Found", guide)
        return False
    
    def get_interfaces(self, ip):
        """Get list of interfaces on device"""
        interfaces = {}
        oids = [
            ('1.3.6.1.2.1.31.1.1.1.1', r'ifName\.(\d+)\s*=\s*STRING:\s*(.*)'),
            ('1.3.6.1.2.1.2.2.1.2', r'ifDescr\.(\d+)\s*=\s*STRING:\s*(.*)')
        ]

        snmpwalk_path = self.get_snmp_tool_path('snmpwalk')
        
        for oid, pattern in oids:
            try:
                result = subprocess.run(
                    [snmpwalk_path, '-v2c', '-c', self.community, ip, oid],
                    capture_output=True,
                    timeout=3,
                    text=True
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        match = re.search(pattern, line)
                        if match:
                            index = int(match.group(1))
                            name = match.group(2).strip()
                            if name:
                                interfaces[index] = name
                elif result.returncode != 0:
                    print(f"SNMP error getting interfaces for {ip} OID {oid}: {result.stderr.strip()}", file=sys.stderr)
            except FileNotFoundError:
                # snmpwalk not found
                print(f"snmpwalk tool not found. Please install net-snmp tools.", file=sys.stderr)
                return {1: "Interface 1"}
            except subprocess.TimeoutExpired:
                print(f"Timeout getting interfaces for {ip} (OID {oid})", file=sys.stderr)
            except Exception as e:
                print(f"Error getting interfaces for {ip} (OID {oid}): {type(e).__name__}: {e}", file=sys.stderr)

        return interfaces
    
    def get_snmp_value(self, ip, oid):
        """Get a single SNMP value using snmpget"""
        snmpget_path = self.get_snmp_tool_path('snmpget')
        try:
            result = subprocess.run(
                [snmpget_path, '-v2c', '-c', self.community, '-Ovq', ip, oid],
                capture_output=True,
                timeout=3,
                text=True
            )
            if result.returncode == 0 and result.stdout:
                raw = result.stdout.strip()
                match = re.search(r'-?\d+', raw)
                if match:
                    return int(match.group(0))
            elif result.returncode != 0:
                print(f"SNMP error for {ip} OID {oid}: {result.stderr.strip()}", file=sys.stderr)
            return 0
        except FileNotFoundError:
            print(f"snmpget tool not found. Please install net-snmp tools.", file=sys.stderr)
            return 0
        except Exception as e:
            print(f"SNMP exception for {ip} OID {oid}: {type(e).__name__}: {e}", file=sys.stderr)
            return 0
            
    def get_interface_stats(self, ip):
        try:
            in_oid = f'1.3.6.1.2.1.2.2.1.10.{self.current_interface}'
            out_oid = f'1.3.6.1.2.1.2.2.1.16.{self.current_interface}'
            
            in_octets = self.get_snmp_value(ip, in_oid)
            out_octets = self.get_snmp_value(ip, out_oid)
            return in_octets, out_octets
        except:
            return 0, 0
        
    def on_device_select(self, event):
        selection = self.device_listbox.curselection()
        if selection:
            ip = self.device_listbox.get(selection[0])
            self.current_device = ip
            
            # Load interfaces for this device
            self.info_label.config(text=f"Loading interfaces for {ip}...")
            self.load_interfaces(ip)
            
    def load_interfaces(self, ip):
        """Load and display interfaces for selected device"""
        threading.Thread(target=self.load_interfaces_thread, args=(ip,), daemon=True).start()
    
    def load_interfaces_thread(self, ip):
        interfaces = self.get_interfaces(ip)
        self.interfaces[ip] = interfaces
        self.root.after(0, self.on_interfaces_loaded, ip, interfaces)

    def on_interfaces_loaded(self, ip, interfaces):
        if interfaces:
            interface_list = [f"{idx}: {name}" for idx, name in sorted(interfaces.items())]
            self.interface_combobox['values'] = interface_list
            if interface_list:
                self.interface_combobox.set(interface_list[0])
                self.current_interface = sorted(interfaces.keys())[0]
                self.info_label.config(text=f"Device: {ip} | Interfaces loaded ({len(interfaces)} found)")
            else:
                self.interface_combobox.set("")
                self.info_label.config(text=f"Device: {ip} | No interfaces found")
        else:
            self.interface_combobox['values'] = []
            self.interface_combobox.set("")
            self.info_label.config(text=f"Device: {ip} | Unable to load interfaces")

        if interfaces:
            self.start_monitoring()
    
    def start_monitoring(self):
        if self.current_device and self.current_interface:
            self.monitoring = True
            self.info_label.config(text=f"Monitoring started for {self.current_device} / IF {self.current_interface}")
            self.start_polling()
        else:
            self.info_label.config(text="Select a device and interface first")
    
    def stop_monitoring(self):
        self.monitoring = False
        self.info_label.config(text="Monitoring stopped")
    
    def start_polling(self):
        if not self.polling:
            self.polling = True
            self.root.after(int(self.poll_interval * 1000), self.poll_current)
    
    def poll_current(self):
        if not self.monitoring or not self.current_device:
            self.polling = False
            return
        threading.Thread(target=self.update_graph_thread, daemon=True).start()
        self.root.after(int(self.poll_interval * 1000), self.poll_current)
    
    def clear_traffic_data(self, ip):
        self.traffic_data[ip] = deque(maxlen=self.max_points)
        self.last_counters = {k: v for k, v in self.last_counters.items() if k[0] != ip}
    
    def on_interface_select(self, event):
        """Handle interface selection"""
        if self.current_device and self.interfaces.get(self.current_device):
            selected = self.interface_var.get()
            if selected:
                # Extract interface index from selection
                match = re.match(r'(\d+):', selected)
                if match:
                    self.current_interface = int(match.group(1))
                    self.clear_traffic_data(self.current_device)
                    self.info_label.config(text=f"Interface {self.current_interface} selected")
                    self.refresh_current()
    
    def refresh_current(self):
        if self.current_device:
            threading.Thread(target=self.update_graph_thread, daemon=True).start()
    
    def update_graph_thread(self):
        if not self.current_device:
            return
            
        ip = self.current_device
        self.root.after(0, lambda: self.info_label.config(text=f"Fetching data from {ip}..."))
        
        in_bytes, out_bytes = self.get_interface_stats(ip)
        if in_bytes < 0 or out_bytes < 0:
            self.root.after(0, lambda: self.info_label.config(text=f"Device: {ip} | Status: Unable to fetch SNMP data"))
            return
        
        current_ts = time.time()
        key = (ip, self.current_interface)
        last = self.last_counters.get(key)
        if last and current_ts > last['ts']:
            in_diff = in_bytes - last['in_bytes']
            out_diff = out_bytes - last['out_bytes']
            if in_diff < 0:
                in_diff += 2**32
            if out_diff < 0:
                out_diff += 2**32
            elapsed = current_ts - last['ts']
            in_rate = max(0.0, in_diff * 8 / elapsed / 1024)
            out_rate = max(0.0, out_diff * 8 / elapsed / 1024)
        else:
            in_rate = 0.0
            out_rate = 0.0

        self.last_counters[key] = {'ts': current_ts, 'in_bytes': in_bytes, 'out_bytes': out_bytes}
        self.traffic_data.setdefault(ip, deque(maxlen=self.max_points)).append((current_ts, datetime.now().strftime("%H:%M:%S"), in_rate, out_rate))
        interface_name = self.interfaces.get(ip, {}).get(self.current_interface, f"Interface {self.current_interface}")
        self.root.after(0, self.update_graph_ui, ip, in_rate, out_rate, interface_name)

    def update_graph_ui(self, ip, in_rate, out_rate, interface_name):
        display_in = self.format_rate(in_rate)
        display_out = self.format_rate(out_rate)
        data = self.get_display_data(ip)
        self.update_graph(ip, data)
        unit = self.unit_label()
        if data:
            stats = self.get_range_stats(data)
            if stats:
                self.stats_in_label.config(
                    text=f"In ({unit})  min: {stats['in']['min']:.1f}, max: {stats['in']['max']:.1f}, avg: {stats['in']['avg']:.1f}"
                )
                self.stats_out_label.config(
                    text=f"Out ({unit}) min: {stats['out']['min']:.1f}, max: {stats['out']['max']:.1f}, avg: {stats['out']['avg']:.1f}"
                )
        else:
            self.stats_in_label.config(text="In: collecting data...")
            self.stats_out_label.config(text="Out: collecting data...")
        self.info_label.config(text=f"{self.current_device} | {interface_name} | In: {display_in:.1f} {unit} | Out: {display_out:.1f} {unit}")
    
    def update_graph(self, ip, data=None):
        self.ax.clear()
        self.ax.set_title(f"Bandwidth Monitor - {ip} (Interface {self.current_interface})")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel(f"Bandwidth ({self.unit_label()})")
        self.ax.grid(True, alpha=0.3)

        if data is None:
            data = self.get_display_data(ip)

        if data:
            labels = [x[0] for x in data]
            in_data = [self.format_rate(x[1]) for x in data]
            out_data = [self.format_rate(x[2]) for x in data]
            x_values = list(range(len(labels)))

            self.ax.plot(x_values, in_data, label="Traffic In", color="#1f77b4", marker='o')
            self.ax.plot(x_values, out_data, label="Traffic Out", color="#2ca02c", marker='s')
            tick_step = max(1, len(x_values) // 12)
            self.ax.set_xticks(x_values[::tick_step])
            self.ax.set_xticklabels([labels[i] for i in x_values[::tick_step]], rotation=45, ha='right')
            self.ax.legend(loc='upper left')
            self.ax.relim()
            self.ax.autoscale_view()
            self.ax.set_ylim(bottom=0)
        else:
            self.ax.text(0.5, 0.5, 'Collecting data...', ha='center', va='center', transform=self.ax.transAxes)

        self.canvas.draw_idle()

if __name__ == "__main__":
    root = tk.Tk()
    app = SNMPBandwidthMonitor(root)
    root.after(2000, lambda: threading.Thread(target=lambda: [app.on_device_select(None)], daemon=True).start())
    root.mainloop()