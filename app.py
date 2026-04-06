import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import asyncio
import re
import sys
import os
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import numpy as np
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
        self.range_keys = ["5m", "15m", "30m", "1h", "3h", "6h"]
        self.range_labels = {"5m": "5m", "15m": "15m", "30m": "30m", "1h": "1h", "3h": "3h", "6h": "6h"}
        self.range_seconds = {"5m": 5 * 60, "15m": 15 * 60, "30m": 30 * 60, "1h": 60 * 60, "3h": 3 * 60 * 60, "6h": 6 * 60 * 60}
        self.selected_range = "5m"
        self.poll_interval = 3  # seconds; longer interval avoids noisy 1s polling and counter jitter
        self.max_range_seconds = self.range_seconds["6h"]
        self.max_points = int(self.max_range_seconds / self.poll_interval) + 1
        self.polling = False
        self.monitoring = False
        
        self.setup_ui()
        self.bring_window_front()
        
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
        self.info_label.config(text=f"Display unit set to: {self.unit}")
        if self.current_device:
            data = self.get_display_data(self.current_device)
            self.update_graph(self.current_device, data)

    def on_range_changed(self, event):
        selected = self.range_var.get()
        for key, label in self.range_labels.items():
            if label == selected:
                self.selected_range = key
                break
        if self.current_device:
            data = self.get_display_data(self.current_device)
            self.update_graph(self.current_device, data)

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
        filtered = [(ts, label, in_rate, out_rate) for ts, label, in_rate, out_rate in data if ts >= cutoff]
        if not filtered:
            filtered = [(data[-1][0], data[-1][1], data[-1][2], data[-1][3])]
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
        in_rates = [self.format_rate(item[2]) for item in data]
        out_rates = [self.format_rate(item[3]) for item in data]
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

    def _snmp_run(self, coro):
        """Run an async coroutine synchronously (safe in threads)"""
        try:
            # Windows ProactorEventLoop does not support UDP; use SelectorEventLoop
            loop = asyncio.SelectorEventLoop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
        except Exception as e:
            import traceback
            print(f'[SNMP ERROR] {type(e).__name__}: {e}', file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return None
    
    def get_interfaces(self, ip):
        """Get list of interfaces on device using pure-Python SNMP"""
        from puresnmp import PyWrapper, V2C, Client

        interfaces = {}
        base_oids = [
            '1.3.6.1.2.1.31.1.1.1.1',  # ifName
            '1.3.6.1.2.1.2.2.1.2',      # ifDescr
        ]

        async def _walk(base_oid):
            client = PyWrapper(Client(ip, V2C(self.community)))
            results = []
            async for vb in client.walk(base_oid):
                results.append(vb)
            return results

        for base_oid in base_oids:
            try:
                results = self._snmp_run(_walk(base_oid))
                if not results:
                    continue
                for vb in results:
                    oid_str = str(vb.oid)
                    index = int(oid_str.split('.')[-1])
                    value = vb.value
                    name = value.decode('utf-8', errors='replace').strip() if isinstance(value, bytes) else str(value).strip()
                    if name:
                        interfaces[index] = name
                if interfaces:
                    break
            except Exception as e:
                print(f"Error getting interfaces for {ip} OID {base_oid}: {e}", file=sys.stderr)

        return interfaces
    
    def get_snmp_value(self, ip, oid):
        """Get a single SNMP value using pure-Python SNMP"""
        from puresnmp import PyWrapper, V2C, Client

        async def _get():
            client = PyWrapper(Client(ip, V2C(self.community)))
            return await client.get(oid)

        try:
            result = self._snmp_run(_get())
            if result is None:
                return 0
            return int(result)
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
    
    def _smooth(self, values, window=9):
        """Smooth data with Gaussian-weighted convolution"""
        arr = np.array(values, dtype=float)
        if len(arr) < 3:
            return arr
        w = min(window, len(arr))
        if w % 2 == 0:
            w -= 1
        if w < 3:
            return arr
        x = np.arange(w) - w // 2
        kernel = np.exp(-0.5 * (x / max(w / 4.0, 0.1)) ** 2)
        kernel /= kernel.sum()
        padded = np.pad(arr, (w // 2, w // 2), mode='edge')
        return np.convolve(padded, kernel, mode='valid')[:len(arr)]

    def update_graph(self, ip, data=None):
        self.ax.clear()
        self.fig.patch.set_facecolor('#f8f9fa')
        self.ax.set_facecolor('#ffffff')
        self.ax.set_title(f"Bandwidth Monitor - {ip} (Interface {self.current_interface})", fontsize=11, pad=8)
        self.ax.set_xlabel("Time", fontsize=9)
        self.ax.set_ylabel(f"Bandwidth ({self.unit_label()})", fontsize=9)
        self.ax.grid(True, alpha=0.2, linestyle='--', color='#aaaaaa')
        for spine in self.ax.spines.values():
            spine.set_visible(False)

        if data is None:
            data = self.get_display_data(ip)

        now = time.time()
        range_secs = self.get_current_range_seconds()
        t_start = datetime.fromtimestamp(now - range_secs)
        t_end = datetime.fromtimestamp(now)

        if data and len(data) >= 2:
            t_nums = np.array([x[0] for x in data])
            in_vals  = np.array([self.format_rate(x[2]) for x in data])
            out_vals = np.array([self.format_rate(x[3]) for x in data])

            in_smooth  = np.clip(self._smooth(in_vals),  0, None)
            out_smooth = np.clip(self._smooth(out_vals), 0, None)

            n_dense = max(len(data) * 8, 400)
            t_dense = np.linspace(t_nums[0], t_nums[-1], n_dense)
            in_dense  = np.clip(np.interp(t_dense, t_nums, in_smooth),  0, None)
            out_dense = np.clip(np.interp(t_dense, t_nums, out_smooth), 0, None)
            t_dt = [datetime.fromtimestamp(t) for t in t_dense]

            color_in  = "#1f77b4"
            color_out = "#2ca02c"
            self.ax.fill_between(t_dt, in_dense,  alpha=0.20, color=color_in)
            self.ax.fill_between(t_dt, out_dense, alpha=0.20, color=color_out)
            self.ax.plot(t_dt, in_dense,  color=color_in,  linewidth=2.0, label="Traffic In")
            self.ax.plot(t_dt, out_dense, color=color_out, linewidth=2.0, label="Traffic Out")
            self.ax.legend(loc='upper left', fontsize=8, framealpha=0.7, edgecolor='none')
            self.ax.set_ylim(bottom=0)

        elif data and len(data) == 1:
            t = datetime.fromtimestamp(data[0][0])
            self.ax.plot([t], [self.format_rate(data[0][2])], 'o', color="#1f77b4", label="Traffic In")
            self.ax.plot([t], [self.format_rate(data[0][3])], 's', color="#2ca02c", label="Traffic Out")
            self.ax.legend(loc='upper left', fontsize=8)
            self.ax.set_ylim(bottom=0)
        else:
            self.ax.text(0.5, 0.5, 'Collecting data...', ha='center', va='center',
                         transform=self.ax.transAxes, fontsize=12, color='gray')

        self.ax.set_xlim(t_start, t_end)
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        self.fig.autofmt_xdate(rotation=45)
        self.canvas.draw_idle()

if __name__ == "__main__":
    root = tk.Tk()
    app = SNMPBandwidthMonitor(root)
    root.after(2000, lambda: threading.Thread(target=lambda: [app.on_device_select(None)], daemon=True).start())
    root.mainloop()