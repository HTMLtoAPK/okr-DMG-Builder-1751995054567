import tkinter as tk
from tkinter import messagebox, ttk
import psutil
import os
import sys
import json
import plistlib
from pathlib import Path

# --- NEW: Define the path for the Launch Agent plist file ---
LAUNCH_AGENT_DIR = Path.home() / "Library/LaunchAgents"
PLIST_FILENAME = "com.niksa.batteryalerter.plist"
PLIST_PATH = LAUNCH_AGENT_DIR / PLIST_FILENAME

class AlertWindow(tk.Toplevel):
    # This class is already polished and remains unchanged.
    def __init__(self, parent, headline, message):
        super().__init__(parent); self.parent = parent; self.flash_after_id = None; self.is_flashing = False
        self.title("Alert!"); self.attributes('-topmost', True); self.resizable(False, False)
        win_w, win_h = 400, 180
        screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
        x, y = (screen_w // 2) - (win_w // 2), (screen_h // 2) - (win_h // 2)
        self.geometry(f'{win_w}x{win_h}+{x}+{y}')
        self.grab_set(); self.transient(parent)
        style = ttk.Style(self); style.configure("Alert.TFrame", background="#cc0000")
        style.configure("Headline.TLabel", background="#cc0000", foreground="white", font=("-size", 18, "bold"))
        style.configure("Message.TLabel", background="#cc0000", foreground="white", font=("-size", 14))
        self.main_frame = ttk.Frame(self, padding=20); self.main_frame.pack(fill=tk.BOTH, expand=True)
        headline_label = ttk.Label(self.main_frame, text=headline, style="Headline.TLabel", anchor="center")
        headline_label.pack(pady=(10, 5), fill="x")
        message_label = ttk.Label(self.main_frame, text=message, style="Message.TLabel", anchor="center", wraplength=360)
        message_label.pack(pady=5, fill="x", expand=True)
        ok_button = ttk.Button(self.main_frame, text="OK", command=self.destroy)
        ok_button.pack(pady=(10, 0))
        os.system('afplay /System/Library/Sounds/Sosumi.aiff &'); self._start_flash()
        self.wait_window(self)

    def _start_flash(self): self.is_flashing = True; self._flash()
    def _flash(self):
        if not self.is_flashing: return
        current_style = self.main_frame.cget("style"); new_style = "Alert.TFrame" if current_style != "Alert.TFrame" else "TFrame"
        self.main_frame.config(style=new_style)
        for widget in self.main_frame.winfo_children():
            try:
                if "Headline.TLabel" in str(widget.cget("style")): widget.config(style="Headline.TLabel" if new_style == "Alert.TFrame" else "TLabel")
                elif "Message.TLabel" in str(widget.cget("style")): widget.config(style="Message.TLabel" if new_style == "Alert.TFrame" else "TLabel")
            except tk.TclError: pass
        self.flash_after_id = self.after(500, self._flash)
    def destroy(self):
        self.is_flashing = False
        if self.flash_after_id: self.after_cancel(self.flash_after_id)
        super().destroy()

class BatteryAlerterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.CONFIG_FILE = "settings.json"; self.is_monitoring = False; self.after_id = None
        self.title("Mac Battery Alerter")
        self.geometry("450x360") # NEW: Made window taller for the new option
        self.resizable(False, False)
        style = ttk.Style(self); style.theme_use('aqua')
        
        # NEW: A Tkinter variable to hold the state of our checkbox
        self.run_on_startup_var = tk.BooleanVar()

        self._setup_widgets()
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self._load_settings()
        self._check_battery(initial_run=True)

    def _setup_widgets(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.grid(row=0, column=0, sticky="nsew"); self.grid_rowconfigure(0, weight=1); self.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(main_frame, text="Alert when battery is BELOW:").grid(row=0, column=0, sticky="w", pady=5)
        self.low_entry = ttk.Entry(main_frame, width=8)
        self.low_entry.grid(row=0, column=1, sticky="ew", pady=5, padx=5)
        ttk.Label(main_frame, text="%").grid(row=0, column=2, sticky="w", pady=5)
        self.estimation_label = ttk.Label(main_frame, text="", style="secondary.TLabel")
        self.estimation_label.grid(row=0, column=3, sticky="w", padx=(10, 0))
        self.low_entry.bind("<KeyRelease>", lambda event: self._check_battery(initial_run=True))

        ttk.Label(main_frame, text="Alert when battery is ABOVE:").grid(row=1, column=0, sticky="w", pady=5)
        self.high_entry = ttk.Entry(main_frame, width=8)
        self.high_entry.grid(row=1, column=1, sticky="ew", pady=5, padx=5)
        ttk.Label(main_frame, text="%").grid(row=1, column=2, sticky="w", pady=5)

        ttk.Label(main_frame, text="Check battery every:").grid(row=2, column=0, sticky="w", pady=5)
        self.interval_entry = ttk.Entry(main_frame, width=8)
        self.interval_entry.grid(row=2, column=1, sticky="ew", pady=5, padx=5)
        ttk.Label(main_frame, text="seconds").grid(row=2, column=2, sticky="w", pady=5)

        # NEW: Add a separator and the startup checkbox
        ttk.Separator(main_frame, orient='horizontal').grid(row=3, column=0, columnspan=4, sticky='ew', pady=15)
        startup_checkbox = ttk.Checkbutton(main_frame, text="Run automatically on startup", variable=self.run_on_startup_var, command=self._toggle_startup)
        startup_checkbox.grid(row=4, column=0, columnspan=4, sticky='w')

        self.monitor_button = ttk.Button(main_frame, text="Start Monitoring", command=self._toggle_monitoring)
        self.monitor_button.grid(row=5, column=0, columnspan=4, pady=(15, 5), sticky="ew")
        self.test_button = ttk.Button(main_frame, text="Test Alert", command=self._send_test_alert)
        self.test_button.grid(row=6, column=0, columnspan=4, pady=5, sticky="ew")
        self.status_label = ttk.Label(main_frame, text="Status: Initializing...", anchor="center")
        self.status_label.grid(row=7, column=0, columnspan=4, pady=(10, 5), sticky="ew")
        self.progress_bar = ttk.Progressbar(main_frame, orient='horizontal', mode='determinate')
        self.progress_bar.grid(row=8, column=0, columnspan=4, sticky="ew", pady=(0, 10))
        footer_label = ttk.Label(main_frame, text="Created by Nikša", style="secondary.TLabel", anchor="center")
        footer_label.grid(row=9, column=0, columnspan=4, sticky="sew")
        main_frame.grid_rowconfigure(9, weight=1)

    # NEW: Function to handle the startup checkbox logic
    def _toggle_startup(self):
        """Creates or deletes the Launch Agent plist file."""
        # This requires the script to be run from the final .app bundle to work correctly after a restart.
        # For now, it will use the path to our portable python.
        python_executable = sys.executable
        script_path = os.path.abspath(__file__)

        if self.run_on_startup_var.get():
            # User wants to run on startup, so we create the plist file.
            plist_data = {
                'Label': PLIST_FILENAME.replace(".plist", ""),
                'ProgramArguments': [python_executable, script_path],
                'RunAtLoad': True
            }
            LAUNCH_AGENT_DIR.mkdir(exist_ok=True)
            with open(PLIST_PATH, 'wb') as fp:
                plistlib.dump(plist_data, fp)
            print(f"Created startup agent at: {PLIST_PATH}")
        else:
            # User doesn't want to run on startup, so we delete the file if it exists.
            if PLIST_PATH.exists():
                PLIST_PATH.unlink()
                print(f"Removed startup agent: {PLIST_PATH}")

    def _show_alert(self, headline, message): AlertWindow(self, headline, message)
    def _send_test_alert(self): self._show_alert("TEST ALERT", "This is how you will be notified.")
    
    def _check_battery(self, initial_run=False):
        # ... (This function remains unchanged) ...
        if not self.is_monitoring and not initial_run: return
        battery = psutil.sensors_battery()
        if battery is None: self.status_label.config(text="Status: No battery detected."); return
        current_percent, is_charging, secs_left = int(battery.percent), battery.power_plugged, battery.secsleft
        time_left_str = ""
        if secs_left not in [None, psutil.POWER_TIME_UNLIMITED, psutil.POWER_TIME_UNKNOWN]:
            h, m = divmod(secs_left // 60, 60)
            if h > 0: time_left_str = f" ({h}h {m}m remaining)"
            else: time_left_str = f" ({m}m remaining)"
        self.status_label.config(text=f"Status: {current_percent}% - {'Charging' if is_charging else 'Discharging'}{time_left_str}")
        self.progress_bar['value'] = current_percent
        estimation_text = ""
        if is_charging: estimation_text = "(Charging)"
        elif secs_left in [None, psutil.POWER_TIME_UNLIMITED, psutil.POWER_TIME_UNKNOWN]: estimation_text = "(Estimating...)"
        else:
            try:
                target_percent = int(self.low_entry.get())
                if target_percent >= current_percent: estimation_text = "(Already below target)"
                else:
                    time_to_target_s = secs_left * (current_percent - target_percent) / current_percent
                    h, m = divmod(int(time_to_target_s) // 60, 60)
                    if h > 0: estimation_text = f"~{h}h {m}m to reach"
                    else: estimation_text = f"~{m}m to reach"
            except (ValueError, ZeroDivisionError): estimation_text = ""
        self.estimation_label.config(text=estimation_text)
        if not initial_run:
            try:
                low_threshold, high_threshold, check_interval_seconds = int(self.low_entry.get()), int(self.high_entry.get()), int(self.interval_entry.get())
            except ValueError: self.status_label.config(text="Status: All inputs must be numbers."); self.after_id = self.after(5000, self._check_battery); return
            low_notified, high_notified = getattr(self, "low_notified", False), getattr(self, "high_notified", False)
            if current_percent <= low_threshold and not is_charging and not low_notified:
                self._show_alert("LOW BATTERY WARNING", f"Battery is at {current_percent}%. Please connect power."); self.low_notified = True
            elif current_percent >= high_threshold and is_charging and not high_notified:
                self._show_alert("BATTERY CHARGED", f"Battery is at {current_percent}%. You can disconnect power."); self.high_notified = True
            if is_charging or current_percent > low_threshold: self.low_notified = False
            if not is_charging or current_percent < high_threshold: self.high_notified = False
            self.after_id = self.after(check_interval_seconds * 1000, self._check_battery)

    def _toggle_monitoring(self):
        # ... (This function remains unchanged) ...
        self.is_monitoring = not self.is_monitoring
        state = "disabled" if self.is_monitoring else "normal"
        self.monitor_button.config(text="Stop Monitoring" if self.is_monitoring else "Start Monitoring")
        self.low_entry.config(state=state); self.high_entry.config(state=state); self.interval_entry.config(state=state)
        if self.is_monitoring:
            self.status_label.config(text="Status: Monitoring started...")
            self._check_battery()
        else:
            if self.after_id: self.after_cancel(self.after_id); self.after_id = None
            self.status_label.config(text="Status: Monitoring stopped.")
            self._check_battery(initial_run=True)

    def _load_settings(self):
        # NEW: Load the startup preference as well
        defaults = {"low_threshold": "20", "high_threshold": "80", "check_interval": "30", "run_on_startup": False}
        try:
            with open(self.CONFIG_FILE, 'r') as f: settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError): settings = defaults
        
        self.low_entry.insert(0, settings.get("low_threshold", defaults["low_threshold"]))
        self.high_entry.insert(0, settings.get("high_threshold", defaults["high_threshold"]))
        self.interval_entry.insert(0, settings.get("check_interval", defaults["check_interval"]))
        
        # Set the checkbox state from the loaded settings or the plist file's existence
        startup_enabled = settings.get("run_on_startup", defaults["run_on_startup"])
        if PLIST_PATH.exists():
            self.run_on_startup_var.set(True)
        else:
            self.run_on_startup_var.set(startup_enabled)
        print("Settings loaded.")

    def _save_settings(self):
        # NEW: Save the startup preference
        settings = {
            "low_threshold": self.low_entry.get() or "20",
            "high_threshold": self.high_entry.get() or "80",
            "check_interval": self.interval_entry.get() or "30",
            "run_on_startup": self.run_on_startup_var.get()
        }
        with open(self.CONFIG_FILE, 'w') as f: json.dump(settings, f)
        print("Settings saved.")

    def _on_closing(self):
        # ... (This function remains unchanged) ...
        if messagebox.askokcancel("Quit", "Do you want to quit the battery monitor?"):
            self._save_settings(); self.is_monitoring = False
            if self.after_id: self.after_cancel(self.after_id)
            self.destroy()

if __name__ == "__main__":
    app = BatteryAlerterApp()
    app.mainloop()