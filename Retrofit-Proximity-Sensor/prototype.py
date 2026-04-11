import RPi.GPIO as GPIO
import time
import tkinter as tk

class UltrasonicMonitorApp:
    def __init__(self, root, trig_pin=23, echo_pin=24):
        """Initializes the GUI and the GPIO pins."""
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
        self.root.title("Ultrasonic Distance Monitor")
        self.root.geometry("400x200")
        self.root.configure(bg="#2c3e50")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.title_label = tk.Label(
            self.root, 
            text="Live Distance reading", 
            font=("Helvetica", 16, "bold"), 
            bg="#2c3e50", 
            fg="white"
        )
        self.title_label.pack(pady=20)

        self.distance_label = tk.Label(
            self.root, 
            text="Distance: -- cm", 
            font=("Helvetica", 24), 
            bg="#2c3e50", 
            fg="#00E676"
        )
        self.distance_label.pack(pady=10)

        # Start the continuous update loop
        self.update_gui()

    def get_distance(self):
        """Triggers the sensor and calculates the distance."""
        GPIO.output(self.trig_pin, True)
        time.sleep(0.00001)
        GPIO.output(self.trig_pin, False)

        pulse_start = time.time()
        pulse_end = time.time()

        # Wait for the echo to go high
        while GPIO.input(self.echo_pin) == 0:
            pulse_start = time.time()

        # Wait for the echo to go low
        while GPIO.input(self.echo_pin) == 1:
            pulse_end = time.time()

        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17150
        
        return round(distance, 2)

    def update_gui(self):
        """Reads the distance and updates the Tkinter label."""
        try:
            dist = self.get_distance()
            self.distance_label.config(text=f"Distance: {dist} cm")
        except Exception as e:
            self.distance_label.config(text="Error reading sensor")
            print(f"Sensor error: {e}")
        
        # Schedule this method to run again
        self.root.after(500, self.update_gui)

    def on_closing(self):
        """Cleans up GPIO pins and closes the application safely."""
        print("Cleaning up and exiting...")
        GPIO.cleanup()
        self.root.destroy()

# --- Main Execution ---
if __name__ == "__main__":
    # Create the main window
    main_window = tk.Tk()
    
    # Initialize our application class
    # You can easily change pins here: app = UltrasonicMonitorApp(main_window, trig_pin=17, echo_pin=27)
    app = UltrasonicMonitorApp(main_window)
    
    # Run the application
    main_window.mainloop()