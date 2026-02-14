import tkinter as tk
from tkinter import colorchooser, messagebox, ttk, simpledialog
import json
import os
import math
import sys
import csv
import re
from app_paths import game_db_file, migrate_legacy_runtime_files

# --- SERVICE ADAPTER (NO DIRECT SOCKETS) ---
try:
    from ServiceAdapter import Arcade
except Exception:
    class Arcade:
        def __init__(self, port=None): self.connected = False
        def reconnect(self, port=None): return False
        def is_connected(self): return False
        def set(self, index_or_name, color): pass
        def set_all(self, color): pass
        def show(self): pass
        def close(self): pass

def _base_dir():
    if hasattr(sys, "_MEIPASS"):
        return os.path.abspath(getattr(sys, "_MEIPASS"))
    return os.path.dirname(os.path.abspath(__file__))

def _db_path():
    migrate_legacy_runtime_files()
    return game_db_file()

def _csv_path():
    return os.path.join(_base_dir(), "Top100_Games.csv")

def _normalize_title(s):
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _rom_key_from_title(title):
    if not title:
        return ""
    t = title.lower()
    t = re.sub(r"[^a-z0-9]+", "", t)
    return t

# --- V2.0 STEALTH COLOR SCHEME ---
COLORS = {
    "BG": "#0A0A0A", "SURFACE": "#161616", "SURFACE_LIGHT": "#252525", 
    "P1": "#39FF14", "P2": "#FF5F1F", "SYS": "#00E5FF", "FX": "#BC13FE",
    "TEXT": "#E0E0E0", "TEXT_DIM": "#888888", "SUCCESS": "#00FF41", "DANGER": "#D50000"
}

CONTROLLER_BADGE_MAP = {
    "ARCADE_PANEL": "AC",
    "GAMEPAD_GENERIC": "GP",
    "XINPUT_XBOX": "XB",
    "LIGHTGUN": "LG",
    "UNKNOWN": "??",
}

CONTROLLER_TOOLTIP_MAP = {
    "AC": "Arcade panel controls expected; map and light arcade buttons.",
    "GP": "Gamepad controls expected; arcade mapping may not apply.",
    "XB": "Xbox/XInput expected; arcade mapping may not apply.",
    "LG": "Lightgun controls expected; arcade mapping may not apply.",
    "??": "Unknown input mode.",
}

SUPPORTED_ANIMATIONS = [
    "RAINBOW",
    "PULSE_RED",
    "PULSE_GREEN",
    "PULSE_BLUE",
    "HYPER_STROBE",
]

class HoverTooltip:
    def __init__(self, widget, text_func):
        self.widget = widget
        self.text_func = text_func
        self.tip = None
        self.widget.bind("<Enter>", self._show, add="+")
        self.widget.bind("<Leave>", self._hide, add="+")

    def _show(self, event):
        self._hide()
        text = self.text_func()
        if not text:
            return
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{event.x_root + 12}+{event.y_root + 12}")
        lbl = tk.Label(
            self.tip,
            text=text,
            bg="#111111",
            fg="#E0E0E0",
            relief="solid",
            bd=1,
            padx=6,
            pady=3,
            font=("Segoe UI", 8),
        )
        lbl.pack()

    def _hide(self, _event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None

class StableStealthManager:
    def __init__(self, root):
        self.root = root
        self.root.title("AC V2.0 - STEALTH MANAGER")
        self.root.geometry("1280x860")
        self.root.minsize(980, 700)
        self.root.maxsize(1920, 1080)
        self.root.configure(bg=COLORS["BG"])
        
        self.button_data = {} 
        self.fx_vars = {} 
        self.current_rom = None
        self.db_path = _db_path()
        self.csv_path = _csv_path()
        self.game_db = self.load_db()
        self.csv_rows, self.col_map = self.load_csv()
        self.cab = Arcade()
        self.preview_enabled = tk.BooleanVar(value=True)
        self.vendor_var = tk.StringVar(value="")
        self._warned_offline = False
        self._last_saved_snapshot = None
        self._row_index = {}
        self._sort_state = {}
        self.section_badges = {}
        self.arcade_edit_widgets = []
        self.tree_columns = ("title", "developer", "platforms", "genres", "rec_platform", "rank", "rom_key", "profile")
        self.tree_headings = {
            "title": "Game Name",
            "developer": "Developer",
            "platforms": "Platforms",
            "genres": "Genres",
            "rec_platform": "Recommended",
            "rank": "Rank",
            "rom_key": "ROM_KEY",
            "profile": "STATUS",
        }
        self.visible_columns = ["title"]
        self._column_vars = {}
        self.controller_mode = "ARCADE_PANEL"
        self.controller_mode_var = tk.StringVar(value="ARCADE_PANEL")
        self.lighting_policy_var = tk.StringVar(value="AUTO")
        self.default_fx_var = tk.StringVar(value="NONE")
        self.use_default_fx_var = tk.BooleanVar(value=False)
        
        self._title_letters = []
        self._title_anim_phase = 0.0
        self.build_ui()
        self._build_tree_context_menu()
        self.start_title_animation()

    def load_db(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r") as f: return json.load(f)
            except: return {}
        return {}

    def load_csv(self):
        if not os.path.exists(self.csv_path):
            return [], {}
        try:
            with open(self.csv_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                rows = [r for r in reader]
            col_map = self._build_col_map(reader.fieldnames or [])
            return rows, col_map
        except:
            return [], {}

    def _build_col_map(self, headers):
        hset = {h: h for h in headers}
        def pick(*cands):
            for c in cands:
                if c in hset:
                    return c
            return None
        return {
            "title": pick("Game Name", "Title", "Game", "Name"),
            "developer": pick("Developer", "Manufacturer", "Vendor", "Publisher"),
            "year": pick("Year", "Release Year", "Released"),
            "platforms": pick("Platforms", "Platform", "System", "Emulator"),
            "genres": pick("Genres", "Genre", "Category"),
            "rec_platform": pick("Recommended Platform", "Recommended", "Best Platform"),
            "rank": pick("Rank", "Ranking"),
        }

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
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background=COLORS["SURFACE"], fieldbackground=COLORS["SURFACE"], foreground=COLORS["TEXT"], rowheight=18)
        style.configure("Treeview.Heading", background=COLORS["SURFACE_LIGHT"], foreground=COLORS["TEXT"], relief="flat")
        style.map("Treeview", background=[("selected", COLORS["P1"])], foreground=[("selected", "black")])

        # Header
        h_frame = tk.Frame(self.root, bg=COLORS["BG"], pady=8); h_frame.pack(fill="x", padx=16)
        tf = tk.Frame(h_frame, bg=COLORS["BG"]); tf.pack(side="left")
        for ch in "GAME MANAGER":
            if ch == " ": tk.Label(tf, text=" ", bg=COLORS["BG"], font=("Segoe UI", 20)).pack(side="left"); continue
            cell = tk.Frame(tf, bg=COLORS["BG"]); cell.pack(side="left")
            main = tk.Label(cell, text=ch, font=("Segoe UI", 20, "bold"), bg=COLORS["BG"], fg=COLORS["TEXT"])
            main.pack(); self._title_letters.append((main, None))

        body = tk.Frame(self.root, bg=COLORS["BG"])
        body.pack(fill="both", expand=True, padx=16, pady=8)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(body)
        notebook.grid(row=0, column=0, sticky="nsew")

        tab_browser = tk.Frame(notebook, bg=COLORS["BG"])
        tab_controls = tk.Frame(notebook, bg=COLORS["BG"])
        notebook.add(tab_browser, text="Game DB Browser + Updater")
        notebook.add(tab_controls, text="Controls + FX")

        tab_browser.columnconfigure(0, weight=1)
        tab_browser.rowconfigure(0, weight=1)
        tab_controls.columnconfigure(0, weight=1)
        tab_controls.rowconfigure(0, weight=1)

        top_row = tk.Frame(tab_browser, bg=COLORS["BG"])
        top_row.grid(row=0, column=0, sticky="nsew", padx=4, pady=(0, 8))
        top_row.columnconfigure(0, weight=3)
        top_row.columnconfigure(1, weight=2)
        top_row.rowconfigure(0, weight=1)

        lib = tk.LabelFrame(top_row, text=" GAME SELECTOR ", bg=COLORS["BG"], fg=COLORS["P1"], font=("Segoe UI", 9, "bold"), padx=8, pady=4)
        lib.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        search_row = tk.Frame(lib, bg=COLORS["BG"])
        search_row.pack(fill="x", pady=1)
        self.search = tk.Entry(search_row, bg=COLORS["SURFACE_LIGHT"], fg="white", borderwidth=0, font=("Consolas", 10))
        self.search.pack(side="left", fill="x", expand=True)
        self.search.bind("<KeyRelease>", self.refresh_list)
        tk.Button(search_row, text="COLUMNS", bg=COLORS["SURFACE_LIGHT"], fg="white", font=("Segoe UI", 8, "bold"), relief="flat",
                  command=self.open_column_chooser).pack(side="right", padx=(6, 0))
        tk.Button(search_row, text="CLEAR", bg=COLORS["SURFACE_LIGHT"], fg="white", font=("Segoe UI", 8, "bold"), relief="flat",
                  command=self._clear_filter).pack(side="right", padx=(6, 0))

        tree_frame = tk.Frame(lib, bg=COLORS["BG"])
        tree_frame.pack(fill="both", expand=True, pady=2)
        self.tree = ttk.Treeview(tree_frame, columns=self.tree_columns, show="headings", height=8)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb = tk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vsb.set)

        for col, label in self.tree_headings.items():
            self.tree.heading(col, text=label, command=lambda c=col: self.sort_tree(c))
        self.tree.column("title", width=420, anchor="w")
        self.tree.column("developer", width=120, anchor="w")
        self.tree.column("platforms", width=110, anchor="w")
        self.tree.column("genres", width=100, anchor="w")
        self.tree.column("rec_platform", width=100, anchor="w")
        self.tree.column("rank", width=50, anchor="center")
        self.tree.column("rom_key", width=90, anchor="w")
        self.tree.column("profile", width=60, anchor="center")
        self._apply_display_columns()
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Button-3>", self._on_tree_right_click)

        info = tk.LabelFrame(top_row, text=" GAME INFO / PROFILE ", bg=COLORS["BG"], fg=COLORS["SYS"], font=("Segoe UI", 9, "bold"), padx=8, pady=6)
        info.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        self.detail_vars = {
            "catalog_title": tk.StringVar(value="—"),
            "catalog_developer": tk.StringVar(value="—"),
            "catalog_year": tk.StringVar(value="—"),
            "catalog_genre": tk.StringVar(value="—"),
            "catalog_platform": tk.StringVar(value="—"),
            "catalog_rank": tk.StringVar(value="—"),
            "profile_rom": tk.StringVar(value="—"),
            "profile_controller_mode": tk.StringVar(value="—"),
            "profile_lighting_policy": tk.StringVar(value="—"),
            "profile_default_fx": tk.StringVar(value="—"),
            "profile_status": tk.StringVar(value="NONE"),
        }

        tk.Label(info, text="CATALOG", bg=COLORS["BG"], fg=COLORS["P1"], font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 2))
        for label, key in [
            ("Title", "catalog_title"),
            ("Vendor/Dev", "catalog_developer"),
            ("Year", "catalog_year"),
            ("Genre", "catalog_genre"),
            ("Platform/Rec", "catalog_platform"),
            ("Rank", "catalog_rank"),
            ("ROM Key", "profile_rom"),
            ("Status", "profile_status"),
        ]:
            row = tk.Frame(info, bg=COLORS["BG"])
            row.pack(fill="x", pady=0)
            tk.Label(row, text=f"{label}:", width=12, anchor="w", bg=COLORS["BG"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(side="left")
            tk.Label(row, textvariable=self.detail_vars[key], bg=COLORS["BG"], fg=COLORS["TEXT"], font=("Segoe UI", 8), anchor="w", wraplength=280, justify="left").pack(side="left", fill="x", expand=True)

        tk.Frame(info, bg=COLORS["SURFACE_LIGHT"], height=1).pack(fill="x", pady=6)
        tk.Label(info, text="EDIT PROFILE", bg=COLORS["BG"], fg=COLORS["SYS"], font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 2))
        tk.Label(info, text="VENDOR", bg=COLORS["BG"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Entry(info, textvariable=self.vendor_var, bg=COLORS["SURFACE_LIGHT"], fg="white", borderwidth=0, font=("Consolas", 9)).pack(fill="x", pady=(0, 4))
        tk.Label(info, text="CONTROLLER MODE", bg=COLORS["BG"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        mode_combo = ttk.Combobox(
            info,
            textvariable=self.controller_mode_var,
            values=("ARCADE_PANEL", "GAMEPAD_GENERIC", "XINPUT_XBOX", "LIGHTGUN", "UNKNOWN"),
            state="readonly",
            font=("Consolas", 8),
        )
        mode_combo.pack(fill="x", pady=(0, 4))
        mode_combo.bind("<<ComboboxSelected>>", self._on_controller_mode_changed)
        tk.Label(info, text="LIGHTING POLICY", bg=COLORS["BG"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        policy_combo = ttk.Combobox(
            info,
            textvariable=self.lighting_policy_var,
            values=("AUTO", "ARCADE_ONLY", "FX_ONLY", "OFF"),
            state="readonly",
            font=("Consolas", 8),
        )
        policy_combo.pack(fill="x", pady=(0, 4))
        policy_combo.bind("<<ComboboxSelected>>", self._on_lighting_policy_changed)
        tk.Label(info, text="DEFAULT FX", bg=COLORS["BG"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        fx_combo = ttk.Combobox(
            info,
            textvariable=self.default_fx_var,
            values=("NONE",) + tuple(SUPPORTED_ANIMATIONS),
            state="readonly",
            font=("Consolas", 8),
        )
        fx_combo.pack(fill="x", pady=(0, 4))
        fx_combo.bind("<<ComboboxSelected>>", self._on_default_fx_changed)
        tk.Checkbutton(
            info,
            text="Use Default FX for GP/XB",
            variable=self.use_default_fx_var,
            command=self._on_use_default_fx_toggle,
            bg=COLORS["BG"],
            fg="white",
            selectcolor=COLORS["BG"],
            font=("Segoe UI", 8),
        ).pack(anchor="w", pady=(0, 4))
        self.arcade_disabled_note = tk.Label(
            info,
            text="Non-arcade title: Dispatch uses FX/IDLE by Lighting Policy.",
            bg=COLORS["BG"],
            fg=COLORS["TEXT_DIM"],
            font=("Segoe UI", 8),
        )
        self.arcade_disabled_note.pack(anchor="w", pady=(0, 4))

        btn_row = tk.Frame(info, bg=COLORS["BG"])
        btn_row.pack(fill="x", pady=(4, 0))
        tk.Button(btn_row, text="UPDATE DB", bg=COLORS["SUCCESS"], fg="black", font=("Segoe UI", 8, "bold"), relief="flat", command=self.save_game).pack(side="left", fill="x", expand=True, padx=(0, 3))
        tk.Button(btn_row, text="OVERRIDE LED SETTINGS", bg=COLORS["SYS"], fg="black", font=("Segoe UI", 8, "bold"), relief="flat", command=self.apply_to_hw).pack(side="left", fill="x", expand=True, padx=(3, 0))
        tk.Button(info, text="CREATE PROFILE FROM DEFAULTS", bg=COLORS["SURFACE_LIGHT"], fg="white", font=("Segoe UI", 8, "bold"),
                  relief="flat", command=self.create_profile_from_defaults).pack(fill="x", pady=(6, 2))
        tk.Button(info, text="ALL LEDS OFF", bg=COLORS["DANGER"], fg="white", font=("Segoe UI", 8, "bold"), relief="flat", command=self.all_off).pack(fill="x", pady=2)
        tk.Button(info, text="CANCEL", bg=COLORS["TEXT_DIM"], fg="white", font=("Segoe UI", 8, "bold"), relief="flat", command=self.cancel_changes).pack(fill="x", pady=(2, 0))

        controls_row = tk.Frame(tab_controls, bg=COLORS["BG"])
        controls_row.grid(row=0, column=0, sticky="nsew", padx=4, pady=(8, 8))
        for col in range(4):
            controls_row.columnconfigure(col, weight=1, uniform="controls")
        p1_tile = tk.Frame(controls_row, bg=COLORS["BG"]); p1_tile.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        p2_tile = tk.Frame(controls_row, bg=COLORS["BG"]); p2_tile.grid(row=0, column=1, sticky="nsew", padx=4)
        sys_tile = tk.Frame(controls_row, bg=COLORS["BG"]); sys_tile.grid(row=0, column=2, sticky="nsew", padx=4)
        fx_tile = tk.Frame(controls_row, bg=COLORS["BG"]); fx_tile.grid(row=0, column=3, sticky="nsew", padx=(4, 0))
        self.build_card(p1_tile, "P1", COLORS["P1"], ["A", "B", "C", "X", "Y", "Z", "START"])
        self.build_card(p2_tile, "P2", COLORS["P2"], ["A", "B", "C", "X", "Y", "Z", "START"])
        self.build_system(sys_tile)
        self.build_fx(fx_tile)

        footer = tk.Frame(self.root, bg=COLORS["BG"], pady=4); footer.pack(fill="x", padx=16)
        self.net_lbl = tk.Label(footer, text="ACLIGHTER: OFFLINE", bg=COLORS["BG"], fg=COLORS["DANGER"], font=("Segoe UI", 9, "bold"))
        self.net_lbl.pack(side="right"); self.refresh_list()
        self._update_controller_badges()
        self._update_editor_enable_state()
        self.refresh_status()
    def _clear_filter(self):
        self.search.delete(0, tk.END)
        self.refresh_list()

    def _build_tree_context_menu(self):
        self.tree_menu = tk.Menu(self.root, tearoff=0)
        self.tree_menu.add_command(label="Create Profile", command=self.context_create_profile)
        self.tree_menu.add_command(label="Duplicate Profile...", command=self.context_duplicate_profile)
        self.tree_menu.add_command(label="Export Profile...", command=self.context_export_profile)
        self.tree_menu.add_separator()
        self.tree_menu.add_command(label="Delete Profile", command=self.context_delete_profile)

    def _on_tree_right_click(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id:
            self.tree.selection_set(row_id)
            self.tree.focus(row_id)
            self.on_select(None)
        self._update_tree_menu_state()
        try:
            self.tree_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.tree_menu.grab_release()

    def _update_tree_menu_state(self):
        row = self._current_row_data()
        rom_key = row.get("_rom_key")
        exists = bool(rom_key and rom_key in self.game_db)
        self.tree_menu.entryconfig("Create Profile", state=("disabled" if exists else "normal"))
        self.tree_menu.entryconfig("Duplicate Profile...", state=("normal" if exists else "disabled"))
        self.tree_menu.entryconfig("Export Profile...", state=("normal" if exists else "disabled"))
        self.tree_menu.entryconfig("Delete Profile", state=("normal" if exists else "disabled"))

    def open_column_chooser(self):
        if hasattr(self, "column_dialog") and self.column_dialog and self.column_dialog.winfo_exists():
            self.column_dialog.lift()
            return
        dlg = tk.Toplevel(self.root)
        dlg.title("Choose Columns")
        dlg.configure(bg=COLORS["BG"])
        dlg.resizable(False, False)
        dlg.transient(self.root)
        self.column_dialog = dlg
        box = tk.Frame(dlg, bg=COLORS["BG"], padx=12, pady=10)
        box.pack(fill="both", expand=True)
        self._column_vars = {}
        for col in self.tree_columns:
            var = tk.BooleanVar(value=(col in self.visible_columns))
            self._column_vars[col] = var
            tk.Checkbutton(
                box,
                text=self.tree_headings.get(col, col),
                variable=var,
                command=self._on_toggle_columns,
                bg=COLORS["BG"],
                fg=COLORS["TEXT"],
                selectcolor=COLORS["SURFACE"],
                activebackground=COLORS["BG"],
                activeforeground=COLORS["TEXT"],
                font=("Segoe UI", 9),
            ).pack(anchor="w", pady=1)

    def _on_toggle_columns(self):
        cols = [c for c in self.tree_columns if self._column_vars.get(c) and self._column_vars[c].get()]
        if not cols:
            first = self.tree_columns[0]
            self._column_vars[first].set(True)
            cols = [first]
        self.visible_columns = cols
        self._apply_display_columns()

    def _apply_display_columns(self):
        self.tree.configure(displaycolumns=tuple(self.visible_columns))

    def _blank_profile_entry(self):
        return {
            "controls": {},
            "fx": {k: v.get() for k, v in self.fx_vars.items()},
            "speed": self.fx_speed.get(),
            "vendor": "",
            "profile": {
                "controller_mode": self.controller_mode_var.get(),
                "lighting_policy": self.lighting_policy_var.get(),
                "default_fx": "" if self.default_fx_var.get() == "NONE" else self.default_fx_var.get(),
            },
        }

    def context_create_profile(self):
        row = self._current_row_data()
        rom_key = row.get("_rom_key")
        if not rom_key:
            return
        if rom_key not in self.game_db:
            self.game_db[rom_key] = self._blank_profile_entry()
            self.current_rom = rom_key
            self.refresh_list()

    def context_duplicate_profile(self):
        row = self._current_row_data()
        src = row.get("_rom_key")
        if not src or src not in self.game_db:
            return
        new_key = simpledialog.askstring("Duplicate Profile", "New ROM key:", parent=self.root)
        if not new_key:
            return
        new_key = new_key.strip().lower()
        if not new_key:
            return
        if new_key in self.game_db:
            messagebox.showwarning("Duplicate Key", f"'{new_key}' already exists.")
            return
        self.game_db[new_key] = json.loads(json.dumps(self.game_db[src]))
        self.refresh_list()

    def context_export_profile(self):
        row = self._current_row_data()
        rom_key = row.get("_rom_key")
        if not rom_key or rom_key not in self.game_db:
            return
        exports_dir = os.path.join(_base_dir(), "exports")
        os.makedirs(exports_dir, exist_ok=True)
        out_path = os.path.join(exports_dir, f"{rom_key}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(self.game_db[rom_key], f, indent=2, sort_keys=True)
            f.write("\n")
        messagebox.showinfo("Exported", f"Profile exported:\n{out_path}")

    def context_delete_profile(self):
        row = self._current_row_data()
        rom_key = row.get("_rom_key")
        if not rom_key or rom_key not in self.game_db:
            return
        if not messagebox.askyesno("Delete Profile", f"Remove in-memory profile '{rom_key}'?"):
            return
        del self.game_db[rom_key]
        if self.current_rom == rom_key:
            self.current_rom = None
        self.refresh_list()

    def apply_to_hw(self):
        if not self._ensure_connected():
            return
        if self.controller_mode == "ARCADE_PANEL":
            controls = self._collect_controls_from_ui()
            self.apply_profile_to_hw(controls)
            messagebox.showinfo("Hardware", "Preview applied.")
            return
        anim = self._selected_fx_animation()
        if anim:
            send = getattr(self.cab, "_send_packet", None)
            if callable(send):
                send({"command": "ANIMATION", "type": anim})

    def all_off(self): 
        for w in self.button_data.values():
            w["p"].config(bg=COLORS["SURFACE"])
            if w["s"]: w["s"].config(bg=COLORS["SURFACE"])
            w["lbl"].config(fg="white", bg=COLORS["SURFACE_LIGHT"])
        if self._ensure_connected():
            self.cab.set_all((0, 0, 0))
            self.cab.show()

    def build_card(self, parent, prefix, accent, buttons, col=0):
        if col > 0:
            c = tk.Frame(parent, bg=COLORS["BG"]); c.grid(row=0, column=col, sticky="nsew", padx=5)
        else: c = parent
        outer = tk.Frame(
            c,
            bg=COLORS["SURFACE"],
            highlightthickness=1,
            highlightbackground=accent,
            highlightcolor=accent,
            bd=0
        )
        outer.pack(fill="x")
        header = tk.Frame(outer, bg=COLORS["SURFACE_LIGHT"], padx=5, pady=4)
        header.pack(fill="x")
        badge = tk.Label(
            header,
            text="AC",
            bg=COLORS["BG"],
            fg=COLORS["TEXT"],
            font=("Segoe UI", 7, "bold"),
            padx=6,
            pady=1,
            highlightthickness=1,
            highlightbackground=accent,
            highlightcolor=accent,
        )
        badge.pack(side="left")
        tk.Label(header, text="PLAYER " + prefix[-1], font=("Segoe UI", 9, "bold"), bg=COLORS["SURFACE_LIGHT"], fg=accent).pack(side="left", padx=8)
        section_key = "P1" if prefix == "P1" else "P2"
        self.section_badges[section_key] = badge
        HoverTooltip(badge, lambda sk=section_key: CONTROLLER_TOOLTIP_MAP.get(self.section_badges[sk].cget("text"), CONTROLLER_TOOLTIP_MAP["??"]))
        inner = tk.Frame(outer, bg=COLORS["SURFACE"], padx=5, pady=5)
        inner.pack(fill="both")
        for b in buttons:
            f = tk.Frame(inner, bg=COLORS["SURFACE_LIGHT"], pady=2); f.pack(fill="x", pady=1)
            lbl = tk.Label(f, text=b, width=5, bg=COLORS["SURFACE_LIGHT"], fg="white", font=("Segoe UI", 8, "bold")); lbl.pack(side="left", padx=5)
            bid = f"{prefix}_{b}"
            s_sw = tk.Button(f, width=2, bg=COLORS["SURFACE"], relief="flat", command=lambda n=bid: self.pick_color(n, 's')); s_sw.pack(side="right", padx=2)
            p_sw = tk.Button(f, width=2, bg=COLORS["SURFACE"], relief="flat", command=lambda n=bid: self.pick_color(n, 'p')); p_sw.pack(side="right", padx=2)
            self.arcade_edit_widgets.extend([s_sw, p_sw])
            self.button_data[bid] = {"lbl": lbl, "p": p_sw, "s": s_sw}

    def build_system(self, parent):
        outer = tk.Frame(
            parent,
            bg=COLORS["SURFACE"],
            highlightthickness=1,
            highlightbackground=COLORS["SYS"],
            highlightcolor=COLORS["SYS"],
            bd=0
        )
        outer.pack(fill="x")
        header = tk.Frame(outer, bg=COLORS["SURFACE_LIGHT"], padx=5, pady=4)
        header.pack(fill="x")
        badge = tk.Label(
            header,
            text="AC",
            bg=COLORS["BG"],
            fg=COLORS["TEXT"],
            font=("Segoe UI", 7, "bold"),
            padx=6,
            pady=1,
            highlightthickness=1,
            highlightbackground=COLORS["SYS"],
            highlightcolor=COLORS["SYS"],
        )
        badge.pack(side="left")
        tk.Label(header, text="SYSTEM", font=("Segoe UI", 9, "bold"), bg=COLORS["SURFACE_LIGHT"], fg=COLORS["SYS"]).pack(side="left", padx=8)
        self.section_badges["SYS"] = badge
        HoverTooltip(badge, lambda: CONTROLLER_TOOLTIP_MAP.get(self.section_badges["SYS"].cget("text"), CONTROLLER_TOOLTIP_MAP["??"]))
        inner = tk.Frame(outer, bg=COLORS["SURFACE"], padx=5, pady=5)
        inner.pack(fill="both")
        for b in ["TRACKBALL", "REWIND", "MENU"]:
            f = tk.Frame(inner, bg=COLORS["SURFACE_LIGHT"], pady=2); f.pack(fill="x", pady=1)
            lbl = tk.Label(f, text=b, width=10, anchor="w", bg=COLORS["SURFACE_LIGHT"], fg="white", font=("Segoe UI", 8, "bold")); lbl.pack(side="left", padx=5)
            sw = tk.Button(f, width=3, bg=COLORS["SURFACE"], relief="flat", command=lambda n=b: self.pick_color(n, 'p')); sw.pack(side="right", padx=5)
            self.arcade_edit_widgets.append(sw)
            self.button_data[b] = {"lbl": lbl, "p": sw, "s": None}

    def build_fx(self, parent):
        fx = tk.LabelFrame(parent, text=" LED FX ", bg=COLORS["BG"], fg=COLORS["FX"], font=("Segoe UI", 9, "bold"), padx=10, pady=10)
        fx.pack(fill="x", anchor="n")
        fx_rows = [
            ("RAINBOW", "rainbow", "RAINBOW"),
            ("BREATH", "breath", "PULSE_RED"),
            ("STROBE", "strobe", "HYPER_STROBE"),
            ("FADE", "fade", "PULSE_BLUE"),
        ]
        for label, key, anim in fx_rows:
            f = tk.Frame(fx, bg=COLORS["SURFACE"], pady=4)
            f.pack(fill="x", pady=1)
            var = tk.BooleanVar()
            self.fx_vars[key] = var
            tk.Checkbutton(
                f,
                text=label,
                variable=var,
                bg=COLORS["SURFACE"],
                fg="white",
                selectcolor=COLORS["BG"],
                font=("Segoe UI", 8),
            ).pack(side="left")
            tk.Button(
                f,
                text="PREVIEW",
                bg=COLORS["SURFACE_LIGHT"],
                fg="white",
                font=("Segoe UI", 8, "bold"),
                relief="flat",
                command=lambda a=anim: self.preview_animation(a),
            ).pack(side="right", padx=(6, 4))
        self.fx_speed = tk.Scale(fx, from_=0.1, to=5.0, resolution=0.1, orient="horizontal", bg=COLORS["BG"], fg="white", highlightthickness=0)
        self.fx_speed.set(1.0)
        self.fx_speed.pack(fill="x", pady=10)
        tk.Button(
            fx,
            text="STOP ANIMATION",
            bg=COLORS["DANGER"],
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            command=self.stop_animation,
        ).pack(fill="x", pady=(4, 2))

    def on_select(self, _):
        sel = self.tree.selection()
        if not sel: return
        row = self._row_index.get(sel[0], {})
        self.current_rom = row.get("_rom_key")
        data = self.game_db.get(self.current_rom, {})
        profile = data.get("profile", {})
        self.controller_mode = profile.get("controller_mode", "ARCADE_PANEL")
        lighting_policy = profile.get("lighting_policy", "AUTO")
        default_fx = profile.get("default_fx", "")
        self.controller_mode_var.set(self.controller_mode)
        self.lighting_policy_var.set(lighting_policy)
        self.default_fx_var.set(default_fx if default_fx else "NONE")
        self.use_default_fx_var.set(str(lighting_policy).upper() == "FX_ONLY")
        self._update_controller_badges()
        self._update_editor_enable_state()
        self._last_saved_snapshot = json.loads(json.dumps(data)) if data else {"controls": {}, "fx": {}, "speed": 1.0}
        self.vendor_var.set(data.get("vendor", "") or row.get("_developer", ""))
        controls = data.get("controls", {})
        for w in self.button_data.values():
            w["p"].config(bg=COLORS["SURFACE"]); w["lbl"].config(fg="white", bg=COLORS["SURFACE_LIGHT"])
            if w["s"]: w["s"].config(bg=COLORS["SURFACE"])
        if controls:
            for bid, val in controls.items():
                if bid in self.button_data:
                    parts = val.split('|'); p_hex = self._ensure_hex(parts[0])
                    self.button_data[bid]["p"].config(bg=p_hex)
                    if len(parts) > 1 and self.button_data[bid]["s"]: self.button_data[bid]["s"].config(bg=self._ensure_hex(parts[1]))
                    if p_hex != COLORS["SURFACE"]: self.button_data[bid]["lbl"].config(fg="black", bg=p_hex)
            fx_data = data.get("fx", {}); [v.set(fx_data.get(k, False)) for k, v in self.fx_vars.items()]
            self.fx_speed.set(data.get("speed", 1.0))
        else:
            for v in self.fx_vars.values(): v.set(False)
            self.fx_speed.set(1.0)
        self._update_details(row)
        if self.preview_enabled.get() and controls:
            self.apply_profile_to_hw(controls)

    def save_game(self):
        rom = self.current_rom
        if not rom:
            messagebox.showinfo("No Game Selected", "Select a game to save an override.")
            return
        controls = self._collect_controls_from_ui()
        vendor = self.vendor_var.get().strip()
        self.game_db[rom] = self.game_db.get(rom, {})
        self.game_db[rom]["controls"] = controls
        self.game_db[rom]["fx"] = {k: v.get() for k, v in self.fx_vars.items()}
        self.game_db[rom]["speed"] = self.fx_speed.get()
        self.game_db[rom]["vendor"] = vendor
        profile = self.game_db[rom].setdefault("profile", {})
        profile["controller_mode"] = self.controller_mode_var.get()
        profile["lighting_policy"] = self.lighting_policy_var.get()
        profile["default_fx"] = "" if self.default_fx_var.get() == "NONE" else self.default_fx_var.get()
        with open(self.db_path, "w") as f: json.dump(self.game_db, f, indent=4)
        self._last_saved_snapshot = json.loads(json.dumps(self.game_db[rom]))
        if self._ensure_connected():
            self.apply_profile_to_hw(controls)
        messagebox.showinfo("Saved", f"Profile '{rom}' updated.")
        self.refresh_list()

    def pick_color(self, n, t):
        if self.controller_mode != "ARCADE_PANEL":
            return
        c = colorchooser.askcolor()[1]
        if c:
            target = self.button_data[n]["p"] if t == 'p' else self.button_data[n]["s"]
            target.config(bg=c)
            if t == 'p': self.button_data[n]["lbl"].config(fg="black", bg=c)
            if t == 'p' and self.preview_enabled.get():
                if self._ensure_connected():
                    self._send_led(n, c)
                    self.cab.show()

    def refresh_list(self, _=None):
        q = (self.search.get() or "").lower()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._row_index = {}
        rows = self._get_library_rows()
        for r in rows:
            values = (
                r.get("_title", ""),
                r.get("_developer", ""),
                r.get("_platforms", ""),
                r.get("_genres", ""),
                r.get("_rec_platform", ""),
                r.get("_rank", ""),
                r.get("_rom_key", ""),
                r.get("_profile", ""),
            )
            hay = " ".join(str(v).lower() for v in values if v)
            if q and q not in hay:
                continue
            item = self.tree.insert("", "end", values=values)
            self._row_index[item] = r

    def _get_library_rows(self):
        rows = []
        seen = set()
        if self.csv_rows and self.col_map.get("title"):
            for r in self.csv_rows:
                row = self._row_from_csv(r)
                rows.append(row)
                if row.get("_rom_key"):
                    seen.add(row["_rom_key"])
        for rom in sorted(self.game_db.keys()):
            if rom not in seen:
                rows.append(self._row_from_db(rom))
        return rows

    def _row_from_csv(self, row):
        title = row.get(self.col_map.get("title") or "", "")
        developer = row.get(self.col_map.get("developer") or "", "")
        year = row.get(self.col_map.get("year") or "", "")
        platforms = row.get(self.col_map.get("platforms") or "", "")
        genres = row.get(self.col_map.get("genres") or "", "")
        rec_platform = row.get(self.col_map.get("rec_platform") or "", "")
        rank = row.get(self.col_map.get("rank") or "", "")
        rom_key = _rom_key_from_title(title)
        profile = self._profile_status_text(rom_key)
        return {
            "_title": title or rom_key,
            "_developer": developer,
            "_year": year,
            "_platforms": platforms,
            "_genres": genres,
            "_rec_platform": rec_platform,
            "_rank": rank,
            "_rom_key": rom_key,
            "_profile": profile,
            "_raw": row,
        }

    def _row_from_db(self, rom_key):
        data = self.game_db.get(rom_key, {})
        title = data.get("full_name", rom_key)
        developer = data.get("vendor", "")
        return {
            "_title": title,
            "_developer": developer,
            "_year": "",
            "_platforms": "",
            "_genres": "",
            "_rec_platform": "",
            "_rank": "",
            "_rom_key": rom_key,
            "_profile": self._profile_status_text(rom_key),
            "_raw": data,
        }

    def _profile_status_text(self, rom_key):
        if not rom_key or rom_key not in self.game_db:
            return "NONE"
        entry = self.game_db.get(rom_key, {})
        controls = entry.get("controls", {})
        has_controls = isinstance(controls, dict) and len(controls) > 0
        profile = entry.get("profile", {})
        has_profile_fields = isinstance(profile, dict) and all(
            k in profile for k in ("controller_mode", "lighting_policy", "default_fx")
        )
        if has_controls and has_profile_fields:
            return "FULL"
        if has_controls:
            return "CONTROLS"
        return "META"

    def sort_tree(self, col):
        reverse = self._sort_state.get(col, False)
        items = []
        for k in self.tree.get_children(""):
            val = self.tree.set(k, col)
            items.append((val, k))
        def key_fn(item):
            v = item[0]
            if col == "rank":
                try:
                    return int(re.sub(r"[^0-9]", "", str(v)))
                except:
                    return 9999
            try:
                return int(v)
            except:
                return str(v).lower()
        items.sort(key=key_fn, reverse=reverse)
        for index, (_, k) in enumerate(items):
            self.tree.move(k, "", index)
        self._sort_state[col] = not reverse

    def _update_details(self, row):
        if not row:
            return
        rom_key = row.get("_rom_key", "")
        title = row.get("_title") or "â€”"
        developer = row.get("_developer") or "â€”"
        year = row.get("_year") or "â€”"
        genre = row.get("_genres") or "â€”"
        platform = row.get("_platforms") or ""
        rec = row.get("_rec_platform") or ""
        if platform and rec:
            platform_rec = f"{platform} / {rec}"
        else:
            platform_rec = platform or rec or "â€”"
        rank = row.get("_rank") or "â€”"

        self.detail_vars["catalog_title"].set(title)
        self.detail_vars["catalog_developer"].set(developer)
        self.detail_vars["catalog_year"].set(year)
        self.detail_vars["catalog_genre"].set(genre)
        self.detail_vars["catalog_platform"].set(platform_rec)
        self.detail_vars["catalog_rank"].set(rank)
        self.detail_vars["profile_rom"].set(rom_key or "â€”")

        status = self._profile_status_text(rom_key)
        self.detail_vars["profile_status"].set(status)
        if status == "NONE":
            self.detail_vars["profile_controller_mode"].set("â€”")
            self.detail_vars["profile_lighting_policy"].set("â€”")
            self.detail_vars["profile_default_fx"].set("â€”")
            return

        entry = self.game_db.get(rom_key, {})
        profile = entry.get("profile", {})
        mode_raw = profile.get("controller_mode", "ARCADE_PANEL")
        mode_badge = CONTROLLER_BADGE_MAP.get(mode_raw, "??")
        self.detail_vars["profile_controller_mode"].set(f"{mode_badge} ({mode_raw})")
        self.detail_vars["profile_lighting_policy"].set(profile.get("lighting_policy", "â€”") or "â€”")
        fx = profile.get("default_fx", "")
        self.detail_vars["profile_default_fx"].set(fx if fx else "â€”")

    def _update_controller_badges(self):
        badge_text = CONTROLLER_BADGE_MAP.get(self.controller_mode, "??")
        for key in ("P1", "P2", "SYS"):
            lbl = self.section_badges.get(key)
            if lbl:
                lbl.config(text=badge_text)

    def _on_controller_mode_changed(self, _event=None):
        self.controller_mode = self.controller_mode_var.get()
        self._update_controller_badges()
        self._update_editor_enable_state()
        self._update_details(self._current_row_data())

    def _update_editor_enable_state(self):
        is_arcade = self.controller_mode == "ARCADE_PANEL"
        for w in self.arcade_edit_widgets:
            try:
                w.config(state=("normal" if is_arcade else "disabled"))
            except Exception:
                pass
        self.arcade_disabled_note.config(
            fg=(COLORS["BG"] if is_arcade else COLORS["TEXT_DIM"])
        )

    def _on_lighting_policy_changed(self, _event=None):
        policy = self.lighting_policy_var.get()
        self.use_default_fx_var.set(str(policy).upper() == "FX_ONLY")
        self._update_details(self._current_row_data())

    def _on_default_fx_changed(self, _event=None):
        self._update_details(self._current_row_data())

    def _on_use_default_fx_toggle(self):
        if self.use_default_fx_var.get():
            self.lighting_policy_var.set("FX_ONLY")
        elif self.lighting_policy_var.get() == "FX_ONLY":
            self.lighting_policy_var.set("AUTO")
        self._update_details(self._current_row_data())

    def _current_row_data(self):
        sel = self.tree.selection()
        if not sel:
            return {}
        return self._row_index.get(sel[0], {})

    def _selected_fx_animation(self):
        mapping = {
            "rainbow": "RAINBOW",
            "breath": "PULSE_RED",
            "strobe": "HYPER_STROBE",
            "fade": "PULSE_BLUE",
        }
        for key in ("rainbow", "breath", "strobe", "fade"):
            v = self.fx_vars.get(key)
            if v and v.get():
                return mapping[key]
        return None

    def create_profile_from_defaults(self):
        if not self.current_rom:
            messagebox.showinfo("No Game Selected", "Select a game first.")
            return
        if self.current_rom in self.game_db:
            messagebox.showinfo("Profile Exists", "A profile already exists for this game.")
            return
        vendor = self.vendor_var.get().strip()
        self.game_db[self.current_rom] = {
            "controls": {},
            "fx": {k: v.get() for k, v in self.fx_vars.items()},
            "speed": self.fx_speed.get(),
            "vendor": vendor,
            "profile": {
                "controller_mode": self.controller_mode_var.get(),
                "lighting_policy": self.lighting_policy_var.get(),
                "default_fx": "" if self.default_fx_var.get() == "NONE" else self.default_fx_var.get(),
            },
        }
        with open(self.db_path, "w") as f:
            json.dump(self.game_db, f, indent=4)
        self._last_saved_snapshot = json.loads(json.dumps(self.game_db[self.current_rom]))
        self.refresh_list()
        messagebox.showinfo("Profile Created", f"Created profile for '{self.current_rom}'.")

    def _collect_controls_from_ui(self):
        controls = {}
        for bid, w in self.button_data.items():
            p_hex = w["p"].cget("bg")
            s_hex = w["s"].cget("bg") if w["s"] else COLORS["SURFACE"]
            if p_hex and p_hex != COLORS["SURFACE"]:
                controls[bid] = f"{p_hex}|{s_hex}"
        return controls

    def apply_profile_to_hw(self, controls):
        if not self._ensure_connected():
            return
        self.cab.set_all((0, 0, 0))
        for name, val in controls.items():
            parts = val.split("|")
            p_hex = self._ensure_hex(parts[0]) if parts else COLORS["SURFACE"]
            if p_hex != COLORS["SURFACE"]:
                self._send_led(name, p_hex)
        self.cab.show()

    def _send_led(self, name, hex_color):
        try:
            h = hex_color.lstrip("#")
            rgb = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            self.cab.set(name, rgb)
        except Exception:
            pass

    def _ensure_connected(self):
        try:
            if not self.cab.is_connected():
                self.cab.reconnect()
        except Exception:
            pass
        try:
            if self.cab.is_connected():
                return True
        except Exception:
            pass
        if not self._warned_offline:
            messagebox.showwarning("ACLighter Offline", "ACLighter is not running or unreachable.\nStart ACLighter.exe to enable live preview.")
            self._warned_offline = True
        return False

    def cancel_changes(self):
        if self.current_rom and self._last_saved_snapshot:
            data = self._last_saved_snapshot
            controls = data.get("controls", {})
            for w in self.button_data.values():
                w["p"].config(bg=COLORS["SURFACE"]); w["lbl"].config(fg="white", bg=COLORS["SURFACE_LIGHT"])
                if w["s"]: w["s"].config(bg=COLORS["SURFACE"])
            for bid, val in controls.items():
                if bid in self.button_data:
                    parts = val.split('|'); p_hex = self._ensure_hex(parts[0])
                    self.button_data[bid]["p"].config(bg=p_hex)
                    if len(parts) > 1 and self.button_data[bid]["s"]:
                        self.button_data[bid]["s"].config(bg=self._ensure_hex(parts[1]))
                    if p_hex != COLORS["SURFACE"]:
                        self.button_data[bid]["lbl"].config(fg="black", bg=p_hex)
            fx_data = data.get("fx", {}); [v.set(fx_data.get(k, False)) for k, v in self.fx_vars.items()]
            self.fx_speed.set(data.get("speed", 1.0))
            self.vendor_var.set(data.get("vendor", ""))
            profile = data.get("profile", {})
            self.controller_mode = profile.get("controller_mode", "ARCADE_PANEL")
            self.controller_mode_var.set(self.controller_mode)
            self.lighting_policy_var.set(profile.get("lighting_policy", "AUTO"))
            fx_name = profile.get("default_fx", "")
            self.default_fx_var.set(fx_name if fx_name else "NONE")
            self.use_default_fx_var.set(self.lighting_policy_var.get() == "FX_ONLY")
            self._update_controller_badges()
            self._update_editor_enable_state()
            self._update_details(self._current_row_data())
            if self._ensure_connected():
                self.apply_profile_to_hw(controls)
        self.root.destroy()

    def refresh_status(self):
        online = False
        try:
            if not self.cab.is_connected():
                self.cab.reconnect()
            online = self.cab.is_connected()
        except Exception:
            online = False
        if online:
            self.net_lbl.config(text="ACLIGHTER: ONLINE", fg=COLORS["SUCCESS"])
        else:
            self.net_lbl.config(text="ACLIGHTER: OFFLINE", fg=COLORS["DANGER"])
        self.root.after(1000, self.refresh_status)

    def preview_animation(self, anim_type):
        if not self._ensure_connected():
            return
        send = getattr(self.cab, "_send_packet", None)
        if not callable(send):
            messagebox.showwarning("Unavailable", "Animation preview is not supported by this adapter.")
            return
        send({"command": "ANIMATION", "type": anim_type})

    def stop_animation(self):
        if not self._ensure_connected():
            return
        send = getattr(self.cab, "_send_packet", None)
        if not callable(send):
            return
        send({"command": "STATE_UPDATE", "mode": "IDLE", "data": {}})

if __name__ == "__main__":
    root = tk.Tk(); app = StableStealthManager(root); root.mainloop()


