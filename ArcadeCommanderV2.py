import tkinter as tk
from tkinter import colorchooser, messagebox, filedialog
import json
import time
import math
import os
import sys
import threading

# --- TRAY LIBRARY ---
try:
    import pystray
    from pystray import MenuItem as item
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    print("DEBUG: pystray not found. Tray features disabled.")

# --- SUPPRESS WARNINGS ---
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

# --- DEPENDENCY CHECKS ---
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("DEBUG: Pygame not found. Joysticks will not work.")

try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False

try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("DEBUG: PIL (Pillow) not found. Images will not load.")

# =========================================================
#  DRIVER SWAP: V2 NETWORK ADAPTER
# =========================================================
# In V1.4 this was 'from ArcadeDriver import ...'
# In V2.0 we use ServiceAdapter to talk to the Background Service
try:
    from ServiceAdapter import Arcade, available_ports, wheel
except ImportError:
    # Fallback only if ServiceAdapter is missing (Prevents crash)
    print("CRITICAL: ServiceAdapter.py not found! Falling back to Dummy.")
    class Arcade:
        LEDS = {}
        def __init__(self, port=None): pass
        def set(self, n, c): pass
        def set_all(self, c): pass
        def show(self): pass
        def close(self): pass
        def is_connected(self): return False
        def reconnect(self, port): pass
    def available_ports(): return []
    def wheel(p): return (0,0,0)

# --- HARDWARE TESTER IMPORT ---
try:
    from ArcadeTester import quick_sanity_test, button_finder, attract_demo
    TESTER_AVAILABLE = True
except ImportError:
    TESTER_AVAILABLE = False
    print("DEBUG: ArcadeTester.py not found. LED Tests disabled.")

APP_VERSION = "V2.0 (Networked)"

# --- HARDCODED INPUT MAP ---
INPUT_MAP = {
    "0_1": "P1_A",      "0_7": "P1_B",      "0_2": "P1_C",
    "0_0": "P1_X",      "0_3": "P1_Y",      "0_5": "P1_Z",
    "0_9": "P1_START",  "0_12": "MENU",     "0_6": "REWIND",
    "1_1": "P2_A",      "1_7": "P2_B",      "1_2": "P2_C",
    "1_0": "P2_X",      "1_3": "P2_Y",      "1_5": "P2_Z",
    "1_9": "P2_START"
}

def asset_path(filename: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(getattr(sys, "_MEIPASS"), "assets", filename)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    asset_check = os.path.join(base_dir, "assets", filename)
    if os.path.exists(asset_check): return asset_check
    root_check = os.path.join(base_dir, filename)
    if os.path.exists(root_check): return root_check
    return asset_check 

# --- GENERATE CUSTOM ICON (Red with "AC") ---
def create_default_icon():
    width = 64
    height = 64
    bg_color = "#D50000" # Deep Red
    text_color = "white"
    
    image = Image.new('RGB', (width, height), bg_color)
    dc = ImageDraw.Draw(image)
    
    try:
        # Try loading standard Windows bold font
        font = ImageFont.truetype("arialbd.ttf", 32)
    except IOError:
        font = ImageFont.load_default()

    text = "AC"
    bbox = dc.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    x = (width - text_w) // 2
    y = (height - text_h) // 2 - 4
    
    dc.text((x, y), text, fill=text_color, font=font)
    return image

COLORS = {
    "BG": "#121212",
    "SURFACE": "#1E1E1E",
    "SURFACE_LIGHT": "#2C2C2C",
    "P1": "#00E5FF",
    "P2": "#FF0055",
    "SYS": "#FFD700",
    "TEXT": "#FFFFFF",
    "TEXT_DIM": "#888888",
    "SUCCESS": "#00C853",
    "DANGER": "#D50000",
}

class ModernButton(tk.Button):
    def __init__(self, master, hover_color=None, **kwargs):
        self.default_bg = kwargs.get('bg', COLORS["SURFACE_LIGHT"])
        self.hover_bg = hover_color if hover_color else self.adjust_brightness(self.default_bg, 1.25)
        kwargs['relief'] = 'flat'
        kwargs['bd'] = 0
        kwargs['activebackground'] = self.hover_bg
        kwargs['activeforeground'] = kwargs.get('fg', COLORS['TEXT'])
        kwargs['cursor'] = 'hand2'
        super().__init__(master, **kwargs)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
    def on_enter(self, _):
        self['bg'] = self.hover_bg
    def on_leave(self, _):
        self['bg'] = self.default_bg
    def adjust_brightness(self, hex_color, factor):
        try:
            r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
            r = min(int(r * factor), 255)
            g = min(int(g * factor), 255)
            b = min(int(b * factor), 255)
            return f"#{r:02x}{g:02x}{b:02x}"
        except: return hex_color
    def set_base_bg(self, hex_color):
        self.default_bg = hex_color
        self.hover_bg = self.adjust_brightness(hex_color, 1.25)
        self.configure(bg=hex_color, activebackground=self.hover_bg)

class InputTestWindow(tk.Toplevel):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.title("Input & Hardware Test Mode")
        self.geometry("1150x700")
        self.configure(bg="#121212")
        self.controller = controller
        self.gui_buttons = {}
        self.last_mouse_x = 0; self.last_mouse_y = 0
        self.create_top_bar()
        self.create_button_grid()
        self.bind('<Motion>', self.handle_mouse)
        self.init_hardware()
    def init_hardware(self):
        if self.controller.is_connected():
            # Force a clean state before testing
            self.controller.cab.set_all((255, 255, 255)); self.controller.cab.show()
    def create_top_bar(self):
        f = tk.Frame(self, bg="#1E1E1E", pady=10); f.pack(fill="x")
        tk.Label(f, text="TEST MODE", font=("Segoe UI", 14, "bold"), bg="#1E1E1E", fg="#00E5FF").pack(side="left", padx=20)
        self.swap_var = tk.BooleanVar(value=False)
        tk.Checkbutton(f, text="Swap P1/P2 Inputs", variable=self.swap_var, bg="#1E1E1E", fg="white", selectcolor="#333333", activebackground="#1E1E1E", activeforeground="white").pack(side="left", padx=10)
        self.trackball_var = tk.BooleanVar(value=False); self.trackball_enable_time = 0.0
        def on_tb_toggle(): 
            if self.trackball_var.get(): self.trackball_enable_time = time.time()
        tk.Checkbutton(f, text="Enable Trackball/Spinners", variable=self.trackball_var, bg="#1E1E1E", fg="white", selectcolor="#333333", activebackground="#1E1E1E", activeforeground="white", command=on_tb_toggle).pack(side="left", padx=20)
    def create_button_grid(self):
        c = tk.Frame(self, bg="#121212"); c.pack(fill="both", expand=True, padx=20, pady=20)
        def panel(title, btns):
            f = tk.LabelFrame(c, text=title, bg="#1E1E1E", fg="#888", font=("Segoe UI", 12, "bold"), padx=10, pady=10)
            f.pack(side="left", fill="both", expand=True, padx=5)
            for row in btns:
                rf = tk.Frame(f, bg="#1E1E1E"); rf.pack(pady=5)
                for b in row:
                    l = tk.Label(rf, text=b, width=11, height=2, bg="#333333", fg="white", relief="raised", font=("Segoe UI", 9))
                    l.pack(side="left", padx=5); self.gui_buttons[b] = l
        panel("PLAYER 1", [["P1_UP"], ["P1_LEFT", "P1_DOWN", "P1_RIGHT"], ["P1_A", "P1_B", "P1_C"], ["P1_X", "P1_Y", "P1_Z"], ["P1_START"]])
        panel("SYSTEM", [["TRACKBALL"], ["SPINNER_X", "SPINNER_Y"], ["MENU", "REWIND"]])
        panel("PLAYER 2", [["P2_UP"], ["P2_LEFT", "P2_DOWN", "P2_RIGHT"], ["P2_A", "P2_B", "P2_C"], ["P2_X", "P2_Y", "P2_Z"], ["P2_START"]])
    def handle_pygame_event(self, event):
        if event.type == pygame.JOYBUTTONDOWN:
            real_id = (1 if event.joy == 0 else 0) if self.swap_var.get() else event.joy
            key = f"{real_id}_{event.button}"
            if key in INPUT_MAP: self.activate_button(INPUT_MAP[key])
        elif event.type == pygame.JOYHATMOTION:
            real_id = (1 if event.joy == 0 else 0) if self.swap_var.get() else event.joy
            self.handle_dpad(real_id, event.value)
        elif event.type == pygame.JOYAXISMOTION:
            real_id = (1 if event.joy == 0 else 0) if self.swap_var.get() else event.joy
            self.handle_axis(real_id, event.axis, event.value)
    def handle_mouse(self, event):
        if not self.trackball_var.get(): 
            self.last_mouse_x, self.last_mouse_y = event.x, event.y; return
        if (time.time() - self.trackball_enable_time) < 2.0: 
            self.last_mouse_x, self.last_mouse_y = event.x, event.y; return
        self.gui_flash("TRACKBALL", lock=True)
        if abs(event.x - self.last_mouse_x) > 2: self.gui_flash("SPINNER_X", lock=True)
        if abs(event.y - self.last_mouse_y) > 2: self.gui_flash("SPINNER_Y", lock=True)
        self.last_mouse_x, self.last_mouse_y = event.x, event.y
    def handle_dpad(self, joy, val):
        p = "P1" if joy == 0 else "P2"; x, y = val
        if x == -1: self.gui_flash(f"{p}_LEFT", lock=True)
        if x == 1: self.gui_flash(f"{p}_RIGHT", lock=True)
        if y == 1: self.gui_flash(f"{p}_UP", lock=True)
        if y == -1: self.gui_flash(f"{p}_DOWN", lock=True)
    def handle_axis(self, joy, axis, val):
        if abs(val) < 0.5: return
        p = "P1" if joy == 0 else "P2"
        if axis == 0:
            if val < -0.5: self.gui_flash(f"{p}_LEFT", lock=True)
            if val > 0.5: self.gui_flash(f"{p}_RIGHT", lock=True)
        elif axis == 1:
            if val < -0.5: self.gui_flash(f"{p}_UP", lock=True)
            if val > 0.5: self.gui_flash(f"{p}_DOWN", lock=True)
    def activate_button(self, name):
        self.gui_flash(name, lock=True)
        if self.controller.is_connected() and name in self.controller.cab.LEDS:
            threading.Thread(target=self.cycle_led, args=(name,), daemon=True).start()
    def gui_flash(self, name, lock=False):
        if name in self.gui_buttons:
            self.gui_buttons[name].configure(bg="#00FF00", fg="black")
            if not lock: self.after(200, lambda: self.gui_buttons[name].configure(bg="#333333", fg="white"))
    def cycle_led(self, name):
        try:
            cab = self.controller.cab
            cab.set(name, (255,0,0)); cab.show(); time.sleep(0.1)
            cab.set(name, (0,0,255)); cab.show(); time.sleep(0.1)
            cab.set(name, (0,255,0)); cab.show()
        except: pass

# =========================================================
#  MAIN APPLICATION
# =========================================================
class ArcadeGUI_V2:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()
        self.force_exit = False
        
        self.pulse_controls = {} 

        if PYGAME_AVAILABLE:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            pygame.init(); pygame.display.init(); pygame.joystick.init()
            if WINSOUND_AVAILABLE: pygame.mixer.init()

        self.setup_tray_icon()
        self.show_splash()

    def setup_tray_icon(self):
        if not TRAY_AVAILABLE: return
        
        image = create_default_icon()
        
        def on_open(icon, item):
            self.root.after(0, self.root.deiconify)
        
        def on_toggle_conn(icon, item):
            self.root.after(0, self.toggle_connection_from_tray)

        def on_stop_all(icon, item):
            self.root.after(0, self.all_off)
            
        def on_quit(icon, item):
            self.force_exit = True
            icon.stop()
            self.root.after(0, self.root.quit)

        menu = pystray.Menu(
            item('Open Arcade Commander', on_open, default=True),
            item(lambda text: 'Disconnect' if self.is_connected() else 'Connect', on_toggle_conn),
            item('Stop All LEDs', on_stop_all),
            item('Quit', on_quit)
        )

        self.icon = pystray.Icon("ArcadeCommander", image, "Arcade Commander", menu)
        
        try:
            self.icon.run_detached()
        except AttributeError:
            threading.Thread(target=self.icon.run, daemon=True).start()

    def show_splash(self):
        self.splash = tk.Toplevel(self.root)
        self.splash.overrideredirect(True)
        path = asset_path("ArcadeCommanderSplash.jpg")
        
        if os.path.exists(path) and PIL_AVAILABLE:
            try:
                img = Image.open(path)
                self.splash_img = ImageTk.PhotoImage(img)
                sw = self.root.winfo_screenwidth()
                sh = self.root.winfo_screenheight()
                w, h = img.width, img.height
                x, y = (sw - w) // 2, (sh - h) // 2
                self.splash.geometry(f"{w}x{h}+{x}+{y}")
                tk.Label(self.splash, image=self.splash_img, bg="black", bd=0).pack()
                snd = asset_path("SystemReady.wav")
                if os.path.exists(snd) and PYGAME_AVAILABLE:
                    try: pygame.mixer.Sound(snd).play()
                    except: pass
            except: pass
        else:
            self.splash.geometry("400x200")
            tk.Label(self.splash, text="LOADING...", bg="black", fg="white", font=("Arial", 20)).pack(expand=True)
        self.root.after(3000, self.initialize_app)

    def initialize_app(self):
        try:
            self.splash.destroy()
            self.root.deiconify()
            self.root.title(f"ARCADE COMMANDER [{APP_VERSION}]")
            self.root.configure(bg=COLORS["BG"])
            self.root.geometry("1100x820")
            
            self.test_window = None 
            self.config_file = "last_profile.cfg"
            self.settings_file = "ac_settings.json"
            self.port = self.load_settings().get("port", None)
            
            # --- V2 CONNECTION LOGIC ---
            # We default to the ServiceAdapter, which auto-connects to localhost
            self.cab = Arcade(port=self.port) 
            if not hasattr(self.cab, 'LEDS'):
                self.cab.LEDS = {"P1_A":0, "P1_B":1, "P1_C":2, "P1_X":3, "P1_Y":4, "P1_Z":5, "P1_START":13, "MENU":14}

            self.joysticks = []
            if PYGAME_AVAILABLE: self.refresh_joysticks()
            
            self.buttons = {}
            self.master_refs = []
            self.led_state = {}
            for name in self.cab.LEDS.keys():
                self.led_state[name] = {'primary': (0, 0, 0), 'secondary': (0, 0, 0), 'pulse': False, 'speed': 1.0, 'phase': 0.0}
            
            self.animating = False; self.mapping_mode = False; self.diag_mode = False
            self.attract_active = False; self.last_activity_ts = time.time(); self._attract_offset = 0
            self.status_var = tk.StringVar(value="Initializing...")
            
            self.build_header()
            self.build_banner()
            
            self.main_container = tk.Frame(self.root, bg=COLORS["BG"])
            self.main_container.pack(expand=True, fill="both", padx=20, pady=10)
            self.main_container.columnconfigure(0, weight=1)
            self.main_container.columnconfigure(1, weight=1)
            self.main_container.columnconfigure(2, weight=1)
            
            self.build_player_card(0, "PLAYER 1", COLORS["P1"], ["P1_A", "P1_B", "P1_C", "P1_X", "P1_Y", "P1_Z", "P1_START"])
            self.build_system_card(1)
            self.build_player_card(2, "PLAYER 2", COLORS["P2"], ["P2_A", "P2_B", "P2_C", "P2_X", "P2_Y", "P2_Z", "P2_START"])
            
            self.build_utilities()
            self.build_status_strip()
            
            if not self.is_connected():
                # In V2, we prompt for port less aggressively since Service handles it
                # But we still check connectivity
                pass 
            
            if not os.path.exists(self.config_file) and not os.path.exists("default.json"):
                self.create_default_profile()
            self.autoload_last_profile()
            
            self.start_pulse_engine()
            self.check_inputs()
            self.start_idle_watchdog()
            self.update_status_loop()
            
            self.root.bind_all("<Key>", lambda e: self.note_activity())
            self.root.bind_all("<Button>", lambda e: self.note_activity())
            
        except Exception as e:
            messagebox.showerror("CRITICAL ERROR", f"Init failed:\n{e}")

    # --- Core Logic ---
    def load_settings(self):
        try:
            with open(self.settings_file, "r") as f: return json.load(f)
        except: return {}
    def save_settings(self, data):
        try:
            with open(self.settings_file, "w") as f: json.dump(data, f, indent=2)
        except: pass
    def is_connected(self):
        try: return self.cab.is_connected()
        except: return False
    def set_port(self, port):
        self.port = port; self.save_settings({"port": port})
        try: self.cab.reconnect(port)
        except: self.cab = Arcade(port=port)
        self.apply_settings_to_hardware()
    def prompt_for_port(self, initial=False):
        ports = available_ports(); win = tk.Toplevel(self.root)
        win.title("Select Port"); win.geometry("400x240")
        tk.Label(win, text="Select PicoCTR COM Port", font=("Segoe UI", 12, "bold")).pack(pady=10)
        box = tk.Listbox(win, height=5); box.pack(fill="x", padx=20)
        for p in ports: box.insert("end", p)
        def apply():
            if box.curselection(): self.set_port(box.get(box.curselection()[0])); win.destroy()
        ModernButton(win, text="CONNECT", bg=COLORS["SUCCESS"], command=apply).pack(pady=10)
        if initial: win.protocol("WM_DELETE_WINDOW", apply)
    
    # --- Tray Helpers ---
    def toggle_connection_from_tray(self):
        if self.is_connected():
            self.cab.close()
        else:
            if self.port: self.set_port(self.port)
            else: self.root.deiconify(); self.prompt_for_port() 

    def refresh_joysticks(self):
        self.joysticks = []
        pygame.joystick.quit(); pygame.joystick.init()
        for i in range(pygame.joystick.get_count()):
            j = pygame.joystick.Joystick(i); j.init(); self.joysticks.append(j)
    def check_inputs(self):
        if PYGAME_AVAILABLE:
            for event in pygame.event.get():
                if event.type in [pygame.JOYBUTTONDOWN, pygame.JOYAXISMOTION, pygame.JOYHATMOTION]: self.note_activity()
                if self.test_window and self.test_window.winfo_exists(): self.test_window.handle_pygame_event(event)
        self.root.after(16, self.check_inputs)

    # --- UI Builders (Headers/Banners) ---
    def _rgb_to_hex(self, r, g, b): return f"#{int(r):02x}{int(g):02x}{int(b):02x}"
    def _blend(self, c1, c2, t): return (int(c1[0]+(c2[0]-c1[0])*t), int(c1[1]+(c2[1]-c1[1])*t), int(c1[2]+(c2[2]-c1[2])*t))
    def _title_anim_step(self):
        if not getattr(self, "_title_anim_running", False): return
        phase = getattr(self, "_title_anim_phase", 0.0)
        for i, (main, glow) in enumerate(getattr(self, "_title_letters", [])):
            t = (math.sin(phase + i * 0.35) + 1.0) / 2.0
            r, g, b = self._blend((0, 229, 255), (255, 0, 85), t)
            main.configure(fg=self._rgb_to_hex(r,g,b)); glow.configure(fg=self._rgb_to_hex(int(r*0.3),int(g*0.3),int(b*0.3)))
        self._title_anim_phase = phase + 0.06; self.root.after(30, self._title_anim_step)
    def build_header(self):
        h = tk.Frame(self.root, bg=COLORS["BG"]); h.pack(fill="x", pady=(14,2), padx=30)
        tf = tk.Frame(h, bg=COLORS["BG"]); tf.pack(side="left")
        self._title_letters = []
        for ch in "ARCADE COMMANDER":
            if ch == " ": tk.Label(tf, text=" ", bg=COLORS["BG"], font=("Segoe UI", 18)).pack(side="left"); continue
            cell = tk.Frame(tf, bg=COLORS["BG"]); cell.pack(side="left")
            glow = tk.Label(cell, text=ch, font=("Segoe UI", 18, "bold"), bg=COLORS["BG"], fg=COLORS["TEXT"])
            main = tk.Label(cell, text=ch, font=("Segoe UI", 18, "bold"), bg=COLORS["BG"], fg=COLORS["TEXT"])
            glow.grid(row=0, column=0, padx=(1,0), pady=(1,0)); main.grid(row=0, column=0)
            self._title_letters.append((main, glow))
        tk.Label(h, text=f"{APP_VERSION}", font=("Consolas", 10), bg=COLORS["BG"], fg=COLORS["P1"]).pack(side="left", padx=12)
        self._title_anim_phase = 0.0; self._title_anim_running = True; self._title_anim_step()
    def build_banner(self):
        wrap = tk.Frame(self.root, bg=COLORS["BG"]); wrap.pack(fill="x", padx=30, pady=(0,10))
        path = asset_path("ArcadeCommanderBanner.png")
        if os.path.exists(path) and PIL_AVAILABLE:
            try:
                self._banner_img = ImageTk.PhotoImage(Image.open(path))
                tk.Label(wrap, image=self._banner_img, bg=COLORS["BG"]).pack(anchor="w")
            except Exception as e: print(f"Banner Load Error: {e}")
        else: print(f"DEBUG: Banner missing at {path}")
    def build_card_frame(self, col, title, accent):
        b = tk.Frame(self.main_container, bg=accent, padx=1, pady=1)
        b.grid(row=0, column=col, sticky="nsew", padx=10, pady=10)
        c = tk.Frame(b, bg=COLORS["SURFACE"]); c.pack(fill="both", expand=True)
        tk.Label(c, text=title, font=("Segoe UI", 11, "bold"), bg=COLORS["SURFACE"], fg=accent, pady=10).pack(fill="x")
        return c
    def build_player_card(self, col, title, color, btns):
        card = self.build_card_frame(col, title, color)
        ctrl = tk.Frame(card, bg=COLORS["SURFACE_LIGHT"]); ctrl.pack(fill="x", padx=12, pady=(0, 10))
        left = tk.Frame(ctrl, bg=COLORS["SURFACE_LIGHT"]); left.pack(side="left", padx=10, pady=10)
        p_btn = ModernButton(left, text="PRIMARY", bg=color, fg="black", width=12)
        p_btn.config(command=lambda b=p_btn: self.set_group_color(btns, 'primary', b))
        p_btn.pack(side="left", padx=5)
        self.master_refs.append({'btn': p_btn, 'group': btns, 'mode': 'primary'})
        s_btn = ModernButton(left, text="SECONDARY", width=12)
        s_btn.config(command=lambda b=s_btn: self.set_group_color(btns, 'secondary', b))
        s_btn.pack(side="left", padx=5)
        self.master_refs.append({'btn': s_btn, 'group': btns, 'mode': 'secondary'})
        right = tk.Frame(ctrl, bg=COLORS["SURFACE_LIGHT"]); right.pack(side="right", padx=10, pady=10)
        self.create_pulse_toggle(right, btns, color)
        g = tk.Frame(card, bg=COLORS["SURFACE"], pady=10); g.pack()
        r, ci = 0, 0
        for b in btns:
            if "START" in b: continue
            self.create_visual_btn(g, b, r, ci); ci += 1
            if ci > 2: ci = 0; r += 1
        self.create_visual_btn(card, [b for b in btns if "START" in b][0], 0, 0, pack=True, width=12)
    def build_system_card(self, col):
        card = self.build_card_frame(col, "SYSTEM", COLORS["SYS"])
        sys_btns = ["TRACKBALL", "MENU", "REWIND"]
        ctrl = tk.Frame(card, bg=COLORS["SURFACE_LIGHT"]); ctrl.pack(fill="x", padx=12, pady=(0, 10))
        ci = tk.Frame(ctrl, bg=COLORS["SURFACE_LIGHT"]); ci.pack(pady=10)
        p_btn = ModernButton(ci, text="PRIMARY", bg=COLORS["SYS"], fg="black", width=10)
        p_btn.config(command=lambda b=p_btn: self.set_group_color(sys_btns, 'primary', b))
        p_btn.pack(side="left", padx=4)
        self.master_refs.append({'btn': p_btn, 'group': sys_btns, 'mode': 'primary'})
        s_btn = ModernButton(ci, text="SECONDARY", width=10)
        s_btn.config(command=lambda b=s_btn: self.set_group_color(sys_btns, 'secondary', b))
        s_btn.pack(side="left", padx=4)
        self.master_refs.append({'btn': s_btn, 'group': sys_btns, 'mode': 'secondary'})
        tk.Label(card, text="BALL", bg=COLORS["SURFACE"], fg=COLORS["TEXT_DIM"]).pack(pady=(15,5))
        self.create_visual_btn(card, "TRACKBALL", 0, 0, pack=True, width=14, height=3)
        self.create_pulse_toggle(card, ["TRACKBALL"], COLORS["SYS"])
        tk.Label(card, text="ADMIN", bg=COLORS["SURFACE"], fg=COLORS["TEXT_DIM"]).pack(pady=(15,5))
        ar = tk.Frame(card, bg=COLORS["SURFACE"]); ar.pack()
        self.create_visual_btn(ar, "REWIND", 0, 0, width=10); self.create_visual_btn(ar, "MENU", 0, 1, width=10)
        tk.Label(card, text="PROFILES", bg=COLORS["SURFACE"], fg=COLORS["TEXT_DIM"]).pack(pady=(15,5))
        pr = tk.Frame(card, bg=COLORS["SURFACE"]); pr.pack(pady=5)
        ModernButton(pr, text="SAVE", bg=COLORS["SUCCESS"], fg="white", width=8, command=self.save_profile).pack(side="left", padx=5)
        ModernButton(pr, text="LOAD", width=8, command=self.load_profile).pack(side="left", padx=5)
    def build_utilities(self):
        bar = tk.Frame(self.root, bg=COLORS["SURFACE"], height=70); bar.pack(side="bottom", fill="x")
        inner = tk.Frame(bar, bg=COLORS["SURFACE"]); inner.pack(pady=18)
        def sep(): tk.Frame(inner, bg=COLORS["SURFACE_LIGHT"], width=1, height=22).pack(side="left", padx=10)
        def btn(t, c, cmd, w=10, f="white"): 
            b = ModernButton(inner, text=t, bg=c, fg=f, width=w, font=("Segoe UI", 8, "bold"), command=cmd)
            b.pack(side="left", padx=4); return b
        btn("APPLY", COLORS["SYS"], self.apply_settings_to_hardware, w=10, f="black"); sep()
        btn("ALL OFF", COLORS["DANGER"], self.all_off, w=9)
        btn("BTN TEST", COLORS["SURFACE_LIGHT"], self.open_button_test, w=9); sep()
        btn("SWAP FIGHT", COLORS["P1"], self.swap_fight_buttons, w=10)
        btn("SWAP START", COLORS["P2"], self.swap_start_buttons, w=10); sep()
        btn("LED TEST", COLORS["SYS"], self.show_tester_menu, w=9, f="black")
        btn("CYCLE", COLORS["SURFACE_LIGHT"], self.start_cycle_mode, w=8)
        btn("DEMO", COLORS["SURFACE_LIGHT"], self.start_demo_mode, w=8); sep()
        self.port_btn = btn("PORT", COLORS["SURFACE_LIGHT"], lambda: self.prompt_for_port(), w=8)
        btn("ABOUT", COLORS["SURFACE_LIGHT"], self.show_about, w=8)
    def build_status_strip(self):
        s = tk.Frame(self.root, bg=COLORS["BG"]); s.pack(side="bottom", fill="x", padx=30, pady=5)
        self.status_lbl = tk.Label(s, textvariable=self.status_var, bg=COLORS["BG"], fg=COLORS["TEXT_DIM"])
        self.status_lbl.pack(side="right")
    def update_status_loop(self):
        connected = self.is_connected()
        c_txt = "CONNECTED" if connected else "DISCONNECTED"
        m_txt = "TESTING" if (self.test_window and self.test_window.winfo_exists()) else ("ANIM" if self.animating else ("DIAG" if self.diag_mode else ("ATTRACT" if self.attract_active else "IDLE")))
        if connected:
            self.status_lbl.config(fg=COLORS["SUCCESS"]); self.port_btn.set_base_bg(COLORS["SUCCESS"])
        else:
            self.status_lbl.config(fg=COLORS["TEXT_DIM"]); self.port_btn.set_base_bg(COLORS["DANGER"])
        self.status_var.set(f"{c_txt} on {getattr(self.cab,'port',self.port)} | Mode: {m_txt}")
        self.root.after(500, self.update_status_loop)
    def create_visual_btn(self, p, n, r, c, pack=False, width=6, height=2):
        l = "BALL" if n == "TRACKBALL" else n.split("_")[-1]
        b = ModernButton(p, text=l, width=width, height=height)
        b.bind("<Button-1>", lambda e: self.show_context_menu(e, n)); self.buttons[n] = b
        if pack: b.pack(pady=2)
        else: b.grid(row=r, column=c, padx=4, pady=4)
    def create_pulse_toggle(self, p, bl, tc):
        v = tk.BooleanVar()
        grp_name = bl[0] 
        self.pulse_controls[grp_name] = {'var': v, 'buttons': bl}
        def toggle(): 
            for b in bl: self.led_state[b]['pulse'] = v.get()
        tk.Checkbutton(p, text="PULSE", variable=v, bg=COLORS["SURFACE"], fg=tc, selectcolor=COLORS["SURFACE"], command=toggle).pack()
        s = tk.Scale(p, from_=0.2, to=3.0, resolution=0.1, orient="horizontal", bg=COLORS["SURFACE"], fg=tc, showvalue=0, length=120, command=lambda val: [self.led_state[b].update({'speed': float(val)}) for b in bl])
        s.set(1.0); s.pack()
        self.pulse_controls[grp_name]['scale'] = s

    def show_context_menu(self, e, n):
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label=f"Edit {n} Primary", command=lambda: self.pick_color(n, 'primary'))
        m.add_command(label=f"Edit {n} Secondary", command=lambda: self.pick_color(n, 'secondary'))
        m.add_separator()
        m.add_command(label="HARDWARE TEST", command=lambda: self.run_button_test(n))
        m.post(e.x_root, e.y_root)
    def pick_color(self, n, mode):
        c = colorchooser.askcolor()[0]
        if c:
            rgb = tuple(map(int, c)); self.led_state[n][mode] = rgb
            if mode == 'primary': self.buttons[n].set_base_bg('#{:02x}{:02x}{:02x}'.format(*rgb))
            if self.is_connected() and not self.led_state[n]['pulse']: self.cab.set(n, rgb); self.cab.show()
    def set_group_color(self, bl, mode, btn_ref=None):
        initial = None
        if btn_ref:
            try: initial = btn_ref.cget('bg')
            except: pass
        c = colorchooser.askcolor(color=initial, title=f"Pick Master {mode}")
        if c[0]:
            rgb = (int(c[0][0]), int(c[0][1]), int(c[0][2]))
            if btn_ref: btn_ref.set_base_bg(c[1])
            for n in bl:
                self.led_state[n][mode] = rgb
                if mode == 'primary' and n in self.buttons: self.buttons[n].set_base_bg(c[1])
            if self.is_connected(): 
                for n in bl: self.cab.set(n, rgb)
                self.cab.show()
    def open_button_test(self):
        if self.test_window and self.test_window.winfo_exists(): self.test_window.lift(); return
        self.animating = False; self.attract_active = False
        self.test_window = InputTestWindow(self.root, self)
        def on_test_close(): self.test_window.destroy(); self.apply_settings_to_hardware()
        self.test_window.protocol("WM_DELETE_WINDOW", on_test_close)
    def show_tester_menu(self, event=None):
        if not TESTER_AVAILABLE: messagebox.showerror("Error", "ArcadeTester.py not found."); return
        m = tk.Menu(self.root, tearoff=0, bg=COLORS["SURFACE_LIGHT"], fg="white")
        m.add_command(label="Quick Sanity Test (Pin 1 & 17)", command=lambda: self.run_external_test(quick_sanity_test))
        m.add_command(label="Pin Finder (Cycle RGBW)", command=lambda: self.run_external_test(button_finder))
        m.add_command(label="Attract Mode (Rainbow)", command=lambda: self.run_external_test(attract_demo))
        if event: m.post(event.x_root, event.y_root)
        else: x, y = self.root.winfo_pointerxy(); m.post(x, y)
    def run_external_test(self, test_func):
        if not self.is_connected(): messagebox.showerror("Error", "Controller not connected."); return
        self.animating = False; self.mapping_mode = False; self.diag_mode = True
        self.hw_set_all((0,0,0)); self.hw_show()
        def _thread_target():
            try: test_func(self.cab)
            except Exception as e: print(f"Test Error: {e}")
            finally:
                def _restore(): self.diag_mode = False; self.apply_settings_to_hardware()
                self.root.after(0, _restore)
        threading.Thread(target=_thread_target, daemon=True).start()

    def start_pulse_engine(self):
        def loop():
            test_active = (self.test_window and self.test_window.winfo_exists())
            if not any([self.animating, test_active, self.diag_mode]):
                upd = False
                for n, d in self.led_state.items():
                    if d.get('pulse'):
                        upd = True; d['phase'] += 0.1 * d.get('speed', 1.0)
                        f = (math.sin(d['phase'])+1)/2; c1, c2 = d['primary'], d['secondary']
                        self.cab.set(n, (int(c1[0]+(c2[0]-c1[0])*f), int(c1[1]+(c2[1]-c1[1])*f), int(c1[2]+(c2[2]-c1[2])*f)))
                if upd: self.cab.show()
            if not self.force_exit: self.root.after(30, loop)
        loop()

    def note_activity(self):
        self.last_activity_ts = time.time()
        if self.attract_active:
            self.attract_active = False; self.apply_settings_to_hardware()

    def apply_settings_to_hardware(self):
        self.animating = False; self.attract_active = False
        if not self.is_connected(): return
        self.cab.set_all((0,0,0)) 
        for n, d in self.led_state.items():
            self.cab.set(n, d['primary'])
        self.cab.show()

    def all_off(self):
        self.animating = False
        self.attract_active = False
        for n in self.led_state: self.led_state[n]['pulse'] = False
        for k in self.pulse_controls:
            self.pulse_controls[k]['var'].set(False)
        self.cab.set_all((0,0,0)); self.cab.show()

    def swap_fight_buttons(self):
        m = self.cab.LEDS
        for s in ["_A", "_B", "_C", "_X", "_Y", "_Z"]:
            p1, p2 = "P1"+s, "P2"+s
            m[p1], m[p2] = m[p2], m[p1]
        self.apply_settings_to_hardware(); messagebox.showinfo("Done", "Buttons Swapped")

    def swap_start_buttons(self):
        m = self.cab.LEDS
        m["P1_START"], m["P2_START"] = m["P2_START"], m["P1_START"]
        self.apply_settings_to_hardware(); messagebox.showinfo("Done", "Start Swapped")

    def start_cycle_mode(self): self.animating = True; self._cycle_step = 0; self._run_cycle()
    def _run_cycle(self):
        if not self.animating: return
        self.cab.set_all([(255,0,0),(0,255,0),(0,0,255),(255,255,255)][self._cycle_step % 4])
        self.cab.show(); self._cycle_step += 1; self.root.after(1000, self._run_cycle)

    def start_demo_mode(self): self.animating = True; self._run_demo()
    def _run_demo(self):
        if not self.animating: return
        import random
        for k in self.cab.LEDS: self.cab.set(k, (random.randint(0,255), random.randint(0,255), random.randint(0,255)))
        self.cab.show(); self.root.after(150, self._run_demo)

    def start_idle_watchdog(self): self.idle_watchdog_loop()
    def idle_watchdog_loop(self):
        test_active = (self.test_window and self.test_window.winfo_exists())
        if not any([test_active, self.diag_mode]):
            if time.time() - self.last_activity_ts > 600 and not self.attract_active: self.start_attract_mode()
        if not self.force_exit: self.root.after(5000, self.idle_watchdog_loop)

    def start_attract_mode(self):
        if not self.is_connected(): return
        self.attract_active = True; self.animating = False; self._attract_offset = 0; self.attract_tick()

    def attract_tick(self):
        if not self.attract_active or not self.is_connected(): return
        off = self._attract_offset
        for i in range(12): self.cab.pixels[i] = wheel((i*20 + off)%255)
        pulse = int((math.sin(time.time()*3)+1)*127.5)
        self.cab.set("P1_START", (pulse,0,0)); self.cab.set("P2_START", (0,0,pulse))
        self.cab.show(); self._attract_offset = (off+2)%255; self.root.after(30, self.attract_tick)

    def show_about(self): messagebox.showinfo("About", f"Arcade Commander {APP_VERSION}")
    
    def create_default_profile(self):
        defaults = {}
        for k in self.cab.LEDS.keys():
            if k.startswith("P1_") and k != "P1_START": 
                defaults[k] = {'primary': (0,0,255), 'secondary': (0,0,0), 'pulse': False, 'speed': 1.0}
            elif k.startswith("P2_") and k != "P2_START": 
                defaults[k] = {'primary': (255,0,0), 'secondary': (0,0,0), 'pulse': False, 'speed': 1.0}
            else: 
                defaults[k] = {'primary': (255,255,255), 'secondary': (0,0,0), 'pulse': False, 'speed': 1.0}
        defaults["MENU"] = {'primary': (255,255,255), 'secondary':(0,0,0), 'pulse':False, 'speed':1.0}
        defaults["REWIND"] = {'primary': (255,0,0), 'secondary':(0,0,0), 'pulse':False, 'speed':1.0}
        defaults["P1_START"] = {'primary': (255,255,255), 'secondary':(0,0,0), 'pulse':False, 'speed':1.0}
        defaults["P2_START"] = {'primary': (255,255,255), 'secondary':(0,0,0), 'pulse':False, 'speed':1.0}
        try:
            with open("default.json", "w") as f:
                json.dump({"leds": defaults}, f, indent=4)
            self.load_profile_internal("default.json", silent=True)
        except Exception as e:
            print(f"DEBUG: Failed to save default profile: {e}")

    def autoload_last_profile(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f: p = f.read().strip()
                if os.path.exists(p): self.load_profile_internal(p, silent=True)
            except: pass
    def update_last_profile_path(self, path):
        try:
            with open(self.config_file, "w") as f: f.write(path)
        except: pass
    def save_profile(self):
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Profile", "*.json")])
        if f:
            with open(f, "w") as j: json.dump({"leds": self.led_state}, j, indent=4)
            self.update_last_profile_path(f); messagebox.showinfo("Saved", "Profile Saved")
    def load_profile(self):
        f = filedialog.askopenfilename(filetypes=[("Profile", "*.json")])
        if f: self.load_profile_internal(f)
    def load_profile_internal(self, filename, silent=False):
        try:
            with open(filename, "r") as f: data = json.load(f)
            leds = data.get("leds", data)
            for n, s in leds.items():
                if n in self.led_state:
                    self.led_state[n].update({
                        'primary': tuple(s.get('primary', (0,0,0))), 
                        'secondary': tuple(s.get('secondary', (0,0,0))), 
                        'pulse': bool(s.get('pulse', False)), 
                        'speed': float(s.get('speed', 1.0))
                    })
            self.refresh_gui_from_state()
            if self.is_connected(): self.apply_settings_to_hardware()
            self.update_last_profile_path(filename)
            if not silent: messagebox.showinfo("Loaded", "Profile Loaded")
        except: pass
    def refresh_gui_from_state(self):
        for n, btn in self.buttons.items():
            if n in self.led_state:
                p_col = self.led_state[n]['primary']
                btn.set_base_bg(self._rgb_to_hex(*p_col))
        for ref in self.master_refs:
            first_btn_name = ref['group'][0]
            if first_btn_name in self.led_state:
                col = self.led_state[first_btn_name][ref['mode']]
                ref['btn'].set_base_bg(self._rgb_to_hex(*col))
        for k, ctrl in self.pulse_controls.items():
            first_btn = ctrl['buttons'][0]
            if first_btn in self.led_state:
                is_pulsing = self.led_state[first_btn]['pulse']
                speed = self.led_state[first_btn]['speed']
                ctrl['var'].set(is_pulsing)
                ctrl['scale'].set(speed)

    def hw_set(self, n, c):
        if self.cab: self.cab.set(n, c)
    def hw_set_all(self, c):
        if self.cab: self.cab.set_all(c)
    def hw_show(self):
        if self.cab: self.cab.show()

    def on_close(self):
        if TRAY_AVAILABLE and not self.force_exit:
            self.root.withdraw()
            if hasattr(self, 'icon'):
                try: self.icon.notify("Arcade Commander is running in the tray.", "Minimized")
                except: pass
        else:
            self.animating = False
            try: self.cab.close()
            except: pass
            if PYGAME_AVAILABLE: pygame.quit()
            if hasattr(self, 'icon'): self.icon.stop()
            self.root.destroy()
            sys.exit(0)

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = ArcadeGUI_V2(root)
        root.protocol("WM_DELETE_WINDOW", app.on_close)
        root.mainloop()
    except KeyboardInterrupt:
        sys.exit(0)