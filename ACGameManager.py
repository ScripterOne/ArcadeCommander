import tkinter as tk
from tkinter import colorchooser, messagebox
import json
import os
import math

# --- V2.0 STEALTH COLOR SCHEME ---
COLORS = {
    "BG": "#0A0A0A", "SURFACE": "#161616", "SURFACE_LIGHT": "#252525", 
    "P1": "#39FF14", "P2": "#FF5F1F", "SYS": "#00E5FF", "FX": "#BC13FE",
    "TEXT": "#E0E0E0", "TEXT_DIM": "#888888", "SUCCESS": "#00FF41", "DANGER": "#D50000"
}

class StableStealthManager:
    def __init__(self, root):
        self.root = root
        self.root.title("AC V2.0 - STEALTH MANAGER")
        self.root.geometry("1100x820") 
        self.root.configure(bg=COLORS["BG"])
        
        self.button_data = {} 
        self.fx_vars = {} 
        self.current_rom = None
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

    def _ensure_hex(self, val):
        """Converts RGB comma strings to Hex if necessary to prevent TclErrors."""
        if not val or val == "None": return COLORS["SURFACE"]
        if val.startswith('#'): return val
        try:
            r, g, b = map(int, val.split(','))
            return f"#{r:02x}{g:02x}{b:02x}"
        except: return COLORS["SURFACE"]

    def start_title_animation(self):
        self._title_anim_phase += 0.06
        for i, (main, _) in enumerate(self._title_letters):
            t = (math.sin(self._title_anim_phase + i * 0.35) + 1.0) / 2.0
            r, g, b = (57, 255, 20) if t < 0.5 else (0, 229, 255)
            main.configure(fg=f"#{int(r):02x}{int(g):02x}{int(b):02x}")
        self.root.after(35, self.start_title_animation)

    def build_ui(self):
        # Header
        h_frame = tk.Frame(self.root, bg=COLORS["BG"], pady=15); h_frame.pack(fill="x", padx=30)
        tf = tk.Frame(h_frame, bg=COLORS["BG"]); tf.pack(side="left")
        for ch in "GAME MANAGER":
            if ch == " ": tk.Label(tf, text=" ", bg=COLORS["BG"], font=("Segoe UI", 24)).pack(side="left"); continue
            cell = tk.Frame(tf, bg=COLORS["BG"]); cell.pack(side="left")
            main = tk.Label(cell, text=ch, font=("Segoe UI", 24, "bold"), bg=COLORS["BG"], fg=COLORS["TEXT"])
            main.pack(); self._title_letters.append((main, None))

        body = tk.Frame(self.root, bg=COLORS["BG"])
        body.pack(fill="both", expand=True, padx=25)
        body.columnconfigure((0,1,2,3), weight=1, uniform="eq")

        # COL 1: P1 + LIBRARY
        c1 = tk.Frame(body, bg=COLORS["BG"]); c1.grid(row=0, column=0, sticky="nsew", padx=5)
        self.build_card(c1, "P1", COLORS["P1"], ["A", "B", "C", "X", "Y", "Z", "START"])
        lib = tk.LabelFrame(c1, text=" GAME LIBRARY ", bg=COLORS["BG"], fg=COLORS["P1"], font=("Segoe UI", 9, "bold"), padx=10, pady=5)
        lib.pack(fill="both", expand=True, pady=10)
        self.search = tk.Entry(lib, bg=COLORS["SURFACE_LIGHT"], fg="white", borderwidth=0, font=("Consolas", 10))
        self.search.pack(fill="x", pady=2); self.search.bind("<KeyRelease>", self.refresh_list)
        self.listbox = tk.Listbox(lib, bg=COLORS["SURFACE"], fg="#888", borderwidth=0, font=("Segoe UI", 9), height=10)
        self.listbox.pack(fill="both", expand=True); self.listbox.bind("<<ListboxSelect>>", self.on_select)

        # COL 2: SYSTEM + ACTIONS
        c2 = tk.Frame(body, bg=COLORS["BG"]); c2.grid(row=0, column=1, sticky="nsew", padx=5)
        self.build_system(c2)
        act = tk.LabelFrame(c2, text=" ACTIONS ", bg=COLORS["BG"], fg=COLORS["SYS"], font=("Segoe UI", 9, "bold"), padx=10, pady=10)
        act.pack(fill="x", pady=10)
        tk.Button(act, text="APPLY TO CABINET", bg=COLORS["SYS"], fg="black", font=("Segoe UI", 9, "bold"), relief="flat", command=self.apply_to_hw).pack(fill="x", pady=2)
        tk.Button(act, text="ALL LEDS OFF", bg=COLORS["DANGER"], fg="white", font=("Segoe UI", 9, "bold"), relief="flat", command=self.all_off).pack(fill="x", pady=2)
        tk.Frame(act, bg=COLORS["SURFACE_LIGHT"], height=1).pack(fill="x", pady=8)
        tk.Button(act, text="SAVE NEW GAME", bg=COLORS["SUCCESS"], fg="black", font=("Segoe UI", 8, "bold"), relief="flat", command=self.save_new).pack(fill="x", pady=2)
        tk.Button(act, text="OVERRIDE DATA", bg=COLORS["TEXT_DIM"], fg="white", font=("Segoe UI", 8, "bold"), relief="flat", command=self.save_game).pack(fill="x", pady=2)

        # COL 3 & 4
        self.build_card(body, "P2", COLORS["P2"], ["A", "B", "C", "X", "Y", "Z", "START"], col=2)
        c4 = tk.Frame(body, bg=COLORS["BG"]); c4.grid(row=0, column=3, sticky="nsew", padx=5)
        self.build_fx(c4)

        footer = tk.Frame(self.root, bg=COLORS["BG"], pady=10); footer.pack(fill="x", padx=30)
        self.net_lbl = tk.Label(footer, text="● ACLIGHTER: ONLINE", bg=COLORS["BG"], fg=COLORS["SUCCESS"], font=("Segoe UI", 9, "bold"))
        self.net_lbl.pack(side="right"); self.refresh_list()

    def apply_to_hw(self): messagebox.showinfo("Hardware", "Settings applied.")
    def all_off(self): 
        for w in self.button_data.values():
            w["p"].config(bg=COLORS["SURFACE"])
            if w["s"]: w["s"].config(bg=COLORS["SURFACE"])
            w["lbl"].config(fg="white", bg=COLORS["SURFACE_LIGHT"])

    def build_card(self, parent, prefix, accent, buttons, col=0):
        if col > 0:
            c = tk.Frame(parent, bg=COLORS["BG"]); c.grid(row=0, column=col, sticky="nsew", padx=5)
        else: c = parent
        outer = tk.Frame(c, bg=accent, padx=1, pady=1); outer.pack(fill="x")
        inner = tk.Frame(outer, bg=COLORS["SURFACE"], padx=5, pady=5); inner.pack(fill="both")
        tk.Label(inner, text="PLAYER "+prefix[-1], font=("Segoe UI", 9, "bold"), bg=COLORS["SURFACE"], fg=accent).pack()
        for b in buttons:
            f = tk.Frame(inner, bg=COLORS["SURFACE_LIGHT"], pady=2); f.pack(fill="x", pady=1)
            lbl = tk.Label(f, text=b, width=5, bg=COLORS["SURFACE_LIGHT"], fg="white", font=("Segoe UI", 8, "bold")); lbl.pack(side="left", padx=5)
            bid = f"{prefix}_{b}"
            s_sw = tk.Button(f, width=2, bg=COLORS["SURFACE"], relief="flat", command=lambda n=bid: self.pick_color(n, 's')); s_sw.pack(side="right", padx=2)
            p_sw = tk.Button(f, width=2, bg=COLORS["SURFACE"], relief="flat", command=lambda n=bid: self.pick_color(n, 'p')); p_sw.pack(side="right", padx=2)
            self.button_data[bid] = {"lbl": lbl, "p": p_sw, "s": s_sw}

    def build_system(self, parent):
        outer = tk.Frame(parent, bg=COLORS["SYS"], padx=1, pady=1); outer.pack(fill="x")
        inner = tk.Frame(outer, bg=COLORS["SURFACE"], padx=5, pady=5); inner.pack(fill="both")
        tk.Label(inner, text="SYSTEM", font=("Segoe UI", 9, "bold"), bg=COLORS["SURFACE"], fg=COLORS["SYS"]).pack()
        for b in ["TRACKBALL", "REWIND", "MENU"]:
            f = tk.Frame(inner, bg=COLORS["SURFACE_LIGHT"], pady=2); f.pack(fill="x", pady=1)
            lbl = tk.Label(f, text=b, width=10, anchor="w", bg=COLORS["SURFACE_LIGHT"], fg="white", font=("Segoe UI", 8, "bold")); lbl.pack(side="left", padx=5)
            sw = tk.Button(f, width=3, bg=COLORS["SURFACE"], relief="flat", command=lambda n=b: self.pick_color(n, 'p')); sw.pack(side="right", padx=5)
            self.button_data[b] = {"lbl": lbl, "p": sw, "s": None}

    def build_fx(self, parent):
        fx = tk.LabelFrame(parent, text=" LED FX ", bg=COLORS["BG"], fg=COLORS["FX"], font=("Segoe UI", 9, "bold"), padx=10, pady=10); fx.pack(fill="both", expand=True)
        for label, key in [("RAINBOW", "rainbow"), ("BREATH", "breath"), ("STROBE", "strobe"), ("FADE", "fade")]:
            f = tk.Frame(fx, bg=COLORS["SURFACE"], pady=4); f.pack(fill="x", pady=1)
            var = tk.BooleanVar(); self.fx_vars[key] = var
            tk.Checkbutton(f, text=label, variable=var, bg=COLORS["SURFACE"], fg="white", selectcolor=COLORS["BG"], font=("Segoe UI", 8)).pack(side="left")
        self.fx_speed = tk.Scale(fx, from_=0.1, to=5.0, resolution=0.1, orient="horizontal", bg=COLORS["BG"], fg="white", highlightthickness=0); self.fx_speed.set(1.0); self.fx_speed.pack(fill="x", pady=10)

    def on_select(self, _):
        if not self.listbox.curselection(): return
        self.current_rom = self.listbox.get(self.listbox.curselection())
        data = self.game_db.get(self.current_rom, {})
        controls = data.get("controls", {})
        for w in self.button_data.values():
            w["p"].config(bg=COLORS["SURFACE"]); w["lbl"].config(fg="white", bg=COLORS["SURFACE_LIGHT"])
            if w["s"]: w["s"].config(bg=COLORS["SURFACE"])
        for bid, val in controls.items():
            if bid in self.button_data:
                parts = val.split('|'); p_hex = self._ensure_hex(parts[0])
                self.button_data[bid]["p"].config(bg=p_hex)
                if len(parts) > 1 and self.button_data[bid]["s"]: self.button_data[bid]["s"].config(bg=self._ensure_hex(parts[1]))
                if p_hex != COLORS["SURFACE"]: self.button_data[bid]["lbl"].config(fg="black", bg=p_hex)
        fx_data = data.get("fx", {}); [v.set(fx_data.get(k, False)) for k, v in self.fx_vars.items()]
        self.fx_speed.set(fx_data.get("speed", 1.0))

    def save_game(self, rom_name=None):
        rom = rom_name if rom_name else self.current_rom
        if not rom: return
        controls = {bid: f"{w['p'].cget('bg')}|{w['s'].cget('bg') if w['s'] else COLORS['SURFACE']}" for bid, w in self.button_data.items() if w['p'].cget('bg') != COLORS["SURFACE"]}
        self.game_db[rom] = {"controls": controls, "fx": {k: v.get() for k, v in self.fx_vars.items()}, "speed": self.fx_speed.get()}
        with open(self.db_path, "w") as f: json.dump(self.game_db, f, indent=4)
        messagebox.showinfo("Saved", f"Profile '{rom}' updated."); self.refresh_list()

    def save_new(self):
        n = self.search.get()
        if n: self.save_game(n)

    def pick_color(self, n, t):
        c = colorchooser.askcolor()[1]
        if c:
            target = self.button_data[n]["p"] if t == 'p' else self.button_data[n]["s"]
            target.config(bg=c)
            if t == 'p': self.button_data[n]["lbl"].config(fg="black", bg=c)

    def refresh_list(self, _=None):
        q = self.search.get().lower(); self.listbox.delete(0, tk.END)
        for rom in sorted(self.game_db.keys()):
            if q in rom.lower(): self.listbox.insert(tk.END, rom)

if __name__ == "__main__":
    root = tk.Tk(); app = StableStealthManager(root); root.mainloop()