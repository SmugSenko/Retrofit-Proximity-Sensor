import serial
import threading
import tkinter as tk
import time

class ProximityApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Vehicle Proximity Radar")
        
        # Setup Scalable UI Window
        self.master.geometry("600x500")
        self.master.configure(bg="#111111")
        
        self.canvas = tk.Canvas(master, bg="#111111", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Visual Center point (bottom middle)
        self.cx = 300
        self.cy = 400 
        
        # Distance thresholds (mm)
        self.ranges = [
            {"max": 25,  "color": "#FF3333", "radius": 100},  # Close
            {"max": 40, "color": "#FFB833", "radius": 180},  # Mid
            {"max": 55, "color": "#33FF57", "radius": 260}   # Far
        ]
        
        # Sensor Zones
        self.sensor_zones = {
            "Sensor 1": {"start_angle": 95, "extent": 70, "arcs": []}, # Rear Left
            "Sensor 2": {"start_angle": 15, "extent": 70, "arcs": []}  # Rear Right
        }

        self.draw_static_ui()
        
        # Serial Ports - Using your specific port paths
        self.ser1 = self.init_serial('/dev/ttyS0', "Sensor 1")
        self.ser2 = self.init_serial('/dev/ttyAMA3', "Sensor 2")

        self.running = True
        
        if self.ser1:
            threading.Thread(target=self.read_sensor, args=(self.ser1, "Sensor 1"), daemon=True).start()
        if self.ser2:
            threading.Thread(target=self.read_sensor, args=(self.ser2, "Sensor 2"), daemon=True).start()

    def draw_static_ui(self):
        """Draws the radar and car body."""
        for sensor, zone in self.sensor_zones.items():
            start = zone["start_angle"]
            ext = zone["extent"]
            
            for r_info in reversed(self.ranges):
                r = r_info["radius"]
                arc_id = self.canvas.create_arc(
                    self.cx - r, self.cy - r, self.cx + r, self.cy + r,
                    start=start, extent=ext,
                    style=tk.ARC, outline="#333333", width=30
                )
                zone["arcs"].insert(0, {
                    "id": arc_id, 
                    "default_color": "#333333", 
                    "active_color": r_info["color"], 
                    "max_dist": r_info["max"]
                })

        # --- FIX APPLIED HERE ---
        # Removed capstyle and joinstyle which are invalid for rectangles
        self.canvas.create_rectangle(self.cx - 45, self.cy, self.cx + 45, self.cy - 100, 
                                     fill="#222222", outline="#AAAAAA", width=2)
        
        self.canvas.create_text(self.cx, self.cy - 50, text="REAR", fill="#AAAAAA", font=("Arial", 12, "bold"))

        self.text_left = self.canvas.create_text(100, 50, text="Left: -- mm", fill="#FFFFFF", font=("Arial", 16))
        self.text_right = self.canvas.create_text(500, 50, text="Right: -- mm", fill="#FFFFFF", font=("Arial", 16))

    def init_serial(self, port, label):
        try:
            ser = serial.Serial(port, 115200, timeout=0.1)
            # Enable target report mode
            enable_report = bytes.fromhex("FD FC FB FA 04 00 64 00 04 03 02 01")
            ser.write(enable_report)
            time.sleep(0.1)
            print(f"{label} initialized on {port}")
            return ser
        except Exception as e:
            print(f"Error opening {label} on {port}: {e}")
            return None

    def read_sensor(self, ser, sensor_name):
        while self.running and ser:
            try:
                line = ser.readline()
                if not line:
                    continue

                # Parse Text Data
                try:
                    text_data = line.decode('utf-8').strip()
                    if "Range" in text_data:
                        val = text_data.split()[-1]
                        if val.isdigit():
                            self.update_ui(sensor_name, int(val))
                            continue
                except UnicodeDecodeError:
                    pass

                # Parse Hex Data
                if line.startswith(b'\xf4\xf3\xf2\xf1'):
                    if len(line) >= 16:
                        dist_low = line[14]
                        dist_high = line[15]
                        distance_mm = (dist_high << 8) | dist_low
                        self.update_ui(sensor_name, distance_mm)

            except Exception as e:
                print(f"Error reading {ser.port}: {e}")

    def update_ui(self, sensor_name, distance):
        self.master.after(0, lambda: self._render_ui(sensor_name, distance))

    def _render_ui(self, sensor_name, distance):
        # 1. Update the corner text and handle "Out of Range" status
        text_id = self.text_left if sensor_name == "Sensor 1" else self.text_right
        
        if distance > self.ranges[-1]["max"]:
            self.canvas.itemconfig(text_id, text=f"{sensor_name}: Out of Range", fill="#555555")
        elif distance <= 0:
            self.canvas.itemconfig(text_id, text=f"{sensor_name}: No Signal", fill="#FF3333")
        else:
            self.canvas.itemconfig(text_id, text=f"{sensor_name}: {distance} mm", fill="#FFFFFF")

        # 2. Update the Radar Arcs
        zone = self.sensor_zones.get(sensor_name)
        if not zone: return

        # Reset all arcs in this zone to grey (inactive) first
        for arc_data in zone["arcs"]:
            self.canvas.itemconfig(arc_data["id"], outline=arc_data["default_color"])

        # If distance exceeds the furthest range (2000mm) or is 0, we leave them grey
        if distance > self.ranges[-1]["max"] or distance <= 0:
            return

        # Highlight ONLY the specific arc the object is currently in
        # Based on your S3KM1110's 0.15m accuracy, this provides clear spatial feedback
        for arc_data in zone["arcs"]:
            if distance <= arc_data["max_dist"]:
                self.canvas.itemconfig(arc_data["id"], outline=arc_data["active_color"])
                break # Stop at the first (closest) matching band

if __name__ == "__main__":
    root = tk.Tk()
    app = ProximityApp(root)
    root.mainloop()