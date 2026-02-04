import tkinter as tk
from tkinter import ttk
import threading
import time

# IMPORT YOUR DRIVER
# This expects "ArcadeDriver.py" to be in the same folder
try:
    from ArcadeDriver import Arcade, available_ports
except ImportError:
    print("CRITICAL ERROR: 'ArcadeDriver.py' not found. Please place it in the same folder.")
    exit()

# ==========================================
# KEY MAPPING CONFIGURATION
# ==========================================
# Standard Keyboard Keys -> Arcade Driver Button Names
KEY_MAP = {
    # Player 1
    "Control_L": "P1_A",  "Alt_L": "P1_B",   "space": "P1_C",
    "Shift_L": "P1_X",    "z": "P1_X",       "x": "P1_Y",   "c": "P1_Z", 
    "1": "P1_START",
    
    # Player 2
    "a": "P2_A", "s": "P2_B", "q": "P2_C",
    "w": "P2_X", "i": "P2_Y", "k": "P2_Z",
    "2": "P2_START",
    
    # Utility
    "Tab": "MENU",
    "Escape": "REWIND",
    "Return": "TRACKBALL" # Example mapping for trackball button
}

class ArcadeDebugger:
    def __init__(self, root):
        self.root = root
        self.root.title("Arcade Input & Hardware Debugger")
        self.root.geometry("1000x650")
        self.root.configure(bg="#121212")

        self.arcade = None # This will hold the Arcade driver instance
        self.gui_buttons = {} # Stores UI widgets

        # 1. Setup the GUI Layout
        self.create_top_bar()
        self.create_button_grid()

        # 2. Bind Keyboard Events
        self.root.bind("<KeyPress>", self.handle_keypress)
        
        # 3. Handle Clean Exit (Prevents Serial Lock!)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_top_bar(self):
        """Creates the Connection controls at the top."""
        top_frame = tk.Frame(self.root, bg="#1e1e1e", pady=10)
        top_frame.pack(fill="x")

        tk.Label(top_frame, text="Port:", bg="#1e1e1e", fg="white").pack(side="left", padx=10)

        # Port Dropdown
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(top_frame, textvariable=self.port_var, width=10)
        self.port_combo['values'] = available_ports()
        if self.port_combo['values']:
            self.port_combo.current(0)
        self.port_combo.pack(side="left")

        # Connect Button
        btn_connect = tk.Button(top_frame, text="Connect / Reset", command=self.connect_hardware, 
                                bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        btn_connect.pack(side="left", padx=10)

        # Status Label
        self.status_lbl = tk.Label(top_frame, text="Not Connected", bg="#1e1e1e", fg="#FF5555")
        self.status_lbl.pack(side="left", padx=10)

    def create_button_grid(self):
        """Creates the 3-panel layout."""
        main_container = tk.Frame(self.root, bg="#121212")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Helper to make panels
        def make_panel(parent, title, buttons):
            frame = tk.LabelFrame(parent, text=title, bg="#1e1e1e", fg="gray", font=("Arial", 12, "bold"), padx=10, pady=10)
            frame.pack(side="left", fill="both", expand=True, padx=5)
            for row in buttons:
                r_frame = tk.Frame(frame, bg="#1e1e1e")
                r_frame.pack(pady=5)
                for b_name in row:
                    lbl = tk.Label(r_frame, text=b_name, width=10, height=2, 
                                   bg="#333333", fg="white", relief="raised")
                    lbl.pack(side="left", padx=5)
                    # Check if this button is mapped in the driver
                    if b_name in Arcade.LEDS: # Use the static dict from driver to verify
                        self.gui_buttons[b_name] = lbl
                    elif b_name in ["P1_LEFT", "P1_RIGHT", "P1_UP", "P1_DOWN", "P2_LEFT", "P2_RIGHT", "P2_UP", "P2_DOWN"]:
                         # Keep non-LED buttons in GUI map so we can test input even if they don't light up
                         self.gui_buttons[b_name] = lbl

        # Player 1
        make_panel(main_container, "PLAYER 1", [
            ["P1_LEFT", "P1_DOWN", "P1_RIGHT"],
            ["P1_A", "P1_B", "P1_C"],
            ["P1_X", "P1_Y", "P1_Z"],
            ["P1_START"]
        ])

        # System
        make_panel(main_container, "SYSTEM", [
            ["TRACKBALL"],
            ["MENU", "REWIND"]
        ])

        # Player 2
        make_panel(main_container, "PLAYER 2", [
            ["P2_LEFT", "P2_DOWN", "P2_RIGHT"],
            ["P2_A", "P2_B", "P2_C"],
            ["P2_X", "P2_Y", "P2_Z"],
            ["P2_START"]
        ])

    def connect_hardware(self):
        """Initializes the Arcade driver connection."""
        selected_port = self.port_var.get()
        if not selected_port:
            self.status_lbl.config(text="No Port Selected", fg="red")
            return

        # Close existing if any
        if self.arcade:
            self.arcade.close()
        
        try:
            # Initialize Driver
            self.arcade = Arcade(port=selected_port)
            
            if self.arcade.is_connected():
                self.status_lbl.config(text=f"Connected: {selected_port}", fg="#00FF00")
                # Run Startup Sequence (White Wall)
                threading.Thread(target=self.startup_sequence, daemon=True).start()
            else:
                 self.status_lbl.config(text="Connection Failed", fg="red")
        except Exception as e:
            self.status_lbl.config(text=f"Error: {e}", fg="red")

    def startup_sequence(self):
        """Turns all LEDs White."""
        time.sleep(0.5) # Let connection settle
        if self.arcade:
            print("Setting all LEDs to WHITE")
            self.arcade.set_all((255, 255, 255))
            self.arcade.show()

    def handle_keypress(self, event):
        """Maps Key -> GUI Green -> LED Cycle"""
        key = event.keysym
        print(f"Key Pressed: {key}") # Debugging helper
        
        if key in KEY_MAP:
            btn_name = KEY_MAP[key]
            
            # 1. Update GUI (Green)
            if btn_name in self.gui_buttons:
                self.gui_buttons[btn_name].configure(bg="#00FF00", fg="black")

            # 2. Update Hardware (Cycle RGB)
            if self.arcade and self.arcade.is_connected():
                # Check if this button has an LED mapping in the driver
                if btn_name in self.arcade.LEDS:
                    threading.Thread(target=self.cycle_led, args=(btn_name,), daemon=True).start()

    def cycle_led(self, btn_name):
        """Flashes Red -> Green -> Blue -> White"""
        delay = 0.15
        
        # Red
        self.arcade.set(btn_name, (255, 0, 0))
        self.arcade.show()
        time.sleep(delay)
        
        # Green
        self.arcade.set(btn_name, (0, 255, 0))
        self.arcade.show()
        time.sleep(delay)
        
        # Blue
        self.arcade.set(btn_name, (0, 0, 255))
        self.arcade.show()
        time.sleep(delay)
        
        # Back to White
        self.arcade.set(btn_name, (255, 255, 255))
        self.arcade.show()

    def on_closing(self):
        """Cleanly closes serial port to prevent 'Access Denied' next time."""
        if self.arcade:
            print("Closing Serial Connection...")
            self.arcade.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ArcadeDebugger(root)
    root.mainloop()