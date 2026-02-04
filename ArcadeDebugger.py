import tkinter as tk
from tkinter import ttk
import threading
import time
import os
import warnings

# ---------------------------------------------------------
# 1. SUPPRESS WARNINGS
# ---------------------------------------------------------
warnings.filterwarnings("ignore", category=UserWarning)

# ---------------------------------------------------------
# DEPENDENCIES
# ---------------------------------------------------------
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    print("WARNING: Pygame not found. Joysticks will not work. (pip install pygame)")
    PYGAME_AVAILABLE = False

try:
    from ArcadeDriver import Arcade, available_ports
except ImportError:
    print("CRITICAL: ArcadeDriver.py not found.")
    class Arcade:
        LEDS = {}
        def __init__(self, port=None): pass
        def set(self, n, c): pass
        def set_all(self, c): pass
        def show(self): pass
        def close(self): pass
        def is_connected(self): return False
    def available_ports(): return []

# ---------------------------------------------------------
# INPUT MAP (Standard: Joy 0 = P1, Joy 1 = P2)
# ---------------------------------------------------------
INPUT_MAP = {
    # Player 1 (Default Joy 0)
    "0_1": "P1_A",      "0_7": "P1_B",      "0_2": "P1_C",
    "0_0": "P1_X",      "0_3": "P1_Y",      "0_5": "P1_Z",
    "0_9": "P1_START",  "0_12": "MENU",     "0_6": "REWIND",
    
    # Player 2 (Default Joy 1)
    "1_1": "P2_A",      "1_7": "P2_B",      "1_2": "P2_C",
    "1_0": "P2_X",      "1_3": "P2_Y",      "1_5": "P2_Z",
    "1_9": "P2_START"
}

class ArcadeDebugger:
    def __init__(self, root):
        self.root = root
        self.root.title("Arcade Input & Hardware Debugger (v5 - Clean Slate)")
        self.root.geometry("1150x700")
        self.root.configure(bg="#121212")

        self.arcade = None 
        self.gui_buttons = {} 
        self.joysticks = []
        
        # Mouse/Spinner Tracking
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.connection_time = 0 
        
        # UI Setup
        self.create_top_bar()
        self.create_button_grid()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # MOUSE LISTENER
        self.root.bind('<Motion>', self.handle_mouse_motion)

        # JOYSTICK LISTENER
        if PYGAME_AVAILABLE:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            pygame.init()
            pygame.display.init()
            pygame.joystick.init()
            threading.Thread(target=self.joystick_listener, daemon=True).start()

    # -----------------------------------------------------
    # UI SETUP
    # -----------------------------------------------------
    def create_top_bar(self):
        top_frame = tk.Frame(self.root, bg="#1e1e1e", pady=15)
        top_frame.pack(fill="x")

        # Port Selector
        tk.Label(top_frame, text="Port:", bg="#1e1e1e", fg="white").pack(side="left", padx=10)
        self.port_var = tk.StringVar()
        cbox = ttk.Combobox(top_frame, textvariable=self.port_var, values=available_ports(), width=10)
        if cbox['values']: cbox.current(0)
        cbox.pack(side="left")

        # Connect Button
        tk.Button(top_frame, text="Connect / Reset", command=self.connect_hardware, 
                  bg="#4CAF50", fg="white", font=("Arial", 10, "bold")).pack(side="left", padx=10)

        # Swap Inputs Checkbox
        self.swap_players_var = tk.BooleanVar(value=False)
        tk.Checkbutton(top_frame, text="Swap P1/P2 Inputs", variable=self.swap_players_var,
                       bg="#1e1e1e", fg="white", selectcolor="#333333", 
                       activebackground="#1e1e1e", activeforeground="white").pack(side="left", padx=20)
        
        self.status_lbl = tk.Label(top_frame, text="Disconnected", bg="#1e1e1e", fg="#FF5555", width=25)
        self.status_lbl.pack(side="left", padx=10)

    def create_button_grid(self):
        main_container = tk.Frame(self.root, bg="#121212")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)

        def make_panel(parent, title, buttons):
            frame = tk.LabelFrame(parent, text=title, bg="#1e1e1e", fg="gray", font=("Arial", 12, "bold"), padx=10, pady=10)
            frame.pack(side="left", fill="both", expand=True, padx=5)
            for row in buttons:
                r_frame = tk.Frame(frame, bg="#1e1e1e")
                r_frame.pack(pady=5)
                for b_name in row:
                    lbl = tk.Label(r_frame, text=b_name, width=12, height=2, 
                                   bg="#333333", fg="white", relief="raised", font=("Arial", 9))
                    lbl.pack(side="left", padx=5)
                    self.gui_buttons[b_name] = lbl

        make_panel(main_container, "PLAYER 1", [
            ["P1_UP"], 
            ["P1_LEFT", "P1_DOWN", "P1_RIGHT"],
            ["P1_A", "P1_B", "P1_C"],
            ["P1_X", "P1_Y", "P1_Z"],
            ["P1_START"]
        ])

        make_panel(main_container, "SYSTEM", [
            ["TRACKBALL"],
            ["SPINNER_X", "SPINNER_Y"],
            ["MENU", "REWIND"]
        ])

        make_panel(main_container, "PLAYER 2", [
            ["P2_UP"],
            ["P2_LEFT", "P2_DOWN", "P2_RIGHT"],
            ["P2_A", "P2_B", "P2_C"],
            ["P2_X", "P2_Y", "P2_Z"],
            ["P2_START"]
        ])

    # -----------------------------------------------------
    # LOGIC: HARDWARE CONNECTION & RESET
    # -----------------------------------------------------
    def connect_hardware(self):
        port = self.port_var.get()
        if self.arcade: self.arcade.close()
        
        # 1. CLEAN SLATE: Reset GUI Buttons to Gray
        print("Resetting GUI...")
        for btn in self.gui_buttons.values():
            btn.configure(bg="#333333", fg="white")

        try:
            self.arcade = Arcade(port=port)
            self.status_lbl.config(text=f"Connected: {port}", fg="#00FF00")
            
            # Timestamp for "Hands Off" delay
            self.connection_time = time.time()
            
            # 2. CLEAN SLATE: Reset Hardware LEDs to White
            threading.Thread(target=self.startup_sequence, daemon=True).start()
        except Exception as e:
            self.status_lbl.config(text=str(e))

    def startup_sequence(self):
        """Forces all LEDs to White on connect."""
        if self.arcade:
            print("System Start: Setting all LEDs to White...")
            self.arcade.set_all((255, 255, 255))
            self.arcade.show()

    # -----------------------------------------------------
    # LOGIC: INPUT HANDLING
    # -----------------------------------------------------
    def handle_mouse_motion(self, event):
        """
        Handles Trackball/Spinner.
        Includes a 2-second 'Hands Off' delay after connect.
        """
        if not (self.arcade and self.arcade.is_connected()): return 
        
        # Buffer to prevent instant triggering on connect
        if (time.time() - self.connection_time) < 2.0:
            self.last_mouse_x = event.x
            self.last_mouse_y = event.y
            return

        # Trackball (Green)
        self.trigger_gui_update("TRACKBALL", lock=True)
        
        # Spinners
        if abs(event.x - self.last_mouse_x) > 2: 
            self.trigger_gui_update("SPINNER_X", lock=True)
        if abs(event.y - self.last_mouse_y) > 2:
            self.trigger_gui_update("SPINNER_Y", lock=True)
            
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y

    def joystick_listener(self):
        while True:
            if not PYGAME_AVAILABLE: break
            
            if not self.joysticks:
                pygame.joystick.quit()
                pygame.joystick.init()
                for i in range(pygame.joystick.get_count()):
                    j = pygame.joystick.Joystick(i)
                    j.init()
                    self.joysticks.append(j)

            try:
                for event in pygame.event.get():
                    if event.type == pygame.JOYBUTTONDOWN:
                        real_joy_id = self.get_swapped_id(event.joy)
                        map_key = f"{real_joy_id}_{event.button}"
                        
                        if map_key in INPUT_MAP:
                            btn_name = INPUT_MAP[map_key]
                            print(f"Input: {btn_name}") # Debug Print
                            self.activate_button(btn_name)

                    elif event.type == pygame.JOYHATMOTION:
                        real_joy_id = self.get_swapped_id(event.joy)
                        self.handle_dpad(real_joy_id, event.value)

                    elif event.type == pygame.JOYAXISMOTION:
                        real_joy_id = self.get_swapped_id(event.joy)
                        self.handle_axis(real_joy_id, event.axis, event.value)
            except Exception as e:
                pass
            
            time.sleep(0.01)

    def get_swapped_id(self, original_id):
        """Swaps 0 and 1 if checkbox is checked."""
        if self.swap_players_var.get():
            return 1 if original_id == 0 else 0
        return original_id

    def handle_dpad(self, joy_id, value):
        prefix = "P1" if joy_id == 0 else "P2"
        x, y = value
        if x == -1: self.trigger_gui_update(f"{prefix}_LEFT", lock=True)
        if x == 1:  self.trigger_gui_update(f"{prefix}_RIGHT", lock=True)
        if y == 1:  self.trigger_gui_update(f"{prefix}_UP", lock=True)
        if y == -1: self.trigger_gui_update(f"{prefix}_DOWN", lock=True)

    def handle_axis(self, joy_id, axis, value):
        if abs(value) < 0.5: return 
        prefix = "P1" if joy_id == 0 else "P2"
        if axis == 0:
            if value < -0.5: self.trigger_gui_update(f"{prefix}_LEFT", lock=True)
            if value > 0.5:  self.trigger_gui_update(f"{prefix}_RIGHT", lock=True)
        elif axis == 1:
            if value < -0.5: self.trigger_gui_update(f"{prefix}_UP", lock=True)
            if value > 0.5:  self.trigger_gui_update(f"{prefix}_DOWN", lock=True)

    def activate_button(self, btn_name):
        # 1. Update GUI
        self.trigger_gui_update(btn_name, lock=True)
        
        # 2. Update Hardware
        if self.arcade and self.arcade.is_connected():
            if btn_name in self.arcade.LEDS:
                threading.Thread(target=self.cycle_led_and_hold_green, args=(btn_name,), daemon=True).start()

    def trigger_gui_update(self, btn_name, lock=False):
        self.root.after(0, lambda: self._gui_turn_green(btn_name, lock))

    def _gui_turn_green(self, btn_name, lock):
        if btn_name in self.gui_buttons:
            self.gui_buttons[btn_name].configure(bg="#00FF00", fg="black")
            if not lock:
                self.root.after(200, lambda: self.gui_buttons[btn_name].configure(bg="#333333", fg="white"))

    def cycle_led_and_hold_green(self, btn_name):
        """RGB Cycle -> Green Hold"""
        try:
            delay = 0.15 # Slightly slower for visibility
            # Red
            self.arcade.set(btn_name, (255, 0, 0))
            self.arcade.show()
            time.sleep(delay)
            # Blue
            self.arcade.set(btn_name, (0, 0, 255))
            self.arcade.show()
            time.sleep(delay)
            # Green (FINAL STATE)
            self.arcade.set(btn_name, (0, 255, 0))
            self.arcade.show()
        except Exception as e:
            print(f"LED Error: {e}")

    def on_closing(self):
        if self.arcade: self.arcade.close()
        if PYGAME_AVAILABLE: pygame.quit()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ArcadeDebugger(root)
    root.mainloop()