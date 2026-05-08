#!/usr/bin/env python3
import math
import serial
import threading
import tkinter as tk
import time
import cv2
from PIL import Image, ImageTk
import numpy as np

class ProximityApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Adaptive 360° Radar Hub")
        self.master.geometry("800x600")
        self.master.configure(bg="#000000")
        
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.canvas = tk.Canvas(master, bg="#000000", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.photo = None
        self.video_item = self.canvas.create_image(0, 0, anchor=tk.NW)

        # Scale mappings and colors
        self.ranges = [
            {"max": 25,  "hex": "#FF0000", "bgr": (0, 0, 255),   "scale": 0.4}, # Red
            {"max": 45,  "hex": "#FFFF00", "bgr": (0, 255, 255), "scale": 0.7}, # Yellow
            {"max": 65,  "hex": "#00FF00", "bgr": (0, 255, 0),   "scale": 1.0}  # Green
        ]
        
        # TOP-DOWN RADAR ONLY
        self.sensor_zones = {
            "S1": {"start": 140, "ext": 40}, # Blind Spot L
            "S2": {"start": 75,  "ext": 30}, # Front
            "S3": {"start": 0,   "ext": 40}  # Blind Spot R
        }

        self.current_data = {f"S{i}": -1 for i in range(1, 6)}
        self.last_seen = {f"S{i}": 0 for i in range(1, 6)}

        self.running = True
        self.start_threads()
        self.refresh_display()

    def start_threads(self):
        self.ser_arduino = self.init_serial('/dev/ttyACM0', "Arduino Hub")
        self.ser4 = self.init_serial('/dev/ttyAMA3', "S4")
        self.ser5 = self.init_serial('/dev/ttyAMA2', "S5")

        if self.ser_arduino: threading.Thread(target=self.read_arduino, daemon=True).start()
        if self.ser4: threading.Thread(target=self.read_direct, args=(self.ser4, "S4"), daemon=True).start()
        if self.ser5: threading.Thread(target=self.read_direct, args=(self.ser5, "S5"), daemon=True).start()

    def init_serial(self, port, label):
        try: return serial.Serial(port, 115200, timeout=1)
        except: return None

    def read_arduino(self):
        while self.running:
            try:
                line = self.ser_arduino.readline().decode('utf-8', errors='ignore').strip()
                if "[" in line and "]" in line:
                    content = line[line.rfind("[")+1 : line.rfind("]")]
                    parts = content.split(",")
                    if len(parts) == 3:
                        self.push_data("S1", int(float(parts[0])))
                        self.push_data("S2", int(float(parts[1])))
                        self.push_data("S3", int(float(parts[2])))
            except: continue

    def read_direct(self, ser, key):
        while self.running:
            try:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if "Range" in line:
                    val = line.split("Range")[-1].strip()
                    self.push_data(key, int(val))
            except: continue

    def push_data(self, key, dist):
        self.current_data[key] = dist
        self.last_seen[key] = time.time()

    def refresh_display(self):
        if not self.running: return
        
        now = time.time()
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        
        if w < 10: 
            self.master.after(100, self.refresh_display)
            return

        self.canvas.delete("dynamic")

        # --- 1. TOP-DOWN RADAR ---
        radar_box_h = h * 0.50
        max_radius = int(min(w / 2, radar_box_h) * 0.85)
        cx = w // 2
        cy = max_radius + 15 
        
        v_w, v_h = int(max_radius * 0.15), int(max_radius * 0.25)
        self.canvas.create_rectangle(cx-v_w, cy-v_h, cx+v_w, cy+v_h, outline="#888888", width=1, tags="dynamic")
        self.canvas.create_text(cx, cy, text="FRONT", fill="#888888", font=("Arial", max(8, int(max_radius*0.06)), "bold"), tags="dynamic")

        for key, zone in self.sensor_zones.items():
            dist = self.current_data[key]
            is_fresh = (now - self.last_seen[key] < 0.8)

            for r_info in self.ranges:
                radius = int(max_radius * r_info["scale"])
                is_active = is_fresh and 0 < dist <= r_info["max"]
                
                arc_color = r_info["hex"] if is_active else "#1A2026"
                arc_width = max(3, int(max_radius * 0.03)) if is_active else max(1, int(max_radius * 0.01))

                self.canvas.create_arc(
                    cx - radius, cy - radius, cx + radius, cy + radius,
                    start=zone["start"], extent=zone["ext"], style=tk.ARC, outline=arc_color, width=arc_width, tags="dynamic"
                )

        # --- 2. CAMERA HUD ---
        if self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                box_w, box_h = w * 0.8, h * 0.45
                ar = 4.0 / 3.0
                if box_w / ar <= box_h:
                    cam_w, cam_h = int(box_w), int(box_w / ar)
                else:
                    cam_h, cam_w = int(box_h), int(box_h * ar)
                
                cam_w, cam_h = max(160, cam_w), max(120, cam_h)
                frame = cv2.resize(frame, (cam_w, cam_h))
                
                overlay = frame.copy()
                bumper_cx = cam_w // 2
                bumper_cy = cam_h + int(cam_h * 0.1) 
                
                rear_sensors = [("S4", 190, 260), ("S5", 280, 350)]
                
                for sensor_key, start_angle, end_angle in rear_sensors:
                    dist = self.current_data[sensor_key]
                    is_fresh = (now - self.last_seen[sensor_key] < 0.8)
                    
                    for r_info in self.ranges:
                        # rx determines the horizontal spread (kept wide)
                        rx = int((cam_w // 2) * r_info["scale"])
                        
                        # ry determines the vertical height (capped explicitly at 60% of camera height)
                        max_vertical_reach = cam_h * 0.60
                        ry = int(max_vertical_reach * r_info["scale"])
                        
                        is_active = is_fresh and 0 < dist <= r_info["max"]
                        
                        color = r_info["bgr"] if is_active else (38, 32, 26)
                        thickness = max(2, int(cam_h * 0.02)) if is_active else max(1, int(cam_h * 0.01))
                        
                        cv2.ellipse(overlay, (bumper_cx, bumper_cy), (rx, ry), 0, start_angle, end_angle, color, thickness)
                
                cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)

                cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(cv2image)
                self.photo = ImageTk.PhotoImage(image=img)
                
                vid_x = (w - cam_w) // 2
                vid_y = h - cam_h - 20
                
                pad = 4 
                self.canvas.create_rectangle(
                    vid_x - pad, vid_y - pad, vid_x + cam_w + pad, vid_y + cam_h + pad,
                    outline="#444444", width=2, tags="dynamic"
                )
                lbl_w = max(40, int(cam_w * 0.1))
                self.canvas.create_rectangle(
                    vid_x, vid_y - 12, vid_x + lbl_w, vid_y + 12,
                    fill="#000000", outline="#444444", width=2, tags="dynamic"
                )
                self.canvas.create_text(
                    vid_x + (lbl_w // 2), vid_y, text="REAR", fill="#FFFFFF", 
                    font=("Arial", max(7, int(cam_w * 0.02)), "bold"), tags="dynamic"
                )
                
                self.canvas.itemconfig(self.video_item, image=self.photo)
                self.canvas.coords(self.video_item, vid_x, vid_y)

        self.master.after(30, self.refresh_display)

    def on_closing(self):
        self.running = False
        if self.cap.isOpened(): self.cap.release()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ProximityApp(root)
    root.mainloop()
