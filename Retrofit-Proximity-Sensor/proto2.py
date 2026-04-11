import RPi.GPIO as GPIO
import time
import tkinter as tk

class UltrasonicMonitorApp:
    def __init__(self, root, trig_pin=17, echo_pin=16):
        """Initializes the GUI, Canvas, and GPIO pins."""
        self.root = root
        self.trig_pin = trig_pin
        self.echo_pin = echo_pin
        
        # --- Hardware Setup ---
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.trig_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)
        
        # Settle the trigger pin
        GPIO.output(self.trig_pin, False)
        time.sleep(0.5)

        # --- GUI Setup ---
        self.root.title("Ultrasonic Proximity Radar")
        self.root.geometry("450x450")
        self.root.configure(bg="#2c3e50")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Digital Readout Label
        self.distance_label = tk.Label(
            self.root, 
            text="Distance: -- cm", 
            font=("Helvetica", 20, "bold"), 
            bg="#2c3e50", 
            fg="white"
        )
        self.distance_label.pack(pady=20)

        # --- Canvas for Crescent Indicators ---
        self.canvas = tk.Canvas(
            self.root, 
            width=400, 
            height=300, 
            bg="#2c3e50", 
            highlightthickness=0
        )
        self.canvas.pack()

        # Define colors
        self.color_unlit = "#455A64"  # Dark gray
        self.color_green = "#00E676"
        self.color_yellow = "#FFEA00"
        self.color_orange = "#FF9100"
        self.color_red = "#FF1744"

        # Draw the 4 concentric crescent arcs (Outer to Inner)
        # Coordinates are bounding boxes: (x0, y0, x1, y1)
        # start=45, extent=90 draws the arc at the "top" of the circle
        arc_width = 18
        
        self.arc_outer = self.canvas.create_arc(
            70, 70, 330, 330, start=45, extent=90, style=tk.ARC, width=arc_width, outline=self.color_unlit
        )
        self.arc_mid_out = self.canvas.create_arc(
            110, 110, 290, 290, start=45, extent=90, style=tk.ARC, width=arc_width, outline=self.color_unlit
        )
        self.arc_mid_in = self.canvas.create_arc(
            150, 150, 250, 250, start=45, extent=90, style=tk.ARC, width=arc_width, outline=self.color_unlit
        )
        self.arc_inner = self.canvas.create_arc(
            190, 190, 210, 210, start=45, extent=90, style=tk.ARC, width=arc_width, outline=self.color_unlit
        )

        # Start the continuous update loop
        self.update_gui()

    def get_distance(self):
        """Triggers the sensor and calculates the distance in cm."""
        GPIO.output(self.trig_pin, True)
        time.sleep(0.00001)
        GPIO.output(self.trig_pin, False)

        pulse_start = time.time()
        pulse_end = time.time()

        while GPIO.input(self.echo_pin) == 0:
            pulse_start = time.time()

        while GPIO.input(self.echo_pin) == 1:
            pulse_end = time.time()

        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17150
        
        return round(distance, 1)

    def update_visuals(self, dist):
        """Updates the colors of the crescent blocks based on distance thresholds."""
        # Zone 0: > 100cm (All unlit)
        if dist > 100:
            self.set_arc_colors(0)
        # Zone 1: 75cm to 100cm (Outer Green)
        elif 75 < dist <= 100:
            self.set_arc_colors(1)
        # Zone 2: 50cm to 75cm (Green + Yellow)
        elif 50 < dist <= 75:
            self.set_arc_colors(2)
        # Zone 3: 25cm to 50cm (Green + Yellow + Orange)
        elif 25 < dist <= 50:
            self.set_arc_colors(3)
        # Zone 4: 0cm to 25cm (All Lit - Inner Red)
        elif dist <= 25:
            self.set_arc_colors(4)

    def set_arc_colors(self, level):
        """Helper method to light up the arcs cumulatively."""
        self.canvas.itemconfig(self.arc_outer, outline=self.color_green if level >= 1 else self.color_unlit)
        self.canvas.itemconfig(self.arc_mid_out, outline=self.color_yellow if level >= 2 else self.color_unlit)
        self.canvas.itemconfig(self.arc_mid_in, outline=self.color_orange if level >= 3 else self.color_unlit)
        self.canvas.itemconfig(self.arc_inner, outline=self.color_red if level >= 4 else self.color_unlit)

    def update_gui(self):
        """Main loop: Reads distance, updates text, and updates canvas."""
        try:
            dist = self.get_distance()
            self.distance_label.config(text=f"Distance: {dist} cm")
            self.update_visuals(dist)
            
        except Exception as e:
            self.distance_label.config(text="Sensor Error")
            # If error, turn all blocks gray
            self.set_arc_colors(0)
            print(f"Sensor error: {e}")
        
        # Schedule next update (running slightly faster at 200ms for a more responsive UI)
        self.root.after(50, self.update_gui)

    def on_closing(self):
        """Safely shuts down."""
        print("Cleaning up GPIO and exiting...")
        GPIO.cleanup()
        self.root.destroy()

# --- Main Execution ---
if __name__ == "__main__":
    main_window = tk.Tk()
    app = UltrasonicMonitorApp(main_window)
    main_window.mainloop()