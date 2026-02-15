import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import json
import os
import colorsys
import time
import math
from AnimationRegistry import resolve_animation
from app_paths import game_db_file, migrate_legacy_runtime_files

COLORS = { "BG": "#0A0A0A", "SURFACE": "#161616", "P1": "#39FF14", 
           "P2": "#FF5F1F", "SYS": "#00E5FF", "TEXT": "#E0E0E0",
           "ACCENT": "#00E5FF", "HILITE": "#333333" }

LABEL_MAP = {
    "P1_A": "A", "P1_B": "B", "P1_C": "C", "P1_X": "X", "P1_Y": "Y", "P1_Z": "Z",
    "P2_A": "A", "P2_B": "B", "P2_C": "C", "P2_X": "X", "P2_Y": "Y", "P2_Z": "Z",
    "REWIND": "«", "P1_START": "P1", "MENU": "≡", "P2_START": "P2", "REWIND_ALT": "»",
    "TRACKBALL": ""
}

class VirtualLED:
    def __init__(self, canvas, x, y, radius, label, label_type):
        self.canvas = canvas
        self.is_lit = False
        self.catchlight_enabled = True
        self.current_color = None
        self._near_white = False
        
        self.glow = canvas.create_oval(x-radius-6, y-radius-6, x+radius+6, y+radius+6, fill="", outline="", state="hidden")
        self.bezel = canvas.create_oval(x-radius, y-radius, x+radius, y+radius, outline="#111", width=2)
        
        self.unlit_fill = "#444444" 
        self.unlit_outline = "#222222"
        self.lens = canvas.create_oval(x-radius+2, y-radius+2, x+radius-2, y+radius-2, 
                                       fill=self.unlit_fill, outline=self.unlit_outline, width=1)
        
        self.reflection = canvas.create_oval(x-radius*0.4, y-radius*0.6, x+radius*0.1, y-radius*0.3, 
                                             fill="#FFFFFF", outline="", stipple="gray25", state="hidden")

        self.text_id = None
        self.label_type = label_type
        if label_type == "INSIDE":
            self.text_id = canvas.create_text(x, y, text=label, fill="#555", font=("Segoe UI", 8, "bold"))
        elif label_type == "BELOW":
            canvas.create_text(x, y+radius+12, text=label, fill="#AAA", font=("Segoe UI", 7, "bold"))
        elif label_type == "ABOVE":
            canvas.create_text(x, y-radius-12, text=label, fill="#AAA", font=("Segoe UI", 7, "bold"))

    def set_color(self, hex_color):
        self.is_lit = bool(hex_color and hex_color != COLORS["SURFACE"])
        self.current_color = hex_color
        
        if not self.is_lit:
            self._near_white = False
            self.canvas.itemconfigure(self.glow, state="hidden")
            self.canvas.itemconfigure(self.lens, fill=self.unlit_fill, outline=self.unlit_outline)
            self.canvas.itemconfigure(self.reflection, state="hidden")
            if self.text_id and self.label_type == "INSIDE":
                self.canvas.itemconfigure(self.text_id, fill="#555")
        else:
            r = g = b = 0
            try:
                h = str(hex_color).lstrip("#")
                if len(h) == 6:
                    r = int(h[0:2], 16)
                    g = int(h[2:4], 16)
                    b = int(h[4:6], 16)
            except Exception:
                pass
            self._near_white = (r >= 245 and g >= 245 and b >= 245)
            if self._near_white:
                # White needs a cleaner lens/overlay treatment so it doesn't read as gray.
                self.canvas.itemconfigure(self.glow, state="normal", fill="#ffffff", stipple="gray25")
                self.canvas.itemconfigure(self.lens, fill="#ffffff", outline="#f7f7f7")
            else:
                self.canvas.itemconfigure(self.glow, state="normal", fill=hex_color, stipple="gray50")
                self.canvas.itemconfigure(self.lens, fill=hex_color, outline=hex_color)
            if self.text_id and self.label_type == "INSIDE":
                self.canvas.itemconfigure(self.text_id, fill="black")
            
            self.update_reflection_visibility()

    def set_catchlight_mode(self, enabled):
        self.catchlight_enabled = enabled
        self.update_reflection_visibility()

    def update_reflection_visibility(self):
        if self.is_lit and self.catchlight_enabled and not self._near_white:
            self.canvas.itemconfigure(self.reflection, state="normal")
        else:
            self.canvas.itemconfigure(self.reflection, state="hidden")

class EmulatorApp:
    def __init__(self, parent, db_path=None, assets_dir="assets", target_w=1320, show_sidebar=True,
                 hw_set=None, hw_set_all=None, hw_show=None, hw_connected=None, hw_snapshot=None, sync_hw=True):
        migrate_legacy_runtime_files()
        self.parent = parent
        self.root = parent if isinstance(parent, tk.Tk) else parent.winfo_toplevel()
        self.container = tk.Frame(parent, bg=COLORS["BG"])
        if isinstance(parent, tk.Tk):
            self.root.title("AC V2.0 - CONSOLE VISUALIZER")
            self.root.geometry("1100x750")
            self.root.configure(bg=COLORS["BG"])
        self.container.pack(fill="both", expand=True)
        
        self.leds = {}
        self.db_path = db_path or game_db_file()
        self.assets_dir = assets_dir
        self.target_w = target_w
        self.current_rom = None
        self.animation_running = False
        self.catchlight_var = tk.BooleanVar(value=True)
        self.show_sidebar = show_sidebar
        self.layout_data = None
        self.bg_img = None
        self._canvas_w = None
        self._source_img = None
        self.profile_colors = {}
        self.hw_set = hw_set
        self.hw_set_all = hw_set_all
        self.hw_show = hw_show
        self.hw_connected = hw_connected
        self.hw_snapshot = hw_snapshot
        self.sync_hw = sync_hw
        self._hw_sync_job = None
        self._pulse_job = None
        self._pulse_state = {}
        self._conn_bg_id = None
        self._conn_text_id = None
        self._conn_status_job = None
        
        self.setup_ui()
        self.load_environment()
        if self.sync_hw:
            self._schedule_hw_sync()
        if self.show_sidebar:
            self.load_db_list()

    def setup_ui(self):
        main = tk.Frame(self.container, bg=COLORS["BG"])
        main.pack(fill="both", expand=True)
        if isinstance(self.parent, tk.Tk):
            tk.Button(
                main,
                text="QUIT",
                bg="#D50000",
                fg="white",
                relief="flat",
                command=self.root.destroy,
                font=("Segoe UI", 8, "bold"),
            ).place(relx=1.0, x=-10, y=10, anchor="ne")

        if self.show_sidebar:
            sidebar = tk.Frame(main, bg=COLORS["BG"], width=240)
            sidebar.pack(side="left", fill="y", padx=10, pady=10)
            sidebar.pack_propagate(False)

            opt_frame = tk.LabelFrame(sidebar, text=" VISUAL OPTIONS ", bg=COLORS["BG"], fg="white", font=("Segoe UI", 8, "bold"), padx=10, pady=5)
            opt_frame.pack(fill="x", pady=(0, 10))
            tk.Checkbutton(opt_frame, text="Show Catchlight", variable=self.catchlight_var, 
                           bg=COLORS["BG"], fg="#CCC", selectcolor="#222", activebackground=COLORS["BG"], 
                           command=self.toggle_catchlight).pack(anchor="w")

            tk.Label(sidebar, text="SELECT CONTEXT (GAME)", fg=COLORS["P1"], bg=COLORS["BG"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(5,0))
            self.listbox = tk.Listbox(sidebar, bg=COLORS["SURFACE"], fg="#EEE", borderwidth=0, height=12, selectbackground=COLORS["ACCENT"], selectforeground="black")
            self.listbox.pack(fill="x", pady=5)
            self.listbox.bind("<<ListboxSelect>>", self.on_game_selected)

            sim_frame = tk.LabelFrame(sidebar, text=" EVENT SIMULATION ", bg=COLORS["BG"], fg=COLORS["SYS"], font=("Segoe UI", 9, "bold"), padx=10, pady=10)
            sim_frame.pack(fill="x", pady=15)
            
            btn_style = {"bg": COLORS["HILITE"], "fg": "white", "relief": "flat", "font": ("Segoe UI", 9)}
            tk.Button(sim_frame, text="▶  LAUNCH EVENT", command=lambda: self.trigger_event("launch"), **btn_style).pack(fill="x", pady=2)
            tk.Button(sim_frame, text="⏸  PAUSE MENU", command=lambda: self.trigger_event("pause"), **btn_style).pack(fill="x", pady=2)
            tk.Button(sim_frame, text="⏹  STOP / GAME OVER", command=lambda: self.trigger_event("stop"), **btn_style).pack(fill="x", pady=2)
            tk.Frame(sim_frame, bg=COLORS["BG"], height=10).pack()
            tk.Button(sim_frame, text="⟳  IDLE / ATTRACT", command=lambda: self.trigger_event("idle"), bg=COLORS["SURFACE"], fg=COLORS["P2"], relief="flat").pack(fill="x", pady=2)
            tk.Button(sim_frame, text="✖  RESET TO STATIC", command=self.reset_to_static, bg="#D50000", fg="white", relief="flat").pack(fill="x", pady=(10, 0))

        self.canvas = tk.Canvas(main, bg="black", highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<Button-1>", self._on_canvas_click)

    def load_environment(self):
        # Load template selection
        img_name = "Consol.png"
        layout_name = "layout.json"
        cfg_path = os.path.join(self.assets_dir, "layout_config.json")
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r") as f:
                    cfg = json.load(f)
                name = cfg.get("template", "ALU")
                if name == "4P":
                    img_name = "4PlayerDeck.jpg"
                    layout_name = "layout_4p.json"
            except Exception:
                pass
        img_path = os.path.join(self.assets_dir, img_name)
        if not os.path.exists(img_path): img_path = img_name
        
        layout_path = os.path.join(self.assets_dir, layout_name)
        self._layout_path = layout_path
        self._layout_mtime = None
        layout_loaded = False
        if os.path.exists(layout_path):
            try:
                self._layout_mtime = os.path.getmtime(layout_path)
                with open(layout_path, "r") as f:
                    self.layout_data = json.load(f)
                layout_loaded = bool(self.layout_data)
            except Exception:
                self.layout_data = None
        if not layout_loaded:
            # Fallback to default layout.json if template layout is missing/empty
            fallback = os.path.join(self.assets_dir, "layout.json")
            if os.path.exists(fallback):
                try:
                    self._layout_path = fallback
                    self._layout_mtime = os.path.getmtime(fallback)
                    with open(fallback, "r") as f:
                        self.layout_data = json.load(f)
                except Exception:
                    self.layout_data = None
            else:
                self.layout_data = None
        
        if os.path.exists(img_path):
            self._source_img = Image.open(img_path)
            self._render_scene()
        else:
            tk.Label(self.canvas, text="BACKGROUND MISSING", fg="red").place(relx=0.5, rely=0.5)
        self._schedule_layout_watch()

    def _render_scene(self):
        if not self._source_img:
            return
        canvas_w = self.canvas.winfo_width() if self.canvas.winfo_width() > 1 else self.target_w
        if canvas_w == self._canvas_w:
            return
        self._canvas_w = canvas_w
        ratio = canvas_w / self._source_img.size[0]
        target_h = int(self._source_img.size[1] * ratio)
        self.bg_img = ImageTk.PhotoImage(self._source_img.resize((canvas_w, target_h), Image.Resampling.LANCZOS))
        self.canvas.delete("all")
        self._conn_bg_id = None
        self._conn_text_id = None
        self.canvas.config(width=canvas_w, height=target_h)
        self.canvas.create_image(0, 0, anchor="nw", image=self.bg_img)
        self.leds = {}
        if self.layout_data:
            for bid, data in self.layout_data.items():
                x = data["rel_x"] * canvas_w
                y = data["rel_y"] * target_h
                r = data["rel_r"] * canvas_w
                l_type = data.get("label_type", "BELOW")
                if bid.endswith("_X") or bid.endswith("_Y") or bid.endswith("_Z"):
                    l_type = "ABOVE"
                self.leds[bid] = VirtualLED(self.canvas, x, y, r, LABEL_MAP.get(bid, bid), l_type)
        else:
            tk.Label(self.canvas, text="LAYOUT MISSING", fg="red").place(relx=0.5, rely=0.5)
        self._update_connection_status()

    def _get_connection_status(self):
        if callable(self.hw_connected):
            try:
                return bool(self.hw_connected())
            except Exception:
                return False
        return False

    def _connection_bounds(self):
        canvas_w = self._canvas_w or (self.canvas.winfo_width() if self.canvas.winfo_width() > 1 else self.target_w)
        if self._source_img:
            ratio = canvas_w / self._source_img.size[0]
            target_h = int(self._source_img.size[1] * ratio)
        else:
            target_h = self.canvas.winfo_height()
        x = int(canvas_w * 0.03)
        y = int(target_h * 0.05)
        w = 220
        h = 22
        return x, y, w, h

    def _update_connection_status(self):
        self._conn_status_job = None
        if not self.canvas:
            return
        is_connected = self._get_connection_status()
        label = "CONSOLE CONNECTED" if is_connected else "CONSOLE DISCONNECTED"
        color = "#39FF14" if is_connected else "#FF5555"
        x, y, w, h = self._connection_bounds()
        if self._conn_bg_id is None:
            self._conn_bg_id = self.canvas.create_rectangle(x, y, x + w, y + h, fill="#0B1116", outline="#1C1C1C")
            self._conn_text_id = self.canvas.create_text(
                x + 8, y + (h // 2), anchor="w", text=label, fill=color, font=("Segoe UI", 9, "bold")
            )
        else:
            self.canvas.coords(self._conn_bg_id, x, y, x + w, y + h)
            self.canvas.coords(self._conn_text_id, x + 8, y + (h // 2))
            self.canvas.itemconfigure(self._conn_text_id, text=label, fill=color)
        self.canvas.tag_raise(self._conn_bg_id)
        self.canvas.tag_raise(self._conn_text_id)
        self._conn_status_job = self.root.after(1000, self._update_connection_status)

    def _on_canvas_resize(self, _evt=None):
        self._render_scene()

    def _schedule_layout_watch(self):
        if getattr(self, "_layout_watch_job", None):
            try:
                self.root.after_cancel(self._layout_watch_job)
            except Exception:
                pass
        self._layout_watch_job = self.root.after(500, self._check_layout_update)

    def _check_layout_update(self):
        self._layout_watch_job = None
        path = getattr(self, "_layout_path", None)
        if path and os.path.exists(path):
            try:
                mtime = os.path.getmtime(path)
                if self._layout_mtime is None or mtime > self._layout_mtime:
                    self._layout_mtime = mtime
                    with open(path, "r") as f:
                        self.layout_data = json.load(f)
                    self._render_scene()
            except Exception:
                pass
        self._schedule_layout_watch()
    def _on_canvas_click(self, event):
        bid = self._hit_test(event.x, event.y)
        if not bid or bid not in self.leds:
            return
        led = self.leds[bid]
        if led.is_lit:
            led.set_color(None)
            self._send_hw_color(bid, None)
        else:
            color = self.profile_colors.get(bid) or "#00E5FF"
            led.set_color(color)
            self._send_hw_color(bid, color)
        self._send_hw_show()

    def _hit_test(self, x, y):
        for bid, data in (self.layout_data or {}).items():
            px = data["rel_x"] * self._canvas_w
            py = data["rel_y"] * (self._canvas_w * (self._source_img.size[1] / self._source_img.size[0])) if self._source_img else 0
            r = data["rel_r"] * self._canvas_w
            if ((x - px) ** 2 + (y - py) ** 2) ** 0.5 <= r:
                return bid
        return None

    def _hex_to_rgb(self, hex_color):
        if not hex_color:
            return None
        h = hex_color.lstrip("#")
        if len(h) != 6:
            return None
        try:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        except Exception:
            return None

    def _rgb_to_hex(self, rgb):
        if not isinstance(rgb, (tuple, list)) or len(rgb) != 3:
            return None
        try:
            r = max(0, min(255, int(rgb[0])))
            g = max(0, min(255, int(rgb[1])))
            b = max(0, min(255, int(rgb[2])))
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return None

    def _parse_hw_color(self, val):
        if val is None:
            return None
        if isinstance(val, str):
            raw = val.split("|", 1)[0].strip()
            if raw.lower() in ("", "-", "none", "off", "null", "n/a"):
                return None
            if raw.startswith("#") and len(raw) == 7:
                return raw
            if "," in raw:
                try:
                    r, g, b = [int(x.strip()) for x in raw.split(",")[:3]]
                    return self._rgb_to_hex((r, g, b))
                except Exception:
                    return None
            # Support named colors from the DB (e.g. "Red", "Blue", "Cyan").
            try:
                r16, g16, b16 = self.root.winfo_rgb(raw)
                return self._rgb_to_hex((r16 // 256, g16 // 256, b16 // 256))
            except Exception:
                return None
        if isinstance(val, (tuple, list)) and len(val) == 3:
            return self._rgb_to_hex(val)
        return None

    def _normalize_rgb(self, val):
        if val is None:
            return None
        if isinstance(val, str):
            hex_c = self._parse_hw_color(val)
            return self._hex_to_rgb(hex_c) if hex_c else None
        if isinstance(val, (tuple, list)) and len(val) == 3:
            try:
                return (int(val[0]), int(val[1]), int(val[2]))
            except Exception:
                return None
        return None

    def _send_hw_color(self, bid, hex_color):
        if not self.hw_set:
            return
        if self.hw_connected and not self.hw_connected():
            return
        rgb = self._hex_to_rgb(hex_color) if hex_color else (0, 0, 0)
        if rgb is None:
            return
        try:
            self.hw_set(bid, rgb)
        except Exception:
            pass

    def _send_hw_all(self, hex_color):
        if not self.hw_set_all:
            return
        if self.hw_connected and not self.hw_connected():
            return
        rgb = self._hex_to_rgb(hex_color) if hex_color else (0, 0, 0)
        if rgb is None:
            return
        try:
            self.hw_set_all(rgb)
        except Exception:
            pass

    def _send_hw_show(self):
        if not self.hw_show:
            return
        if self.hw_connected and not self.hw_connected():
            return
        try:
            self.hw_show()
        except Exception:
            pass

    def _schedule_hw_sync(self):
        if not callable(self.hw_snapshot):
            return
        if self._hw_sync_job:
            try:
                self.root.after_cancel(self._hw_sync_job)
            except Exception:
                pass
        self._hw_sync_job = self.root.after(120, self._sync_from_hw_state)

    def _sync_from_hw_state(self):
        self._hw_sync_job = None
        if not callable(self.hw_snapshot):
            return
        try:
            snapshot = self.hw_snapshot() or {}
        except Exception:
            snapshot = {}
        if snapshot and any(isinstance(v, dict) for v in snapshot.values()):
            self.apply_snapshot(snapshot)
            self._hw_sync_job = self.root.after(120, self._sync_from_hw_state)
            return
        if self.leds:
            source = snapshot if snapshot else self.profile_colors
            for bid, led in self.leds.items():
                color = None
                if source:
                    color = self._parse_hw_color(source.get(bid))
                led.set_color(color)
        self._hw_sync_job = self.root.after(120, self._sync_from_hw_state)

    def apply_snapshot(self, snapshot):
        if not self.leds or not isinstance(snapshot, dict):
            return
        any_pulse = False
        for bid, led in self.leds.items():
            entry = snapshot.get(bid)
            if isinstance(entry, dict):
                color = self._parse_hw_color(entry.get("color"))
                pulse = bool(entry.get("pulse"))
                try:
                    speed = float(entry.get("speed", 1.0))
                except Exception:
                    speed = 1.0
                colors_raw = entry.get("colors", [])
                try:
                    phase = float(entry.get("phase", 0.0))
                except Exception:
                    phase = 0.0
                fx_mode = entry.get("fx_mode")
            else:
                color = self._parse_hw_color(entry)
                pulse = False
                speed = 1.0
                colors_raw = []
                phase = 0.0
                fx_mode = None
            colors = []
            if isinstance(colors_raw, list):
                for c in colors_raw:
                    rgb = self._normalize_rgb(c)
                    if rgb:
                        colors.append(rgb)
            if not colors and color:
                base = self._hex_to_rgb(color)
                if base:
                    colors = [base]
            # Render pulse/fx frame immediately using provided phase.
            if pulse or fx_mode:
                any_pulse = True
                if pulse:
                    if colors:
                        if len(colors) == 1:
                            r, g, b = colors[0]
                            led.set_color(self._rgb_to_hex((r, g, b)))
                        else:
                            t = phase % len(colors)
                            i = int(t)
                            f = t - i
                            c1 = colors[i]
                            c2 = colors[(i + 1) % len(colors)]
                            r = int(c1[0] + (c2[0] - c1[0]) * f)
                            g = int(c1[1] + (c2[1] - c1[1]) * f)
                            b = int(c1[2] + (c2[2] - c1[2]) * f)
                            led.set_color(self._rgb_to_hex((r, g, b)))
                    else:
                        led.set_color(color)
                else:
                    if fx_mode == "RAINBOW":
                        hue = (phase % 255) / 255.0
                        rr, gg, bb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                        led.set_color(self._rgb_to_hex((int(rr * 255), int(gg * 255), int(bb * 255))))
                    elif fx_mode == "BREATH":
                        base = colors[0] if colors else (0, 255, 255)
                        breathe = (math.sin(phase) + 1.0) / 2.0
                        led.set_color(self._rgb_to_hex((int(base[0] * breathe), int(base[1] * breathe), int(base[2] * breathe))))
                    elif fx_mode == "STROBE":
                        base = colors[0] if colors else (255, 255, 255)
                        on = int(phase) % 2 == 0
                        led.set_color(self._rgb_to_hex(base if on else (0, 0, 0)))
                    elif fx_mode == "FADE":
                        if colors:
                            if len(colors) == 1:
                                r, g, b = colors[0]
                            else:
                                t = phase % len(colors)
                                i = int(t)
                                f = t - i
                                c1 = colors[i]
                                c2 = colors[(i + 1) % len(colors)]
                                r = int(c1[0] + (c2[0] - c1[0]) * f)
                                g = int(c1[1] + (c2[1] - c1[1]) * f)
                                b = int(c1[2] + (c2[2] - c1[2]) * f)
                            led.set_color(self._rgb_to_hex((r, g, b)))
                        else:
                            led.set_color(color)
                    else:
                        led.set_color(color)
            else:
                led.set_color(color or (self._rgb_to_hex(colors[0]) if colors else None))
        # Commander drives timing; render snapshot only to avoid drift.
        self._stop_pulse_loop()

    def _start_pulse_loop(self):
        if self._pulse_job:
            return
        self._pulse_job = self.root.after(30, self._pulse_tick)

    def _stop_pulse_loop(self):
        if self._pulse_job:
            try:
                self.root.after_cancel(self._pulse_job)
            except Exception:
                pass
            self._pulse_job = None

    def _pulse_tick(self):
        self._pulse_job = None
        if not self._pulse_state:
            return
        any_active = False
        for bid, state in self._pulse_state.items():
            colors = state.get("colors") or []
            speed = max(0.2, float(state.get("speed", 1.0)))
            state["phase"] = float(state.get("phase", 0.0)) + 0.1 * speed
            if state.get("pulse"):
                if not colors:
                    continue
                any_active = True
                if len(colors) == 1:
                    r, g, b = colors[0]
                else:
                    t = state["phase"] % len(colors)
                    i = int(t)
                    f = t - i
                    c1 = colors[i]
                    c2 = colors[(i + 1) % len(colors)]
                    r = int(c1[0] + (c2[0] - c1[0]) * f)
                    g = int(c1[1] + (c2[1] - c1[1]) * f)
                    b = int(c1[2] + (c2[2] - c1[2]) * f)
            else:
                fx_mode = state.get("fx_mode")
                if not fx_mode:
                    continue
                any_active = True
                if fx_mode == "RAINBOW":
                    hue = (state["phase"] % 255) / 255.0
                    rr, gg, bb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                    r, g, b = int(rr * 255), int(gg * 255), int(bb * 255)
                elif fx_mode == "BREATH":
                    base = colors[0] if colors else (0, 255, 255)
                    phase = (math.sin(state["phase"]) + 1.0) / 2.0
                    r = int(base[0] * phase)
                    g = int(base[1] * phase)
                    b = int(base[2] * phase)
                elif fx_mode == "STROBE":
                    base = colors[0] if colors else (255, 255, 255)
                    on = int(state["phase"]) % 2 == 0
                    r, g, b = base if on else (0, 0, 0)
                elif fx_mode == "FADE":
                    if not colors:
                        continue
                    if len(colors) == 1:
                        r, g, b = colors[0]
                    else:
                        t = state["phase"] % len(colors)
                        i = int(t)
                        f = t - i
                        c1 = colors[i]
                        c2 = colors[(i + 1) % len(colors)]
                        r = int(c1[0] + (c2[0] - c1[0]) * f)
                        g = int(c1[1] + (c2[1] - c1[1]) * f)
                        b = int(c1[2] + (c2[2] - c1[2]) * f)
                else:
                    continue
            if bid in self.leds:
                self.leds[bid].set_color(self._rgb_to_hex((r, g, b)))
        if any_active:
            self._pulse_job = self.root.after(30, self._pulse_tick)

    def toggle_catchlight(self):
        enabled = self.catchlight_var.get()
        for led in self.leds.values(): led.set_catchlight_mode(enabled)

    def load_db_list(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r") as f:
                    data = json.load(f)
                    for rom in sorted(data.keys()): self.listbox.insert(tk.END, rom)
            except: pass

    def on_game_selected(self, _):
        if not self.listbox.curselection(): return
        self.current_rom = self.listbox.get(self.listbox.curselection())
        self.reset_to_static()

    def load_profile_by_rom(self, rom):
        self.current_rom = rom
        self.reset_to_static()

    def reset_to_static(self):
        self.animation_running = False
        self.clear_leds()
        self.profile_colors = {}
        if not self.current_rom: return
        try:
            with open(self.db_path, "r") as f:
                data = json.load(f).get(self.current_rom, {}).get("controls", {})
            for bid, val in data.items():
                if bid in self.leds:
                    color = self._parse_hw_color(val)
                    self.leds[bid].set_color(color)
                    self.profile_colors[bid] = color
                    self._send_hw_color(bid, color)
            self._send_hw_show()
        except: pass

    def clear_leds(self):
        for led in self.leds.values(): led.set_color(None)
        self._send_hw_all(None)
        self._send_hw_show()

    def trigger_event(self, event_type):
        resolved = resolve_animation(event_type)
        if resolved in ("LAUNCH", "PAUSE", "STOP", "IDLE"):
            event_type = resolved.lower()
        self.animation_running = True
        self.clear_leds()
        if event_type == "launch":
            self.anim_hue = 0.0
            self.animate_rainbow()
        elif event_type == "stop":
            self.anim_flash_count = 6
            self.animate_flash("#D50000")
        elif event_type == "idle":
            self.anim_time = 0.0
            self.animate_breathe()
        elif event_type == "pause":
            for led in self.leds.values(): led.set_color("#AA8800")
            self.animation_running = False

    def animate_rainbow(self):
        if not self.animation_running: return
        rgb = colorsys.hsv_to_rgb(self.anim_hue, 1.0, 1.0)
        hex_c = "#%02x%02x%02x" % (int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))
        for bid, led in self.leds.items():
            led.set_color(hex_c)
            self._send_hw_color(bid, hex_c)
        self._send_hw_show()
        self.anim_hue = (self.anim_hue + 0.02) % 1.0
        self.root.after(20, self.animate_rainbow)

    def animate_flash(self, color):
        if not self.animation_running or self.anim_flash_count <= 0:
            if self.anim_flash_count <= 0: self.reset_to_static()
            return
        is_on = self.anim_flash_count % 2 == 0
        c = color if is_on else None
        for bid, led in self.leds.items():
            led.set_color(c)
            self._send_hw_color(bid, c)
        self._send_hw_show()
        self.anim_flash_count -= 1
        self.root.after(150, lambda: self.animate_flash(color))

    def animate_breathe(self):
        if not self.animation_running: return
        import math
        brightness = (math.sin(self.anim_time) + 1) / 2
        r, g, b = 0, int(229 * brightness), int(255 * brightness)
        hex_c = "#%02x%02x%02x" % (r, g, b)
        for bid, led in self.leds.items():
            led.set_color(hex_c)
            self._send_hw_color(bid, hex_c)
        self._send_hw_show()
        self.anim_time += 0.1
        self.root.after(50, self.animate_breathe)

    # --- External helpers for ALU tab buttons ---
    def start_rainbow(self):
        self.trigger_event("launch")
    def start_strobe(self):
        self.trigger_event("stop")
    def stop_animation(self):
        self.animation_running = False
        self.reset_to_static()

if __name__ == "__main__":
    root = tk.Tk()
    app = EmulatorApp(root)
    root.mainloop()
