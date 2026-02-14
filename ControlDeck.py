import tkinter as tk
from tkinter import colorchooser, messagebox
from PIL import Image, ImageTk
import json
import os
import math

# --- CYBER-STEALTH PALETTE ---
COLORS = {
    "BG": "#0A0A0A", "SURFACE": "#161616", "SURFACE_LIGHT": "#252525", 
    "P1": "#39FF14", "P2": "#FF5F1F", "SYS": "#00E5FF", "TEXT": "#E0E0E0", 
    "SUCCESS": "#00FF41", "DANGER": "#D50000"
}

# Coordinate mapping tuned for Consol.jpg
# Format: (Center_X, Center_Y, Radius)
ALU_MAP = {
    "P1_A": (273, 275, 22), "P1_B": (323, 275, 22), "P1_C": (373, 275, 22),
    "P1_X": (273, 335, 22), "P1_Y": (323, 335, 22), "P1_Z": (373, 335, 22),
    "P2_A": (627, 275, 22), "P2_B": (677, 275, 22), "P2_C": (727, 275, 22),
    "P2_X": (627, 335, 22), "P2_Y": (677, 335, 22), "P2_Z": (727, 335, 22),
    "P1_START": (420, 85, 18), "P2_START": (580, 85, 18), "MENU": (340, 85, 18),
    "TRACKBALL": (500, 360, 48), "REWIND": (500, 85, 18)
}

class ALUVectorEmulator:
    def __init__(self, root):
        self.root = root
        self.root.title("AC V2.0 - CONSOLE EMULATOR")
        self.root.geometry("1100x820")
        self.root.configure(bg=COLORS["BG"])
        
        self.led_widgets = {}
        self.db_path = "AC_GameData.json"
        self.game_db = self.load_db()
        
        self._title_letters = []
        self._title_anim_phase = 0.0
        self.build_ui()
        self.start_title_animation()

    def load_db(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r") as f: return json.load(f)
            except: return {}
        return {}

    def _rgb_to_hex(self, r, g, b): return f"#{int(r):02x}{int(g):02x}{int(b):02x}"
    
    def start_title_animation(self):
        self._title_anim_phase += 0.06
        for i, (main, _) in enumerate(self._title_letters):
            t = (math.sin(self._title_anim_phase + i * 0.35) + 1.0) / 2.0
            r, g, b = (57, 255, 20) if t < 0.5 else (0, 229, 255)
            main.configure(fg=self._rgb_to_hex(r,g,b))
        self.root.after(35, self.start_title_animation)

    def build_ui(self):
        # Header - Left Aligned
        h_frame = tk.Frame(self.root, bg=COLORS["BG"], pady=10); h_frame.pack(fill="x", padx=30)
        tf = tk.Frame(h_frame, bg=COLORS["BG"]); tf.pack(side="left")
        for ch in "EMULATOR":
            cell = tk.Frame(tf, bg=COLORS["BG"]); cell.pack(side="left")
            main = tk.Label(cell, text=ch, font=("Segoe UI", 24, "bold"), bg=COLORS["BG"], fg=COLORS["TEXT"])
            main.pack(); self._title_letters.append((main, None))

        # Main Layout: Sidebar Loader + Canvas
        main_body = tk.Frame(self.root, bg=COLORS["BG"])
        main_body.pack(fill="both", expand=True, padx=20)

        # 1. Profile Loader Sidebar
        lib = tk.LabelFrame(main_body, text=" LOAD GAME ", bg=COLORS["BG"], fg=COLORS["P1"], font=("Segoe UI", 9, "bold"), padx=10, pady=10)
        lib.pack(side="left", fill="y", padx=(0, 20), pady=10)
        self.search = tk.Entry(lib, bg=COLORS["SURFACE_LIGHT"], fg="white", font=("Consolas", 11), borderwidth=0)
        self.search.pack(fill="x", pady=2); self.search.bind("<KeyRelease>", self.refresh_list)
        self.listbox = tk.Listbox(lib, bg=COLORS["SURFACE"], fg="#888", borderwidth=0, font=("Segoe UI", 9), width=22)
        self.listbox.pack(fill="both", expand=True); self.listbox.bind("<<ListboxSelect>>", self.on_select)

        # 2. Vector Canvas
        self.canvas = tk.Canvas(main_body, bg="black", width=1000, height=500, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True, pady=10)

        bg_path = os.path.join("assets", "Consol.png")
        if os.path.exists(bg_path):
            bg_img = Image.open(bg_path).resize((1000, 500), Image.Resampling.LANCZOS)
            self.bg_photo = ImageTk.PhotoImage(bg_img)
            self.canvas.create_image(0, 0, anchor="nw", image=self.bg_photo)

        self.init_leds()

        # 3. Quick Actions
        act = tk.Frame(self.root, bg=COLORS["BG"], pady=10); act.pack(fill="x", padx=30)
        tk.Button(act, text="ALL OFF", bg=COLORS["DANGER"], fg="white", width=12, relief="flat", command=self.all_off).pack(side="left", padx=5)
        self.net_lbl = tk.Label(act, text="● ACLIGHTER: ONLINE", bg=COLORS["BG"], fg=COLORS["SUCCESS"], font=("Segoe UI", 9, "bold"))
        self.net_lbl.pack(side="right")

        self.refresh_list()

    def init_leds(self):
        """Creates interactive LED overlays"""
        for key, (x, y, rad) in ALU_MAP.items():
            # Glowing diffusion layer
            glow = self.canvas.create_oval(x-rad-5, y-rad-5, x+rad+5, y+rad+5, outline="", fill="", tags="glow")
            # Solid button lens
            btn = self.canvas.create_oval(x-rad, y-rad, x+rad, y+rad, outline="#444", fill="", width=2, tags="btn")
            # Dynamic Label
            txt = self.canvas.create_text(x, y, text=key.split('_')[-1], fill="white", font=("Segoe UI", 7, "bold"), tags="txt")
            self.led_widgets[key] = {"glow": glow, "btn": btn, "txt": txt}

    def on_select(self, _):
        """Loads ROM and illuminates the console"""
        if not self.listbox.curselection(): return
        rom = self.listbox.get(self.listbox.curselection())
        data = self.game_db.get(rom, {})
        controls = data.get("controls", {})

        # Darken console
        for w in self.led_widgets.values():
            self.canvas.itemconfig(w["glow"], fill="")
            self.canvas.itemconfig(w["btn"], fill="", outline="#444")
            self.canvas.itemconfig(w["txt"], fill="white")

        # Light up active keys
        for bid, val in controls.items():
            if bid in self.led_widgets:
                p_hex = val.split('|')[0]
                if p_hex != COLORS["SURFACE"]:
                    self.canvas.itemconfig(self.led_widgets[bid]["glow"], fill=p_hex, stipple="gray50")
                    self.canvas.itemconfig(self.led_widgets[bid]["btn"], fill=p_hex, outline=p_hex)
                    self.canvas.itemconfig(self.led_widgets[bid]["txt"], fill="black")

    def all_off(self):
        for w in self.led_widgets.values():
            self.canvas.itemconfig(w["glow"], fill="")
            self.canvas.itemconfig(w["btn"], fill="", outline="#444")
            self.canvas.itemconfig(w["txt"], fill="white")

    def refresh_list(self, _=None):
        q = self.search.get().lower(); self.listbox.delete(0, tk.END)
        for rom in sorted(self.game_db.keys()):
            if q in rom.lower(): self.listbox.insert(tk.END, rom)

if __name__ == "__main__":
    root = tk.Tk(); app = ALUVectorEmulator(root); root.mainloop()
