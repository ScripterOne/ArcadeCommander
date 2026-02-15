import tkinter as tk
import tkinter.font as tkfont
from tkinter import colorchooser, messagebox, filedialog, ttk, simpledialog
import json
import time
import math
import random
import os
import sys
import platform
import colorsys
import threading
import subprocess
import shutil
import tempfile
import re
import traceback
import wave
import copy
from app_paths import (
    animation_library_file,
    controller_config_file,
    fx_library_file,
    game_db_file,
    keymap_dir,
    last_profile_file,
    migrate_legacy_runtime_files,
    profile_file,
    settings_file,
)

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
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("DEBUG: OpenCV not found. Video playback disabled.")
try:
    from AMHelp import ArcadeCommanderHelp
    HELP_AVAILABLE = True
except ImportError:
    HELP_AVAILABLE = False
    print("DEBUG: AMHelp.py not found. Help disabled.")
try:
    from ACGameManager import StableStealthManager
    GM_AVAILABLE = True
except ImportError:
    GM_AVAILABLE = False
    print("DEBUG: ACGameManager.py not found. Game Manager disabled.")
try:
    from AudioFXEngine import AudioFXEngine
    AUDIOFX_AVAILABLE = True
except ImportError:
    AUDIOFX_AVAILABLE = False
    print("DEBUG: AudioFXEngine.py not found. Audio FX disabled.")
try:
    from FXLibrary import FXLibrary, FXEffect
    FXLIB_AVAILABLE = True
except ImportError:
    FXLIB_AVAILABLE = False
    print("DEBUG: FXLibrary.py not found. FX Library disabled.")
try:
    from AnimationRegistry import resolve_animation, list_supported, list_aliases
    ANIM_REGISTRY_AVAILABLE = True
except ImportError:
    ANIM_REGISTRY_AVAILABLE = False
    def resolve_animation(name): return name
    def list_supported(scope=None): return []
    def list_aliases(key): return []
try:
    from Effects import EffectContext, EffectEngine, InputState, Mixer, build_button_layout, get_preset_map
    EFFECTS_ENGINE_AVAILABLE = True
except ImportError:
    EFFECTS_ENGINE_AVAILABLE = False

# --- ALU EMULATOR ---
try:
    from ACConsoleEmulator import EmulatorApp
    from LayoutDesigner import LayoutDesigner
    ALU_AVAILABLE = True
except ImportError:
    ALU_AVAILABLE = False
    print("DEBUG: ACConsoleEmulator.py not found. ALU tab disabled.")

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
APP_NAME = "Arcade Commander"
APP_SUBTITLE = "Arcade Lighting & Control Platform"
APP_SEMVER = "2.0.0-alpha.1"
APP_CHANNEL = "ALPHA (Pre-Release)"
APP_BUILD_DATE = "2026-02-13"
APP_COPYRIGHT = "\u00a9 2026 Mark Abraham"

MIT_LICENSE_FALLBACK = """MIT License

Copyright (c) 2026 Mark Abraham

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

THIRD_PARTY_NOTICES_FALLBACK = """Third-Party Notices

ACLighter
- Purpose: Required lighting engine for Arcade Commander
- License: TBD
- Copyright: Mark Abraham
- Source: Internal component
- Notes: Required for LED and lighting features.

If this file is missing from a packaged build, include THIRD_PARTY_NOTICES.txt
next to the Arcade Commander executable.
"""


def _extract_python_file_version(py_path):
    try:
        with open(py_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        m = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", text)
        return m.group(1).strip() if m else None
    except Exception:
        return None


def _detect_exe_version(exe_path):
    if not exe_path or not os.path.isfile(exe_path):
        return None
    commands = (
        [exe_path, "--version"],
        [exe_path, "-v"],
        [exe_path, "version"],
    )
    for cmd in commands:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1.0)
            out = (proc.stdout or proc.stderr or "").strip()
            if not out:
                continue
            # First semver-like token wins.
            m = re.search(r"\b\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.\-]+)?\b", out)
            if m:
                return m.group(0)
            line = out.splitlines()[0].strip()
            if line:
                return line[:80]
        except Exception:
            continue
    return None


def DetectACLighter(settings=None):
    """
    DetectACLighter() => {detected: bool, version: str|None, path: str|None, note: str|None}
    """
    result = {"detected": False, "version": None, "path": None, "note": None}
    artifacts = ("ACLighter.exe", "aclighter.exe", "ACLighter.dll", "aclighter.py")

    settings = settings if isinstance(settings, dict) else {}
    configured = []
    for key in ("aclighter_path", "aclighter_exe", "aclighter_dir"):
        val = settings.get(key)
        if isinstance(val, str) and val.strip():
            configured.append(val.strip())

    # Same folder as executable/script is checked before standard fallback paths.
    runtime_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    default_dirs = [
        runtime_dir,
        os.path.join(runtime_dir, "tools", "ACLighter"),
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "ACLighter"),
        os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "ACLighter"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "ACLighter"),
    ]

    checked = []

    def _expand_candidate(path):
        p = os.path.normpath(path)
        out = []
        if os.path.isfile(p):
            out.append(p)
            out.append(os.path.dirname(p))
        else:
            out.append(p)
        return out

    candidates = []
    for p in configured + default_dirs:
        if not p:
            continue
        for expanded in _expand_candidate(p):
            if expanded and expanded not in candidates:
                candidates.append(expanded)

    found_artifact = None
    found_via = None
    for cand in candidates:
        if not cand:
            continue
        checked.append(cand)
        if os.path.isfile(cand):
            base = os.path.basename(cand).lower()
            if base in tuple(a.lower() for a in artifacts):
                found_artifact = cand
                found_via = cand
                break
            continue
        if not os.path.isdir(cand):
            continue
        for art in artifacts:
            fp = os.path.join(cand, art)
            if os.path.isfile(fp):
                found_artifact = fp
                found_via = cand
                break
        if found_artifact:
            break

    if not found_artifact:
        result["note"] = "No ACLighter artifacts found in expected locations."
        return result

    version = None
    lower = found_artifact.lower()
    if lower.endswith(".exe"):
        version = _detect_exe_version(found_artifact)
    elif lower.endswith(".py"):
        version = _extract_python_file_version(found_artifact)
    elif lower.endswith(".dll"):
        # DLL version may not be exposed without metadata APIs; keep fast and safe.
        version = None

    result["detected"] = True
    result["version"] = version
    result["path"] = found_artifact
    result["note"] = f"Detected via {found_via}"
    return result

# --- HARDCODED INPUT MAP ---
INPUT_MAP = {
    "0_1": "P1_A",      "0_7": "P1_B",      "0_2": "P1_C",
    "0_0": "P1_X",      "0_3": "P1_Y",      "0_5": "P1_Z",
    "0_9": "P1_START",  "0_12": "MENU",     "0_6": "REWIND",
    "1_1": "P2_A",      "1_7": "P2_B",      "1_2": "P2_C",
    "1_0": "P2_X",      "1_3": "P2_Y",      "1_5": "P2_Z",
    "1_9": "P2_START"
}

# --- ALU CONSOLE MAP (ControlDeck) ---
# Format: (Center_X, Center_Y, Radius) based on a 1000x500 reference
ALU_MAP_BASE_SIZE = (1000, 500)
ALU_MAP = {
    "P1_A": (273, 275, 22), "P1_B": (323, 275, 22), "P1_C": (373, 275, 22),
    "P1_X": (273, 335, 22), "P1_Y": (323, 335, 22), "P1_Z": (373, 335, 22),
    "P2_A": (627, 275, 22), "P2_B": (677, 275, 22), "P2_C": (727, 275, 22),
    "P2_X": (627, 335, 22), "P2_Y": (677, 335, 22), "P2_Z": (727, 335, 22),
    "P1_START": (420, 85, 18), "P2_START": (580, 85, 18), "MENU": (340, 85, 18),
    "TRACKBALL": (500, 360, 48), "REWIND": (500, 85, 18)
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
    "FX": "#BC13FE",
    "TEXT": "#FFFFFF",
    "TEXT_DIM": "#888888",
    "SUCCESS": "#00C853",
    "DANGER": "#D50000",
    "NB_PURPLE": "#6A1B9A",
    "NB_RED": "#B00020",
    "TAB_BLUE": "#2196F3",
    "TAB_GREEN": "#00C853",
    "DB": "#FF9800",
    "CHARCOAL": "#1A1A1A",
    "SCROLLBAR_LIGHT": "#3A3A3A",
}

if ANIM_REGISTRY_AVAILABLE:
    SUPPORTED_ANIMATIONS = list_supported("commander_preview")
else:
    SUPPORTED_ANIMATIONS = [
        "RAINBOW",
        "PULSE_RED",
        "PULSE_GREEN",
        "PULSE_BLUE",
        "HYPER_STROBE",
        "TEASE",
        "TEASE_INDEPENDENT",
    ]

def _hex_to_rgb(hex_color):
    try:
        h = hex_color.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except:
        return 0, 0, 0

def _rgb_to_hex(rgb):
    r, g, b = rgb
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

def _blend_hex(c1, c2, t):
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return _rgb_to_hex((r, g, b))

def _draw_round_rect(canvas, x0, y0, x1, y1, r, **kwargs):
    r = max(0, int(r))
    if r == 0:
        return canvas.create_rectangle(x0, y0, x1, y1, **kwargs)
    points = [
        x0 + r, y0,
        x1 - r, y0,
        x1, y0,
        x1, y0 + r,
        x1, y1 - r,
        x1, y1,
        x1 - r, y1,
        x0 + r, y1,
        x0, y1,
        x0, y1 - r,
        x0, y0 + r,
        x0, y0,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=16, **kwargs)

class ModernButton(tk.Frame):
    def __init__(self, master, hover_color=None, **kwargs):
        self.text = kwargs.pop("text", "")
        self.command = kwargs.pop("command", None)
        self.default_bg = kwargs.pop("bg", COLORS["SURFACE_LIGHT"])
        self.fg = kwargs.pop("fg", COLORS["TEXT"])
        self.font = kwargs.pop("font", ("Segoe UI", 8, "bold"))
        self.width_chars = kwargs.pop("width", None)
        self.height_chars = kwargs.pop("height", None)
        self.state = kwargs.pop("state", "normal")
        self.hover_bg = hover_color if hover_color else self.adjust_brightness(self.default_bg, 1.15)
        self._pressed = False
        self._hovered = False
        self._sizing = False
        super().__init__(master, bg=kwargs.pop("bg", self.default_bg), highlightthickness=0, bd=0)
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=self.master["bg"])
        self.canvas.pack(fill="both", expand=True)
        self.pack_propagate(False)
        self._recompute_size()
        self._draw()
        self.canvas.bind("<Enter>", self.on_enter)
        self.canvas.bind("<Leave>", self.on_leave)
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.configure(cursor="hand2" if self.state != "disabled" else "arrow")
    def _recompute_size(self):
        f = tkfont.Font(font=self.font)
        text_w = f.measure(self.text) if self.text else f.measure(" ")
        text_h = f.metrics("linespace")
        pad_x = 16
        pad_y = 8
        if self.width_chars:
            text_w = f.measure("0" * int(self.width_chars))
        if self.height_chars:
            text_h = text_h * int(self.height_chars)
        self._w_px = max(10, text_w + pad_x)
        self._h_px = max(10, text_h + pad_y)
        self._sizing = True
        tk.Frame.configure(self, width=self._w_px, height=self._h_px)
        self._sizing = False
        self.canvas.configure(width=self._w_px, height=self._h_px)
    def _current_bg(self):
        if self.state == "disabled":
            return _blend_hex(self.default_bg, COLORS["SURFACE_LIGHT"], 0.6)
        if self._pressed:
            return self.adjust_brightness(self.default_bg, 0.95)
        if self._hovered:
            return self.hover_bg
        return self.default_bg
    def _draw(self):
        self.canvas.delete("all")
        w = int(self._w_px)
        h = int(self._h_px)
        radius = 7
        shadow = _blend_hex(self.default_bg, "#000000", 0.35)
        face = self._current_bg()
        # Shadow
        _draw_round_rect(self.canvas, 2, 3, w - 1, h - 1, radius, fill=shadow, outline="")
        # Face
        _draw_round_rect(self.canvas, 1, 1, w - 2, h - 3, radius, fill=face, outline="")
        # Inner top highlight
        highlight = _blend_hex(face, "#ffffff", 0.25)
        self.canvas.create_line(2 + radius, 2, w - 3 - radius, 2, fill=highlight)
        # Text
        text_color = self.fg if self.state != "disabled" else _blend_hex(self.fg, face, 0.6)
        self.canvas.create_text(w // 2, (h - 2) // 2, text=self.text, fill=text_color, font=self.font)
    def on_enter(self, _):
        if self.state != "disabled":
            self._hovered = True
            self._draw()
    def on_leave(self, _):
        if self.state != "disabled":
            self._hovered = False
            self._pressed = False
            self._draw()
    def on_press(self, _):
        if self.state != "disabled":
            self._pressed = True
            self._draw()
    def on_release(self, _):
        if self.state != "disabled":
            was_pressed = self._pressed
            self._pressed = False
            self._draw()
            if was_pressed and self.command:
                self.command()
    def adjust_brightness(self, hex_color, factor):
        try:
            r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
            r = min(int(r * factor), 255)
            g = min(int(g * factor), 255)
            b = min(int(b * factor), 255)
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return hex_color
    def set_base_bg(self, hex_color):
        self.default_bg = hex_color
        self.hover_bg = self.adjust_brightness(hex_color, 1.15)
        self._draw()
    def configure(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)
        if "text" in kwargs:
            self.text = kwargs.pop("text")
        if "command" in kwargs:
            self.command = kwargs.pop("command")
        if "bg" in kwargs:
            self.default_bg = kwargs.pop("bg")
        if "fg" in kwargs:
            self.fg = kwargs.pop("fg")
        if "font" in kwargs:
            self.font = kwargs.pop("font")
        if "width" in kwargs:
            self.width_chars = kwargs.pop("width")
        if "height" in kwargs:
            self.height_chars = kwargs.pop("height")
        if "state" in kwargs:
            self.state = kwargs.pop("state")
        super().configure(**kwargs)
        self.canvas.configure(cursor="hand2" if self.state != "disabled" else "arrow")
        if not self._sizing:
            self._recompute_size()
        self._draw()
    config = configure

class MultiColorButton(tk.Frame):
    def __init__(self, master, text="", width=6, height=2, bg=COLORS["SURFACE_LIGHT"]):
        super().__init__(master, bg=COLORS["SURFACE_LIGHT"], highlightthickness=0)
        self.text = text
        self.colors = [bg, bg, bg, bg]
        self.selected = False
        self._btn_w = max(40, int(width * 16))
        self._btn_h = max(28, int(height * 18))
        self.configure(width=self._btn_w, height=self._btn_h)
        self.pack_propagate(False)
        self.canvas = tk.Canvas(self, width=self._btn_w, height=self._btn_h, highlightthickness=0, bg=COLORS["SURFACE_LIGHT"])
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self._draw())
        self._draw()

    def _draw(self):
        self.canvas.delete("all")
        w = max(self.canvas.winfo_width(), self._btn_w)
        h = max(self.canvas.winfo_height(), self._btn_h)
        inset = 3
        gap = 1
        x0, y0 = inset, inset
        x1, y1 = w - inset, h - inset
        area_w = x1 - x0
        primary_w = int(area_w * 0.5)
        radius = 7
        shadow = _blend_hex(COLORS["SURFACE_LIGHT"], "#000000", 0.35)
        face = COLORS["SURFACE_LIGHT"]
        # Shadow + base
        _draw_round_rect(self.canvas, 2, 3, w - 2, h - 2, radius, fill=shadow, outline="")
        _draw_round_rect(self.canvas, 1, 1, w - 3, h - 4, radius, fill=face, outline="")
        if self.selected:
            _draw_round_rect(self.canvas, 1, 1, w - 3, h - 4, radius, fill="", outline=COLORS["SYS"])
        # Inner top highlight
        highlight = _blend_hex(face, "#ffffff", 0.25)
        self.canvas.create_line(2 + radius, 2, w - 4 - radius, 2, fill=highlight)
        # Primary (left half)
        self.canvas.create_rectangle(x0, y0, x0 + primary_w - gap, y1, fill=self.colors[0], outline="")
        # Secondary stripes on right half (3 stripes + one blank slice)
        right_start = x0 + primary_w + gap
        remaining = x1 - right_start
        stripe_w = max(4, int((remaining - 3 * gap) / 4))
        x = right_start
        for idx in range(1, 4):
            self.canvas.create_rectangle(x, y0, x + stripe_w, y1, fill=self.colors[idx], outline="")
            x += stripe_w + gap
        # Blank slice at end for breathing room
        if x < x1:
            self.canvas.create_rectangle(x, y0, x1, y1, fill=COLORS["SURFACE_LIGHT"], outline="")
        # Divider line
        self.canvas.create_line(x0 + primary_w, y0, x0 + primary_w, y1, fill=COLORS["SURFACE"])
        # Text with subtle shadow (left aligned for readability)
        text_x = x0 + 8
        text_y = h // 2
        self.canvas.create_text(text_x + 1, text_y + 1, text=self.text, fill="#000000",
                                font=("Segoe UI", 8, "bold"), anchor="w")
        self.canvas.create_text(text_x, text_y, text=self.text, fill="white",
                                font=("Segoe UI", 8, "bold"), anchor="w")
    def swatch_index_from_x(self, x):
        w = max(self.canvas.winfo_width(), self._btn_w)
        inset = 3
        gap = 1
        x0 = inset
        x1 = w - inset
        area_w = x1 - x0
        primary_w = int(area_w * 0.5)
        if x < x0 or x > x1:
            return None
        if x <= x0 + primary_w - gap:
            return 0
        right_start = x0 + primary_w + gap
        remaining = x1 - right_start
        stripe_w = max(4, int((remaining - 3 * gap) / 4))
        if x < right_start:
            return None
        rel = x - right_start
        idx = int(rel / max(1, stripe_w + gap))
        if 0 <= idx <= 2:
            return 1 + idx
        return None

    def set_colors(self, colors):
        self.colors = list(colors)[:4]
        while len(self.colors) < 4:
            self.colors.append(COLORS["SURFACE_LIGHT"])
        self._draw()

    def set_base_bg(self, hex_color):
        self.colors[0] = hex_color
        self._draw()

    def set_selected(self, is_selected):
        self.selected = bool(is_selected)
        self._draw()

class CompactDial(tk.Frame):
    def __init__(self, master, text, variable, from_, to, resolution=0.1, bg=COLORS["CHARCOAL"], fg="white", accent=COLORS["P1"]):
        super().__init__(master, bg=bg)
        self.variable = variable
        self.from_ = float(from_)
        self.to = float(to)
        self.resolution = float(resolution)
        self.bg = bg
        self.fg = fg
        self.accent = accent
        self._drag_start_y = None
        self._drag_start_val = None
        self._trace_id = None

        tk.Label(self, text=text, bg=bg, fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(anchor="center")
        self.canvas = tk.Canvas(self, width=76, height=76, bg=bg, highlightthickness=0)
        self.canvas.pack(pady=(2, 0))
        self.value_label = tk.Label(self, text="", bg=bg, fg=fg, font=("Consolas", 8, "bold"))
        self.value_label.pack(anchor="center", pady=(2, 0))

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-4>", lambda _e: self._step(1))
        self.canvas.bind("<Button-5>", lambda _e: self._step(-1))
        self.canvas.bind("<Configure>", lambda _e: self._draw())

        self._trace_id = self.variable.trace_add("write", lambda *_: self._draw())
        self._draw()

    def destroy(self):
        try:
            if self._trace_id:
                self.variable.trace_remove("write", self._trace_id)
        except Exception:
            pass
        super().destroy()

    def _quantize(self, value):
        v = max(self.from_, min(self.to, float(value)))
        if self.resolution > 0:
            steps = round((v - self.from_) / self.resolution)
            v = self.from_ + (steps * self.resolution)
        return max(self.from_, min(self.to, v))

    def _set(self, value):
        try:
            self.variable.set(self._quantize(value))
        except Exception:
            pass

    def _get(self):
        try:
            return float(self.variable.get())
        except Exception:
            return self.from_

    def _step(self, direction):
        self._set(self._get() + (self.resolution * float(direction)))

    def _on_wheel(self, event):
        delta = 1 if event.delta > 0 else -1
        self._step(delta)

    def _on_press(self, event):
        self._drag_start_y = event.y_root
        self._drag_start_val = self._get()

    def _on_drag(self, event):
        if self._drag_start_y is None or self._drag_start_val is None:
            return
        dy = self._drag_start_y - event.y_root
        span = max(1e-9, self.to - self.from_)
        sensitivity = span / 120.0
        self._set(self._drag_start_val + (dy * sensitivity))

    def _format_value(self, value):
        if self.resolution >= 1.0:
            return f"{int(round(value))}"
        if self.resolution >= 0.1:
            return f"{value:.1f}"
        return f"{value:.2f}"

    def _draw(self):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width() if c.winfo_width() > 1 else 76
        h = c.winfo_height() if c.winfo_height() > 1 else 76
        cx = w // 2
        cy = h // 2
        r = min(w, h) // 2 - 8
        value = self._quantize(self._get())
        t = 0.0 if self.to == self.from_ else (value - self.from_) / (self.to - self.from_)
        angle_start = 135
        angle_span = 270
        angle_value = angle_start + int(angle_span * t)

        c.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#2f2f2f", width=6)
        c.create_arc(cx - r, cy - r, cx + r, cy + r, start=angle_start, extent=angle_span, style="arc", outline="#3a3a3a", width=6)
        c.create_arc(cx - r, cy - r, cx + r, cy + r, start=angle_start, extent=max(1, angle_value - angle_start), style="arc", outline=self.accent, width=6)

        rad = math.radians(angle_value)
        px = cx + int((r - 6) * math.cos(rad))
        py = cy - int((r - 6) * math.sin(rad))
        c.create_line(cx, cy, px, py, fill=self.fg, width=2)
        c.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill=self.fg, outline="")

        self.value_label.config(text=self._format_value(value))

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
        migrate_legacy_runtime_files()
        self.settings_file = settings_file()
        
        self.pulse_controls = {} 
        self.app_settings = self.load_settings() or {}
        if not isinstance(self.app_settings, dict):
            self.app_settings = {}
        self.app_settings.setdefault("skip_splash", False)
        self.app_settings.setdefault("skip_startup_sound", False)
        self.app_settings.setdefault("fx_editor_video_enabled", True)
        self.app_settings.setdefault("fx_editor_video_audio_enabled", True)
        self.app_settings.setdefault("effects_enabled", True)
        self.app_settings.setdefault("effects_seed", 1337)
        self.app_settings.setdefault("effects_preset_id", "showroom_default")
        self.save_settings(
            {
                "effects_enabled": self.app_settings.get("effects_enabled", True),
                "effects_seed": self.app_settings.get("effects_seed", 1337),
                "effects_preset_id": self.app_settings.get("effects_preset_id", "showroom_default"),
            }
        )

        if PYGAME_AVAILABLE:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            pygame.init(); pygame.display.init(); pygame.joystick.init()
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
            except Exception:
                pass

        self.setup_tray_icon()
        if self.app_settings.get("skip_splash"):
            self.initialize_app()
        else:
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
                if (not self.app_settings.get("skip_startup_sound")) and os.path.exists(snd) and PYGAME_AVAILABLE:
                    try: pygame.mixer.Sound(snd).play()
                    except: pass
            except: pass
        else:
            self.splash.geometry("400x200")
            tk.Label(self.splash, text="LOADING...", bg="black", fg="white", font=("Arial", 20)).pack(expand=True)
        self.root.after(3000, self.initialize_app)

    def initialize_app(self):
        try:
            if hasattr(self, "splash") and self.splash.winfo_exists():
                self.splash.destroy()
            self.root.deiconify()
            self.root.title(f"ARCADE COMMANDER [{APP_VERSION}]")
            self.root.configure(bg=COLORS["BG"])
            self._apply_scale_theme()
            self.root.geometry("1400x1080")
            
            self.test_window = None 
            self.help_window = None
            self.about_window = None
            self.gm_window = None
            self._aclighter_detect_cache = None
            self.config_file = last_profile_file()
            self.settings_file = settings_file()
            self.controller_config_file = controller_config_file()
            self.game_db_path = game_db_file()
            self.default_profile_path = profile_file("default.json")
            settings = self.load_settings() or {}
            if isinstance(settings, dict):
                self.app_settings.update(settings)
            self.port = self.app_settings.get("port", None)
            
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
                primary, secondary, colors = self._default_colors_for(name)
                self.led_state[name] = {
                    'primary': primary,
                    'secondary': secondary,
                    'colors': list(colors),
                    'fx': [None, None, None, None],
                    'fx_mode': None,
                    'pulse': False,
                    'speed': 1.0,
                    'phase': 0.0
                }
            # Ensure emulator-visible controls exist even if hardware mapping is missing.
            for name in ALU_MAP.keys():
                if name not in self.led_state:
                    primary, secondary, colors = self._default_colors_for(name)
                    self.led_state[name] = {
                        'primary': primary,
                        'secondary': secondary,
                        'colors': list(colors),
                        'fx': [None, None, None, None],
                        'fx_mode': None,
                        'pulse': False,
                        'speed': 1.0,
                        'phase': 0.0
                    }
            self.effects_layout = None
            self.effects_context = None
            self.effects_engine = None
            self.effects_preset_map = get_preset_map() if EFFECTS_ENGINE_AVAILABLE else {}
            self.effects_enabled = bool(self.app_settings.get("effects_enabled", True))
            self.effects_preset_id = str(self.app_settings.get("effects_preset_id", "showroom_default"))
            self.effects_pending_presses = set()
            self.effects_in_game = False
            self.effects_has_credits = False
            self._init_effects_runtime()
            
            self.animating = False; self.mapping_mode = False; self.diag_mode = False
            self.attract_active = False; self.last_activity_ts = time.time(); self._attract_offset = 0
            self.status_var = tk.StringVar(value="Initializing...")
            self.game_rows = []
            self.game_col_map = {}
            self.game_title_key = None
            self.game_detail_vars = {}
            self.game_db = {}
            self.player_mode_labels = {}
            self.current_controller_mode = "UNKNOWN"
            self.fx_vars = {}
            self.fx_speed = None
            self.fx_active = None
            self._fx_offset = 0
            self.fx_on_start_var = tk.StringVar(value="NONE")
            self.fx_on_end_var = tk.StringVar(value="NONE")
            self.audio_engine = AudioFXEngine() if AUDIOFX_AVAILABLE else None
            self.audio_wav_path = None
            self.audio_source_path = None
            self.audio_tmp_path = None
            self.audio_trim_preview_path = None
            self.audio_trim_preview_key = None
            self.audio_analysis = None
            self.audio_sequence = None
            self.fx_editor_window = None
            self.fx_editor_state = {}
            self.fx_assignments = {}
            self.fx_library = FXLibrary(path=fx_library_file()) if FXLIB_AVAILABLE else None
            self._ensure_quick_fx_library_entries()
            self._ensure_effects_preset_library_entries()
            self.fx_library_cache = []
            self.fx_lib_selected_id = None
            self.animation_library_path = animation_library_file()
            self.animation_library = self._load_animation_library()
            self.keymap_dir = keymap_dir()
            self.keymap_library = self._load_keymap_library()
            self.fx_video_playing = False
            self.fx_video_played = False
            self.fx_video_cap = None
            self.fx_video_label = None
            self._fx_video_img = None
            self.fx_video_audio_path = None
            self.fx_video_audio_sound = None
            self.fx_video_audio_channel = None
            self.fx_video_audio_stop_id = None
            self.gm_rows = []
            self.gm_title_key = None
            self.gm_selected_rom = None
            self.gm_fields = {}
            self.controller_config = self.load_controller_config()
            self.fx_selected_rom = None
            self.override_enabled_var = tk.BooleanVar(value=True)
            self.color_clipboard = None
            self._palette_popup = None
            self.tab_help_map = {
                "ARCADE COMMANDER": {
                    "short": "Build and apply game button color maps to deck/hardware.",
                    "full": (
                        "Purpose:\n"
                        "Build button profiles and assign/preview game-specific button colors on the control deck.\n\n"
                        "You can:\n"
                        "- Select games and load their mapped controls.\n"
                        "- Edit live button colors/effects for deck groups.\n"
                        "- Apply to hardware/emulator and run quick control tests."
                    ),
                },
                "EMULATOR": {
                    "short": "Preview game maps/effects on the virtual control deck.",
                    "full": (
                        "Purpose:\n"
                        "Preview what a game profile, effect, or animation looks like on the virtual control deck.\n\n"
                        "You can:\n"
                        "- Load a game and view DB-driven button map colors.\n"
                        "- Apply shared effects/animations to preview behavior.\n"
                        "- Validate visual results before sending to hardware."
                    ),
                },
                "GAME MANAGER": {
                    "short": "Edit game DB metadata, profile policy, and event assignments.",
                    "full": (
                        "Purpose:\n"
                        "Manage each game's database record, profile settings, and event mapping.\n\n"
                        "You can:\n"
                        "- Edit catalog metadata and ROM-key-linked profile fields.\n"
                        "- Assign event-to-animation and button-map behavior.\n"
                        "- Preview assignment impact and save overrides to the shared DB."
                    ),
                },
                "FX EDITOR": {
                    "short": "Create/tune FX and animations in a sandbox preview.",
                    "full": (
                        "Purpose:\n"
                        "Design and test effects/animations, then save to the shared FX library and game profile events.\n\n"
                        "You can:\n"
                        "- Build/tune modulation, audio-driven behavior, and animations.\n"
                        "- Save/load FX library entries and assign FX start/end for a game.\n"
                        "- Preview in-editor and publish shared FX choices.\n\n"
                        "Note:\n"
                        "FX Editor does not overwrite a game's default button color map (controls) unless you explicitly update controls elsewhere."
                    ),
                },
                "CONTROLLER CONFIG": {
                    "short": "Set global controller capabilities and app behavior.",
                    "full": (
                        "Purpose:\n"
                        "Configure hardware capabilities and global app settings used across all tabs.\n\n"
                        "You can:\n"
                        "- Set controller type/layout/player configuration.\n"
                        "- Configure app defaults (startup behavior/effects engine settings).\n"
                        "- Review summary stats and planned enhancement items."
                    ),
                },
            }
            self._tab_help_tip = None
            self._tab_help_tip_label = None
            self._tab_help_tip_tab = ""
            self._tab_help_hover_poll_id = None
            self.fx_presets = {
                  "Warm Pulse": {
                      "colors": ["#FFB703", "#FB8500", "#E63946", "#FF006E"],
                      "rate": 1.1,
                      "intensity": 0.9,
                      "stagger": 0.05,
                      "curve": "Linear",
                  },
                  "Cool Wave": {
                      "colors": ["#00C7BE", "#007AFF", "#5856D6", "#5AC8FA"],
                      "rate": 0.8,
                      "intensity": 1.0,
                      "stagger": 0.1,
                      "curve": "Linear",
                  },
                  "Neon Rush": {
                      "colors": ["#FF2D55", "#AF52DE", "#5856D6", "#00C7BE"],
                      "rate": 1.6,
                      "intensity": 1.0,
                      "stagger": 0.15,
                      "curve": "Ease In",
                  },
                  "Arcade Classic": {
                      "colors": ["#FF3B30", "#FFCC00", "#34C759", "#007AFF"],
                      "rate": 1.0,
                      "intensity": 0.85,
                      "stagger": 0.0,
                      "curve": "Linear",
                  },
                  "Monochrome": {
                      "colors": ["#FFFFFF", "#B0B0B0", "#808080", "#4D4D4D"],
                      "rate": 0.6,
                      "intensity": 0.7,
                      "stagger": 0.0,
                      "curve": "Ease Out",
                  },
              }
            
            self.build_header()
            self.build_banner()
            
            self.main_content = tk.Frame(self.root, bg=COLORS["BG"])
            self.main_content.pack(expand=True, fill="both", padx=20, pady=10)
            self.main_content.columnconfigure(0, weight=1)
            self.main_content.rowconfigure(0, weight=1)

            self.nb_style = ttk.Style()
            self.nb_style.theme_use("default")
            self.nb_style.configure("AC.TNotebook", background=COLORS["CHARCOAL"], borderwidth=0)
            self.nb_style.configure("AC.TNotebook.Tab", padding=[12, 6], background=COLORS["SURFACE"], foreground=COLORS["TEXT"])
            self.nb_style.configure(
                "AC.Vertical.TScrollbar",
                background=COLORS["SCROLLBAR_LIGHT"],
                troughcolor=COLORS["CHARCOAL"],
                bordercolor=COLORS["SCROLLBAR_LIGHT"],
                lightcolor=COLORS["SCROLLBAR_LIGHT"],
                darkcolor=COLORS["SCROLLBAR_LIGHT"],
                arrowcolor=COLORS["TEXT_DIM"],
                relief="flat",
                borderwidth=0,
                gripcount=0,
            )
            self.nb_style.map(
                "AC.Vertical.TScrollbar",
                background=[("active", COLORS["SCROLLBAR_LIGHT"]), ("!active", COLORS["SCROLLBAR_LIGHT"])],
                arrowcolor=[("active", COLORS["TEXT"]), ("!active", COLORS["TEXT_DIM"])],
            )

            self.notebook = ttk.Notebook(self.main_content, style="AC.TNotebook")
            self.notebook.grid(row=0, column=0, sticky="nsew")

            self.tab_main = tk.Frame(self.notebook, bg=COLORS["BG"])
            self.tab_gm = tk.Frame(self.notebook, bg=COLORS["BG"])
            self.tab_alu = tk.Frame(self.notebook, bg=COLORS["BG"])
            self.tab_fx_editor = tk.Frame(self.notebook, bg=COLORS["BG"])
            self.tab_controller = tk.Frame(self.notebook, bg=COLORS["BG"])
            self.notebook.add(self.tab_main, text="ARCADE COMMANDER")
            self.notebook.add(self.tab_alu, text="EMULATOR")
            self.notebook.add(self.tab_gm, text="GAME MANAGER")
            self.notebook.add(self.tab_fx_editor, text="FX EDITOR")
            self.notebook.add(self.tab_controller, text="CONTROLLER CONFIG")
            self.notebook.bind("<<NotebookTabChanged>>", self._update_notebook_theme)
            self.notebook.bind("<Motion>", self._on_notebook_tab_hover)
            self.notebook.bind("<Enter>", self._on_notebook_tab_enter)
            self.notebook.bind("<Leave>", self._on_notebook_tab_leave)
            self.notebook.bind("<Button-3>", self._on_notebook_tab_right_click)

            self.commander_fx_row = tk.Frame(self.tab_main, bg=COLORS["CHARCOAL"])
            self.commander_fx_row.pack(fill="x", padx=8, pady=(6, 2))
            tk.Label(
                self.commander_fx_row,
                text="LOAD EFFECT",
                bg=COLORS["CHARCOAL"],
                fg=COLORS["TEXT_DIM"],
                font=("Segoe UI", 8, "bold"),
            ).pack(side="left", padx=(8, 6))
            self.commander_effect_var = tk.StringVar(value="")
            self.commander_effect_combo = ttk.Combobox(
                self.commander_fx_row,
                textvariable=self.commander_effect_var,
                values=self._get_shared_effect_options(),
                state="readonly",
                width=24,
                font=("Consolas", 9),
            )
            self.commander_effect_combo.pack(side="left", padx=(0, 6), pady=4)
            if self.commander_effect_combo["values"]:
                self.commander_effect_var.set(self.commander_effect_combo["values"][0])
            ModernButton(
                self.commander_fx_row,
                text="APPLY FX",
                bg=COLORS["SURFACE_LIGHT"],
                fg="white",
                width=9,
                font=("Segoe UI", 8, "bold"),
                command=self._commander_apply_selected_effect,
            ).pack(side="left", padx=(0, 6), pady=4)
            tk.Label(
                self.commander_fx_row,
                text="Shared effect list: Commander / Emulator / FX Editor",
                bg=COLORS["CHARCOAL"],
                fg=COLORS["SYS"],
                font=("Segoe UI", 8),
            ).pack(side="left", padx=(4, 0))

            self.main_container = tk.Frame(self.tab_main, bg=COLORS["BG"])
            self.main_container.pack(expand=True, fill="both")
            self.main_container.grid_anchor("n")
            self.main_container.rowconfigure(0, weight=1)
            for i in range(4):
                self.main_container.columnconfigure(i, weight=1)
            
            # Layout: GameDB (Left) | P1 | System | P2
            self.main_container.columnconfigure(0, weight=3) # Give GameDB more space
            self.game_db = self._load_game_db()
            self.build_game_db_panel(0)
            
            self.build_player_card(1, "PLAYER 1", COLORS["P1"], ["P1_A", "P1_B", "P1_C", "P1_X", "P1_Y", "P1_Z", "P1_START"])
            self.build_system_card(2)
            self.build_player_card(3, "PLAYER 2", COLORS["P2"], ["P2_A", "P2_B", "P2_C", "P2_X", "P2_Y", "P2_Z", "P2_START"])
            self.build_alu_console_tab()
            self.build_game_manager_tab()
            self.build_fx_editor_tab()
            self.build_controller_config_tab()


            self._update_notebook_theme()

            self._add_tab_quit_button(self.tab_gm)
            # ALU tab has its quit button in the emulator toolbar
            self._add_tab_quit_button(self.tab_fx_editor)
            self._add_tab_quit_button(self.tab_controller)
            
            self.build_utilities()
            self.build_status_strip()
            
            if not self.is_connected():
                # In V2, we prompt for port less aggressively since Service handles it
                # But we still check connectivity
                pass 
            
            if not os.path.exists(self.config_file) and not os.path.exists(self.default_profile_path):
                self.create_default_profile()
            self.autoload_last_profile()
            
            self.start_pulse_engine()
            self.check_inputs()
            self.start_idle_watchdog()
            self.update_status_loop()
            
            self.root.bind_all("<Key>", lambda e: self.note_activity())
            self.root.bind_all("<Button>", lambda e: self.note_activity())
            self._init_dev_smoke_runner()
             
        except Exception as e:
            tb = traceback.format_exc()
            messagebox.showerror("CRITICAL ERROR", f"Init failed:\n{e}\n\n{tb}")

    def _apply_scale_theme(self):
        # Global light-charcoal styling for tk.Scale and tk.Scrollbar controls.
        try:
            self.root.option_add("*Scale.background", COLORS["SURFACE_LIGHT"])
            self.root.option_add("*Scale.troughColor", COLORS["SURFACE_LIGHT"])
            self.root.option_add("*Scale.activeBackground", COLORS["SURFACE_LIGHT"])
            self.root.option_add("*Scale.highlightBackground", COLORS["SURFACE_LIGHT"])
            self.root.option_add("*Scale.highlightColor", COLORS["SURFACE_LIGHT"])
            self.root.option_add("*Scale.foreground", "white")
            self.root.option_add("*Scrollbar.background", COLORS["SCROLLBAR_LIGHT"])
            self.root.option_add("*Scrollbar.troughColor", COLORS["CHARCOAL"])
            self.root.option_add("*Scrollbar.troughcolor", COLORS["CHARCOAL"])
            self.root.option_add("*Scrollbar.activeBackground", COLORS["SCROLLBAR_LIGHT"])
            self.root.option_add("*Scrollbar.highlightBackground", COLORS["SCROLLBAR_LIGHT"])
            self.root.option_add("*Scrollbar.highlightColor", COLORS["SCROLLBAR_LIGHT"])
            self.root.option_add("*Scrollbar.borderWidth", 0)
        except Exception:
            pass
    def _style_scrollbar(self, sb):
        try:
            sb.configure(
                bg=COLORS["SCROLLBAR_LIGHT"],
                troughcolor=COLORS["CHARCOAL"],
                activebackground=COLORS["SCROLLBAR_LIGHT"],
                highlightbackground=COLORS["SCROLLBAR_LIGHT"],
                highlightcolor=COLORS["SCROLLBAR_LIGHT"],
                relief="flat",
                borderwidth=0,
                width=12,
            )
        except Exception:
            pass

    # --- Core Logic ---
    def load_settings(self):
        try:
            with open(self.settings_file, "r") as f: return json.load(f)
        except: return {}
    def save_settings(self, data):
        try:
            existing = {}
            if os.path.exists(self.settings_file):
                try:
                    with open(self.settings_file, "r") as f:
                        existing = json.load(f)
                except Exception:
                    existing = {}
            if not isinstance(existing, dict):
                existing = {}
            if isinstance(data, dict):
                existing.update(data)
            with open(self.settings_file, "w") as f:
                json.dump(existing, f, indent=2)
        except: pass
    def _load_animation_library(self):
        path = self.animation_library_path
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    def _save_animation_library(self):
        try:
            with open(self.animation_library_path, "w", encoding="utf-8") as f:
                json.dump(self.animation_library, f, indent=2)
        except Exception:
            pass
    def _load_keymap_library(self):
        os.makedirs(self.keymap_dir, exist_ok=True)
        library = {}
        for name in os.listdir(self.keymap_dir):
            if not name.lower().endswith(".json"):
                continue
            path = os.path.join(self.keymap_dir, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                key_name = data.get("name") or os.path.splitext(name)[0]
                library[key_name] = {
                    "path": path,
                    "controls": data.get("controls", {}),
                }
            except Exception:
                continue
        return library
    def _refresh_keymap_library(self):
        self.keymap_library = self._load_keymap_library()
    def load_controller_config(self):
        defaults = {
            "controller_type": "ALU 2P",
            "controller_style": "Arcade Panel",
            "players": 2,
            "max_players": 8,
            "buttons_per_player": 6,
            "sticks_per_player": 1,
            "triggers_per_player": 0,
            "dpad_per_player": 1,
            "include_start": True,
            "include_coin": False,
            "trackball": True,
            "spinner": False,
            "pinball_left_flipper": False,
            "pinball_left_nudge": False,
            "pinball_right_flipper": False,
            "pinball_right_nudge": False,
            "led_enabled": True,
            "notes": "",
        }
        try:
            with open(self.controller_config_file, "r") as f:
                data = json.load(f)
            for k, v in defaults.items():
                data.setdefault(k, v)
            return data
        except:
            return defaults
    def save_controller_config(self):
        if not hasattr(self, "controller_vars"):
            return
        data = {
            "controller_type": self.controller_vars["controller_type"].get(),
            "controller_style": self.controller_vars["controller_style"].get(),
            "players": int(self.controller_vars["players"].get()),
            "max_players": int(self.controller_vars["max_players"].get()),
            "buttons_per_player": int(self.controller_vars["buttons_per_player"].get()),
            "sticks_per_player": int(self.controller_vars["sticks_per_player"].get()),
            "triggers_per_player": int(self.controller_vars["triggers_per_player"].get()),
            "dpad_per_player": int(self.controller_vars["dpad_per_player"].get()),
            "include_start": bool(self.controller_vars["include_start"].get()),
            "include_coin": bool(self.controller_vars["include_coin"].get()),
            "trackball": bool(self.controller_vars["trackball"].get()),
            "spinner": bool(self.controller_vars["spinner"].get()),
            "pinball_left_flipper": bool(self.controller_vars["pinball_left_flipper"].get()),
            "pinball_left_nudge": bool(self.controller_vars["pinball_left_nudge"].get()),
            "pinball_right_flipper": bool(self.controller_vars["pinball_right_flipper"].get()),
            "pinball_right_nudge": bool(self.controller_vars["pinball_right_nudge"].get()),
            "led_enabled": bool(self.controller_vars["led_enabled"].get()),
            "notes": self.controller_notes.get("1.0", "end").strip() if hasattr(self, "controller_notes") else "",
        }
        try:
            with open(self.controller_config_file, "w") as f:
                json.dump(data, f, indent=2)
            self.controller_config = data
            if hasattr(self, "controller_status"):
                self.controller_status.config(text="Saved.")
        except Exception as e:
            if hasattr(self, "controller_status"):
                self.controller_status.config(text=f"Save failed: {e}")
    def _effect_button_names(self):
        try:
            if hasattr(self, "cab") and hasattr(self.cab, "LEDS") and isinstance(self.cab.LEDS, dict):
                pairs = []
                for name, idx in self.cab.LEDS.items():
                    try:
                        order = int(idx)
                    except Exception:
                        order = 9999
                    pairs.append((order, str(name)))
                pairs.sort(key=lambda x: (x[0], x[1]))
                return [name for _, name in pairs]
        except Exception:
            pass
        return sorted(self.led_state.keys()) if hasattr(self, "led_state") else []
    def _init_effects_runtime(self):
        self.effects_layout = None
        self.effects_context = None
        self.effects_engine = None
        if not EFFECTS_ENGINE_AVAILABLE:
            return
        button_names = self._effect_button_names()
        if not button_names:
            return
        try:
            self.effects_layout = build_button_layout(button_names)
            self.effects_context = EffectContext(
                button_names=button_names,
                button_index={name: i for i, name in enumerate(button_names)},
                seed=int(self.app_settings.get("effects_seed", 1337)),
                config={
                    "layout_groups": self.effects_layout.groups,
                    "layout_adjacency": self.effects_layout.adjacency,
                    "blend_base": "max",
                    "blend_overlay": "screen",
                    "blend_attract": "screen",
                },
            )
            mixer = Mixer(
                button_count=len(button_names),
                base_blend="max",
                overlay_blend="screen",
                attract_blend="screen",
            )
            self.effects_engine = EffectEngine(context=self.effects_context, mixer=mixer)
            self._apply_effects_preset(self.effects_preset_id)
        except Exception as exc:
            print(f"DEBUG: Effect runtime init failed: {exc}")
            self.effects_layout = None
            self.effects_context = None
            self.effects_engine = None
    def _apply_effects_preset(self, preset_id):
        if not (EFFECTS_ENGINE_AVAILABLE and self.effects_engine):
            return False
        preset = None
        if isinstance(self.effects_preset_map, dict):
            preset = self.effects_preset_map.get(str(preset_id))
        if preset is None and isinstance(self.effects_preset_map, dict):
            preset = self.effects_preset_map.get("showroom_default")
            preset_id = "showroom_default"
        if preset is None:
            return False
        self.effects_engine.effects = []
        for effect in preset.build_effects():
            self.effects_engine.add_effect(effect)
        self.effects_preset_id = str(preset_id)
        return True
    def _build_effect_input_state(self, now_ms):
        pressed = set(getattr(self, "effects_pending_presses", set()))
        self.effects_pending_presses = set()
        idle_ms = max(0.0, (time.time() - float(self.last_activity_ts)) * 1000.0)
        return InputState(
            pressed_buttons=pressed,
            released_buttons=set(),
            held_buttons=set(),
            now_ms=float(now_ms),
            idle_ms=idle_ms,
            in_game=bool(self.effects_in_game),
            in_menu=not bool(self.effects_in_game),
            has_credits=bool(self.effects_has_credits),
        )
    def _get_shared_effect_catalog(self):
        catalog = []
        seen_labels = set()
        if ANIM_REGISTRY_AVAILABLE:
            items = list_supported(None)
        else:
            items = list(SUPPORTED_ANIMATIONS)
        for item in items:
            label = str(item).strip().upper()
            if not label or label in seen_labels:
                continue
            seen_labels.add(label)
            catalog.append({
                "type": "animation",
                "label": label,
                "animation": label,
            })
        preset_map = self.effects_preset_map if isinstance(self.effects_preset_map, dict) else {}
        for preset_id, preset in preset_map.items():
            name = str(getattr(preset, "name", "")).strip() or str(preset_id).strip()
            label = f"FX: {name}"
            norm = label.upper()
            if norm in seen_labels:
                continue
            seen_labels.add(norm)
            catalog.append({
                "type": "effect",
                "label": label,
                "preset_id": str(preset_id),
            })
        return catalog
    def _get_shared_effect_options(self):
        return tuple(item.get("label", "") for item in self._get_shared_effect_catalog() if item.get("label"))
    def _resolve_shared_effect_entry(self, effect_name):
        name = str(effect_name or "").strip()
        if not name:
            return None
        u = name.upper()
        for item in self._get_shared_effect_catalog():
            label = str(item.get("label", "")).strip()
            if not label:
                continue
            if u == label.upper():
                return item
        resolved = resolve_animation(name) if ANIM_REGISTRY_AVAILABLE else u
        if resolved:
            for item in self._get_shared_effect_catalog():
                if item.get("type") == "animation" and str(item.get("animation", "")).upper() == str(resolved).upper():
                    return item
        return None
    def _preview_effect_on_control_deck(self, resolved_effect):
        effect = str(resolved_effect or "").strip().upper()
        if not effect:
            return
        if effect == "LAUNCH":
            self.preview_animation("RAINBOW")
        elif effect == "PAUSE":
            self.preview_animation("PULSE_BLUE")
        elif effect == "STOP":
            self.preview_animation("HYPER_STROBE")
        elif effect == "IDLE":
            self.preview_animation("PULSE_GREEN")
        else:
            self.preview_animation(effect)
    def _apply_shared_effect(self, effect_name):
        entry = self._resolve_shared_effect_entry(effect_name)
        if not entry:
            return
        etype = str(entry.get("type", "animation")).strip().lower()
        if etype == "effect":
            preset_id = str(entry.get("preset_id", "")).strip()
            if preset_id and self._apply_effects_preset(preset_id):
                self.effects_enabled = True
                self.app_settings["effects_enabled"] = True
                self.app_settings["effects_preset_id"] = preset_id
                self.save_settings({"effects_enabled": True, "effects_preset_id": preset_id})
                self.animating = False
                self.fx_active = None
                self.attract_active = False
                self._tick_effects_engine()
                self._select_alu_tab()
            return
        resolved = str(entry.get("animation", "")).strip().upper()
        if resolved in ("LAUNCH", "PAUSE", "STOP", "IDLE") and hasattr(self, "alu_emulator"):
            try:
                self.alu_emulator.trigger_event(str(resolved).lower())
            except Exception:
                pass
        self._preview_effect_on_control_deck(resolved or str(effect_name).strip())
        self._select_alu_tab()
    def _commander_apply_selected_effect(self):
        effect_name = self.commander_effect_var.get().strip() if hasattr(self, "commander_effect_var") else ""
        if not effect_name:
            return
        self._apply_shared_effect(effect_name)
    def _tick_effects_engine(self):
        if not (self.effects_enabled and self.effects_engine and self.effects_context):
            return False
        if not self.is_connected():
            return False
        try:
            now_ms = time.monotonic() * 1000.0
            input_state = self._build_effect_input_state(now_ms)
            frame = self.effects_engine.tick(
                input_state=input_state,
                now_ms=now_ms,
                attract_active=(input_state.idle_ms >= 45000.0),
            )
            frame_override = {}
            for name, idx in self.effects_context.button_index.items():
                if idx < len(frame):
                    col = frame[idx]
                    self.cab.set(name, col)
                    frame_override[name] = col
            self.cab.show()
            self._sync_alu_emulator(frame_override)
            return True
        except Exception as exc:
            print(f"DEBUG: Effect tick failed: {exc}")
            return False
    def is_connected(self):
        try:
            return bool(self.cab.is_connected())
        except Exception:
            return False
    def _get_aclighter_status(self, force=False):
        if not hasattr(self, "cab") or not hasattr(self.cab, "get_status"):
            return None
        now = time.time()
        last = float(getattr(self, "_acl_status_ts", 0.0))
        if (not force) and (now - last < 0.8):
            return getattr(self, "_acl_status_cache", None)
        status = None
        try:
            status = self.cab.get_status(timeout=0.25)
        except Exception:
            status = None
        self._acl_status_ts = now
        if isinstance(status, dict):
            self._acl_status_cache = status
            return status
        return getattr(self, "_acl_status_cache", None)
    def _ensure_hw_ready(self):
        if not self.is_connected():
            return False
        status = self._get_aclighter_status(force=True)
        if not isinstance(status, dict):
            return True
        if bool(status.get("driver_connected", False)):
            return True
        if hasattr(self.cab, "request_driver_reconnect"):
            try:
                self.cab.request_driver_reconnect(timeout=2.5)
            except Exception:
                pass
            status = self._get_aclighter_status(force=True)
            if isinstance(status, dict) and bool(status.get("driver_connected", False)):
                return True
        return False
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
                if event.type == pygame.JOYBUTTONDOWN:
                    key = INPUT_MAP.get(f"{event.joy}_{event.button}")
                    if key:
                        self.effects_pending_presses.add(key)
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
        self.header_frame = h
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
        self.banner_frame = wrap
        self.banner_visible = True
        self.banner_label = None
        path = asset_path("ArcadeCommanderBanner.png")
        if os.path.exists(path) and PIL_AVAILABLE:
            try:
                self._banner_img = ImageTk.PhotoImage(Image.open(path))
                self.banner_label = tk.Label(wrap, image=self._banner_img, bg=COLORS["BG"])
                self.banner_label.pack(anchor="w")
            except Exception as e: print(f"Banner Load Error: {e}")
        else: print(f"DEBUG: Banner missing at {path}")
    def _add_tab_quit_button(self, tab, x=-20, y=10):
        if not tab:
            return
        btn = ModernButton(
            tab,
            text="QUIT",
            bg=COLORS["DANGER"],
            fg="white",
            width=8,
            font=("Segoe UI", 8, "bold"),
            command=self.quit_now,
        )
        btn.place(relx=1.0, x=x, y=y, anchor="ne")
    def _default_colors_for(self, name):
        if name.startswith("P1_"):
            primary = (255, 136, 0)
            secondary = (255, 220, 0)
            colors = [
                (255, 136, 0),
                (255, 220, 0),
                (255, 255, 255),
                (255, 0, 180),
            ]
        elif name.startswith("P2_"):
            primary = (0, 255, 140)
            secondary = (0, 220, 255)
            colors = [
                (0, 255, 140),
                (0, 220, 255),
                (255, 255, 255),
                (0, 120, 255),
            ]
        else:
            primary = (0, 140, 255)
            secondary = (0, 255, 120)
            colors = [
                (0, 140, 255),
                (0, 255, 120),
                (255, 255, 255),
                (180, 0, 255),
            ]
        return primary, secondary, colors

    def _sync_alu_emulator(self, frame_override=None):
        if hasattr(self, "alu_emulator") and self.alu_emulator:
            try:
                if hasattr(self, "led_state") and isinstance(self.led_state, dict):
                    snap = {}
                    for name, data in self.led_state.items():
                        snap[name] = {
                            "color": data.get("primary"),
                            "pulse": bool(data.get("pulse")),
                            "speed": data.get("speed", 1.0),
                            "colors": data.get("colors", []),
                            "phase": data.get("phase", 0.0),
                            "fx_mode": data.get("fx_mode"),
                        }
                    if isinstance(frame_override, dict):
                        for name, color in frame_override.items():
                            if name not in snap:
                                snap[name] = {
                                    "color": (0, 0, 0),
                                    "pulse": False,
                                    "speed": 1.0,
                                    "colors": [(0, 0, 0)],
                                    "phase": 0.0,
                                    "fx_mode": None,
                                }
                            if isinstance(color, (list, tuple)) and len(color) >= 3:
                                try:
                                    rgb = (int(color[0]), int(color[1]), int(color[2]))
                                    snap[name]["color"] = rgb
                                    # Force live frame render in emulator when override is provided.
                                    snap[name]["pulse"] = False
                                    snap[name]["fx_mode"] = None
                                    snap[name]["speed"] = 1.0
                                    snap[name]["phase"] = 0.0
                                    snap[name]["colors"] = [rgb]
                                except Exception:
                                    pass
                    if hasattr(self.alu_emulator, "apply_snapshot"):
                        self.alu_emulator.apply_snapshot(snap)
                        return
                self.alu_emulator._sync_from_hw_state()
            except Exception:
                pass
    def _apply_group_button_colors(self, btn, group, mode):
        if not btn or not group:
            return
        first_btn_name = group[0]
        if first_btn_name not in self.led_state:
            return
        self._ensure_color_slots(first_btn_name)
        cols = [self._rgb_to_hex(*c) for c in self.led_state[first_btn_name]['colors']]
        if mode == "secondary" and len(cols) >= 2:
            cols = [cols[1], cols[0], cols[2], cols[3]]
        if hasattr(btn, "set_colors"):
            btn.set_colors(cols)
        else:
            col = self.led_state[first_btn_name].get(mode) or self.led_state[first_btn_name]['primary']
            btn.set_base_bg(self._rgb_to_hex(*col))
    def build_card_frame(self, col, title, accent):
        b = tk.Frame(self.main_container, bg="white", padx=2, pady=2)
        b.grid(row=0, column=col, sticky="nsew", padx=5, pady=10)
        c = tk.Frame(b, bg=COLORS["CHARCOAL"]); c.pack(fill="both", expand=True)
        tk.Label(c, text=title, font=("Segoe UI", 11, "bold"), bg=COLORS["CHARCOAL"], fg=accent, pady=10).pack(fill="x")
        return c
    def build_player_card(self, col, title, color, btns):
        card = self.build_card_frame(col, title, color)
        ctrl = tk.Frame(card, bg=COLORS["SURFACE_LIGHT"]); ctrl.pack(fill="x", padx=8, pady=(0, 6))
        grp_row = tk.Frame(ctrl, bg=COLORS["SURFACE_LIGHT"])
        grp_row.pack(pady=(6, 6))
        self.create_group_theme_controls(ctrl, btns, color)
        mode_lbl = tk.Label(card, text="MODE: UNKNOWN", bg=COLORS["SURFACE"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold"))
        mode_lbl.pack(pady=(6, 0))
        if "PLAYER 1" in title:
            self.player_mode_labels["P1"] = mode_lbl
        elif "PLAYER 2" in title:
            self.player_mode_labels["P2"] = mode_lbl
        tk.Frame(card, bg=COLORS["SURFACE"], height=6).pack()
        g = tk.Frame(card, bg=COLORS["SURFACE"], pady=8); g.pack(pady=(4, 0))
        r, ci = 0, 0
        for b in btns:
            if "START" in b: continue
            self.create_visual_btn(g, b, r, ci, width=5, height=2); ci += 1
            if ci > 1: ci = 0; r += 1
        self.create_visual_btn(card, [b for b in btns if "START" in b][0], 0, 0, pack=True, width=10)
    def build_system_card(self, col):
        card = self.build_card_frame(col, "SYSTEM", COLORS["SYS"])
        sys_btns = ["TRACKBALL", "MENU", "REWIND"]
        ctrl = tk.Frame(card, bg=COLORS["SURFACE_LIGHT"]); ctrl.pack(fill="x", padx=12, pady=(0, 10))
        self.create_group_theme_controls(ctrl, sys_btns, COLORS["SYS"])
        tk.Label(card, text="BALL", bg=COLORS["SURFACE"], fg=COLORS["TEXT_DIM"]).pack(pady=(15,5))
        self.create_visual_btn(card, "TRACKBALL", 0, 0, pack=True, width=14, height=3)
        self.create_pulse_toggle(card, ["TRACKBALL"], COLORS["SYS"])
        tk.Label(card, text="ADMIN", bg=COLORS["SURFACE"], fg=COLORS["TEXT_DIM"]).pack(pady=(15,5))
        ar = tk.Frame(card, bg=COLORS["SURFACE"]); ar.pack()
        self.create_visual_btn(ar, "REWIND", 0, 0, width=10, pack=True); self.create_visual_btn(ar, "MENU", 0, 1, width=10, pack=True)
        tk.Label(card, text="PROFILES", bg=COLORS["SURFACE"], fg=COLORS["TEXT_DIM"]).pack(pady=(15,5))
        pr = tk.Frame(card, bg=COLORS["SURFACE"]); pr.pack(pady=5)
        ModernButton(pr, text="SAVE MAP", bg=COLORS["SUCCESS"], fg="white", width=10, command=self.save_profile).pack(side="left", padx=5)
        ModernButton(pr, text="LOAD MAP", width=10, command=self.load_profile).pack(side="left", padx=5)
    def build_alu_console_tab(self):
        wrap = tk.Frame(self.tab_alu, bg=COLORS["BG"])
        wrap.pack(fill="both", expand=True, padx=0, pady=0)

        body = tk.Frame(wrap, bg=COLORS["BG"])
        body.pack(fill="both", expand=True, pady=0)
        body.rowconfigure(0, weight=0, minsize=550)
        body.rowconfigure(1, weight=1)
        body.rowconfigure(2, weight=0)
        body.columnconfigure(0, weight=1)

        canvas_wrap = tk.Frame(body, bg="#050d15")
        canvas_wrap.grid(row=0, column=0, sticky="nsew", pady=(0, 10), padx=0)
        canvas_wrap.grid_propagate(False)
        toggle_row = tk.Frame(canvas_wrap, bg="#050d15")
        toggle_row.pack(fill="x", padx=8, pady=6)
        self.alu_view_var = tk.StringVar(value="EMULATOR")
        tk.Label(toggle_row, text="VIEW:", bg="#050d15", fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(side="left")
        ttk.Combobox(
            toggle_row,
            textvariable=self.alu_view_var,
            values=("EMULATOR", "DESIGNER"),
            state="readonly",
            font=("Consolas", 8),
            width=10,
        ).pack(side="left", padx=6)
        ModernButton(toggle_row, text="SWITCH", bg=COLORS["SURFACE_LIGHT"], fg="white", width=7, font=("Segoe UI", 8, "bold"),
                     command=self._alu_switch_view).pack(side="left")
        self.alu_catchlight_var = tk.BooleanVar(value=True)
        def _update_catchlight_btn():
            is_on = bool(self.alu_catchlight_var.get())
            label = "CATCHLIGHT ON" if is_on else "CATCHLIGHT OFF"
            color = COLORS["SUCCESS"] if is_on else COLORS["SURFACE_LIGHT"]
            self.alu_catchlight_btn.config(text=label, bg=color)
        def _toggle_catchlight():
            self.alu_catchlight_var.set(not bool(self.alu_catchlight_var.get()))
            if ALU_AVAILABLE and hasattr(self, "alu_emulator"):
                try:
                    self.alu_emulator.toggle_catchlight()
                except Exception:
                    pass
            _update_catchlight_btn()
        self.alu_catchlight_btn = ModernButton(
            toggle_row,
            text="CATCHLIGHT ON",
            bg=COLORS["SUCCESS"],
            fg="white",
            width=13,
            font=("Segoe UI", 8, "bold"),
            command=_toggle_catchlight,
        )
        self.alu_catchlight_btn.pack(side="left", padx=8)
        _update_catchlight_btn()
        test_row = tk.Frame(toggle_row, bg="#050d15")
        test_row.pack(side="right")
        ModernButton(test_row, text="QUIT", bg=COLORS["DANGER"], fg="white", width=7,
                     font=("Segoe UI", 8, "bold"), command=self.quit_now).pack(side="left", padx=4)
        # Effects / Animations controls moved into the lower card
        self.alu_view_host = tk.Frame(canvas_wrap, bg="#050d15")
        self.alu_view_host.pack(fill="both", expand=True)
        if ALU_AVAILABLE:
            def _alu_hw_set(bid, rgb):
                if bid in self.cab.LEDS:
                    self.cab.set(bid, rgb)
            def _alu_hw_set_all(rgb):
                self.cab.set_all(rgb)
            def _alu_hw_show():
                self.cab.show()
            def _alu_hw_connected():
                return self.is_connected()
            def _alu_hw_snapshot():
                cab = getattr(self, "cab", None)
                if not cab:
                    return {}
                if getattr(self, "alu_static_preview_lock", False):
                    if hasattr(self, "led_state") and isinstance(self.led_state, dict):
                        snap = {}
                        for name, data in self.led_state.items():
                            snap[name] = data.get("primary")
                        return snap
                # When not animating, prefer Commander state so theme changes reflect immediately.
                effects_live = bool(getattr(self, "effects_enabled", False) and getattr(self, "effects_engine", None))
                if (not getattr(self, "animating", False)
                        and not getattr(self, "attract_active", False)
                        and not effects_live):
                    if hasattr(self, "led_state") and isinstance(self.led_state, dict):
                        snap = {}
                        for name, data in self.led_state.items():
                            snap[name] = data.get("primary")
                        return snap
                pixels = getattr(cab, "pixels", None)
                snap = {}
                if isinstance(pixels, dict):
                    snap = pixels.copy()
                if isinstance(pixels, (list, tuple)) and hasattr(cab, "LEDS"):
                    for name, idx in cab.LEDS.items():
                        if isinstance(idx, int) and 0 <= idx < len(pixels):
                            snap[name] = pixels[idx]
                def _is_blank(val):
                    if val is None:
                        return True
                    if isinstance(val, str):
                        v = val.strip().lower()
                        return v in ("", "#000000", "0,0,0")
                    if isinstance(val, (tuple, list)) and len(val) == 3:
                        return all(int(c) == 0 for c in val)
                    return False
                # Fallback to UI state when hardware snapshot is empty or missing keys
                if hasattr(self, "led_state") and isinstance(self.led_state, dict):
                    for name, data in self.led_state.items():
                        primary = data.get("primary")
                        if name not in snap or _is_blank(snap.get(name)):
                            snap[name] = primary
                return snap
            self.alu_emulator = EmulatorApp(
                self.alu_view_host,
                db_path=self.game_db_path,
                assets_dir="assets",
                target_w=1320,
                show_sidebar=False,
                hw_set=_alu_hw_set,
                hw_set_all=_alu_hw_set_all,
                hw_show=_alu_hw_show,
                hw_connected=_alu_hw_connected,
                hw_snapshot=_alu_hw_snapshot,
                sync_hw=False,
            )
            self.alu_catchlight_var = self.alu_emulator.catchlight_var
            _update_catchlight_btn()
            self.alu_designer = LayoutDesigner(
                self.alu_view_host,
                assets_dir="assets",
                target_w=1320,
                show_sidebar=False,
                hw_connected=_alu_hw_connected,
            )
            self.alu_designer.container.pack_forget()
        else:
            tk.Label(canvas_wrap, text="ALU Emulator unavailable", bg="#050d15", fg="white").pack(expand=True)

        loader = tk.Frame(body, bg=COLORS["BG"])
        loader.grid(row=1, column=0, sticky="nsew")
        loader.columnconfigure(0, weight=1)
        cards_row = tk.Frame(loader, bg=COLORS["BG"])
        cards_row.pack(fill="both", expand=True)
        for i in range(2):
            cards_row.columnconfigure(i, weight=1)
        # Card 1: Game library (same size as others)
        lib_card = tk.Frame(cards_row, bg=COLORS["SURFACE"], highlightthickness=1, highlightbackground=COLORS["SURFACE_LIGHT"])
        lib_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tk.Label(lib_card, text="LOAD GAME", bg=COLORS["SURFACE"], fg=COLORS["P1"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10, pady=(10, 6))
        tools = tk.Frame(lib_card, bg=COLORS["SURFACE"])
        tools.pack(fill="x", padx=10, pady=(0, 6))
        tk.Label(tools, text="VISUALIZER", bg=COLORS["SURFACE"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(side="left")
        tk.Checkbutton(
            tools,
            text="Catchlight",
            variable=self.alu_emulator.catchlight_var if ALU_AVAILABLE else tk.BooleanVar(value=True),
            bg=COLORS["SURFACE"],
            fg="#CCC",
            selectcolor="#222",
            command=(self.alu_emulator.toggle_catchlight if ALU_AVAILABLE else None),
        ).pack(side="left", padx=10)
        search_row = tk.Frame(lib_card, bg=COLORS["SURFACE"])
        search_row.pack(fill="x", padx=10, pady=(0, 6))
        self.alu_search_var = tk.StringVar(value="")
        self.alu_search_entry = tk.Entry(
            search_row,
            textvariable=self.alu_search_var,
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            font=("Consolas", 10),
            borderwidth=0,
        )
        self.alu_search_entry.pack(side="left", fill="x", expand=True)
        self.alu_search_entry.bind("<KeyRelease>", self._alu_refresh_list)
        self.alu_search_entry.bind("<Return>", self._alu_load_selected)
        ModernButton(search_row, text="LOAD", bg=COLORS["SURFACE_LIGHT"], fg="white", width=6, font=("Segoe UI", 8, "bold"),
                     command=self._alu_load_selected).pack(side="right", padx=(6, 0))
        ModernButton(search_row, text="REFRESH", bg=COLORS["SURFACE_LIGHT"], fg="white", width=7, font=("Segoe UI", 8, "bold"),
                     command=self._alu_refresh_list).pack(side="right", padx=(6, 0))
        ModernButton(search_row, text="APPLY", bg=COLORS["SURFACE_LIGHT"], fg="white", width=6, font=("Segoe UI", 8, "bold"),
                     command=self._alu_apply_selected).pack(side="right", padx=(6, 0))
        list_wrap = tk.Frame(lib_card, bg=COLORS["SURFACE"])
        list_wrap.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.alu_listbox = tk.Listbox(list_wrap, bg=COLORS["SURFACE"], fg="#888", borderwidth=0, highlightthickness=0, font=("Segoe UI", 9))
        self.alu_listbox.pack(side="left", fill="both", expand=True)
        vsb = tk.Scrollbar(list_wrap, orient="vertical", command=self.alu_listbox.yview)
        vsb.pack(side="right", fill="y")
        self.alu_listbox.configure(yscrollcommand=vsb.set)
        self.alu_listbox.bind("<<ListboxSelect>>", self._alu_on_select)
        self.alu_game_meta_var = tk.StringVar(value="Select a game to view DB profile and keymap settings.")
        tk.Label(
            lib_card,
            textvariable=self.alu_game_meta_var,
            bg=COLORS["SURFACE"],
            fg=COLORS["TEXT_DIM"],
            font=("Segoe UI", 8),
            justify="left",
            anchor="w",
            wraplength=420,
        ).pack(fill="x", padx=10, pady=(0, 8))
        self._alu_refresh_list()
        # Card 2: Effects & Animations (for emulator preview)
        fx_card = tk.Frame(cards_row, bg=COLORS["SURFACE"], highlightthickness=1, highlightbackground=COLORS["SURFACE_LIGHT"])
        fx_card.grid(row=0, column=1, sticky="nsew")
        tk.Label(fx_card, text="EFFECTS & ANIMATIONS", bg=COLORS["SURFACE"], fg=COLORS["FX"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10, pady=(10, 6))

        top_row = tk.Frame(fx_card, bg=COLORS["SURFACE"])
        top_row.pack(fill="x", padx=10, pady=(0, 6))

        # Effects list (animations registry)
        effects_col = tk.Frame(top_row, bg=COLORS["SURFACE"])
        effects_col.pack(side="left", fill="both", expand=True, padx=(0, 6))
        tk.Label(effects_col, text="EFFECTS", bg=COLORS["SURFACE"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        effects_list_wrap = tk.Frame(effects_col, bg=COLORS["SURFACE"])
        effects_list_wrap.pack(fill="both", expand=True)
        self.alu_fx_listbox = tk.Listbox(effects_list_wrap, height=6, bg=COLORS["SURFACE"], fg="#DDD",
                                         borderwidth=0, highlightthickness=0, font=("Segoe UI", 9), exportselection=False)
        self.alu_fx_listbox.pack(side="left", fill="both", expand=True)
        fx_scroll = tk.Scrollbar(effects_list_wrap, orient="vertical", command=self.alu_fx_listbox.yview)
        fx_scroll.pack(side="right", fill="y")
        self.alu_fx_listbox.configure(yscrollcommand=fx_scroll.set)
        alu_effect_items = self._get_shared_effect_options()
        for fx in alu_effect_items:
            self.alu_fx_listbox.insert(tk.END, fx)
        if alu_effect_items:
            self.alu_fx_listbox.selection_set(0)
        ModernButton(effects_col, text="APPLY FX", bg=COLORS["SURFACE_LIGHT"], fg="white", width=9,
                     font=("Segoe UI", 8, "bold"), command=self._alu_apply_effect_selection).pack(anchor="w", pady=(4, 0))

        # Animation library list
        anim_col = tk.Frame(top_row, bg=COLORS["SURFACE"])
        anim_col.pack(side="left", fill="both", expand=True, padx=(6, 0))
        tk.Label(anim_col, text="ANIMATIONS", bg=COLORS["SURFACE"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        anim_list_wrap = tk.Frame(anim_col, bg=COLORS["SURFACE"])
        anim_list_wrap.pack(fill="both", expand=True)
        self.alu_anim_lib_list = tk.Listbox(anim_list_wrap, height=6, bg=COLORS["SURFACE"], fg="#DDD",
                                            borderwidth=0, highlightthickness=0, font=("Segoe UI", 9), exportselection=False)
        self.alu_anim_lib_list.pack(side="left", fill="both", expand=True)
        anim_scroll = tk.Scrollbar(anim_list_wrap, orient="vertical", command=self.alu_anim_lib_list.yview)
        anim_scroll.pack(side="right", fill="y")
        self.alu_anim_lib_list.configure(yscrollcommand=anim_scroll.set)
        for name in sorted(getattr(self, "animation_library", {}).keys()):
            self.alu_anim_lib_list.insert(tk.END, name)
        event_row = tk.Frame(anim_col, bg=COLORS["SURFACE"])
        event_row.pack(fill="x", pady=(4, 0))
        tk.Label(event_row, text="Event", bg=COLORS["SURFACE"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(side="left")
        self.alu_anim_event_var = tk.StringVar(value="GAME_START")
        ttk.Combobox(
            event_row,
            textvariable=self.alu_anim_event_var,
            values=("FE_START","FE_QUIT","SCREENSAVER_START","SCREENSAVER_STOP","LIST_CHANGE","GAME_START","GAME_QUIT","GAME_PAUSE","AUDIO_ANIMATION","SPEAK_CONTROLS","DEFAULT"),
            state="readonly",
            width=12,
            font=("Consolas", 8),
        ).pack(side="left", padx=(6, 0))
        ModernButton(anim_col, text="APPLY ANIM", bg=COLORS["SURFACE_LIGHT"], fg="white", width=10,
                     font=("Segoe UI", 8, "bold"), command=self._alu_apply_animation_selection).pack(anchor="w", pady=(4, 0))

        self.alu_fx_status = tk.Label(fx_card, text="", bg=COLORS["SURFACE"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8))
        self.alu_fx_status.pack(anchor="w", padx=10, pady=(6, 8))
        emu_tools = tk.Frame(body, bg="black", height=64)
        emu_tools.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        emu_tools.pack_propagate(False)
        emu_tools_inner = tk.Frame(emu_tools, bg="black")
        emu_tools_inner.pack(pady=14)
        self._build_tools_buttons(emu_tools_inner, track_port=False)
        self.alu_last_rom = None
        self.alu_static_preview_lock = False
        self._alu_fx_refresh_list()

    def _alu_init_leds(self):
        self.alu_led_widgets = {}
        self.alu_canvas.delete("alu_led")

    def _alu_clear(self):
        for w in self.alu_led_widgets.values():
            self.alu_canvas.itemconfig(w["glow"], fill="")
            self.alu_canvas.itemconfig(w["btn"], fill="", outline="#444")
            self.alu_canvas.itemconfig(w["txt"], fill="white")

    def _alu_parse_color(self, val):
        if not val:
            return None
        part = val.split("|")[0] if isinstance(val, str) and "|" in val else val
        if isinstance(part, str):
            p = part.strip()
            if p.lower() in ("", "-", "none", "off", "null", "n/a"):
                return None
            if p.startswith("#") and len(p) == 7:
                return p
            if "," in p:
                try:
                    r, g, b = [int(x.strip()) for x in p.split(",")[:3]]
                    return self._rgb_to_hex(r, g, b)
                except Exception:
                    return None
            # Support named colors used in DB entries (e.g. Red, Blue, Cyan).
            try:
                r16, g16, b16 = self.root.winfo_rgb(p)
                return self._rgb_to_hex(r16 // 256, g16 // 256, b16 // 256)
            except Exception:
                return None
        return None

    def _alu_preview_from_rom(self, rom):
        if not hasattr(self, "alu_emulator"):
            return
        # Lock emulator to selected ROM static colors until user explicitly starts an effect/animation.
        self.alu_static_preview_lock = True
        # Keep shared deck state aligned with the selected ROM so emulator sync
        # does not snap back to stale/off values.
        try:
            entry = self.game_db.get(rom, {}) if hasattr(self, "game_db") else {}
            controls = entry.get("controls", {}) if isinstance(entry, dict) else {}
            if isinstance(controls, dict):
                self._load_controls_into_commander_preview(controls, apply_hardware=False)
        except Exception:
            pass
        self.alu_last_rom = rom
        self.alu_emulator.load_profile_by_rom(rom)
        # Keep Emulator tab strictly in sync with the in-memory JSON DB used by all tabs.
        try:
            entry = self.game_db.get(rom, {}) if hasattr(self, "game_db") else {}
            controls = entry.get("controls", {}) if isinstance(entry, dict) else {}
            if isinstance(controls, dict) and hasattr(self.alu_emulator, "apply_snapshot"):
                snap = {}
                for bid, val in controls.items():
                    hex_c = self._alu_parse_color(val)
                    rgb = _hex_to_rgb(hex_c) if hex_c else None
                    if rgb is not None:
                        snap[bid] = rgb
                for bid, rgb in {
                    "REWIND": (255, 0, 0),
                    "P1_START": (0, 0, 255),
                    "MENU": (255, 255, 255),
                    "P2_START": (0, 255, 0),
                }.items():
                    if bid not in snap:
                        snap[bid] = rgb
                if snap:
                    self.alu_emulator.apply_snapshot(snap)
        except Exception:
            pass

    def _alu_apply_to_control_deck(self, rom):
        entry = self.game_db.get(rom, {}) if hasattr(self, "game_db") else {}
        controls = entry.get("controls", {}) or {}
        self._load_controls_into_commander_preview(controls, apply_hardware=True)

    def _load_controls_into_commander_preview(self, controls, apply_hardware=False):
        if not hasattr(self, "led_state"):
            return
        def _is_off(rgb):
            return (not isinstance(rgb, (tuple, list)) or len(rgb) < 3 or (int(rgb[0]) == 0 and int(rgb[1]) == 0 and int(rgb[2]) == 0))
        for n, d in self.led_state.items():
            d['primary'] = (0, 0, 0)
            d['secondary'] = (0, 0, 0)
            d['colors'] = [(0, 0, 0)] * 4
            d['pulse'] = False
            d['fx_mode'] = None
            d['phase'] = 0.0
            d['speed'] = 1.0
            d['fx'] = [None, None, None, None]
        for bid, val in controls.items():
            if bid not in self.led_state:
                continue
            slot_colors = []
            if isinstance(val, str) and "|" in val:
                for part in val.split("|"):
                    hex_c = self._alu_parse_color(part)
                    rgb = _hex_to_rgb(hex_c) if hex_c else None
                    if rgb is not None:
                        slot_colors.append(rgb)
            if not slot_colors:
                hex_c = self._alu_parse_color(val)
                rgb = _hex_to_rgb(hex_c) if hex_c else (0, 0, 0)
                slot_colors = [rgb]
            while len(slot_colors) < 4:
                slot_colors.append((0, 0, 0))
            slot_colors = slot_colors[:4]
            d = self.led_state[bid]
            d['primary'] = slot_colors[0]
            d['secondary'] = slot_colors[1]
            d['colors'] = list(slot_colors)
            d['pulse'] = False
            d['fx_mode'] = None
            d['phase'] = 0.0
            d['speed'] = 1.0
            d['fx'] = [None, None, None, None]
        # Admin defaults if missing/unassigned in a game entry.
        admin_defaults = {
            "REWIND": (255, 0, 0),
            "P1_START": (0, 0, 255),
            "MENU": (255, 255, 255),
            "P2_START": (0, 255, 0),
        }
        for bid, rgb in admin_defaults.items():
            if bid not in self.led_state:
                continue
            cur = self.led_state[bid].get('primary', (0, 0, 0))
            if _is_off(cur):
                self.led_state[bid]['primary'] = rgb
                self.led_state[bid]['secondary'] = (0, 0, 0)
                self.led_state[bid]['colors'] = [rgb, (0, 0, 0), (0, 0, 0), (0, 0, 0)]
                self.led_state[bid]['pulse'] = False
                self.led_state[bid]['fx_mode'] = None
                self.led_state[bid]['phase'] = 0.0
                self.led_state[bid]['speed'] = 1.0
                self.led_state[bid]['fx'] = [None, None, None, None]
        self.refresh_gui_from_state()
        if apply_hardware:
            self.apply_settings_to_hardware()

    def _alu_apply_selected(self):
        rom = self._alu_selected_or_search_rom()
        if not rom and self.alu_last_rom:
            rom = self.alu_last_rom
        if not rom:
            return
        self.apply_game_profile(rom, event="start")

    def _alu_apply_effect_selection(self):
        self.alu_static_preview_lock = False
        if not hasattr(self, "alu_fx_listbox"):
            return
        sel = self.alu_fx_listbox.curselection()
        if not sel:
            return
        effect = self.alu_fx_listbox.get(sel[0])
        self._apply_shared_effect(effect)

    def _alu_apply_animation_selection(self):
        self.alu_static_preview_lock = False
        if not hasattr(self, "alu_anim_lib_list"):
            return
        sel = self.alu_anim_lib_list.curselection()
        if not sel:
            if hasattr(self, "alu_fx_status"):
                self.alu_fx_status.config(text="Select an animation first.")
            return
        name = self.alu_anim_lib_list.get(sel[0])
        anim = getattr(self, "animation_library", {}).get(name, {})
        if not anim:
            if hasattr(self, "alu_fx_status"):
                self.alu_fx_status.config(text="Animation not found.")
            return
        event = self.alu_anim_event_var.get() if hasattr(self, "alu_anim_event_var") else "GAME_START"
        events = anim.get("events", {})
        seq = events.get(event, [])
        if not seq:
            if hasattr(self, "alu_fx_status"):
                self.alu_fx_status.config(text=f"No {event} events for {name}.")
            return
        self._alu_start_animation_sequence(seq)

    def _alu_start_animation_sequence(self, seq):
        self.alu_static_preview_lock = False
        if not isinstance(seq, list) or not seq:
            return
        # Stop any previously scheduled sequence playback.
        if hasattr(self, "_alu_anim_seq_after_id") and self._alu_anim_seq_after_id:
            try:
                self.root.after_cancel(self._alu_anim_seq_after_id)
            except Exception:
                pass
            self._alu_anim_seq_after_id = None
        queue = []
        for step in seq:
            if not isinstance(step, dict):
                continue
            anim = step.get("anim")
            if not anim:
                continue
            try:
                dur = float(step.get("duration", 2.0))
            except Exception:
                dur = 2.0
            queue.append({"anim": anim, "duration": max(0.1, dur)})
        if not queue:
            return
        self._alu_anim_seq_queue = queue
        self._alu_anim_seq_index = 0
        self._alu_anim_sequence_tick()

    def _alu_anim_sequence_tick(self):
        queue = getattr(self, "_alu_anim_seq_queue", None)
        idx = int(getattr(self, "_alu_anim_seq_index", 0))
        if not queue or idx >= len(queue):
            self._alu_anim_seq_after_id = None
            return
        step = queue[idx]
        mode = step.get("anim")
        duration = float(step.get("duration", 2.0))
        if mode:
            self.preview_animation(mode)
        self._alu_anim_seq_index = idx + 1
        self._alu_anim_seq_after_id = self.root.after(int(max(100, duration * 1000)), self._alu_anim_sequence_tick)


    def _alu_refresh_list(self, _evt=None):
        if not hasattr(self, "alu_listbox"):
            return
        q = (self.alu_search_var.get() or "").lower()
        self.alu_listbox.delete(0, tk.END)
        self.alu_label_to_rom = {}
        title_key = self.game_title_key if hasattr(self, "game_title_key") else None
        if getattr(self, "game_rows", None) and title_key:
            labels = []
            for row in self.game_rows:
                title = str(row.get(title_key, "")).strip() if isinstance(row, dict) else ""
                if not title:
                    continue
                rom = self._row_rom_key(row, self.game_col_map, title_key)
                if not rom:
                    continue
                label = title
                if label in self.alu_label_to_rom and self.alu_label_to_rom[label] != rom:
                    label = f"{title} [{rom}]"
                if q and q not in label.lower() and q not in rom.lower():
                    continue
                self.alu_label_to_rom[label] = rom
                labels.append(label)
            for label in sorted(labels, key=lambda s: str(s).lower()):
                self.alu_listbox.insert(tk.END, label)
            return
        for rom in sorted(self.game_db.keys()):
            label = rom
            if q and q not in label.lower():
                continue
            self.alu_label_to_rom[label] = rom
            self.alu_listbox.insert(tk.END, label)

    def _alu_selected_or_search_rom(self):
        if hasattr(self, "alu_listbox") and self.alu_listbox.curselection():
            sel_label = self.alu_listbox.get(self.alu_listbox.curselection()[0])
            if isinstance(getattr(self, "alu_label_to_rom", None), dict):
                return self.alu_label_to_rom.get(sel_label, sel_label)
            return sel_label
        q = (self.alu_search_var.get() or "").strip().lower() if hasattr(self, "alu_search_var") else ""
        if not q:
            return None
        matches = []
        if isinstance(getattr(self, "alu_label_to_rom", None), dict) and self.alu_label_to_rom:
            for label, rom in self.alu_label_to_rom.items():
                if q in str(label).lower() or q in str(rom).lower():
                    matches.append((label, rom))
        else:
            for rom in sorted(self.game_db.keys()):
                if q in rom.lower():
                    matches.append((rom, rom))
        if not matches:
            return None
        if hasattr(self, "alu_listbox"):
            self.alu_listbox.selection_clear(0, tk.END)
            idx = None
            for i in range(self.alu_listbox.size()):
                if self.alu_listbox.get(i) == matches[0][0]:
                    idx = i
                    break
            if idx is not None:
                self.alu_listbox.selection_set(idx)
                self.alu_listbox.activate(idx)
                self.alu_listbox.see(idx)
        return matches[0][1]

    def _alu_on_select(self, _evt=None):
        if not self.alu_listbox.curselection():
            return
        label = self.alu_listbox.get(self.alu_listbox.curselection()[0])
        rom = self.alu_label_to_rom.get(label, label) if isinstance(getattr(self, "alu_label_to_rom", None), dict) else label
        entry = self.game_db.get(rom, {}) if hasattr(self, "game_db") else {}
        self._load_controls_into_commander_preview(entry.get("controls", {}) or {}, apply_hardware=False)
        self._alu_preview_from_rom(rom)
        self._alu_update_game_meta(rom)

    def _format_event_summary_items(self, event_map):
        if not isinstance(event_map, dict):
            return []
        items = []
        for key, val in sorted(event_map.items()):
            if not val:
                continue
            if isinstance(val, dict):
                anim = str(val.get("animation") or "NONE")
                bmap = str(val.get("button_map") or "Current Deck")
                items.append(f"{key}:{anim} ({bmap})")
            else:
                items.append(f"{key}:{val}")
        return items

    def _alu_update_game_meta(self, rom):
        if not hasattr(self, "alu_game_meta_var"):
            return
        entry = self.game_db.get(rom, {}) if hasattr(self, "game_db") else {}
        profile = entry.get("profile", {}) if isinstance(entry, dict) else {}
        controller = str(profile.get("controller_mode", "ARCADE_PANEL"))
        policy = str(profile.get("lighting_policy", "AUTO"))
        default_fx = str(profile.get("default_fx", "") or "NONE")
        event_map = profile.get("events") or entry.get("events") or {}
        events = self._format_event_summary_items(event_map)
        events_txt = ", ".join(events) if events else "NONE"
        self.alu_game_meta_var.set(
            f"ROM: {rom} | Controller: {controller} | Policy: {policy} | Default FX: {default_fx} | Events: {events_txt}"
        )
    def _alu_fx_refresh_list(self, _evt=None):
        if not hasattr(self, "alu_fx_list"):
            return
        self.alu_fx_list.delete(0, tk.END)
        if not self.fx_library:
            self.alu_fx_list.insert(tk.END, "FX Library unavailable")
            return
        q = (self.alu_fx_search.get().strip().lower() if hasattr(self, "alu_fx_search") else "")
        fx_items = list(self.fx_library._db.get("fx", {}).values())
        fx_items.sort(key=lambda f: f.get("name", "").lower())
        self.alu_fx_cache = fx_items
        for fx in fx_items:
            name = fx.get("name", "Unnamed")
            if q and q not in name.lower():
                continue
            icon = "A" if fx.get("audio_path") else "P"
            self.alu_fx_list.insert(tk.END, f"[{icon}] {name}")
    def _alu_fx_item_from_index(self, idx):
        q = (self.alu_fx_search.get().strip().lower() if hasattr(self, "alu_fx_search") else "")
        filtered = []
        for fx in getattr(self, "alu_fx_cache", []):
            name = fx.get("name", "Unnamed")
            if q and q not in name.lower():
                continue
            filtered.append(fx)
        if idx < 0 or idx >= len(filtered):
            return None
        return filtered[idx]
    def _alu_fx_select(self, _evt=None):
        if not hasattr(self, "alu_fx_list"):
            return
        sel = self.alu_fx_list.curselection()
        if not sel:
            return
        fx = self._alu_fx_item_from_index(sel[0])
        if fx:
            self.alu_fx_selected_id = fx.get("fx_id")
    def _alu_fx_apply(self, slot):
        if not self.alu_last_rom:
            if hasattr(self, "alu_fx_status"):
                self.alu_fx_status.config(text="Select a game first.")
            return
        if not self.fx_library:
            if hasattr(self, "alu_fx_status"):
                self.alu_fx_status.config(text="FX Library unavailable.")
            return
        fx = None
        if hasattr(self, "alu_fx_list"):
            sel = self.alu_fx_list.curselection()
            if sel:
                fx = self._alu_fx_item_from_index(sel[0])
        if not fx:
            if hasattr(self, "alu_fx_status"):
                self.alu_fx_status.config(text="Select an FX first.")
            return
        entry = self.game_db.get(self.alu_last_rom, {})
        profile = entry.get("profile", {})
        fx_name = fx.get("name", "")
        if slot == "start":
            profile["fx_on_start"] = fx_name
        elif slot == "end":
            profile["fx_on_end"] = fx_name
        else:
            profile["default_fx"] = fx_name
        entry["profile"] = profile
        self.game_db[self.alu_last_rom] = entry
        self._save_game_db()
        if hasattr(self, "alu_fx_status"):
            self.alu_fx_status.config(text=f"Saved {fx_name} to {slot}.")
    def _alu_load_selected(self, _evt=None):
        if not hasattr(self, "alu_listbox"):
            return
        rom = self._alu_selected_or_search_rom()
        if not rom:
            return
        entry = self.game_db.get(rom, {}) if hasattr(self, "game_db") else {}
        self._load_controls_into_commander_preview(entry.get("controls", {}) or {}, apply_hardware=False)
        self._alu_preview_from_rom(rom)
        self._alu_update_game_meta(rom)
    def _alu_switch_view(self):
        if not ALU_AVAILABLE:
            return
        view = self.alu_view_var.get()
        if view == "DESIGNER":
            if hasattr(self, "alu_emulator"):
                self.alu_emulator.container.pack_forget()
            if hasattr(self, "alu_designer"):
                self.alu_designer.container.pack(fill="both", expand=True)
        else:
            if hasattr(self, "alu_designer"):
                self.alu_designer.container.pack_forget()
            if hasattr(self, "alu_emulator"):
                self.alu_emulator.container.pack(fill="both", expand=True)
    def _alu_test_rainbow(self):
        if hasattr(self, "alu_emulator"):
            self.alu_emulator.start_rainbow()
    def _alu_test_strobe(self):
        if hasattr(self, "alu_emulator"):
            self.alu_emulator.start_strobe()
    def _alu_test_stop(self):
        if hasattr(self, "alu_emulator"):
            self.alu_emulator.stop_animation()
    def _rom_key_from_title(self, title):
        if not title:
            return ""
        t = title.lower()
        t = re.sub(r"[^a-z0-9]+", "", t)
        return t
    def _row_rom_key(self, row, col_map, title_key):
        if not isinstance(row, dict):
            return ""
        rom_col = (col_map or {}).get("rom_key")
        if rom_col:
            rom_val = str(row.get(rom_col, "")).strip().lower()
            if rom_val:
                return rom_val
        title = row.get(title_key, "") if title_key else ""
        return self._rom_key_from_title(title)
    def _load_game_db(self):
        path = getattr(self, "game_db_path", game_db_file())
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    def _save_game_db(self):
        path = getattr(self, "game_db_path", game_db_file())
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.game_db, f, indent=4)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save DB:\n{e}")
    def _set_controller_mode(self, mode):
        self.current_controller_mode = mode or "UNKNOWN"
        text = f"MODE: {self.current_controller_mode}"
        if "P1" in self.player_mode_labels:
            self.player_mode_labels["P1"].configure(text=text)
        if "P2" in self.player_mode_labels:
            self.player_mode_labels["P2"].configure(text=text)
    def _find_catalog_row_by_rom(self, rom_key):
        if not rom_key:
            return None
        title_key = self.game_title_key or self.gm_title_key
        rows = self.game_rows or self.gm_rows
        for r in rows:
            if self._row_rom_key(r, self.game_col_map, title_key) == rom_key:
                return r
        return None
    def _game_build_col_map(self, headers):
        hset = {h: h for h in headers}
        def pick(*cands):
            for c in cands:
                if c in hset:
                    return c
            return None
        return {
            "title": pick("Game Name", "Title", "Game", "Name"),
            "rom_key": pick("ROM Key", "Rom Key", "ROM"),
            "developer": pick("Developer", "Manufacturer", "Vendor", "Publisher"),
            "year": pick("Year", "Release Year", "Released"),
            "platforms": pick("Platforms", "Platform", "System", "Emulator"),
            "genres": pick("Genres", "Genre", "Category"),
            "rec_platform": pick("Recommended Platform", "Recommended", "Best Platform"),
            "rank": pick("Rank", "Ranking"),
        }
    def _load_game_catalog(self):
        headers = ["ROM Key", "Game Name", "Developer", "Year", "Genres", "Platforms", "Recommended Platform", "Rank"]
        col_map = self._game_build_col_map(headers)
        title_col = col_map.get("title") or "Game Name"
        rom_col = col_map.get("rom_key") or "ROM Key"
        rows = []

        for rom in sorted(getattr(self, "game_db", {}).keys(), key=lambda s: str(s).lower()):
            rom_l = str(rom).strip().lower()
            if not rom_l:
                continue
            entry = self.game_db.get(rom_l, {})
            if not isinstance(entry, dict):
                continue
            md = entry.get("metadata", {}) if isinstance(entry.get("metadata"), dict) else {}
            override = entry.get("catalog_override", {}) if isinstance(entry.get("catalog_override"), dict) else {}
            base = entry.get("catalog_base", {}) if isinstance(entry.get("catalog_base"), dict) else {}
            row = {h: "" for h in headers}
            row[rom_col] = rom_l
            row[title_col] = (
                str(override.get("title", "")).strip()
                or str(md.get("title", "")).strip()
                or str(base.get("title", "")).strip()
                or rom_l
            )
            dev_col = col_map.get("developer")
            year_col = col_map.get("year")
            genre_col = col_map.get("genres")
            plat_col = col_map.get("platforms")
            rec_col = col_map.get("rec_platform")
            rank_col = col_map.get("rank")
            if dev_col:
                row[dev_col] = (
                    str(override.get("developer", "")).strip()
                    or str(entry.get("vendor", "")).strip()
                    or str(md.get("manufacturer", "")).strip()
                    or str(base.get("developer", "")).strip()
                )
            if year_col:
                row[year_col] = (
                    str(override.get("year", "")).strip()
                    or str(md.get("year", "")).strip()
                    or str(base.get("year", "")).strip()
                )
            if genre_col:
                row[genre_col] = (
                    str(override.get("genre", "")).strip()
                    or str(md.get("genre", "")).strip()
                    or str(base.get("genre", "")).strip()
                )
            if plat_col:
                row[plat_col] = (
                    str(override.get("platforms", "")).strip()
                    or str(base.get("platforms", "")).strip()
                )
            if rec_col:
                row[rec_col] = (
                    str(override.get("rec_platform", "")).strip()
                    or str(base.get("rec_platform", "")).strip()
                )
            if rank_col:
                row[rank_col] = (
                    str(override.get("rank", "")).strip()
                    or str(base.get("rank", "")).strip()
                )
            rows.append(row)
        return rows, col_map
    def _upsert_catalog_row(self, data):
        # Catalog data is now sourced from game_db JSON only.
        rows, col_map = self._load_game_catalog()
        self.game_rows = list(rows)
        self.gm_rows = list(rows)
        self.game_col_map = col_map
        self.game_title_key = col_map.get("title")
        self.gm_title_key = col_map.get("title")
    def _refresh_game_list(self, _evt=None):
        if not hasattr(self, "game_list"):
            return
        q = self.game_search.get().strip().lower()
        self.game_list.delete(0, tk.END)
        title_key = self.game_title_key
        titles = []
        for row in self.game_rows:
            title = row.get(title_key, "") if title_key else ""
            if not title:
                continue
            if q and q not in title.lower():
                continue
            titles.append(title)
        for title in sorted(titles, key=lambda s: str(s).lower()):
            self.game_list.insert(tk.END, title)
        if self.game_list.size() > 0:
            self.game_list.selection_set(0)
            self._on_game_select()
    def _on_game_select(self, _evt=None):
        if not hasattr(self, "game_list"):
            return
        sel = self.game_list.curselection()
        if not sel:
            return
        title = self.game_list.get(sel[0])
        row = None
        title_key = self.game_title_key
        for r in self.game_rows:
            if r.get(title_key, "") == title:
                row = r
                break
        if not row:
            return
        def setv(k, v):
            if k in self.game_detail_vars:
                self.game_detail_vars[k].set(v if v else "â€”")
        base_title = row.get(self.game_col_map.get("title", ""), "â€”")
        rom_key = self._row_rom_key(row, self.game_col_map, title_key)
        entry = self.game_db.get(rom_key, {})
        self._load_controls_into_commander_preview(entry.get("controls", {}) or {}, apply_hardware=False)
        override_enabled = entry.get("override_enabled", True)
        catalog_override = entry.get("catalog_override", {}) or entry.get("catalog", {})
        catalog_base = entry.get("catalog_base", {})
        def pick(field, col_key, default="â€”"):
            base = catalog_base.get(field) or row.get(self.game_col_map.get(col_key, ""), default)
            if override_enabled:
                return catalog_override.get(field) or base
            return base
        setv("catalog_title", pick("title", "title", "â€”"))
        setv("catalog_developer", pick("developer", "developer", "â€”"))
        setv("catalog_year", pick("year", "year", "â€”"))
        setv("catalog_genre", pick("genre", "genres", "â€”"))
        plat = pick("platforms", "platforms", "â€”")
        rec = pick("rec_platform", "rec_platform", "")
        setv("catalog_platform", f"{plat} / {rec}".strip(" /"))
        setv("catalog_rank", pick("rank", "rank", "â€”"))
        profile = entry.get("profile", {})
        setv("profile_rom", rom_key or "â€”")
        if override_enabled:
            setv("profile_controller", profile.get("controller_mode", "â€”"))
            setv("profile_policy", profile.get("lighting_policy", "â€”"))
            setv("profile_default_fx", profile.get("default_fx", "â€”"))
            # Events summary
            event_map = profile.get("events") or entry.get("events") or {}
            if not isinstance(event_map, dict):
                event_map = {}
            if profile.get("fx_on_start"):
                event_map.setdefault("GAME_START", profile.get("fx_on_start"))
            if profile.get("fx_on_end"):
                event_map.setdefault("GAME_QUIT", profile.get("fx_on_end"))
            if profile.get("default_fx"):
                event_map.setdefault("DEFAULT", profile.get("default_fx"))
            events = self._format_event_summary_items(event_map)
            setv("profile_events", ", ".join(sorted(events)) if events else "â€”")
            self._set_controller_mode(profile.get("controller_mode", "UNKNOWN"))
        else:
            setv("profile_controller", "â€”")
            setv("profile_policy", "â€”")
            setv("profile_default_fx", "â€”")
            setv("profile_events", "â€”")
            self._set_controller_mode("UNKNOWN")
        status = "OVERRIDE" if rom_key in self.game_db else "NONE"
        if status == "OVERRIDE" and not override_enabled:
            status = "OVERRIDE (OFF)"
        setv("profile_status", status)
        self._alu_preview_from_rom(rom_key)
    def build_game_db_panel(self, col):
        border = tk.Frame(self.main_container, bg="white", padx=2, pady=2)
        border.grid(row=0, column=col, sticky="nsew", padx=5, pady=10)
        outer = tk.Frame(border, bg=COLORS["CHARCOAL"], padx=10, pady=10)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=3)
        outer.columnconfigure(1, weight=2)
        outer.rowconfigure(0, weight=1)

        library = tk.Frame(outer, bg=COLORS["CHARCOAL"])
        library.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        details = tk.Frame(outer, bg=COLORS["CHARCOAL"])
        details.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        tk.Label(library, text="GAME LIBRARY", bg=COLORS["CHARCOAL"], fg=COLORS["SUCCESS"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
        search_row = tk.Frame(library, bg=COLORS["CHARCOAL"])
        search_row.pack(fill="x", pady=(6, 6))
        self.game_search = tk.Entry(search_row, bg=COLORS["SURFACE_LIGHT"], fg="white", borderwidth=0, font=("Consolas", 9))
        self.game_search.pack(side="left", fill="x", expand=True)
        self.game_search.bind("<KeyRelease>", self._refresh_game_list)
        # Column selection isn't applicable on the main screen.

        list_wrap = tk.Frame(library, bg=COLORS["CHARCOAL"])
        list_wrap.pack(fill="both", expand=True)
        self.game_list = tk.Listbox(list_wrap, bg=COLORS["SURFACE_LIGHT"], fg="white", borderwidth=0, highlightthickness=0,
                                    selectbackground=COLORS["P1"], selectforeground="black", font=("Segoe UI", 9))
        self.game_list.pack(side="left", fill="both", expand=True)
        vsb = tk.Scrollbar(list_wrap, orient="vertical", command=self.game_list.yview)
        vsb.pack(side="right", fill="y")
        self.game_list.configure(yscrollcommand=vsb.set)
        self.game_list.bind("<<ListboxSelect>>", self._on_game_select)

        lib_btn_row = tk.Frame(library, bg=COLORS["CHARCOAL"])
        lib_btn_row.pack(fill="x", pady=(8, 0))
        ModernButton(
            lib_btn_row,
            text="NEW GAME",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=12,
            font=("Segoe UI", 8, "bold"),
            command=self.new_game_entry,
        ).pack(side="left", padx=(0, 6))
        ModernButton(
            lib_btn_row,
            text="ASSIGN MAP",
            bg=COLORS["SYS"],
            fg="black",
            width=12,
            font=("Segoe UI", 8, "bold"),
            command=self.save_game_entry,
        ).pack(side="left")
        ModernButton(
            lib_btn_row,
            text="IMPORT",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=8,
            font=("Segoe UI", 8, "bold"),
            command=self.game_import,
        ).pack(side="left", padx=(6, 0))
        ModernButton(
            lib_btn_row,
            text="EXPORT",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=8,
            font=("Segoe UI", 8, "bold"),
            command=self.game_export,
        ).pack(side="left", padx=(6, 0))
        ModernButton(
            lib_btn_row,
            text="SAVE MAP",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=9,
            font=("Segoe UI", 8, "bold"),
            command=self.save_keymap_from_commander,
        ).pack(side="left", padx=(6, 0))

        tk.Label(details, text="DETAILS", bg=COLORS["CHARCOAL"], fg=COLORS["SUCCESS"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(details, text="CATALOG", bg=COLORS["CHARCOAL"], fg=COLORS["P1"], font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(6, 2))
        self.game_detail_vars = {
            "catalog_title": tk.StringVar(value="â€”"),
            "catalog_developer": tk.StringVar(value="â€”"),
            "catalog_year": tk.StringVar(value="â€”"),
            "catalog_genre": tk.StringVar(value="â€”"),
            "catalog_platform": tk.StringVar(value="â€”"),
            "catalog_rank": tk.StringVar(value="â€”"),
            "profile_rom": tk.StringVar(value="â€”"),
            "profile_controller": tk.StringVar(value="â€”"),
            "profile_policy": tk.StringVar(value="â€”"),
            "profile_default_fx": tk.StringVar(value="â€”"),
            "profile_events": tk.StringVar(value="â€”"),
            "profile_status": tk.StringVar(value="NONE"),
        }
        for label, key in [
            ("Title", "catalog_title"),
            ("Vendor/Dev", "catalog_developer"),
            ("Year", "catalog_year"),
            ("Genre", "catalog_genre"),
            ("Platform/Rec", "catalog_platform"),
            ("Rank", "catalog_rank"),
        ]:
            row = tk.Frame(details, bg=COLORS["CHARCOAL"])
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"{label}:", width=12, anchor="w", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(side="left")
            tk.Label(row, textvariable=self.game_detail_vars[key], bg=COLORS["CHARCOAL"], fg=COLORS["TEXT"], font=("Segoe UI", 8), anchor="w", wraplength=220, justify="left").pack(side="left", fill="x", expand=True)

        tk.Frame(details, bg=COLORS["SURFACE_LIGHT"], height=1).pack(fill="x", pady=6)
        tk.Label(details, text="PROFILE", bg=COLORS["CHARCOAL"], fg=COLORS["P1"], font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 2))
        for label, key in [
            ("ROM Key", "profile_rom"),
            ("Controller", "profile_controller"),
            ("Policy", "profile_policy"),
            ("Default FX", "profile_default_fx"),
            ("Events", "profile_events"),
            ("Status", "profile_status"),
        ]:
            row = tk.Frame(details, bg=COLORS["CHARCOAL"])
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"{label}:", width=12, anchor="w", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(side="left")
            tk.Label(row, textvariable=self.game_detail_vars[key], bg=COLORS["CHARCOAL"], fg=COLORS["TEXT"], font=("Segoe UI", 8), anchor="w", wraplength=220, justify="left").pack(side="left", fill="x", expand=True)

        self.game_rows, self.game_col_map = self._load_game_catalog()
        self.game_title_key = self.game_col_map.get("title")
        self._refresh_game_list()
        if hasattr(self, "alu_listbox"):
            self._alu_refresh_list()
    def new_game_entry(self):
        if hasattr(self, "notebook") and hasattr(self, "tab_gm"):
            self.notebook.select(self.tab_gm)
        self.gm_new_game()
    def save_game_entry(self):
        if not hasattr(self, "game_list"):
            messagebox.showinfo("Save Game", "Game list is not available.")
            return
        sel = self.game_list.curselection()
        if not sel:
            messagebox.showinfo("Save Game", "Select a game to save overrides.")
            return
        title = self.game_list.get(sel[0])
        row = None
        title_key = self.game_title_key
        for r in self.game_rows:
            if r.get(title_key, "") == title:
                row = r
                break
        if not row:
            messagebox.showinfo("Save Game", "Unable to locate catalog entry for selection.")
            return
        if not hasattr(self, "gm_fields"):
            messagebox.showinfo("Save Game", "Game Manager is not available.")
            return
        rom_key = self._row_rom_key(row, self.game_col_map, title_key)
        decision = messagebox.askyesnocancel(
            "Save Override",
            "Enable override for this game?\nYes = override on, No = override off, Cancel = abort.",
        )
        if decision is None:
            return
        entry = self.game_db.get(rom_key, {})
        entry["controls"] = self._collect_controls_from_led_state(include_slots=True)
        profile = entry.get("profile", {})
        catalog_override = entry.get("catalog_override", {}) or entry.get("catalog", {})
        catalog_base = entry.get("catalog_base", {})
        override_enabled = bool(decision)
        self.override_enabled_var.set(override_enabled)
        def base_from_csv(col_key, default=""):
            return row.get(self.game_col_map.get(col_key, ""), default)
        def pick(field, col_key, default=""):
            base = catalog_base.get(field) or base_from_csv(col_key, default)
            if override_enabled:
                return catalog_override.get(field) or base
            return base
        self.gm_fields["title"].set(pick("title", "title", ""))
        self.gm_fields["developer"].set(pick("developer", "developer", ""))
        self.gm_fields["year"].set(pick("year", "year", ""))
        self.gm_fields["genre"].set(pick("genre", "genres", ""))
        self.gm_fields["platform"].set(pick("platforms", "platforms", ""))
        self.gm_fields["rec_platform"].set(pick("rec_platform", "rec_platform", ""))
        self.gm_fields["rank"].set(pick("rank", "rank", ""))
        self.gm_fields["rom_key"].set(rom_key)
        self.gm_fields["vendor"].set(entry.get("vendor", ""))
        self.gm_fields["controller_mode"].set(profile.get("controller_mode", "ARCADE_PANEL"))
        self.gm_fields["lighting_policy"].set(profile.get("lighting_policy", "AUTO"))
        self.gm_fields["default_fx"].set(profile.get("default_fx", "") or "NONE")
        self.gm_fields["fx_on_start"].set(profile.get("fx_on_start", "") or "NONE")
        self.gm_fields["fx_on_end"].set(profile.get("fx_on_end", "") or "NONE")
        # Event summary + details (read-only)
        event_map = profile.get("events") or entry.get("events") or {}
        if not isinstance(event_map, dict):
            event_map = {}
        # Backfill from legacy fields
        if self.gm_fields["fx_on_start"].get() not in ("", "NONE"):
            event_map.setdefault("GAME_START", self.gm_fields["fx_on_start"].get())
        if self.gm_fields["fx_on_end"].get() not in ("", "NONE"):
            event_map.setdefault("GAME_QUIT", self.gm_fields["fx_on_end"].get())
        if self.gm_fields["default_fx"].get() not in ("", "NONE"):
            event_map.setdefault("DEFAULT", self.gm_fields["default_fx"].get())
        events = self._format_event_summary_items(event_map)
        if hasattr(self, "gm_fields") and "event_summary" in self.gm_fields:
            self.gm_fields["event_summary"].set("Configured: " + (", ".join(events) if events else "NONE"))
        self.game_db[rom_key] = entry
        self.gm_selected_rom = rom_key
        self.gm_save_changes()
    def build_utilities(self):
        parent = self.tab_main if hasattr(self, "tab_main") else self.root
        bar = tk.Frame(parent, bg="black", height=70); bar.pack(side="bottom", fill="x")
        inner = tk.Frame(bar, bg="black"); inner.pack(pady=18)
        self._build_tools_buttons(inner, track_port=True)
    def _build_tools_buttons(self, inner, track_port=False):
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
        port_btn = btn("PORT", COLORS["SURFACE_LIGHT"], lambda: self.prompt_for_port(), w=8)
        if track_port or not hasattr(self, "port_btn"):
            self.port_btn = port_btn
        btn("ABOUT", COLORS["SURFACE_LIGHT"], self.show_about, w=8)
        btn("HELP", COLORS["SURFACE_LIGHT"], self.show_help, w=8)
        btn("QUIT", COLORS["DANGER"], self.quit_now, w=8)
    def build_status_strip(self):
        parent = self.tab_main if hasattr(self, "tab_main") else self.root
        s = tk.Frame(parent, bg=COLORS["BG"]); s.pack(side="bottom", fill="x", padx=30, pady=5)
        self.status_lbl = tk.Label(s, textvariable=self.status_var, bg=COLORS["BG"], fg=COLORS["TEXT_DIM"])
        self.status_lbl.pack(side="right")
    def update_status_loop(self):
        connected = self.is_connected()
        ac_status = self._get_aclighter_status(force=False) if connected else None
        hw_connected = bool(ac_status.get("driver_connected", connected)) if isinstance(ac_status, dict) else connected
        c_txt = "CONNECTED" if connected else "DISCONNECTED"
        if connected and not hw_connected:
            c_txt = "CONNECTED (HW OFFLINE)"
        m_txt = "TESTING" if (self.test_window and self.test_window.winfo_exists()) else ("ANIM" if self.animating else ("DIAG" if self.diag_mode else ("ATTRACT" if self.attract_active else "IDLE")))
        if connected and hw_connected:
            self.status_lbl.config(fg=COLORS["SUCCESS"]); self.port_btn.set_base_bg(COLORS["SUCCESS"])
        elif connected and not hw_connected:
            self.status_lbl.config(fg=COLORS["DB"]); self.port_btn.set_base_bg(COLORS["DB"])
        else:
            self.status_lbl.config(fg=COLORS["TEXT_DIM"]); self.port_btn.set_base_bg(COLORS["DANGER"])
        port_txt = getattr(self.cab, "port", self.port)
        if isinstance(ac_status, dict):
            port_txt = ac_status.get("port", port_txt)
        self.status_var.set(f"{c_txt} on {port_txt} | Mode: {m_txt}")
        self.root.after(500, self.update_status_loop)
    def _init_dev_smoke_runner(self):
        self.dev_smoke_running = False
        self.dev_smoke_steps = []
        self.dev_smoke_index = 0
        self.dev_smoke_results = []
        self.dev_smoke_after_id = None
        self.dev_smoke_started_ts = 0.0
        self.dev_smoke_delay_ms = 900
        self.dev_smoke_ctx = {}
        self.dev_smoke_overlay = tk.Label(
            self.root,
            text="",
            bg=COLORS["SURFACE"],
            fg=COLORS["SYS"],
            font=("Consolas", 8, "bold"),
            padx=8,
            pady=3,
        )
        # Hidden developer shortcuts.
        self.root.bind_all("<Control-Shift-F12>", self._dev_smoke_toggle)
        self.root.bind_all("<Control-Shift-Escape>", self._dev_smoke_stop)
    def _dev_smoke_overlay_show(self, text, color=None):
        if not hasattr(self, "dev_smoke_overlay"):
            return
        self.dev_smoke_overlay.config(text=text, fg=(color or COLORS["SYS"]))
        self.dev_smoke_overlay.place(relx=0.01, rely=0.99, anchor="sw")
    def _dev_smoke_overlay_hide(self):
        if hasattr(self, "dev_smoke_overlay"):
            self.dev_smoke_overlay.place_forget()
    def _dev_smoke_toggle(self, _evt=None):
        if getattr(self, "dev_smoke_running", False):
            return self._dev_smoke_stop()
        self._dev_smoke_start()
        return "break"
    def _dev_smoke_start(self):
        if not hasattr(self, "notebook"):
            return
        if self.dev_smoke_after_id:
            try:
                self.root.after_cancel(self.dev_smoke_after_id)
            except Exception:
                pass
            self.dev_smoke_after_id = None
        self.dev_smoke_running = True
        self.dev_smoke_started_ts = time.time()
        self.dev_smoke_index = 0
        self.dev_smoke_results = []
        self.dev_smoke_log_lines = []
        self.dev_smoke_ctx = self._dev_smoke_init_context()
        self.dev_smoke_steps = [
            ("Commander Tab", self._dev_smoke_step_commander),
            ("FX Editor Tab", self._dev_smoke_step_fx_editor),
            ("Game Manager Tab", self._dev_smoke_step_game_manager),
            ("Emulator Tab (Load + Start)", self._dev_smoke_step_emulator),
            ("Hold START Event", self._dev_smoke_step_wait_start),
            ("Emulator Tab (Trigger End)", self._dev_smoke_step_emulator_end),
            ("Hold END Event", self._dev_smoke_step_wait_end),
            ("Cleanup SmokeTest Artifacts", self._dev_smoke_step_cleanup),
            ("Return To Commander", self._dev_smoke_step_return_home),
        ]
        self._dev_smoke_overlay_show("DEV SMOKE STARTED (Ctrl+Shift+Esc to stop)")
        self.dev_smoke_after_id = self.root.after(180, self._dev_smoke_run_next)
    def _dev_smoke_stop(self, _evt=None):
        if self.dev_smoke_after_id:
            try:
                self.root.after_cancel(self.dev_smoke_after_id)
            except Exception:
                pass
            self.dev_smoke_after_id = None
        try:
            if isinstance(getattr(self, "dev_smoke_ctx", None), dict) and self.dev_smoke_ctx:
                self._dev_smoke_step_cleanup()
        except Exception as exc:
            self._dev_smoke_log(f"Cleanup on stop failed: {exc}")
        self.dev_smoke_running = False
        self._dev_smoke_overlay_show("DEV SMOKE STOPPED", COLORS["DANGER"])
        self.root.after(2200, self._dev_smoke_overlay_hide)
        return "break"
    def _dev_smoke_finish(self):
        self.dev_smoke_running = False
        elapsed = max(0.0, time.time() - float(getattr(self, "dev_smoke_started_ts", time.time())))
        total = len(self.dev_smoke_results)
        passed = sum(1 for _, ok, _ in self.dev_smoke_results if ok)
        failed = total - passed
        color = COLORS["SUCCESS"] if failed == 0 else COLORS["DANGER"]
        self._dev_smoke_overlay_show(f"DEV SMOKE DONE: {passed}/{total} passed in {elapsed:.1f}s", color)
        for name, ok, detail in self.dev_smoke_results:
            state = "PASS" if ok else "FAIL"
            print(f"[DEV SMOKE] {state} | {name} | {detail}")
        self._dev_smoke_show_report_window()
        self.root.after(5000, self._dev_smoke_overlay_hide)
    def _dev_smoke_log(self, text):
        line = str(text)
        self.dev_smoke_log_lines.append(line)
        print(f"[DEV SMOKE] {line}")
    def _dev_smoke_show_report_window(self):
        try:
            if hasattr(self, "_dev_smoke_report_win") and self._dev_smoke_report_win and self._dev_smoke_report_win.winfo_exists():
                self._dev_smoke_report_win.destroy()
            win = tk.Toplevel(self.root)
            win.title("DEV SMOKE REPORT")
            win.geometry("760x360")
            win.configure(bg=COLORS["BG"])
            self._dev_smoke_report_win = win
            text = tk.Text(win, bg=COLORS["SURFACE"], fg="white", insertbackground="white", wrap="none")
            text.pack(fill="both", expand=True, padx=10, pady=10)
            text.insert("end", "Dev Smoke Report\n")
            text.insert("end", "=" * 70 + "\n")
            for name, ok, detail in self.dev_smoke_results:
                state = "PASS" if ok else "FAIL"
                text.insert("end", f"{state:4} | {name} | {detail}\n")
            if self.dev_smoke_log_lines:
                text.insert("end", "\nDetails\n")
                text.insert("end", "-" * 70 + "\n")
                for line in self.dev_smoke_log_lines:
                    text.insert("end", f"{line}\n")
            text.configure(state="disabled")
        except Exception:
            pass
    def _dev_smoke_run_next(self):
        self.dev_smoke_after_id = None
        if not self.dev_smoke_running:
            return
        if self.dev_smoke_index >= len(self.dev_smoke_steps):
            self._dev_smoke_finish()
            return
        name, fn = self.dev_smoke_steps[self.dev_smoke_index]
        ok = True
        detail = ""
        next_delay_ms = int(self.dev_smoke_delay_ms)
        try:
            out = fn()
            if isinstance(out, dict):
                detail = str(out.get("detail", "") or "")
                try:
                    next_delay_ms = int(out.get("delay_ms", self.dev_smoke_delay_ms))
                except Exception:
                    next_delay_ms = int(self.dev_smoke_delay_ms)
            else:
                detail = str(out) if out is not None else ""
        except Exception as exc:
            ok = False
            detail = str(exc)
        self.dev_smoke_results.append((name, ok, detail))
        state = "PASS" if ok else "FAIL"
        color = COLORS["SUCCESS"] if ok else COLORS["DANGER"]
        self._dev_smoke_overlay_show(
            f"DEV SMOKE {self.dev_smoke_index + 1}/{len(self.dev_smoke_steps)} {state}: {name}{(' | ' + detail) if detail else ''}",
            color,
        )
        self.dev_smoke_index += 1
        if self.dev_smoke_running:
            self.dev_smoke_after_id = self.root.after(max(20, int(next_delay_ms)), self._dev_smoke_run_next)
    def _dev_smoke_color_slots_for_button(self, index):
        base_h = (float(index) * 0.123) % 1.0
        slots = []
        for sidx, offset in enumerate((0.00, 0.17, 0.34, 0.51)):
            h = (base_h + offset) % 1.0
            sat = 0.95 if (sidx % 2 == 0) else 0.80
            val = 1.00 if sidx < 3 else 0.85
            r, g, b = colorsys.hsv_to_rgb(h, sat, val)
            slots.append((int(r * 255), int(g * 255), int(b * 255)))
        return slots
    def _dev_smoke_clone(self, value):
        try:
            return json.loads(json.dumps(value))
        except Exception:
            try:
                return copy.deepcopy(value)
            except Exception:
                return value
    def _dev_smoke_init_context(self):
        rom_key = "smoketest"
        keymap_name = "SmokeTest"
        keymap_path = os.path.join(self.keymap_dir, f"{keymap_name}.json")
        ctx = {
            "rom_key": rom_key,
            "title": "SmokeTest",
            "keymap_name": keymap_name,
            "keymap_path": keymap_path,
            "fx_name": "Smoke Test",
            "start_anim_name": "SmokeTest_Start",
            "end_anim_name": "SmokeTest_End",
            "created_fx_id": "",
            "created_temp_files": [],
            "backup_game_entry": self._dev_smoke_clone(self.game_db.get(rom_key)) if rom_key in self.game_db else None,
            "backup_anim_start": self._dev_smoke_clone(self.animation_library.get("SmokeTest_Start")) if "SmokeTest_Start" in self.animation_library else None,
            "backup_anim_end": self._dev_smoke_clone(self.animation_library.get("SmokeTest_End")) if "SmokeTest_End" in self.animation_library else None,
            "backup_keymap_text": None,
        }
        try:
            if os.path.exists(keymap_path):
                with open(keymap_path, "r", encoding="utf-8") as f:
                    ctx["backup_keymap_text"] = f.read()
        except Exception:
            ctx["backup_keymap_text"] = None
        return ctx
    def _dev_smoke_select_listbox_item(self, listbox, target_text):
        if not listbox:
            return False
        target = str(target_text or "").strip().lower()
        for i in range(listbox.size()):
            value = str(listbox.get(i)).strip().lower()
            if value == target:
                listbox.selection_clear(0, tk.END)
                listbox.selection_set(i)
                listbox.activate(i)
                listbox.see(i)
                return True
        return False
    def _dev_smoke_input_get(self, target):
        if target is None:
            return ""
        if hasattr(target, "get"):
            try:
                return str(target.get())
            except Exception:
                pass
        return ""
    def _dev_smoke_input_set(self, target, value):
        if target is None:
            return
        text = "" if value is None else str(value)
        # tk.StringVar path
        if hasattr(target, "set"):
            try:
                target.set(text)
                return
            except Exception:
                pass
        # tk.Entry path
        if hasattr(target, "delete") and hasattr(target, "insert"):
            try:
                target.delete(0, tk.END)
                if text:
                    target.insert(0, text)
            except Exception:
                pass
    def _dev_smoke_select_rom_in_mapped_list(self, listbox, mapping, rom_key):
        if not listbox:
            return False
        target = str(rom_key or "").strip().lower()
        for i in range(listbox.size()):
            label = str(listbox.get(i))
            resolved = mapping.get(label, label) if isinstance(mapping, dict) else label
            if str(resolved).strip().lower() == target:
                listbox.selection_clear(0, tk.END)
                listbox.selection_set(i)
                listbox.activate(i)
                listbox.see(i)
                return True
        return False
    def _dev_smoke_find_audio_asset(self):
        for name in ("SmokeTest.mp3", "SmokeTest.MP3", "smoketest.mp3", "smoketest.MP3"):
            p = asset_path(name)
            if p and os.path.exists(p):
                return p
        assets_dir = os.path.dirname(asset_path("placeholder.bin"))
        if os.path.isdir(assets_dir):
            for fn in os.listdir(assets_dir):
                if str(fn).lower() == "smoketest.mp3":
                    p = os.path.join(assets_dir, fn)
                    if os.path.exists(p):
                        return p
        return ""
    def _dev_smoke_trim_analysis(self, analysis, start_ratio=0.15, end_ratio=0.85):
        if not isinstance(analysis, dict):
            return {}
        start = max(0.0, min(1.0, float(start_ratio)))
        end = max(0.0, min(1.0, float(end_ratio)))
        if end <= start:
            end = min(1.0, start + 0.01)
        rms = analysis.get("rms", []) or []
        frame_count = len(rms)
        if frame_count <= 0:
            return dict(analysis)
        s_idx = int(start * frame_count)
        e_idx = int(end * frame_count)
        s_idx = max(0, min(frame_count - 1, s_idx))
        e_idx = max(s_idx + 1, min(frame_count, e_idx))
        def _slice(seq):
            seq = seq or []
            return seq[s_idx:e_idx]
        trimmed = dict(analysis)
        trimmed["rms"] = _slice(analysis.get("rms", []))
        trimmed["bass"] = _slice(analysis.get("bass", []))
        trimmed["mid"] = _slice(analysis.get("mid", []))
        trimmed["treble"] = _slice(analysis.get("treble", []))
        trimmed["onsets"] = [i - s_idx for i in (analysis.get("onsets", []) or []) if s_idx <= i < e_idx]
        trimmed["beats"] = [i - s_idx for i in (analysis.get("beats", []) or []) if s_idx <= i < e_idx]
        return trimmed
    def _dev_smoke_controls_for_button_map(self, rom_key, button_map):
        map_name = str(button_map or "Current Deck").strip() or "Current Deck"
        if map_name != "Current Deck":
            self._refresh_keymap_library()
            km = self.keymap_library.get(map_name, {}) if isinstance(getattr(self, "keymap_library", {}), dict) else {}
            controls = km.get("controls", {}) if isinstance(km, dict) else {}
            if isinstance(controls, dict) and controls:
                return controls
        entry = self.game_db.get(rom_key, {}) if isinstance(getattr(self, "game_db", None), dict) else {}
        controls = entry.get("controls", {}) if isinstance(entry, dict) else {}
        return controls if isinstance(controls, dict) else {}
    def _dev_smoke_ensure_hw_connected(self):
        if self.is_connected():
            return True
        try:
            if hasattr(self, "cab") and hasattr(self.cab, "reconnect"):
                try:
                    self.cab.reconnect(getattr(self, "port", None), timeout=0.35)
                except TypeError:
                    self.cab.reconnect(getattr(self, "port", None))
        except Exception:
            pass
        return self.is_connected()
    def _dev_smoke_trigger_profile_event(self, rom_key, event_name):
        event_key = str(event_name or "").strip().upper()
        if not event_key:
            return "no_event"
        entry = self.game_db.get(rom_key, {}) if isinstance(getattr(self, "game_db", None), dict) else {}
        profile = entry.get("profile", {}) if isinstance(entry, dict) else {}
        events = profile.get("events", {}) if isinstance(profile, dict) else {}
        evt_val = events.get(event_key)
        anim_name = ""
        button_map = "Current Deck"
        if isinstance(evt_val, dict):
            anim_name = str(evt_val.get("animation", "")).strip()
            button_map = str(evt_val.get("button_map", "Current Deck") or "Current Deck")
        elif evt_val:
            anim_name = str(evt_val).strip()
        if not anim_name:
            if event_key == "GAME_START":
                anim_name = str(profile.get("fx_on_start", "")).strip()
            elif event_key == "GAME_QUIT":
                anim_name = str(profile.get("fx_on_end", "")).strip()
        hw_connected = self._dev_smoke_ensure_hw_connected()
        controls = self._dev_smoke_controls_for_button_map(rom_key, button_map)
        if controls:
            self._load_controls_into_commander_preview(controls, apply_hardware=bool(hw_connected))
            self._sync_alu_emulator()
        if not anim_name:
            return f"{event_key}: no_animation ({button_map}){' [not connected]' if not hw_connected else ''}"
        anim_entry = self.animation_library.get(anim_name, {}) if isinstance(getattr(self, "animation_library", {}), dict) else {}
        sequence_keys = [event_key]
        if event_key == "GAME_START":
            sequence_keys.append("START")
        elif event_key == "GAME_QUIT":
            sequence_keys.append("END")
        seq = []
        if isinstance(anim_entry, dict):
            event_block = anim_entry.get("events", {})
            if isinstance(event_block, dict):
                for key in sequence_keys:
                    seq = event_block.get(key, [])
                    if isinstance(seq, list) and seq:
                        break
        if seq and hw_connected:
            self._alu_start_animation_sequence(seq)
            return f"{event_key}: {anim_name} ({button_map}) seq={len(seq)}"
        if hw_connected:
            self.preview_animation(anim_name)
            return f"{event_key}: {anim_name} ({button_map})"
        # No hardware connection: keep emulator/deck map synced and continue without raising.
        self._dev_smoke_log(f"Event {event_key} skipped live animation (not connected): {anim_name}")
        return f"{event_key}: {anim_name} ({button_map}) [not connected]"
    def _dev_smoke_assign_gm_event(self, event_name, anim_name, button_map):
        if "btn_map_list" not in self.gm_fields or "anim_list" not in self.gm_fields or "event_list" not in self.gm_fields:
            return False
        ok_map = self._dev_smoke_select_listbox_item(self.gm_fields["btn_map_list"], button_map)
        ok_anim = self._dev_smoke_select_listbox_item(self.gm_fields["anim_list"], anim_name)
        ok_evt = self._dev_smoke_select_listbox_item(self.gm_fields["event_list"], event_name)
        if not (ok_map and ok_anim and ok_evt):
            return False
        self._gm_assign_event()
        return True
    def _dev_smoke_step_commander(self):
        self.notebook.select(self.tab_main)
        self.root.update_idletasks()
        if hasattr(self, "_refresh_game_list"):
            self._refresh_game_list()
        total = int(self.game_list.size()) if hasattr(self, "game_list") else 0
        if total <= 0:
            raise RuntimeError("Commander game list is empty")
        # Exercise search filter path.
        prior_q = self._dev_smoke_input_get(self.game_search) if hasattr(self, "game_search") else ""
        if hasattr(self, "game_search"):
            self._dev_smoke_input_set(self.game_search, "x")
            self._refresh_game_list()
            filtered = int(self.game_list.size())
            self._dev_smoke_log(f"Commander filter 'x' -> {filtered} rows")
            self._dev_smoke_input_set(self.game_search, prior_q if prior_q is not None else "")
            self._refresh_game_list()
            total = int(self.game_list.size())
        # Build a deterministic 4-slot multicolor profile across all buttons.
        keys = sorted(self.led_state.keys()) if isinstance(getattr(self, "led_state", None), dict) else []
        if not keys:
            raise RuntimeError("Commander LED state is unavailable")
        for idx, key in enumerate(keys):
            slots = self._dev_smoke_color_slots_for_button(idx)
            d = self.led_state.get(key, {})
            d["colors"] = list(slots)
            d["primary"] = slots[0]
            d["secondary"] = slots[1]
            d["pulse"] = False
            d["fx_mode"] = None
            d["phase"] = 0.0
            d["speed"] = 1.0
            d["fx"] = [None, None, None, None]
            self.led_state[key] = d
        self.refresh_gui_from_state()
        self._sync_alu_emulator()

        ctx = self.dev_smoke_ctx if isinstance(getattr(self, "dev_smoke_ctx", None), dict) else {}
        rom_key = str(ctx.get("rom_key", "smoketest"))
        smoke_title = str(ctx.get("title", "SmokeTest"))
        keymap_name = str(ctx.get("keymap_name", "SmokeTest"))
        keymap_path = str(ctx.get("keymap_path", os.path.join(self.keymap_dir, f"{keymap_name}.json")))
        controls = self._collect_controls_from_led_state(include_slots=True)
        if not controls:
            raise RuntimeError("Failed to capture commander controls")
        entry = self.game_db.get(rom_key, {})
        profile = entry.get("profile", {}) if isinstance(entry.get("profile"), dict) else {}
        profile.setdefault("controller_mode", "ARCADE_PANEL")
        profile.setdefault("lighting_policy", "AUTO")
        entry["profile"] = profile
        entry["controls"] = controls
        entry["vendor"] = "Arcade Commander"
        entry["override_enabled"] = True
        md = entry.get("metadata", {}) if isinstance(entry.get("metadata"), dict) else {}
        md.update(
            {
                "title": smoke_title,
                "year": str(time.localtime().tm_year),
                "manufacturer": "Arcade Commander",
                "players": "2",
                "genre": "Diagnostics / Smoke Test",
                "source": "dev_smoke",
                "description": "Automated Commander smoke-test profile with 4-slot multicolor button mapping.",
            }
        )
        entry["metadata"] = md
        self.game_db[rom_key] = entry
        self._save_game_db()

        # Save keymap set as SmokeTest.
        os.makedirs(self.keymap_dir, exist_ok=True)
        with open(keymap_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "name": keymap_name,
                    "controls": controls,
                    "saved_at": time.time(),
                    "source": "dev_smoke",
                },
                f,
                indent=2,
            )
        self._refresh_keymap_library()

        # Refresh shared game catalogs/lists so SmokeTest is available everywhere.
        self.game_rows, self.game_col_map = self._load_game_catalog()
        self.game_title_key = self.game_col_map.get("title")
        self.gm_rows = list(self.game_rows)
        self.gm_title_key = self.game_title_key
        self._refresh_game_list()
        if hasattr(self, "_refresh_gm_list"):
            self._refresh_gm_list()
        if hasattr(self, "_refresh_fx_list"):
            self._refresh_fx_list()
        if hasattr(self, "_alu_refresh_list"):
            self._alu_refresh_list()

        # Select SmokeTest in Commander and verify ROM resolution.
        if hasattr(self, "game_search"):
            self._dev_smoke_input_set(self.game_search, "")
            self._refresh_game_list()
        smoke_idx = None
        if hasattr(self, "game_list"):
            for i in range(self.game_list.size()):
                lbl = str(self.game_list.get(i)).strip().lower()
                if lbl == smoke_title.lower():
                    smoke_idx = i
                    break
        if smoke_idx is None:
            raise RuntimeError(f"{smoke_title} was not found in Commander game list")
        self.game_list.selection_clear(0, tk.END)
        self.game_list.selection_set(smoke_idx)
        self.game_list.activate(smoke_idx)
        self.game_list.see(smoke_idx)
        self._on_game_select()
        rom = self.game_detail_vars.get("profile_rom").get() if isinstance(getattr(self, "game_detail_vars", None), dict) and self.game_detail_vars.get("profile_rom") else ""
        if str(rom).strip().lower() != rom_key.lower():
            raise RuntimeError(f"Commander did not resolve {smoke_title} ROM (got: {rom})")

        sample = next(iter(controls.values()), "")
        if "|" not in str(sample):
            raise RuntimeError("SmokeTest controls were not saved as 4-slot multicolor values")
        return f"games={total} rom={rom_key} controls={len(controls)} keymap={keymap_name}"
    def _dev_smoke_step_fx_editor(self):
        ctx = self.dev_smoke_ctx if isinstance(getattr(self, "dev_smoke_ctx", None), dict) else {}
        rom_key = str(ctx.get("rom_key", "smoketest"))
        fx_name = str(ctx.get("fx_name", "Smoke Test"))
        start_anim = str(ctx.get("start_anim_name", "SmokeTest_Start"))
        end_anim = str(ctx.get("end_anim_name", "SmokeTest_End"))
        keymap_name = str(ctx.get("keymap_name", "SmokeTest"))
        self.notebook.select(self.tab_fx_editor)
        self.root.update_idletasks()
        if hasattr(self, "_refresh_fx_list"):
            self._refresh_fx_list()
        if not hasattr(self, "fx_list") or int(self.fx_list.size()) <= 0:
            raise RuntimeError("FX game list is empty")
        if not self._dev_smoke_select_rom_in_mapped_list(self.fx_list, getattr(self, "fx_title_to_rom", {}), rom_key):
            raise RuntimeError("SmokeTest was not found in FX game list")
        self._on_fx_select()
        # Assign Full Range to all buttons in FX Editor assignment matrix.
        if "assign_var" in self.fx_editor_state and "assign_group_var" in self.fx_editor_state:
            self.fx_editor_state["assign_var"].set("Full Range")
            self.fx_editor_state["assign_group_var"].set("All")
            self._fx_editor_assign(notify=False)
        else:
            for btn in sorted(self.led_state.keys()):
                self.fx_assignments[btn] = "Full Range"
        # Build audio-driven sequence from assets/SmokeTest.mp3.
        audio_asset = self._dev_smoke_find_audio_asset()
        if not audio_asset:
            raise RuntimeError("SmokeTest.mp3 not found in assets folder")
        if not (AUDIOFX_AVAILABLE and getattr(self, "audio_engine", None)):
            raise RuntimeError("AudioFXEngine not available for smoke test")
        wav_path, tmp_path = self._prepare_audio_wav(audio_asset)
        if tmp_path and os.path.exists(tmp_path):
            ctx.setdefault("created_temp_files", []).append(tmp_path)
        analysis = self.audio_engine.analyze_wav(wav_path)
        trimmed = self._dev_smoke_trim_analysis(analysis, start_ratio=0.15, end_ratio=0.85)
        frame_count = len(trimmed.get("rms", []) or [])
        if frame_count < 2:
            raise RuntimeError("SmokeTest trimmed audio range is too small")
        sequence = self.audio_engine.build_sequence(trimmed)
        meta = sequence.get("meta", {}) if isinstance(sequence.get("meta", {}), dict) else {}
        meta["trim_start_pct"] = 15.0
        meta["trim_end_pct"] = 85.0
        meta["trim_frames"] = int(frame_count)
        meta["source"] = "dev_smoke"
        sequence["meta"] = meta
        # Save effect to FX library as "Smoke Test".
        if not self.fx_library:
            raise RuntimeError("FX library not available")
        editor_state = self._fx_editor_collect_state()
        effect = FXEffect(
            fx_id="",
            name=fx_name,
            entrance=sequence.get("entrance", {}),
            main=sequence.get("main", {}),
            exit=sequence.get("exit", {}),
            audio_path=os.path.basename(audio_asset),
            applied_to=sorted(list(self.fx_assignments.keys())),
            meta={"source": "dev_smoke_audio", "editor_state": editor_state},
        )
        fx_id = self.fx_library.save_fx(effect)
        ctx["created_fx_id"] = fx_id
        # Build start/end animations from the same audio sequence.
        self.animation_library[start_anim] = {
            "events": {"GAME_START": [{"anim": "TEASE", "duration": 30.0}]},
            "audio_sequence": sequence,
            "meta": {"source": "dev_smoke_audio", "audio_path": os.path.basename(audio_asset), "role": "start"},
        }
        self.animation_library[end_anim] = {
            "events": {"GAME_QUIT": [{"anim": "PULSE_BLUE", "duration": 30.0}]},
            "audio_sequence": sequence,
            "meta": {"source": "dev_smoke_audio", "audio_path": os.path.basename(audio_asset), "role": "end"},
        }
        self._save_animation_library()
        if hasattr(self, "_fx_editor_refresh_animation_library"):
            self._fx_editor_refresh_animation_library()
        if hasattr(self, "_fx_tab_library_refresh"):
            self._fx_tab_library_refresh()
        # Update SmokeTest profile with start/end and event map.
        entry = self.game_db.get(rom_key, {})
        profile = entry.setdefault("profile", {})
        events = profile.setdefault("events", {})
        profile["fx_on_start"] = "TEASE"
        profile["fx_on_end"] = "PULSE_BLUE"
        events["GAME_START"] = {"animation": start_anim, "button_map": keymap_name}
        events["GAME_QUIT"] = {"animation": end_anim, "button_map": keymap_name}
        entry["profile"] = profile
        entry["fx_id"] = fx_id
        self.game_db[rom_key] = entry
        self._save_game_db()
        self._refresh_game_list()
        self._refresh_gm_list()
        self._refresh_fx_list()
        self._alu_refresh_list()
        return f"rom={rom_key} fx='{fx_name}' start='{start_anim}' end='{end_anim}' frames={frame_count}"
    def _dev_smoke_step_game_manager(self):
        ctx = self.dev_smoke_ctx if isinstance(getattr(self, "dev_smoke_ctx", None), dict) else {}
        rom_key = str(ctx.get("rom_key", "smoketest"))
        keymap_name = str(ctx.get("keymap_name", "SmokeTest"))
        start_anim = str(ctx.get("start_anim_name", "SmokeTest_Start"))
        end_anim = str(ctx.get("end_anim_name", "SmokeTest_End"))
        self.notebook.select(self.tab_gm)
        self.root.update_idletasks()
        self._refresh_gm_list()
        total = int(self.gm_list.size()) if hasattr(self, "gm_list") else 0
        if total <= 0:
            raise RuntimeError("Game Manager list is empty")
        if hasattr(self, "gm_search"):
            self._dev_smoke_input_set(self.gm_search, "smoketest")
            self._refresh_gm_list()
        if not self._dev_smoke_select_rom_in_mapped_list(self.gm_list, getattr(self, "gm_title_to_rom", {}), rom_key):
            # Fallback for older GM list variants where item text resolves directly.
            found = False
            for i in range(self.gm_list.size()):
                label = str(self.gm_list.get(i)).strip().lower()
                if "smoketest" in label:
                    self.gm_list.selection_clear(0, tk.END)
                    self.gm_list.selection_set(i)
                    self.gm_list.activate(i)
                    self.gm_list.see(i)
                    found = True
                    break
            if not found:
                raise RuntimeError("SmokeTest was not found in Game Manager list")
        self._on_gm_select()
        ok_start = self._dev_smoke_assign_gm_event("GAME_START", start_anim, keymap_name)
        ok_end = self._dev_smoke_assign_gm_event("GAME_QUIT", end_anim, keymap_name)
        if not (ok_start and ok_end):
            raise RuntimeError("Failed to assign SmokeTest start/end events in Game Manager")
        return f"gm_assign start={start_anim} end={end_anim} map={keymap_name}"
    def _dev_smoke_step_emulator(self):
        ctx = self.dev_smoke_ctx if isinstance(getattr(self, "dev_smoke_ctx", None), dict) else {}
        rom_key = str(ctx.get("rom_key", "smoketest"))
        self.notebook.select(self.tab_alu)
        self.root.update_idletasks()
        self._alu_refresh_list()
        total = int(self.alu_listbox.size()) if hasattr(self, "alu_listbox") else 0
        if total <= 0:
            raise RuntimeError("Emulator list is empty")
        if hasattr(self, "alu_search_var"):
            self.alu_search_var.set("smoketest")
            self._alu_refresh_list()
        if not self._dev_smoke_select_rom_in_mapped_list(self.alu_listbox, getattr(self, "alu_label_to_rom", {}), rom_key):
            raise RuntimeError("SmokeTest was not found in Emulator list")
        self._alu_on_select()
        self._alu_load_selected()
        # Push mapped controls to physical deck before smoke start trigger (if connected).
        hw_connected = self._dev_smoke_ensure_hw_connected()
        if hw_connected:
            self._alu_apply_to_control_deck(rom_key)
        loaded_rom = str(getattr(self, "alu_last_rom", "") or "")
        if loaded_rom.lower() != rom_key.lower():
            raise RuntimeError(f"Emulator loaded wrong ROM: {loaded_rom}")
        detail = self._dev_smoke_trigger_profile_event(rom_key, "GAME_START")
        return f"games={total} rom={loaded_rom} hw={'connected' if hw_connected else 'not_connected'} start={detail}"
    def _dev_smoke_step_wait_start(self):
        return {"detail": "START event hold for 30s", "delay_ms": 30000}
    def _dev_smoke_step_emulator_end(self):
        ctx = self.dev_smoke_ctx if isinstance(getattr(self, "dev_smoke_ctx", None), dict) else {}
        rom_key = str(ctx.get("rom_key", "smoketest"))
        self.stop_animation()
        detail = self._dev_smoke_trigger_profile_event(rom_key, "GAME_QUIT")
        return f"end={detail}"
    def _dev_smoke_step_wait_end(self):
        return {"detail": "END event hold for 30s", "delay_ms": 30000}
    def _dev_smoke_step_cleanup(self):
        ctx = self.dev_smoke_ctx if isinstance(getattr(self, "dev_smoke_ctx", None), dict) else {}
        rom_key = str(ctx.get("rom_key", "smoketest"))
        fx_name = str(ctx.get("fx_name", "Smoke Test"))
        keymap_path = str(ctx.get("keymap_path", os.path.join(self.keymap_dir, "SmokeTest.json")))
        start_anim = str(ctx.get("start_anim_name", "SmokeTest_Start"))
        end_anim = str(ctx.get("end_anim_name", "SmokeTest_End"))
        removed = []
        smoke_target = "smoketest"

        def _norm_smoke(value):
            return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())

        def _is_smoke_value(value):
            return smoke_target in _norm_smoke(value)

        self.stop_animation()
        if getattr(self, "_alu_anim_seq_after_id", None):
            try:
                self.root.after_cancel(self._alu_anim_seq_after_id)
            except Exception:
                pass
            self._alu_anim_seq_after_id = None
        # Always remove SmokeTest FX artifacts by id/name/source.
        if self.fx_library:
            try:
                fx_db = self.fx_library._db.get("fx", {}) if isinstance(self.fx_library._db, dict) else {}
                remove_ids = set()
                fx_id = str(ctx.get("created_fx_id", "") or "")
                if fx_id:
                    remove_ids.add(fx_id)
                for fid, fx in list(fx_db.items()):
                    fx_obj = fx if isinstance(fx, dict) else {}
                    name = str(fx_obj.get("name", "")).strip()
                    meta = fx_obj.get("meta", {}) if isinstance(fx_obj.get("meta"), dict) else {}
                    source = str(meta.get("source", "")).strip().lower()
                    if _is_smoke_value(name) or _is_smoke_value(fid) or "dev_smoke" in source:
                        remove_ids.add(str(fid))
                if fx_name:
                    for fid, fx in list(fx_db.items()):
                        name = str((fx or {}).get("name", "")).strip().lower() if isinstance(fx, dict) else ""
                        if name == fx_name.strip().lower():
                            remove_ids.add(str(fid))
                for fid in list(remove_ids):
                    key = str(fid)
                    if key in fx_db:
                        del fx_db[key]
                        removed.append(f"fx:{key}")
                if remove_ids:
                    self.fx_library._save()
            except Exception:
                pass
        # Always remove SmokeTest game entries.
        removed_games = []
        for rk, entry in list(self.game_db.items()):
            try:
                rk_s = str(rk or "")
                if rk_s.strip().lower() == rom_key.strip().lower():
                    removed_games.append(rk_s)
                    continue
                data = entry if isinstance(entry, dict) else {}
                md = data.get("metadata", {}) if isinstance(data.get("metadata"), dict) else {}
                source = str(md.get("source", "")).strip().lower()
                title = str(md.get("title", "")).strip()
                if "dev_smoke" in source or _is_smoke_value(title) or _is_smoke_value(rk_s):
                    removed_games.append(rk_s)
            except Exception:
                continue
        for rk in removed_games:
            if rk in self.game_db:
                self.game_db.pop(rk, None)
                removed.append(f"game:{rk}")
        self._save_game_db()
        # Always remove SmokeTest keymap/profile files.
        removed_file_paths = set()
        candidate_files = [keymap_path, profile_file("SmokeTest.json"), profile_file("smoketest.json")]
        for p in ctx.get("created_temp_files", []):
            if p:
                candidate_files.append(str(p))
        for p in candidate_files:
            try:
                if p and os.path.exists(p):
                    os.unlink(p)
                    removed_file_paths.add(os.path.abspath(p))
                    removed.append(f"file:{os.path.basename(p)}")
            except Exception:
                pass
        try:
            if os.path.isdir(self.keymap_dir):
                for fn in os.listdir(self.keymap_dir):
                    if not str(fn).lower().endswith(".json"):
                        continue
                    fp = os.path.join(self.keymap_dir, fn)
                    if os.path.abspath(fp) in removed_file_paths:
                        continue
                    kill = _is_smoke_value(fn)
                    if not kill:
                        try:
                            with open(fp, "r", encoding="utf-8") as f:
                                payload = json.load(f)
                            src = str(payload.get("source", "")).strip().lower() if isinstance(payload, dict) else ""
                            name = str(payload.get("name", "")).strip() if isinstance(payload, dict) else ""
                            if "dev_smoke" in src or _is_smoke_value(name):
                                kill = True
                        except Exception:
                            kill = _is_smoke_value(fn)
                    if kill:
                        try:
                            os.unlink(fp)
                            removed_file_paths.add(os.path.abspath(fp))
                            removed.append(f"keymap:{fn}")
                        except Exception:
                            pass
        except Exception:
            pass
        # Always remove SmokeTest animations (name and source scan).
        remove_anim_keys = set()
        for name, anim in list(self.animation_library.items()):
            name_s = str(name or "")
            anim_obj = anim if isinstance(anim, dict) else {}
            meta = anim_obj.get("meta", {}) if isinstance(anim_obj.get("meta"), dict) else {}
            source = str(meta.get("source", "")).strip().lower()
            audio_path = str(meta.get("audio_path", "")).strip()
            if name_s in (start_anim, end_anim) or _is_smoke_value(name_s) or "dev_smoke" in source or _is_smoke_value(audio_path):
                remove_anim_keys.add(name_s)
        for name in remove_anim_keys:
            if name in self.animation_library:
                self.animation_library.pop(name, None)
                removed.append(f"anim:{name}")
        if remove_anim_keys:
            self._save_animation_library()
        # Safety pass: remove any SmokeTest audio conversion files in temp dir.
        try:
            tmp_root = tempfile.gettempdir()
            for fn in os.listdir(tmp_root):
                if not _is_smoke_value(fn):
                    continue
                fp = os.path.join(tmp_root, fn)
                if not os.path.isfile(fp):
                    continue
                try:
                    os.unlink(fp)
                    removed.append(f"tmp:{fn}")
                except Exception:
                    pass
        except Exception:
            pass
        # Cleanup temporary WAV files created during smoke audio conversion.
        for p in ctx.get("created_temp_files", []):
            try:
                if p and os.path.exists(p):
                    os.unlink(p)
                    removed.append(f"tmp:{os.path.basename(p)}")
            except Exception:
                pass
        self._refresh_keymap_library()
        if hasattr(self, "_fx_editor_refresh_animation_library"):
            self._fx_editor_refresh_animation_library()
        if hasattr(self, "_fx_tab_library_refresh"):
            self._fx_tab_library_refresh()
        self._refresh_game_list()
        self._refresh_gm_list()
        self._refresh_fx_list()
        self._alu_refresh_list()
        self.dev_smoke_ctx = {}
        return f"cleanup removed={len(removed)}"
    def _dev_smoke_step_controller(self):
        self.notebook.select(self.tab_controller)
        self.root.update_idletasks()
        # Exercise summary recompute by toggling one non-destructive option.
        if hasattr(self, "controller_vars") and isinstance(self.controller_vars, dict) and self.controller_vars.get("include_coin"):
            v = bool(self.controller_vars["include_coin"].get())
            self.controller_vars["include_coin"].set(not v)
            self.controller_vars["include_coin"].set(v)
        self._controller_update_summary()
        summary = self.controller_summary.get().strip() if hasattr(self, "controller_summary") else ""
        if not summary:
            raise RuntimeError("Controller summary not available")
        return "summary=ok"
    def _dev_smoke_step_return_home(self):
        self.notebook.select(self.tab_main)
        self.root.update_idletasks()
        return "home"
    def create_visual_btn(self, p, n, r, c, pack=False, width=6, height=2):
        l = "BALL" if n == "TRACKBALL" else n.split("_")[-1]
        b = MultiColorButton(p, text=l, width=width, height=height)
        b.bind("<Button-1>", lambda e, k=n, w=b: self._on_button_swatch_click(k, w, e))
        b.canvas.bind("<Button-1>", lambda e, k=n, w=b: self._on_button_swatch_click(k, w, e))
        b.bind("<Button-3>", lambda e, k=n, w=b: self._on_button_swatch_right_click(k, w, e))
        b.canvas.bind("<Button-3>", lambda e, k=n, w=b: self._on_button_swatch_right_click(k, w, e))
        self.buttons[n] = b
        if pack: b.pack(pady=2)
        else: b.grid(row=r, column=c, padx=4, pady=4)
    def create_pulse_toggle(self, p, bl, tc):
        v = tk.BooleanVar()
        grp_name = bl[0] 
        self.pulse_controls[grp_name] = {'var': v, 'buttons': bl}
        def toggle(): 
            for b in bl:
                self.led_state[b]['pulse'] = v.get()
            self._sync_alu_emulator()
        tk.Checkbutton(p, text="PULSE", variable=v, bg=COLORS["SURFACE"], fg=tc, selectcolor=COLORS["SURFACE"], command=toggle).pack()
        def _on_speed(val):
            for b in bl:
                self.led_state[b].update({'speed': float(val)})
            self._sync_alu_emulator()
        s = tk.Scale(
            p,
            from_=0.2,
            to=3.0,
            resolution=0.1,
            orient="horizontal",
            bg=COLORS["SURFACE"],
            fg=tc,
            showvalue=0,
            length=120,
            command=_on_speed,
        )
        s.set(1.0); s.pack()
        self.pulse_controls[grp_name]['scale'] = s
    def create_group_theme_controls(self, p, bl, tc):
        grp_name = f"GROUP_{bl[0]}"
        wrap = tk.Frame(p, bg=COLORS["SURFACE_LIGHT"])
        wrap.pack(fill="x", padx=6, pady=(6, 2))

        theme_row = tk.Frame(wrap, bg=COLORS["SURFACE_LIGHT"])
        theme_row.pack(fill="x")
        t_btn = MultiColorButton(theme_row, text="THEME", width=10, height=1)
        t_btn.bind("<Button-1>", lambda e, b=t_btn: self._on_group_swatch_click(bl, b, e))
        t_btn.canvas.bind("<Button-1>", lambda e, b=t_btn: self._on_group_swatch_click(bl, b, e))
        t_btn.bind("<Button-3>", lambda e, b=t_btn: self._on_group_swatch_right_click(bl, b, e))
        t_btn.canvas.bind("<Button-3>", lambda e, b=t_btn: self._on_group_swatch_right_click(bl, b, e))
        t_btn.pack(fill="x", pady=2)
        self.master_refs.append({'btn': t_btn, 'group': bl, 'mode': 'theme'})
        self._apply_group_button_colors(t_btn, bl, "theme")

        opts_row = tk.Frame(wrap, bg=COLORS["SURFACE_LIGHT"])
        opts_row.pack(fill="x", pady=(4, 0))
        opts_grid = tk.Frame(opts_row, bg=COLORS["SURFACE_LIGHT"])
        opts_grid.pack(anchor="w")

        ctrl = self.pulse_controls.setdefault(grp_name, {})
        ctrl['buttons'] = bl
        ctrl['theme_btn'] = t_btn
        ctrl['mode_vars'] = {}
        ctrl['current_mode'] = None

        def make_toggle(mode):
            def _toggle():
                var = ctrl['mode_vars'][mode]
                if var.get():
                    for m, v in ctrl['mode_vars'].items():
                        if m != mode:
                            v.set(False)
                    ctrl['current_mode'] = mode
                    self._apply_group_fx_mode(bl, mode)
                else:
                    if ctrl.get('current_mode') == mode:
                        ctrl['current_mode'] = None
                        self._apply_group_fx_mode(bl, None)
            return _toggle

        label_map = {
            "PULSE": "PLS",
            "RAINBOW": "RNBW",
            "BREATH": "BRTH",
            "STROBE": "STRB",
            "FADE": "FADE",
        }
        labels = ("PULSE", "RAINBOW", "BREATH", "STROBE", "FADE")
        for i, label in enumerate(labels):
            v = tk.BooleanVar(value=False)
            ctrl['mode_vars'][label] = v
            tk.Checkbutton(
                opts_grid,
                text=label_map.get(label, label),
                variable=v,
                bg=COLORS["SURFACE_LIGHT"],
                fg="white",
                selectcolor=COLORS["SURFACE_LIGHT"],
                font=("Segoe UI", 6, "bold"),
                command=make_toggle(label),
            ).grid(row=i % 3, column=0 if i < 3 else 1, sticky="w", padx=(0, 4), pady=1)

        speed_row = tk.Frame(wrap, bg=COLORS["SURFACE_LIGHT"])
        speed_row.pack(fill="x", pady=(2, 0))
        tk.Label(speed_row, text="SPD", bg=COLORS["SURFACE_LIGHT"], fg=tc, font=("Segoe UI", 7, "bold")).pack(side="left")
        s = tk.Scale(
            speed_row,
            from_=0.2,
            to=3.0,
            resolution=0.1,
            orient="horizontal",
            bg=COLORS["SURFACE_LIGHT"],
            fg=tc,
            showvalue=0,
            length=70,
            command=lambda val: [self.led_state[b].update({'speed': float(val)}) for b in bl] or self._sync_alu_emulator(),
        )
        s.set(self.led_state.get(bl[0], {}).get('speed', 1.0))
        s.pack(side="left", padx=(6, 0))
        ctrl['speed_scale'] = s
        ctrl['scale'] = s
    def _on_button_swatch_click(self, n, btn, e):
        idx = btn.swatch_index_from_x(e.x if hasattr(e, "x") else 0)
        if idx is None:
            self.show_context_menu(e, n)
            return
        self._open_palette_popup(n, idx, e.x_root, e.y_root)
    def _on_button_swatch_right_click(self, n, btn, e):
        idx = btn.swatch_index_from_x(e.x if hasattr(e, "x") else 0)
        if idx is None:
            self.show_context_menu(e, n)
            return
        self._show_slot_menu(n, idx, e.x_root, e.y_root)
    def _get_slot_color_hex(self, n, idx):
        self._ensure_color_slots(n)
        rgb = self.led_state[n]['colors'][idx]
        return self._rgb_to_hex(*rgb)
    def _set_slot_color(self, n, idx, rgb):
        self._ensure_color_slots(n)
        self.led_state[n]['colors'][idx] = rgb
        self.led_state[n]['primary'] = self.led_state[n]['colors'][0]
        self.led_state[n]['secondary'] = self.led_state[n]['colors'][1]
        if n in self.buttons:
            self.buttons[n].set_colors([self._rgb_to_hex(*c) for c in self.led_state[n]['colors']])
        self._refresh_group_theme_swatch_for_button(n)
        if idx == 0 and self.is_connected() and not self.led_state[n].get('pulse'):
            self.cab.set(n, rgb); self.cab.show()
            self._sync_alu_emulator({n: rgb})
    def _copy_slot_color(self, n, idx):
        self.color_clipboard = self._get_slot_color_hex(n, idx)
    def _paste_slot_color(self, n, idx):
        if not self.color_clipboard:
            return
        try:
            r, g, b = int(self.color_clipboard[1:3], 16), int(self.color_clipboard[3:5], 16), int(self.color_clipboard[5:7], 16)
            self._set_slot_color(n, idx, (r, g, b))
        except:
            pass
    def _clear_slot_color(self, n, idx):
        self._set_slot_color(n, idx, (0, 0, 0))
    def _show_slot_menu(self, n, idx, x_root, y_root):
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label="Copy Color", command=lambda: self._copy_slot_color(n, idx))
        m.add_command(label="Paste Color", command=lambda: self._paste_slot_color(n, idx))
        m.add_command(label="Clear Slot", command=lambda: self._clear_slot_color(n, idx))
        m.post(x_root, y_root)
    def _open_palette_popup(self, n, idx, x_root, y_root):
        if self._palette_popup and self._palette_popup.winfo_exists():
            self._palette_popup.destroy()
        pop = tk.Toplevel(self.root)
        pop.overrideredirect(True)
        pop.attributes("-topmost", True)
        pop.configure(bg=COLORS["SURFACE"])
        pop.geometry(f"+{x_root+8}+{y_root+8}")
        self._palette_popup = pop
        frame = tk.Frame(pop, bg=COLORS["SURFACE"], padx=6, pady=6, highlightthickness=1, highlightbackground=COLORS["SURFACE_LIGHT"])
        frame.pack()
        palette = [
            "#FFFFFF", "#E0E0E0", "#B0B0B0", "#808080",
            "#FF3B30", "#FF9500", "#FFCC00", "#34C759",
            "#00C7BE", "#007AFF", "#5856D6", "#AF52DE",
            "#FF2D55", "#8E8E93", "#5AC8FA", "#FFD60A",
        ]
        swatch_row = 0
        swatch_col = 0
        for i, col in enumerate(palette):
            lbl = tk.Label(frame, bg=col, width=2, height=1, bd=0, relief="flat")
            lbl.grid(row=swatch_row, column=swatch_col, padx=2, pady=2)
            lbl.bind("<Button-1>", lambda _e, c=col: self._apply_palette_color(n, idx, c))
            lbl.bind("<Button-3>", lambda _e: self._show_slot_menu(n, idx, x_root, y_root))
            swatch_col += 1
            if (i + 1) % 4 == 0:
                swatch_row += 1
                swatch_col = 0
        more = ModernButton(frame, text="More...", bg=COLORS["SURFACE_LIGHT"], fg="white", width=6, font=("Segoe UI", 8, "bold"),
                            command=lambda: self._open_advanced_color(n, idx))
        more.grid(row=swatch_row + 1, column=0, columnspan=4, pady=(4, 0))
        pop.bind("<FocusOut>", lambda _e: pop.destroy())
        pop.focus_force()
    def _apply_palette_color(self, n, idx, hex_color):
        try:
            r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
            self._set_slot_color(n, idx, (r, g, b))
        finally:
            if self._palette_popup and self._palette_popup.winfo_exists():
                self._palette_popup.destroy()
    def _open_advanced_color(self, n, idx):
        c = colorchooser.askcolor()[0]
        if c:
            rgb = tuple(map(int, c))
            self._set_slot_color(n, idx, rgb)
        if self._palette_popup and self._palette_popup.winfo_exists():
            self._palette_popup.destroy()

    def _on_group_swatch_click(self, bl, btn, e):
        idx = btn.swatch_index_from_x(e.x if hasattr(e, "x") else 0)
        if idx is None:
            self.show_group_context_menu(bl)
            return
        self._open_group_palette_popup(bl, idx, e.x_root, e.y_root)

    def _on_group_swatch_right_click(self, bl, btn, e):
        idx = btn.swatch_index_from_x(e.x if hasattr(e, "x") else 0)
        if idx is None:
            self.show_group_context_menu(bl)
            return
        self._show_group_slot_menu(bl, idx, e.x_root, e.y_root)

    def _set_group_slot_color(self, bl, idx, rgb):
        for n in bl:
            self._set_slot_color(n, idx, rgb)
        self._refresh_group_theme_swatch(bl)

    def _refresh_group_theme_swatch(self, bl):
        if not bl or not hasattr(self, "pulse_controls"):
            return
        grp_name = f"GROUP_{bl[0]}"
        ctrl = self.pulse_controls.get(grp_name, {}) if isinstance(self.pulse_controls, dict) else {}
        btn = ctrl.get("theme_btn") if isinstance(ctrl, dict) else None
        if btn:
            self._apply_group_button_colors(btn, bl, "theme")

    def _refresh_group_theme_swatch_for_button(self, btn_name):
        if not btn_name or not hasattr(self, "pulse_controls") or not isinstance(self.pulse_controls, dict):
            return
        for ctrl in self.pulse_controls.values():
            if not isinstance(ctrl, dict):
                continue
            bl = ctrl.get("buttons")
            tbtn = ctrl.get("theme_btn")
            if not tbtn or not isinstance(bl, (list, tuple)):
                continue
            if btn_name in bl:
                self._apply_group_button_colors(tbtn, bl, "theme")

    def _copy_group_slot_color(self, bl, idx):
        if not bl:
            return
        self.color_clipboard = self._get_slot_color_hex(bl[0], idx)

    def _paste_group_slot_color(self, bl, idx):
        if not self.color_clipboard:
            return
        try:
            r, g, b = int(self.color_clipboard[1:3], 16), int(self.color_clipboard[3:5], 16), int(self.color_clipboard[5:7], 16)
            self._set_group_slot_color(bl, idx, (r, g, b))
        except:
            pass

    def _clear_group_slot_color(self, bl, idx):
        self._set_group_slot_color(bl, idx, (0, 0, 0))

    def _show_group_slot_menu(self, bl, idx, x_root, y_root):
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label="Copy Color", command=lambda: self._copy_group_slot_color(bl, idx))
        m.add_command(label="Paste Color", command=lambda: self._paste_group_slot_color(bl, idx))
        m.add_command(label="Clear Slot", command=lambda: self._clear_group_slot_color(bl, idx))
        m.post(x_root, y_root)

    def _open_group_palette_popup(self, bl, idx, x_root, y_root):
        if self._palette_popup and self._palette_popup.winfo_exists():
            self._palette_popup.destroy()
        pop = tk.Toplevel(self.root)
        pop.overrideredirect(True)
        pop.attributes("-topmost", True)
        pop.configure(bg=COLORS["SURFACE"])
        pop.geometry(f"+{x_root+8}+{y_root+8}")
        self._palette_popup = pop
        frame = tk.Frame(pop, bg=COLORS["SURFACE"], padx=6, pady=6, highlightthickness=1, highlightbackground=COLORS["SURFACE_LIGHT"])
        frame.pack()
        palette = [
            "#FFFFFF", "#E0E0E0", "#B0B0B0", "#808080",
            "#FF3B30", "#FF9500", "#FFCC00", "#34C759",
            "#00C7BE", "#007AFF", "#5856D6", "#AF52DE",
            "#FF2D55", "#8E8E93", "#5AC8FA", "#FFD60A",
        ]
        swatch_row = 0
        swatch_col = 0
        for i, col in enumerate(palette):
            lbl = tk.Label(frame, bg=col, width=2, height=1, bd=0, relief="flat")
            lbl.grid(row=swatch_row, column=swatch_col, padx=2, pady=2)
            lbl.bind("<Button-1>", lambda _e, c=col: self._apply_group_palette_color(bl, idx, c))
            lbl.bind("<Button-3>", lambda _e: self._show_group_slot_menu(bl, idx, x_root, y_root))
            swatch_col += 1
            if (i + 1) % 4 == 0:
                swatch_row += 1
                swatch_col = 0
        more = ModernButton(frame, text="More...", bg=COLORS["SURFACE_LIGHT"], fg="white", width=6, font=("Segoe UI", 8, "bold"),
                            command=lambda: self._open_group_advanced_color(bl, idx))
        more.grid(row=swatch_row + 1, column=0, columnspan=4, pady=(4, 0))
        pop.bind("<FocusOut>", lambda _e: pop.destroy())
        pop.focus_force()

    def _apply_group_palette_color(self, bl, idx, hex_color):
        try:
            r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
            self._set_group_slot_color(bl, idx, (r, g, b))
        finally:
            if self._palette_popup and self._palette_popup.winfo_exists():
                self._palette_popup.destroy()

    def _open_group_advanced_color(self, bl, idx):
        c = colorchooser.askcolor()[0]
        if c:
            rgb = tuple(map(int, c))
            self._set_group_slot_color(bl, idx, rgb)
        if self._palette_popup and self._palette_popup.winfo_exists():
            self._palette_popup.destroy()
    def _apply_group_fx_mode(self, bl, mode):
        for n in bl:
            d = self.led_state.get(n)
            if not d:
                continue
            if mode == "PULSE":
                d['pulse'] = True
                d['fx_mode'] = "PULSE"
            elif mode in ("RAINBOW", "BREATH", "STROBE", "FADE"):
                d['pulse'] = False
                d['fx_mode'] = mode
            else:
                d['pulse'] = False
                d['fx_mode'] = None
        if self.is_connected():
            self.apply_settings_to_hardware()
        self._sync_alu_emulator()

    def show_context_menu(self, e, n):
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label=f"Edit {n} Color 1 (Primary)", command=lambda: self._open_palette_popup(n, 0, e.x_root, e.y_root))
        m.add_command(label=f"Edit {n} Color 2", command=lambda: self._open_palette_popup(n, 1, e.x_root, e.y_root))
        m.add_command(label=f"Edit {n} Color 3", command=lambda: self._open_palette_popup(n, 2, e.x_root, e.y_root))
        m.add_command(label=f"Edit {n} Color 4", command=lambda: self._open_palette_popup(n, 3, e.x_root, e.y_root))
        fx_menu = tk.Menu(m, tearoff=0)
        for idx in range(4):
            sub = tk.Menu(fx_menu, tearoff=0)
            sub.add_command(label="NONE", command=lambda i=idx: self.assign_fx(n, i, None))
            for fx in SUPPORTED_ANIMATIONS:
                sub.add_command(label=fx, command=lambda i=idx, f=fx: self.assign_fx(n, i, f))
            fx_menu.add_cascade(label=f"Color {idx+1} FX", menu=sub)
        m.add_cascade(label="Assign FX", menu=fx_menu)
        m.add_separator()
        m.add_command(label="Copy Color 1", command=lambda: self._copy_slot_color(n, 0))
        m.add_command(label="Copy Color 2", command=lambda: self._copy_slot_color(n, 1))
        m.add_command(label="Copy Color 3", command=lambda: self._copy_slot_color(n, 2))
        m.add_command(label="Copy Color 4", command=lambda: self._copy_slot_color(n, 3))
        m.add_command(label="Paste Color 1", command=lambda: self._paste_slot_color(n, 0))
        m.add_command(label="Paste Color 2", command=lambda: self._paste_slot_color(n, 1))
        m.add_command(label="Paste Color 3", command=lambda: self._paste_slot_color(n, 2))
        m.add_command(label="Paste Color 4", command=lambda: self._paste_slot_color(n, 3))
        m.add_command(label="Clear Color 1", command=lambda: self._clear_slot_color(n, 0))
        m.add_command(label="Clear Color 2", command=lambda: self._clear_slot_color(n, 1))
        m.add_command(label="Clear Color 3", command=lambda: self._clear_slot_color(n, 2))
        m.add_command(label="Clear Color 4", command=lambda: self._clear_slot_color(n, 3))
        m.add_separator()
        m.add_command(label="HARDWARE TEST", command=lambda: self.run_button_test(n))
        m.post(e.x_root, e.y_root)
    def show_group_context_menu(self, bl, title="GROUP"):
        m = tk.Menu(self.root, tearoff=0)
        try:
            x, y = self.root.winfo_pointerxy()
        except Exception:
            x, y = 0, 0
        m.add_command(label=f"{title} Color 1", command=lambda: self._open_group_palette_popup(bl, 0, x, y))
        m.add_command(label=f"{title} Color 2", command=lambda: self._open_group_palette_popup(bl, 1, x, y))
        m.add_command(label=f"{title} Color 3", command=lambda: self._open_group_palette_popup(bl, 2, x, y))
        m.add_command(label=f"{title} Color 4", command=lambda: self._open_group_palette_popup(bl, 3, x, y))
        fx_menu = tk.Menu(m, tearoff=0)
        for idx in range(4):
            sub = tk.Menu(fx_menu, tearoff=0)
            sub.add_command(label="NONE", command=lambda i=idx: self.assign_group_fx(bl, i, None))
            for fx in SUPPORTED_ANIMATIONS:
                sub.add_command(label=fx, command=lambda i=idx, f=fx: self.assign_group_fx(bl, i, f))
            fx_menu.add_cascade(label=f"Color {idx+1} FX", menu=sub)
        m.add_cascade(label="Assign FX", menu=fx_menu)
        try:
            m.post(x, y)
        except Exception:
            pass
    def pick_color(self, n, mode):
        c = colorchooser.askcolor()[0]
        if c:
            rgb = tuple(map(int, c))
            self._ensure_color_slots(n)
            idx = self._mode_to_index(mode)
            if idx is not None:
                self.led_state[n]['colors'][idx] = rgb
                self.led_state[n]['primary'] = self.led_state[n]['colors'][0]
                self.led_state[n]['secondary'] = self.led_state[n]['colors'][1]
                if n in self.buttons:
                    self.buttons[n].set_colors([self._rgb_to_hex(*c) for c in self.led_state[n]['colors']])
            if idx == 0 and self.is_connected() and not self.led_state[n]['pulse']:
                self.cab.set(n, rgb); self.cab.show()
                self._sync_alu_emulator({n: rgb})
    def assign_fx(self, n, idx, fx_name):
        self._ensure_color_slots(n)
        self.led_state[n]['fx'][idx] = fx_name
        messagebox.showinfo("FX Assigned", f"{n} Color {idx+1}: {fx_name or 'NONE'}")
    def assign_group_fx(self, bl, idx, fx_name):
        for n in bl:
            self._ensure_color_slots(n)
            self.led_state[n]['fx'][idx] = fx_name
        messagebox.showinfo("FX Assigned", f"{len(bl)} buttons Color {idx+1}: {fx_name or 'NONE'}")
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
                self._ensure_color_slots(n)
                idx = self._mode_to_index(mode)
                if idx is None:
                    continue
                self.led_state[n]['colors'][idx] = rgb
                self.led_state[n]['primary'] = self.led_state[n]['colors'][0]
                self.led_state[n]['secondary'] = self.led_state[n]['colors'][1]
                if n in self.buttons:
                    self.buttons[n].set_colors([self._rgb_to_hex(*col) for col in self.led_state[n]['colors']])
            if self.is_connected(): 
                for n in bl: self.cab.set(n, rgb)
                self.cab.show()
            self._sync_alu_emulator()
    def set_group_theme(self, bl, btn_ref=None):
        initial = None
        if btn_ref:
            try: initial = btn_ref.cget('bg')
            except: pass
        c = colorchooser.askcolor(color=initial, title="Pick Group Theme Color")
        if not c[0]:
            return
        rgb = (int(c[0][0]), int(c[0][1]), int(c[0][2]))
        for n in bl:
            self._ensure_color_slots(n)
            self.led_state[n]['colors'] = [rgb, rgb, rgb, rgb]
            self.led_state[n]['primary'] = rgb
            self.led_state[n]['secondary'] = rgb
            if n in self.buttons:
                self.buttons[n].set_colors([self._rgb_to_hex(*rgb)] * 4)
        if btn_ref:
            btn_ref.set_base_bg(c[1])
            self._apply_group_button_colors(btn_ref, bl, "theme")
        if self.is_connected():
            for n in bl: self.cab.set(n, rgb)
            self.cab.show()
        self._sync_alu_emulator()
    def open_button_test(self):
        if self.test_window and self.test_window.winfo_exists(): self.test_window.lift(); return
        self.animating = False; self.attract_active = False
        self.test_window = InputTestWindow(self.root, self)
        def on_test_close(): self.test_window.destroy(); self.apply_settings_to_hardware()
        self.test_window.protocol("WM_DELETE_WINDOW", on_test_close)
    def _ensure_color_slots(self, n):
        if n not in self.led_state:
            return
        s = self.led_state[n]
        if 'colors' not in s or not isinstance(s['colors'], list) or len(s['colors']) < 4:
            c1 = s.get('primary', (0, 0, 0))
            c2 = s.get('secondary', (0, 0, 0))
            s['colors'] = [c1, c2, (0, 0, 0), (0, 0, 0)]
        if 'fx' not in s or not isinstance(s['fx'], list) or len(s['fx']) < 4:
            s['fx'] = [None, None, None, None]
    def _coerce_rgb_slot(self, raw):
        if isinstance(raw, str):
            v = raw.strip()
            if len(v) == 7 and v.startswith("#"):
                try:
                    return (int(v[1:3], 16), int(v[3:5], 16), int(v[5:7], 16))
                except Exception:
                    return None
            if "," in v:
                try:
                    parts = [int(float(p.strip())) for p in v.split(",")[:3]]
                    if len(parts) == 3:
                        return tuple(max(0, min(255, p)) for p in parts)
                except Exception:
                    return None
            return None
        if isinstance(raw, (list, tuple)) and len(raw) >= 3:
            try:
                r = int(float(raw[0]))
                g = int(float(raw[1]))
                b = int(float(raw[2]))
                return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
            except Exception:
                return None
        return None
    def _get_button_color_slots(self, key, keep_black=False):
        d = self.led_state.get(key, {})
        raw_slots = d.get("colors", [])
        slots = []
        if isinstance(raw_slots, list):
            for raw in raw_slots[:4]:
                rgb = self._coerce_rgb_slot(raw)
                if rgb is not None:
                    slots.append(rgb)
        if not slots:
            primary = self._coerce_rgb_slot(d.get("primary", (0, 0, 0)))
            slots = [primary if primary is not None else (0, 0, 0)]
        if keep_black:
            while len(slots) < 4:
                slots.append(slots[-1] if slots else (0, 0, 0))
            return slots[:4]
        filtered = [c for c in slots if c != (0, 0, 0)]
        if filtered:
            return filtered
        # If user recently used ALL OFF, preserve preview visibility via default palette fallback.
        try:
            _p, _s, defaults = self._default_colors_for(key)
            fallback = [tuple(c) for c in (defaults or []) if tuple(c) != (0, 0, 0)]
            if fallback:
                return fallback[:4]
        except Exception:
            pass
        return [slots[0]]
    def _format_rgb_slot(self, rgb):
        c = self._coerce_rgb_slot(rgb) or (0, 0, 0)
        return f"{int(c[0])},{int(c[1])},{int(c[2])}"
    def _serialize_button_slots(self, key):
        slots = self._get_button_color_slots(key, keep_black=True)
        return "|".join(self._format_rgb_slot(c) for c in slots[:4])
    def _collect_controls_from_led_state(self, include_slots=True):
        controls = {}
        if not hasattr(self, "led_state") or not isinstance(self.led_state, dict):
            return controls
        for key in sorted(self.led_state.keys()):
            if include_slots:
                controls[key] = self._serialize_button_slots(key)
            else:
                primary = self._get_button_color_slots(key, keep_black=True)[0]
                controls[key] = self._format_rgb_slot(primary)
        return controls
    def _slot_cycle_color_rgb(self, key, elapsed_sec, speed=2.0, phase_offset=0.0, keep_black=False):
        slots = self._get_button_color_slots(key, keep_black=keep_black)
        if not slots:
            return (0, 0, 0)
        idx = int((max(0.0, float(elapsed_sec)) * max(0.05, float(speed)) + float(phase_offset)) % len(slots))
        return slots[idx]
    def _slot_cycle_color_hex(self, key, elapsed_sec, speed=2.0, phase_offset=0.0, keep_black=False):
        r, g, b = self._slot_cycle_color_rgb(key, elapsed_sec, speed=speed, phase_offset=phase_offset, keep_black=keep_black)
        return self._rgb_to_hex(r, g, b)
    def _mode_to_index(self, mode):
        if mode in ('primary', 'c1'): return 0
        if mode in ('secondary', 'c2'): return 1
        if mode == 'c3': return 2
        if mode == 'c4': return 3
        return None
    def build_game_manager_tab(self):
        gm_container = tk.Frame(self.tab_gm, bg=COLORS["BG"])
        gm_container.pack(expand=True, fill="both", padx=20, pady=20)
        gm_canvas = tk.Canvas(gm_container, bg=COLORS["BG"], highlightthickness=0, borderwidth=0)
        gm_canvas.pack(side="left", fill="both", expand=True)
        wrap = tk.Frame(gm_canvas, bg=COLORS["BG"])
        gm_canvas_window = gm_canvas.create_window((0, 0), window=wrap, anchor="nw")
        wrap.bind("<Configure>", lambda _e: gm_canvas.configure(scrollregion=gm_canvas.bbox("all")))
        gm_canvas.bind("<Configure>", lambda e: gm_canvas.itemconfigure(gm_canvas_window, width=e.width))
        wrap.columnconfigure(0, weight=2)
        wrap.columnconfigure(1, weight=3)
        wrap.rowconfigure(0, weight=1)
        wrap.rowconfigure(1, weight=0)

        left = tk.Frame(wrap, bg=COLORS["CHARCOAL"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right = tk.Frame(wrap, bg=COLORS["CHARCOAL"])
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        bottom = tk.Frame(wrap, bg=COLORS["CHARCOAL"])
        bottom.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        tk.Label(left, text="GAME LIBRARY", bg=COLORS["CHARCOAL"], fg=COLORS["SUCCESS"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        search_row = tk.Frame(left, bg=COLORS["CHARCOAL"])
        search_row.pack(fill="x", pady=(6, 6))
        self.gm_search = tk.Entry(search_row, bg=COLORS["SURFACE_LIGHT"], fg="white", borderwidth=0, font=("Consolas", 9))
        self.gm_search.pack(side="left", fill="x", expand=True)
        self.gm_search.bind("<KeyRelease>", self._refresh_gm_list)
        ModernButton(
            search_row,
            text="NEW GAME",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=10,
            font=("Segoe UI", 8, "bold"),
            command=self.gm_new_game,
        ).pack(side="right", padx=(6, 0))

        list_wrap = tk.Frame(left, bg=COLORS["CHARCOAL"], height=300)
        list_wrap.pack(fill="x", expand=False, pady=(0, 8))
        list_wrap.pack_propagate(False)
        self.gm_list = tk.Listbox(list_wrap, bg=COLORS["SURFACE_LIGHT"], fg="white", borderwidth=0, highlightthickness=0,
                                  selectbackground=COLORS["P1"], selectforeground="black", font=("Segoe UI", 9))
        self.gm_list.pack(side="left", fill="both", expand=True)
        vsb = tk.Scrollbar(list_wrap, orient="vertical", command=self.gm_list.yview)
        self._style_scrollbar(vsb)
        vsb.pack(side="right", fill="y")
        self.gm_list.configure(yscrollcommand=vsb.set)
        self.gm_list.bind("<<ListboxSelect>>", self._on_gm_select)

        tk.Label(right, text="EDITOR", bg=COLORS["CHARCOAL"], fg=COLORS["SUCCESS"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        form = tk.Frame(right, bg=COLORS["CHARCOAL"])
        form.pack(fill="x", pady=(6, 0))

        def add_field(label, key, readonly=False):
            row = tk.Frame(form, bg=COLORS["CHARCOAL"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{label}:", width=12, anchor="w", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(side="left")
            var = tk.StringVar(value="")
            if readonly:
                # Use a label for readonly fields to avoid platform/theme readonly Entry rendering issues.
                ent = tk.Label(
                    row,
                    textvariable=var,
                    bg=COLORS["SURFACE_LIGHT"],
                    fg="white",
                    font=("Consolas", 9),
                    anchor="w",
                    padx=4,
                )
                ent.pack(side="left", fill="x", expand=True)
            else:
                ent = tk.Entry(row, textvariable=var, bg=COLORS["SURFACE_LIGHT"], fg="white", borderwidth=0, font=("Consolas", 9))
                ent.pack(side="left", fill="x", expand=True)
            self.gm_fields[key] = var

        add_field("Title", "title")
        add_field("Vendor/Dev", "developer")
        add_field("Year", "year")
        add_field("Genre", "genre")
        add_field("Platform", "platform")
        add_field("Recommended", "rec_platform")
        add_field("Rank", "rank")
        add_field("ROM Key", "rom_key", readonly=True)
        add_field("Players", "players", readonly=True)
        add_field("Input Btns", "input_buttons", readonly=True)
        add_field("Input Type", "input_control", readonly=True)
        add_field("Source", "source", readonly=True)
        desc_row = tk.Frame(form, bg=COLORS["CHARCOAL"])
        desc_row.pack(fill="x", pady=(4, 2))
        tk.Label(
            desc_row,
            text="Description:",
            width=12,
            anchor="nw",
            bg=COLORS["CHARCOAL"],
            fg=COLORS["TEXT_DIM"],
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left", anchor="n")
        self.gm_fields["description"] = tk.StringVar(value="")
        tk.Label(
            desc_row,
            textvariable=self.gm_fields["description"],
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            font=("Segoe UI", 8),
            anchor="w",
            justify="left",
            wraplength=420,
            padx=4,
            pady=4,
        ).pack(side="left", fill="x", expand=True)

        tk.Frame(bottom, bg=COLORS["SURFACE_LIGHT"], height=1).pack(fill="x", pady=(0, 8))
        tk.Label(bottom, text="PROFILE", bg=COLORS["CHARCOAL"], fg=COLORS["P1"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
        profile = tk.Frame(bottom, bg=COLORS["CHARCOAL"])
        profile.pack(fill="x", pady=(6, 0))

        self.gm_fields["vendor"] = tk.StringVar(value="")
        self.gm_fields["controller_mode"] = tk.StringVar(value="ARCADE_PANEL")
        self.gm_fields["lighting_policy"] = tk.StringVar(value="AUTO")
        self.gm_fields["default_fx"] = tk.StringVar(value="NONE")
        self.gm_fields["fx_on_start"] = tk.StringVar(value="NONE")
        self.gm_fields["fx_on_end"] = tk.StringVar(value="NONE")
        self.gm_fields["event_summary"] = tk.StringVar(value="Configured: NONE")

        profile_top = tk.Frame(profile, bg=COLORS["CHARCOAL"])
        profile_top.pack(fill="x", pady=(0, 2))

        vendor_cell = tk.Frame(profile_top, bg=COLORS["CHARCOAL"])
        vendor_cell.pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Label(vendor_cell, text="Vendor:", anchor="w", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Entry(vendor_cell, textvariable=self.gm_fields["vendor"], bg=COLORS["SURFACE_LIGHT"], fg="white", borderwidth=0, font=("Consolas", 9)).pack(fill="x")

        controller_cell = tk.Frame(profile_top, bg=COLORS["CHARCOAL"])
        controller_cell.pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Label(controller_cell, text="Controller:", anchor="w", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        ttk.Combobox(
            controller_cell,
            textvariable=self.gm_fields["controller_mode"],
            values=("ARCADE_PANEL", "GAMEPAD_GENERIC", "XINPUT_XBOX", "LIGHTGUN", "UNKNOWN"),
            state="readonly",
            font=("Consolas", 8),
        ).pack(fill="x")

        policy_cell = tk.Frame(profile_top, bg=COLORS["CHARCOAL"])
        policy_cell.pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Label(policy_cell, text="Policy:", anchor="w", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        ttk.Combobox(
            policy_cell,
            textvariable=self.gm_fields["lighting_policy"],
            values=("AUTO", "ARCADE_ONLY", "FX_ONLY", "OFF"),
            state="readonly",
            font=("Consolas", 8),
        ).pack(fill="x")

        events_cell = tk.Frame(profile_top, bg=COLORS["CHARCOAL"])
        events_cell.pack(side="left", fill="x", expand=True)
        tk.Label(events_cell, text="Events:", anchor="w", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(
            events_cell,
            textvariable=self.gm_fields["event_summary"],
            bg=COLORS["SURFACE_LIGHT"],
            fg=COLORS["TEXT"],
            font=("Consolas", 8),
            anchor="w",
            padx=4,
        ).pack(fill="x")

        # Quick assignment row so event mapping is always obvious/accessible.
        quick_row = tk.Frame(profile, bg=COLORS["CHARCOAL"])
        quick_row.pack(fill="x", pady=(4, 2))
        tk.Label(quick_row, text="Quick Assign:", width=12, anchor="w", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(side="left")
        quick_inner = tk.Frame(quick_row, bg=COLORS["CHARCOAL"])
        quick_inner.pack(side="left", fill="x", expand=True)
        self.gm_fields["quick_event"] = tk.StringVar(value="GAME_START")
        self.gm_fields["quick_anim"] = tk.StringVar(value="")
        self.gm_fields["quick_map"] = tk.StringVar(value="Current Deck")
        quick_event_values = (
            "FE_START", "FE_QUIT", "SCREENSAVER_START", "SCREENSAVER_STOP", "LIST_CHANGE",
            "GAME_START", "GAME_QUIT", "GAME_PAUSE", "AUDIO_ANIMATION", "SPEAK_CONTROLS", "DEFAULT"
        )
        quick_event_combo = ttk.Combobox(
            quick_inner,
            textvariable=self.gm_fields["quick_event"],
            values=quick_event_values,
            state="readonly",
            width=16,
            font=("Consolas", 8),
        )
        quick_event_combo.pack(side="left", padx=(0, 6))
        quick_anim_combo = ttk.Combobox(
            quick_inner,
            textvariable=self.gm_fields["quick_anim"],
            values=tuple(self._gm_assignable_effect_options()),
            state="readonly",
            width=24,
            font=("Consolas", 8),
        )
        quick_anim_combo.pack(side="left", padx=(0, 6))
        quick_map_combo = ttk.Combobox(
            quick_inner,
            textvariable=self.gm_fields["quick_map"],
            values=("Current Deck",),
            state="readonly",
            width=16,
            font=("Consolas", 8),
        )
        quick_map_combo.pack(side="left", padx=(0, 6))
        self.gm_fields["quick_event_combo"] = quick_event_combo
        self.gm_fields["quick_anim_combo"] = quick_anim_combo
        self.gm_fields["quick_map_combo"] = quick_map_combo
        ModernButton(
            quick_inner,
            text="ASSIGN",
            bg=COLORS["SYS"],
            fg="black",
            width=8,
            font=("Segoe UI", 8, "bold"),
            command=self._gm_assign_quick_event,
        ).pack(side="left", padx=(0, 6))
        ModernButton(
            quick_inner,
            text="PREVIEW",
            bg=COLORS["P1"],
            fg="black",
            width=8,
            font=("Segoe UI", 8, "bold"),
            command=self._gm_preview_quick_event,
        ).pack(side="left")

        details_row = tk.Frame(profile, bg=COLORS["CHARCOAL"]); details_row.pack(fill="x", pady=(2, 4))
        tk.Label(details_row, text="Details:", width=12, anchor="nw", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(side="left", anchor="n")
        details_wrap = tk.Frame(details_row, bg=COLORS["CHARCOAL"])
        details_wrap.pack(side="left", fill="both", expand=True)
        self.gm_fields["event_details"] = tk.Text(details_wrap, height=4, bg=COLORS["SURFACE_LIGHT"], fg="white",
                                                  borderwidth=0, highlightthickness=0, font=("Consolas", 8))
        self.gm_fields["event_details"].pack(side="left", fill="both", expand=True)
        details_scroll = tk.Scrollbar(details_wrap, orient="vertical", command=self.gm_fields["event_details"].yview)
        self._style_scrollbar(details_scroll)
        details_scroll.pack(side="left", fill="y")
        self.gm_fields["event_details"].configure(yscrollcommand=details_scroll.set, state="disabled")

        # Event Assignment panel (Button Map + Animation + Event)
        assign_panel = tk.LabelFrame(profile, text=" EVENT ASSIGNMENT ", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"],
                                     font=("Segoe UI", 8, "bold"), padx=8, pady=6)
        assign_panel.pack(fill="x", pady=(8, 0))
        lists_row = tk.Frame(assign_panel, bg=COLORS["CHARCOAL"])
        lists_row.pack(fill="x")
        # Button Map list
        bm_col = tk.Frame(lists_row, bg=COLORS["CHARCOAL"])
        bm_col.pack(side="left", fill="both", expand=True, padx=(0, 6))
        tk.Label(bm_col, text="BUTTON MAP", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.gm_fields["btn_map_search"] = tk.Entry(bm_col, bg=COLORS["SURFACE_LIGHT"], fg="white", borderwidth=0, font=("Consolas", 8))
        self.gm_fields["btn_map_search"].pack(fill="x", pady=(2, 4))
        self.gm_fields["btn_map_search"].bind("<KeyRelease>", self._gm_filter_event_lists)
        self.gm_fields["btn_map_list"] = tk.Listbox(bm_col, height=4, bg=COLORS["SURFACE_LIGHT"], fg="white",
                                                    borderwidth=0, highlightthickness=0, font=("Segoe UI", 8))
        self.gm_fields["btn_map_list"].pack(fill="both", expand=True)
        # Animations list
        an_col = tk.Frame(lists_row, bg=COLORS["CHARCOAL"])
        an_col.pack(side="left", fill="both", expand=True, padx=(6, 6))
        tk.Label(an_col, text="EFFECT / ANIMATION", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.gm_fields["anim_search"] = tk.Entry(an_col, bg=COLORS["SURFACE_LIGHT"], fg="white", borderwidth=0, font=("Consolas", 8))
        self.gm_fields["anim_search"].pack(fill="x", pady=(2, 4))
        self.gm_fields["anim_search"].bind("<KeyRelease>", self._gm_filter_event_lists)
        self.gm_fields["anim_list"] = tk.Listbox(an_col, height=4, bg=COLORS["SURFACE_LIGHT"], fg="white",
                                                 borderwidth=0, highlightthickness=0, font=("Segoe UI", 8))
        self.gm_fields["anim_list"].pack(fill="both", expand=True)
        # Events list
        ev_col = tk.Frame(lists_row, bg=COLORS["CHARCOAL"])
        ev_col.pack(side="left", fill="both", expand=True, padx=(6, 0))
        tk.Label(ev_col, text="EVENT", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.gm_fields["event_search"] = tk.Entry(ev_col, bg=COLORS["SURFACE_LIGHT"], fg="white", borderwidth=0, font=("Consolas", 8))
        self.gm_fields["event_search"].pack(fill="x", pady=(2, 4))
        self.gm_fields["event_search"].bind("<KeyRelease>", self._gm_filter_event_lists)
        self.gm_fields["event_list"] = tk.Listbox(ev_col, height=4, bg=COLORS["SURFACE_LIGHT"], fg="white",
                                                  borderwidth=0, highlightthickness=0, font=("Segoe UI", 8))
        self.gm_fields["event_list"].pack(fill="both", expand=True)

        assign_btn_row = tk.Frame(assign_panel, bg=COLORS["CHARCOAL"])
        assign_btn_row.pack(fill="x", pady=(6, 0))
        ModernButton(assign_btn_row, text="ASSIGN", bg=COLORS["SYS"], fg="black", width=8,
                     font=("Segoe UI", 8, "bold"), command=self._gm_assign_event).pack(side="left")
        ModernButton(assign_btn_row, text="PREVIEW", bg=COLORS["P1"], fg="black", width=8,
                     font=("Segoe UI", 8, "bold"), command=self._gm_preview_assignment).pack(side="left", padx=(6, 0))
        ModernButton(assign_btn_row, text="STOP", bg=COLORS["DANGER"], fg="white", width=8,
                     font=("Segoe UI", 8, "bold"), command=self.stop_animation).pack(side="left", padx=(6, 0))
        self.gm_fields["preview_status"] = tk.StringVar(value="Preview: NONE")
        tk.Label(assign_panel, textvariable=self.gm_fields["preview_status"], bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"],
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 0))

        gm_preview = tk.LabelFrame(
            profile,
            text=" MAP PREVIEW ",
            bg=COLORS["CHARCOAL"],
            fg=COLORS["SYS"],
            font=("Segoe UI", 8, "bold"),
            padx=6,
            pady=6,
        )
        gm_preview.pack(fill="x", pady=(8, 0))
        self.gm_preview_canvas = tk.Canvas(gm_preview, height=170, bg=COLORS["SURFACE"], highlightthickness=0)
        self.gm_preview_canvas.pack(fill="x")
        self.gm_preview_controls = {}
        self.gm_preview_canvas.bind("<Configure>", lambda _e: self._gm_draw_map_preview(self.gm_preview_controls))
        self._gm_draw_map_preview({})

        row = tk.Frame(profile, bg=COLORS["CHARCOAL"]); row.pack(fill="x", pady=6)
        tk.Checkbutton(
            row,
            text="Enable Override",
            variable=self.override_enabled_var,
            bg=COLORS["CHARCOAL"],
            fg="white",
            selectcolor=COLORS["CHARCOAL"],
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w")

        action_row = tk.Frame(right, bg=COLORS["CHARCOAL"])
        action_row.pack(fill="x", pady=(10, 0))
        ModernButton(
            action_row,
            text="LOAD DB",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=10,
            font=("Segoe UI", 9, "bold"),
            command=self.gm_reload_db,
        ).pack(side="left", padx=(0, 6))
        ModernButton(
            action_row,
            text="SAVE DB",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=10,
            font=("Segoe UI", 9, "bold"),
            command=self._save_game_db,
        ).pack(side="left", padx=(0, 6))
        ModernButton(
            action_row,
            text="SAVE CHANGES",
            bg=COLORS["SYS"],
            fg="black",
            width=14,
            font=("Segoe UI", 9, "bold"),
            command=self.gm_save_changes,
        ).pack(side="left", padx=(0, 6))
        ModernButton(
            action_row,
            text="DELETE GAME",
            bg=COLORS["DANGER"],
            fg="white",
            width=12,
            font=("Segoe UI", 9, "bold"),
            command=self.gm_delete_game,
        ).pack(side="left")

        self.gm_rows, self.game_col_map = self._load_game_catalog()
        self.gm_title_key = self.game_col_map.get("title")
        self._refresh_gm_list()
    def build_fx_tab(self):
        wrap = tk.Frame(self.tab_fx, bg=COLORS["BG"])
        wrap.pack(expand=True, fill="both", padx=20, pady=20)
        wrap.columnconfigure(0, weight=3)
        wrap.columnconfigure(1, weight=2)
        wrap.rowconfigure(0, weight=1)

        left = tk.Frame(wrap, bg=COLORS["CHARCOAL"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right = tk.Frame(wrap, bg=COLORS["CHARCOAL"])
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        right_inner = tk.Frame(right, bg=COLORS["CHARCOAL"])
        right_inner.grid(row=0, column=0, sticky="nsew")

        tk.Label(left, text="GAME LIBRARY", bg=COLORS["CHARCOAL"], fg=COLORS["SUCCESS"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        fx_search_row = tk.Frame(left, bg=COLORS["CHARCOAL"])
        fx_search_row.pack(fill="x", pady=(6, 6))
        self.fx_search = tk.Entry(fx_search_row, bg=COLORS["SURFACE_LIGHT"], fg="white", borderwidth=0, font=("Consolas", 9))
        self.fx_search.pack(side="left", fill="x", expand=True)
        self.fx_search.bind("<KeyRelease>", self._refresh_fx_list)
        ModernButton(
            fx_search_row,
            text="NEW GAME",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=10,
            font=("Segoe UI", 8, "bold"),
            command=self.new_game_entry,
        ).pack(side="right", padx=(6, 0))

        fx_list_wrap = tk.Frame(left, bg=COLORS["CHARCOAL"], height=320)
        fx_list_wrap.pack(fill="x", expand=False, pady=(0, 8))
        fx_list_wrap.pack_propagate(False)
        self.fx_list = tk.Listbox(fx_list_wrap, bg=COLORS["SURFACE_LIGHT"], fg="white", borderwidth=0, highlightthickness=0,
                                  selectbackground=COLORS["P1"], selectforeground="black", font=("Segoe UI", 9))
        self.fx_list.pack(side="left", fill="both", expand=True)
        fx_vsb = tk.Scrollbar(fx_list_wrap, orient="vertical", command=self.fx_list.yview)
        fx_vsb.pack(side="right", fill="y")
        self.fx_list.configure(yscrollcommand=fx_vsb.set)
        self.fx_list.bind("<<ListboxSelect>>", self._on_fx_select)

        right_inner.columnconfigure(0, weight=1)
        right_inner.columnconfigure(1, weight=1)
        fx_left = tk.Frame(right_inner, bg=COLORS["CHARCOAL"])
        fx_left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        fx_right = tk.Frame(right_inner, bg=COLORS["CHARCOAL"])
        fx_right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        fx = tk.LabelFrame(fx_left, text=" LED FX ", bg=COLORS["BG"], fg=COLORS["FX"], font=("Segoe UI", 10, "bold"), padx=12, pady=12)
        fx.pack(fill="x", anchor="n")
        fx_rows = [
            ("RAINBOW", "rainbow", "RAINBOW"),
            ("BREATH", "breath", "PULSE_RED"),
            ("STROBE", "strobe", "HYPER_STROBE"),
            ("FADE", "fade", "PULSE_BLUE"),
        ]
        for label, key, anim in fx_rows:
            f = tk.Frame(fx, bg=COLORS["SURFACE"], pady=4)
            f.pack(fill="x", pady=2)
            var = tk.BooleanVar()
            self.fx_vars[key] = var
            tk.Checkbutton(
                f,
                text=label,
                variable=var,
                bg=COLORS["SURFACE"],
                fg="white",
                selectcolor=COLORS["BG"],
                font=("Segoe UI", 9),
            ).pack(side="left")
            ModernButton(
                f,
                text="PREVIEW",
                bg=COLORS["SURFACE_LIGHT"],
                fg="white",
                font=("Segoe UI", 8, "bold"),
                command=lambda a=anim: self.preview_animation(a),
            ).pack(side="right", padx=(6, 4))
        self.fx_speed = tk.Scale(
            fx,
            from_=0.1,
            to=5.0,
            resolution=0.1,
            orient="horizontal",
            bg=COLORS["BG"],
            fg="white",
            highlightthickness=0,
            label="SPEED",
        )
        self.fx_speed.set(1.0)
        self.fx_speed.pack(fill="x", pady=10)
        ModernButton(
            fx,
            text="STOP ANIMATION",
            bg=COLORS["DANGER"],
            fg="white",
            font=("Segoe UI", 9, "bold"),
            command=self.stop_animation,
        ).pack(fill="x", pady=(4, 2))
        fx_btn_row = tk.Frame(fx_left, bg=COLORS["CHARCOAL"])
        fx_btn_row.pack(fill="x", pady=(10, 0))
        ModernButton(
            fx_btn_row,
            text="APPLY FX TO GAME",
            bg=COLORS["SYS"],
            fg="black",
            width=16,
            font=("Segoe UI", 9, "bold"),
            command=self.fx_apply_to_game,
        ).pack(side="left", padx=(0, 6))
        ModernButton(
            fx_btn_row,
            text="LOAD GAME FX",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=14,
            font=("Segoe UI", 9, "bold"),
            command=self.fx_load_from_game,
        ).pack(side="left")

        rand_row = tk.Frame(fx_left, bg=COLORS["CHARCOAL"])
        rand_row.pack(fill="x", pady=(10, 0))
        tk.Label(rand_row, text="RANDOM FX", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.random_fx_var = tk.DoubleVar(value=0.0)
        tk.Scale(
            rand_row,
            from_=0.0,
            to=1.0,
            resolution=0.05,
            orient="horizontal",
            bg=COLORS["CHARCOAL"],
            fg="white",
            label="Intensity",
            variable=self.random_fx_var,
            command=lambda _v: self.apply_random_fx(),
        ).pack(fill="x")

        assign = tk.Frame(fx_left, bg=COLORS["CHARCOAL"])
        assign.pack(fill="x", pady=(12, 0))
        tk.Label(assign, text="FX On Start:", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            assign,
            textvariable=self.fx_on_start_var,
            values=("NONE",) + self._get_shared_effect_options(),
            state="readonly",
            font=("Consolas", 8),
            width=16,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))
        tk.Label(assign, text="FX On End:", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Combobox(
            assign,
            textvariable=self.fx_on_end_var,
            values=("NONE",) + self._get_shared_effect_options(),
            state="readonly",
            font=("Consolas", 8),
            width=16,
        ).grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=(6, 0))
        assign.columnconfigure(1, weight=1)
        ModernButton(
            assign,
            text="SAVE START/END",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=16,
            font=("Segoe UI", 9, "bold"),
            command=self.fx_save_start_end,
        ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        audio = tk.LabelFrame(fx_right, text=" AUDIO FX ", bg=COLORS["BG"], fg=COLORS["FX"], font=("Segoe UI", 9, "bold"), padx=10, pady=8)
        audio.pack(fill="x", pady=(14, 0))
        self.audio_status = tk.StringVar(value="No WAV loaded.")
        tk.Label(audio, textvariable=self.audio_status, bg=COLORS["BG"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8)).pack(anchor="w")
        audio_btns = tk.Frame(audio, bg=COLORS["BG"])
        audio_btns.pack(fill="x", pady=(6, 0))
        ModernButton(
            audio_btns,
            text="LOAD WAV",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=10,
            font=("Segoe UI", 8, "bold"),
            command=self.audio_load_wav,
        ).pack(side="left", padx=(0, 6))
        ModernButton(
            audio_btns,
            text="BUILD SEQ",
            bg=COLORS["SYS"],
            fg="black",
            width=10,
            font=("Segoe UI", 8, "bold"),
            command=self.audio_build_sequence,
        ).pack(side="left", padx=(0, 6))
        ModernButton(
            audio_btns,
            text="SAVE TO GAME",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=12,
            font=("Segoe UI", 8, "bold"),
            command=self.audio_save_to_game,
        ).pack(side="left")
        ModernButton(
            audio_btns,
            text="OPEN FX EDITOR",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=14,
            font=("Segoe UI", 8, "bold"),
            command=self.open_fx_editor,
        ).pack(side="right")

        lib = tk.LabelFrame(fx_right, text=" FX LIBRARY ", bg=COLORS["BG"], fg=COLORS["SYS"], font=("Segoe UI", 9, "bold"), padx=10, pady=8)
        lib.pack(fill="x", pady=(12, 0))
        self.fx_lib_search = tk.StringVar(value="")
        lib_search = tk.Entry(lib, textvariable=self.fx_lib_search, bg=COLORS["SURFACE_LIGHT"], fg="white", borderwidth=0, font=("Consolas", 9))
        lib_search.pack(fill="x")
        lib_search.bind("<KeyRelease>", self._fx_tab_library_refresh)
        lib_filter_row = tk.Frame(lib, bg=COLORS["BG"])
        lib_filter_row.pack(fill="x", pady=(6, 0))
        tk.Label(lib_filter_row, text="Filter", bg=COLORS["BG"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(side="left")
        self.fx_lib_filter = tk.StringVar(value="all")
        ttk.Combobox(
            lib_filter_row,
            textvariable=self.fx_lib_filter,
            values=("all", "audio", "presets"),
            state="readonly",
            width=10,
            font=("Consolas", 8),
        ).pack(side="left", padx=(6, 0))
        self.fx_lib_filter.trace_add("write", lambda *_: self._fx_tab_library_refresh())
        lib_list_wrap = tk.Frame(lib, bg=COLORS["BG"])
        lib_list_wrap.pack(fill="x", pady=(6, 0))
        self.fx_lib_list = tk.Listbox(lib_list_wrap, bg=COLORS["SURFACE_LIGHT"], fg="white", borderwidth=0, highlightthickness=0,
                                      selectbackground=COLORS["P1"], selectforeground="black", font=("Segoe UI", 9), height=6)
        self.fx_lib_list.pack(side="left", fill="x", expand=True)
        lib_vsb = tk.Scrollbar(lib_list_wrap, orient="vertical", command=self.fx_lib_list.yview)
        lib_vsb.pack(side="right", fill="y")
        self.fx_lib_list.configure(yscrollcommand=lib_vsb.set)
        self.fx_lib_list.bind("<<ListboxSelect>>", self._fx_tab_library_select)
        lib_btns = tk.Frame(lib, bg=COLORS["BG"])
        lib_btns.pack(fill="x", pady=(6, 0))
        ModernButton(
            lib_btns,
            text="SAVE FX",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=10,
            font=("Segoe UI", 8, "bold"),
            command=self.fx_save_to_library,
        ).pack(side="left", padx=(0, 6))
        ModernButton(
            lib_btns,
            text="APPLY TO GAME",
            bg=COLORS["SYS"],
            fg="black",
            width=14,
            font=("Segoe UI", 8, "bold"),
            command=self.fx_apply_library_to_game,
        ).pack(side="left", padx=(0, 6))
        ModernButton(
            lib_btns,
            text="LOAD GAME FX",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=12,
            font=("Segoe UI", 8, "bold"),
            command=self.fx_load_from_game,
        ).pack(side="left")
        lib_btns2 = tk.Frame(lib, bg=COLORS["BG"])
        lib_btns2.pack(fill="x", pady=(6, 0))
        ModernButton(
            lib_btns2,
            text="IMPORT",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=10,
            font=("Segoe UI", 8, "bold"),
            command=self._fx_tab_library_import,
        ).pack(side="left", padx=(0, 6))
        ModernButton(
            lib_btns2,
            text="EXPORT",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=10,
            font=("Segoe UI", 8, "bold"),
            command=self._fx_tab_library_export,
        ).pack(side="left", padx=(0, 6))
        ModernButton(
            lib_btns2,
            text="DELETE",
            bg=COLORS["DANGER"],
            fg="white",
            width=10,
            font=("Segoe UI", 8, "bold"),
            command=self._fx_tab_library_delete,
        ).pack(side="left")

        # Spacer removed at user request.

        self._fx_tab_library_refresh()
        self._refresh_fx_list()
    def preview_animation(self, anim):
        entry = self._resolve_shared_effect_entry(anim)
        if entry and str(entry.get("type", "")).lower() == "effect":
            preset_id = str(entry.get("preset_id", "")).strip()
            if preset_id and self._apply_effects_preset(preset_id):
                self.effects_enabled = True
                self.app_settings["effects_enabled"] = True
                self.app_settings["effects_preset_id"] = preset_id
                self.save_settings({"effects_enabled": True, "effects_preset_id": preset_id})
                self.animating = False
                self.fx_active = None
                self.attract_active = False
                self._tick_effects_engine()
            return
        resolved = str(entry.get("animation", "")).strip().upper() if entry else (
            resolve_animation(anim) if ANIM_REGISTRY_AVAILABLE else str(anim).strip().upper()
        )
        if str(resolved).upper() == "ALL_OFF":
            self.all_off()
            return
        if not self.is_connected():
            messagebox.showerror("Error", "Controller not connected.")
            return
        if str(resolved).lower() == "demomode":
            self._start_demo_mode_preview(10.0)
            return
        if str(resolved).lower() == "bazerk":
            self._start_bazerk_preview(5.0)
            return
        self.animating = True
        self.attract_active = False
        self.fx_active = resolved
        self._fx_offset = 0
        self._run_fx_preview()
    def _select_alu_tab(self):
        if hasattr(self, "notebook") and hasattr(self, "tab_alu"):
            try:
                self.notebook.select(self.tab_alu)
            except Exception:
                pass
    def _preview_to_alu(self, anim):
        self.preview_animation(anim)
        self._select_alu_tab()
    def _start_demo_mode_preview(self, duration):
        if not self.is_connected():
            return
        self.animating = True
        self.attract_active = False
        self.fx_active = "DEMOMODE"
        self._demo_start_ts = time.time()
        self._demo_duration = float(duration)
        self._fx_offset = 0
        self._run_demo_mode_preview()
    def _run_demo_mode_preview(self):
        if not self.animating or self.fx_active != "DEMOMODE":
            return
        elapsed = time.time() - getattr(self, "_demo_start_ts", time.time())
        if elapsed >= getattr(self, "_demo_duration", 10.0):
            self.stop_animation()
            return
        # Assigned-slot cycle on player buttons (0-11)
        keys = list(self.cab.LEDS.keys())
        frame_override = {}
        for i, k in enumerate(keys[:12]):
            col = self._slot_cycle_color_rgb(k, elapsed, speed=2.2, phase_offset=i * 0.45)
            self.cab.set(k, col)
            frame_override[k] = col
        # Admin cluster cycles slower for contrast.
        for i, k in enumerate(keys[12:16]):
            col = self._slot_cycle_color_rgb(k, elapsed, speed=1.4, phase_offset=1.0 + i * 0.35)
            self.cab.set(k, col)
            frame_override[k] = col
        # Trackball (16) if available
        if len(keys) > 16:
            col = self._slot_cycle_color_rgb(keys[16], elapsed, speed=1.0, phase_offset=0.0)
            self.cab.set(keys[16], col)
            frame_override[keys[16]] = col
        self.cab.show()
        self._sync_alu_emulator(frame_override)
        self._fx_offset = (self._fx_offset + 5) % 255
        self.root.after(30, self._run_demo_mode_preview)
    def _start_bazerk_preview(self, duration):
        if not self.is_connected():
            return
        self.animating = True
        self.attract_active = False
        self.fx_active = "BAZERK"
        self._bazerk_start_ts = time.time()
        self._bazerk_duration = float(duration)
        self._bazerk_on = True
        self._run_bazerk_preview()
    def _run_bazerk_preview(self):
        if not self.animating or self.fx_active != "BAZERK":
            return
        elapsed = time.time() - getattr(self, "_bazerk_start_ts", time.time())
        if elapsed >= getattr(self, "_bazerk_duration", 5.0):
            self.stop_animation()
            return
        color = (255, 0, 0) if self._bazerk_on else (255, 255, 255)
        frame_override = {}
        for k in self.cab.LEDS.keys():
            self.cab.set(k, color)
            frame_override[k] = color
        self.cab.show()
        self._sync_alu_emulator(frame_override)
        self._bazerk_on = not self._bazerk_on
        self.root.after(80, self._run_bazerk_preview)
    def _run_fx_preview(self):
        if not self.animating or not self.fx_active or not self.is_connected():
            return
        speed = 1.0
        if self.fx_speed is not None:
            try:
                speed = float(self.fx_speed.get())
            except Exception:
                speed = 1.0
        delay = max(20, int(150 / max(speed, 0.1)))
        frame_override = {}
        if self.fx_active == "RAINBOW":
            keys = list(self.cab.LEDS.keys())
            for i, k in enumerate(keys):
                col = wheel((i * 20 + self._fx_offset) % 255)
                self.cab.set(k, col)
                frame_override[k] = col
            self.cab.show()
            self._sync_alu_emulator(frame_override)
            self._fx_offset = (self._fx_offset + int(5 * speed)) % 255
        elif self.fx_active in ("PULSE_RED", "PULSE_BLUE", "PULSE_GREEN"):
            phase = time.time() * (2.0 * speed)
            pulse = int((math.sin(phase) + 1) * 127.5)
            if self.fx_active == "PULSE_GREEN":
                color = (0, pulse, 0)
            else:
                color = (pulse, 0, 0) if self.fx_active == "PULSE_RED" else (0, 0, pulse)
            self.cab.set_all(color)
            self.cab.show()
            for k in self.cab.LEDS.keys():
                frame_override[k] = color
            self._sync_alu_emulator(frame_override)
        elif self.fx_active == "HYPER_STROBE":
            on = (int(time.time() * (10 * speed)) % 2) == 0
            color = (255, 255, 255) if on else (0, 0, 0)
            self.cab.set_all(color)
            self.cab.show()
            for k in self.cab.LEDS.keys():
                frame_override[k] = color
            self._sync_alu_emulator(frame_override)
        elif self.fx_active == "TEASE":
            # Slow pulse-cycle with per-button phase offsets and global speed sweep (2.0Hz <-> 0.5Hz).
            now = time.time()
            keys = list(self.cab.LEDS.keys())
            sweep_period = 16.0
            sweep = (now % sweep_period) / sweep_period
            sweep_mix = 1.0 - abs((2.0 * sweep) - 1.0)  # triangle wave
            hz = 0.5 + (1.5 * sweep_mix)  # 0.5 to 2.0 pulses/sec
            hue_base = now * 0.03
            for i, k in enumerate(keys):
                phase_offset = (i * 0.61803398875) % 1.0
                pulse = 0.5 + (0.5 * math.sin((now * hz * math.tau) + (phase_offset * math.tau)))
                brightness = 0.08 + (0.92 * pulse)
                hue = (hue_base + ((i * 0.38196601125) % 1.0)) % 1.0
                r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                col = (int(r * 255 * brightness), int(g * 255 * brightness), int(b * 255 * brightness))
                self.cab.set(k, col)
                frame_override[k] = col
            self.cab.show()
            self._sync_alu_emulator(frame_override)
        elif self.fx_active == "TEASE_INDEPENDENT":
            # Copy of TEASE, but each button runs independent pulse sweep timing and hue cycle speed.
            now = time.time()
            keys = list(self.cab.LEDS.keys())
            sweep_period = 16.0
            for i, k in enumerate(keys):
                sweep_offset = ((i * 0.41421356237) % 1.0) * sweep_period
                sweep = ((now + sweep_offset) % sweep_period) / sweep_period
                sweep_mix = 1.0 - abs((2.0 * sweep) - 1.0)  # triangle wave
                hz = 0.5 + (1.5 * sweep_mix)  # 0.5 to 2.0 pulses/sec
                phase_offset = (i * 0.61803398875) % 1.0
                pulse = 0.5 + (0.5 * math.sin((now * hz * math.tau) + (phase_offset * math.tau)))
                brightness = 0.08 + (0.92 * pulse)
                hue_speed = 0.03 * (0.75 + (((i * 0.27182818284) % 1.0) * 0.90))
                hue = ((now * hue_speed) + ((i * 0.38196601125) % 1.0)) % 1.0
                r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                col = (int(r * 255 * brightness), int(g * 255 * brightness), int(b * 255 * brightness))
                self.cab.set(k, col)
                frame_override[k] = col
            self.cab.show()
            self._sync_alu_emulator(frame_override)
        self.root.after(delay, self._run_fx_preview)
    def stop_animation(self):
        self.animating = False
        self.fx_active = None
        self.apply_settings_to_hardware()
    def _refresh_gm_list(self, _evt=None):
        if not hasattr(self, "gm_list"):
            return
        q = self.gm_search.get().strip().lower()
        self.gm_list.delete(0, tk.END)
        title_key = self.gm_title_key
        titles = []
        for row in self.gm_rows:
            title = row.get(title_key, "") if title_key else ""
            if not title:
                continue
            if q and q not in title.lower():
                continue
            titles.append(title)
        for title in sorted(titles, key=lambda s: str(s).lower()):
            self.gm_list.insert(tk.END, title)
        if self.gm_list.size() > 0:
            self.gm_list.selection_set(0)
            self._on_gm_select()
    def save_keymap_from_commander(self):
        if not hasattr(self, "led_state"):
            messagebox.showinfo("Keymap", "No control mapping available.")
            return
        name = simpledialog.askstring("Save Key Mapping", "Keymap name:")
        if not name:
            return
        controls = self._collect_controls_from_led_state(include_slots=True)
        payload = {
            "name": name,
            "controls": controls,
            "saved_at": time.time(),
        }
        os.makedirs(self.keymap_dir, exist_ok=True)
        path = filedialog.asksaveasfilename(
            title="Save Key Mapping",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile=f"{name}.json",
            initialdir=self.keymap_dir,
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        self._refresh_keymap_library()
        messagebox.showinfo("Saved", f"Keymap saved to:\n{path}")
    def _on_gm_select(self, _evt=None):
        if not hasattr(self, "gm_list"):
            return
        sel = self.gm_list.curselection()
        if not sel:
            return
        title = self.gm_list.get(sel[0])
        row = None
        title_key = self.gm_title_key
        for r in self.gm_rows:
            if r.get(title_key, "") == title:
                row = r
                break
        if not row:
            return
        rom_key = self._row_rom_key(row, self.game_col_map, title_key)
        if not rom_key:
            rom_key = self._rom_key_from_title(title)
        self.gm_selected_rom = rom_key
        entry = self.game_db.get(rom_key, {})
        profile = entry.get("profile", {})
        metadata = entry.get("metadata", {}) if isinstance(entry.get("metadata"), dict) else {}
        catalog_override = entry.get("catalog_override", {}) or entry.get("catalog", {})
        catalog_base = entry.get("catalog_base", {})
        override_enabled = entry.get("override_enabled", True)
        self.override_enabled_var.set(bool(override_enabled))
        def base_from_csv(col_key, default=""):
            return row.get(self.game_col_map.get(col_key, ""), default)
        def pick(field, col_key, default=""):
            base = catalog_base.get(field) or base_from_csv(col_key, default)
            if override_enabled:
                return catalog_override.get(field) or base
            return base
        self.gm_fields["title"].set(pick("title", "title", ""))
        self.gm_fields["developer"].set(pick("developer", "developer", ""))
        self.gm_fields["year"].set(pick("year", "year", ""))
        self.gm_fields["genre"].set(pick("genre", "genres", ""))
        self.gm_fields["platform"].set(pick("platforms", "platforms", ""))
        self.gm_fields["rec_platform"].set(pick("rec_platform", "rec_platform", ""))
        self.gm_fields["rank"].set(pick("rank", "rank", ""))
        self.gm_fields["rom_key"].set(rom_key)
        self.gm_fields["players"].set(str(metadata.get("players", "")).strip())
        self.gm_fields["input_buttons"].set(str(metadata.get("input_buttons", "")).strip())
        self.gm_fields["input_control"].set(str(metadata.get("input_control", "")).strip())
        self.gm_fields["source"].set(str(metadata.get("source", "")).strip())
        self.gm_fields["description"].set(str(metadata.get("description", "")).strip())
        self.gm_fields["vendor"].set(entry.get("vendor", ""))
        self.gm_fields["controller_mode"].set(profile.get("controller_mode", "ARCADE_PANEL"))
        self.gm_fields["lighting_policy"].set(profile.get("lighting_policy", "AUTO"))
        self.gm_fields["default_fx"].set(profile.get("default_fx", "") or "NONE")
        self.gm_fields["fx_on_start"].set(profile.get("fx_on_start", "") or "NONE")
        self.gm_fields["fx_on_end"].set(profile.get("fx_on_end", "") or "NONE")
        # Event summary (read-only)
        event_map = profile.get("events") or entry.get("events") or {}
        if not isinstance(event_map, dict):
            event_map = {}
        if self.gm_fields["fx_on_start"].get() not in ("", "NONE"):
            event_map.setdefault("GAME_START", {"animation": self.gm_fields["fx_on_start"].get(), "button_map": "Current Deck"})
        if self.gm_fields["fx_on_end"].get() not in ("", "NONE"):
            event_map.setdefault("GAME_QUIT", {"animation": self.gm_fields["fx_on_end"].get(), "button_map": "Current Deck"})
        if self.gm_fields["default_fx"].get() not in ("", "NONE"):
            event_map.setdefault("DEFAULT", {"animation": self.gm_fields["default_fx"].get(), "button_map": "Current Deck"})
        event_types = [
            "FE_START", "FE_QUIT", "SCREENSAVER_START", "SCREENSAVER_STOP", "LIST_CHANGE",
            "GAME_START", "GAME_QUIT", "GAME_PAUSE", "AUDIO_ANIMATION", "SPEAK_CONTROLS", "DEFAULT"
        ]
        events = self._format_event_summary_items(event_map)
        if "event_summary" in self.gm_fields:
            self.gm_fields["event_summary"].set("Configured: " + (", ".join(events) if events else "NONE"))
        if "event_details" in self.gm_fields:
            lines = []
            for ev in event_types:
                val = event_map.get(ev)
                if isinstance(val, dict):
                    anim = val.get("animation") or "NONE"
                    bmap = val.get("button_map") or "NONE"
                    lines.append(f"{ev}: {anim} ({bmap})")
                elif val:
                    lines.append(f"{ev}: {val}")
                else:
                    lines.append(f"{ev}: NONE")
            details = "\n".join(lines)
            self.gm_fields["event_details"].configure(state="normal")
            self.gm_fields["event_details"].delete("1.0", tk.END)
            self.gm_fields["event_details"].insert("1.0", details)
            self.gm_fields["event_details"].configure(state="disabled")
        # Populate assignment lists
        if "btn_map_list" in self.gm_fields:
            self._refresh_keymap_library()
            items = ["Current Deck"] + sorted(self.keymap_library.keys())
            self.gm_fields["btn_map_items"] = items
        if "anim_list" in self.gm_fields:
            items = list(self._gm_assignable_effect_options(entry))
            self.gm_fields["anim_items"] = items
        if "event_list" in self.gm_fields:
            self.gm_fields["event_items"] = list(event_types)
        self._gm_filter_event_lists()
        # Keep quick-assign controls in sync with available maps/animations.
        if "quick_anim_combo" in self.gm_fields:
            quick_anims = self._gm_assignable_effect_options(entry)
            self.gm_fields["quick_anim_combo"]["values"] = tuple(quick_anims)
        if "quick_map_combo" in self.gm_fields:
            quick_maps = ["Current Deck"] + sorted(self.keymap_library.keys())
            self.gm_fields["quick_map_combo"]["values"] = tuple(quick_maps)
        if "quick_event" in self.gm_fields:
            qev = self.gm_fields["quick_event"].get().strip() or "GAME_START"
            qanim = ""
            qmap = "Current Deck"
            cur = event_map.get(qev)
            if isinstance(cur, dict):
                qanim = str(cur.get("animation", "")).strip()
                qmap = str(cur.get("button_map", "Current Deck") or "Current Deck")
            elif cur:
                qanim = str(cur).strip()
            if qanim:
                self.gm_fields["quick_anim"].set(qanim)
            if "quick_map_combo" in self.gm_fields:
                try:
                    vals = list(self.gm_fields["quick_map_combo"]["values"])
                except Exception:
                    vals = ["Current Deck"]
                self.gm_fields["quick_map"].set(qmap if qmap in vals else "Current Deck")
        self._gm_draw_map_preview(entry.get("controls", {}) or {})
        if "preview_status" in self.gm_fields:
            self.gm_fields["preview_status"].set("Preview: Ready")
        self._alu_preview_from_rom(rom_key)
    def _gm_filter_event_lists(self, _evt=None):
        if not hasattr(self, "gm_fields"):
            return
        def apply_filter(list_key, items_key, search_key):
            lb = self.gm_fields.get(list_key)
            items = self.gm_fields.get(items_key, [])
            search = self.gm_fields.get(search_key)
            if not lb:
                return
            q = search.get().strip().lower() if search else ""
            lb.delete(0, tk.END)
            for item in items:
                if not q or q in str(item).lower():
                    lb.insert(tk.END, item)
            if lb.size() > 0:
                lb.selection_set(0)
        apply_filter("btn_map_list", "btn_map_items", "btn_map_search")
        apply_filter("anim_list", "anim_items", "anim_search")
        apply_filter("event_list", "event_items", "event_search")
    def gm_new_game(self):
        self.gm_selected_rom = ""
        for k in ["title", "developer", "year", "genre", "platform", "rec_platform", "rank", "vendor", "players", "input_buttons", "input_control", "source", "description"]:
            self.gm_fields[k].set("")
        self.gm_fields["rom_key"].set("")
        self.gm_fields["controller_mode"].set("ARCADE_PANEL")
        self.gm_fields["lighting_policy"].set("AUTO")
        self.gm_fields["default_fx"].set("NONE")
        self.gm_fields["fx_on_start"].set("NONE")
        self.gm_fields["fx_on_end"].set("NONE")
        if "event_summary" in self.gm_fields:
            self.gm_fields["event_summary"].set("Configured: NONE")
        if "event_details" in self.gm_fields:
            self.gm_fields["event_details"].configure(state="normal")
            self.gm_fields["event_details"].delete("1.0", tk.END)
            self.gm_fields["event_details"].configure(state="disabled")
        if "preview_status" in self.gm_fields:
            self.gm_fields["preview_status"].set("Preview: NONE")
        if "quick_event" in self.gm_fields:
            self.gm_fields["quick_event"].set("GAME_START")
        if "quick_anim" in self.gm_fields:
            self.gm_fields["quick_anim"].set("")
        if "quick_map" in self.gm_fields:
            self.gm_fields["quick_map"].set("Current Deck")
        self._gm_draw_map_preview({})
        self.override_enabled_var.set(True)
    def _gm_assignable_effect_options(self, entry=None):
        values = []
        seen = set()
        def add(value):
            text = str(value or "").strip()
            if not text:
                return
            key = text.upper()
            if key in seen:
                return
            seen.add(key)
            values.append(text)
        add("NONE")
        for label in self._get_shared_effect_options():
            add(label)
        if isinstance(getattr(self, "animation_library", None), dict):
            for name in sorted(self.animation_library.keys(), key=lambda s: str(s).lower()):
                add(name)
        if entry is None and getattr(self, "gm_selected_rom", ""):
            entry = self.game_db.get(self.gm_selected_rom, {})
        if isinstance(entry, dict):
            profile = entry.get("profile", {})
            if isinstance(profile, dict):
                add(profile.get("default_fx"))
                add(profile.get("fx_on_start"))
                add(profile.get("fx_on_end"))
                p_events = profile.get("events", {})
                if isinstance(p_events, dict):
                    for item in p_events.values():
                        if isinstance(item, dict):
                            add(item.get("animation"))
                        else:
                            add(item)
            legacy_events = entry.get("events", {})
            if isinstance(legacy_events, dict):
                for item in legacy_events.values():
                    if isinstance(item, dict):
                        add(item.get("animation"))
                    else:
                        add(item)
        if not values:
            return ("NONE",)
        if values[0].upper() != "NONE":
            values.insert(0, "NONE")
        head = values[0]
        tail = sorted(values[1:], key=lambda s: str(s).lower())
        return tuple([head] + tail)
    def _gm_build_effective_event_map(self, entry):
        profile = entry.get("profile", {}) if isinstance(entry, dict) else {}
        event_map = profile.get("events") or entry.get("events") or {}
        if not isinstance(event_map, dict):
            event_map = {}
        if profile.get("fx_on_start"):
            event_map.setdefault("GAME_START", {"animation": profile.get("fx_on_start"), "button_map": "Current Deck"})
        if profile.get("fx_on_end"):
            event_map.setdefault("GAME_QUIT", {"animation": profile.get("fx_on_end"), "button_map": "Current Deck"})
        if profile.get("default_fx"):
            event_map.setdefault("DEFAULT", {"animation": profile.get("default_fx"), "button_map": "Current Deck"})
        return event_map
    def _gm_controls_from_button_map(self, button_map):
        map_name = str(button_map or "Current Deck").strip() or "Current Deck"
        if map_name != "Current Deck":
            km = self.keymap_library.get(map_name, {}) if isinstance(getattr(self, "keymap_library", {}), dict) else {}
            controls = km.get("controls", {}) if isinstance(km, dict) else {}
            if isinstance(controls, dict) and controls:
                return controls
        entry = self.game_db.get(self.gm_selected_rom, {}) if self.gm_selected_rom else {}
        controls = entry.get("controls", {}) if isinstance(entry, dict) else {}
        return controls if isinstance(controls, dict) else {}
    def _gm_draw_map_preview(self, controls):
        if not hasattr(self, "gm_preview_canvas"):
            return
        self.gm_preview_controls = controls if isinstance(controls, dict) else {}
        c = self.gm_preview_canvas
        c.delete("all")
        w = max(720, int(c.winfo_width() or 720))
        h = max(170, int(c.winfo_height() or 170))
        c.config(width=w, height=h)
        def color_for(key):
            val = self.gm_preview_controls.get(key)
            hx = self._alu_parse_color(val) if val is not None else None
            return hx or "#1b1b1b"
        def draw_btn(x, y, r, key, label):
            fill = color_for(key)
            c.create_oval(x-r, y-r, x+r, y+r, fill=fill, outline="#4a4a4a", width=1)
            c.create_text(x, y+r+10, text=label, fill=COLORS["TEXT_DIM"], font=("Segoe UI", 7, "bold"))
        c.create_text(int(w*0.16), 16, text="PLAYER 1", fill=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold"))
        c.create_text(int(w*0.50), 16, text="ADMIN", fill=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold"))
        c.create_text(int(w*0.84), 16, text="PLAYER 2", fill=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold"))
        p1x = int(w*0.16); p2x = int(w*0.84); ay = 56; by = 96; step = 44; r = 16
        draw_btn(p1x-step, ay, r, "P1_A", "A"); draw_btn(p1x, ay, r, "P1_B", "B"); draw_btn(p1x+step, ay, r, "P1_C", "C")
        draw_btn(p1x-step, by, r, "P1_X", "X"); draw_btn(p1x, by, r, "P1_Y", "Y"); draw_btn(p1x+step, by, r, "P1_Z", "Z")
        draw_btn(p2x-step, ay, r, "P2_A", "A"); draw_btn(p2x, ay, r, "P2_B", "B"); draw_btn(p2x+step, ay, r, "P2_C", "C")
        draw_btn(p2x-step, by, r, "P2_X", "X"); draw_btn(p2x, by, r, "P2_Y", "Y"); draw_btn(p2x+step, by, r, "P2_Z", "Z")
        ax = int(w*0.50)
        draw_btn(ax-70, ay, r, "P1_START", "P1")
        draw_btn(ax-22, ay, r, "P2_START", "P2")
        draw_btn(ax+26, ay, r, "REWIND", "RWD")
        draw_btn(ax+74, ay, r, "MENU", "MENU")
        tr = 26
        tfill = color_for("TRACKBALL")
        c.create_oval(ax-tr, 126-tr, ax+tr, 126+tr, fill=tfill, outline="#4a4a4a", width=1)
        c.create_text(ax, 126, text="TB", fill=COLORS["TEXT_DIM"], font=("Segoe UI", 7, "bold"))
    def _gm_preview_assignment(self):
        if not self.gm_selected_rom:
            messagebox.showinfo("Preview", "Select a game first.")
            return
        ev_sel = self.gm_fields["event_list"].curselection() if "event_list" in self.gm_fields else ()
        anim_sel = self.gm_fields["anim_list"].curselection() if "anim_list" in self.gm_fields else ()
        map_sel = self.gm_fields["btn_map_list"].curselection() if "btn_map_list" in self.gm_fields else ()
        event = self.gm_fields["event_list"].get(ev_sel[0]) if ev_sel else "GAME_START"
        animation = self.gm_fields["anim_list"].get(anim_sel[0]) if anim_sel else ""
        button_map = self.gm_fields["btn_map_list"].get(map_sel[0]) if map_sel else "Current Deck"
        entry = self.game_db.get(self.gm_selected_rom, {})
        if not animation:
            event_map = self._gm_build_effective_event_map(entry)
            cur = event_map.get(event)
            if isinstance(cur, dict):
                animation = str(cur.get("animation", "")).strip()
                if button_map == "Current Deck":
                    button_map = str(cur.get("button_map", "Current Deck") or "Current Deck")
            elif cur:
                animation = str(cur).strip()
        self._gm_preview_event_values(event, animation, button_map)
    def _gm_preview_quick_event(self):
        if not self.gm_selected_rom:
            messagebox.showinfo("Preview", "Select a game first.")
            return
        event = str(self.gm_fields.get("quick_event").get() if "quick_event" in self.gm_fields else "GAME_START").strip() or "GAME_START"
        animation = str(self.gm_fields.get("quick_anim").get() if "quick_anim" in self.gm_fields else "").strip()
        button_map = str(self.gm_fields.get("quick_map").get() if "quick_map" in self.gm_fields else "Current Deck").strip() or "Current Deck"
        if not animation:
            entry = self.game_db.get(self.gm_selected_rom, {})
            event_map = self._gm_build_effective_event_map(entry)
            cur = event_map.get(event)
            if isinstance(cur, dict):
                animation = str(cur.get("animation", "")).strip()
                if button_map == "Current Deck":
                    button_map = str(cur.get("button_map", "Current Deck") or "Current Deck")
            elif cur:
                animation = str(cur).strip()
        self._gm_preview_event_values(event, animation, button_map)
    def _gm_preview_event_values(self, event, animation, button_map):
        controls = self._gm_controls_from_button_map(button_map)
        self._gm_draw_map_preview(controls)
        self._load_controls_into_commander_preview(controls, apply_hardware=False)
        self._sync_alu_emulator()
        status = f"Preview: {event} -> {animation or 'NONE'} ({button_map})"
        if animation and animation.upper() != "NONE":
            if self.is_connected():
                played_sequence = False
                anim_entry = self.animation_library.get(animation, {}) if isinstance(getattr(self, "animation_library", {}), dict) else {}
                if isinstance(anim_entry, dict):
                    event_block = anim_entry.get("events", {})
                    if isinstance(event_block, dict):
                        sequence_keys = [str(event or "").strip().upper()]
                        if sequence_keys[0] == "GAME_START":
                            sequence_keys.append("START")
                        elif sequence_keys[0] == "GAME_QUIT":
                            sequence_keys.append("END")
                        for key in sequence_keys:
                            seq = event_block.get(key, [])
                            if isinstance(seq, list) and seq:
                                self._alu_start_animation_sequence(seq)
                                status += f" | Sequence started ({len(seq)} steps)."
                                played_sequence = True
                                break
                if not played_sequence:
                    self.preview_animation(animation)
                    status += " | Effect started."
            else:
                status += " | Not connected: map preview only."
        if "preview_status" in self.gm_fields:
            self.gm_fields["preview_status"].set(status)
    def _gm_assign_quick_event(self):
        if not self.gm_selected_rom:
            messagebox.showinfo("Assign", "Select a game first.")
            return
        event = str(self.gm_fields.get("quick_event").get() if "quick_event" in self.gm_fields else "GAME_START").strip() or "GAME_START"
        anim = str(self.gm_fields.get("quick_anim").get() if "quick_anim" in self.gm_fields else "").strip()
        bmap = str(self.gm_fields.get("quick_map").get() if "quick_map" in self.gm_fields else "Current Deck").strip() or "Current Deck"
        if not anim:
            messagebox.showinfo("Assign", "Select an Effect/Animation (or NONE to clear).")
            return
        self._gm_assign_event_values(event, anim, bmap)
    def _gm_assign_event_values(self, event, anim, bmap):
        event = str(event or "").strip()
        anim = str(anim or "").strip()
        bmap = str(bmap or "Current Deck").strip() or "Current Deck"
        if not event:
            messagebox.showinfo("Assign", "Select an Event.")
            return
        entry = self.game_db.get(self.gm_selected_rom, {})
        profile = entry.setdefault("profile", {})
        events = profile.get("events", {})
        if not isinstance(events, dict):
            events = {}
        clearing = (not anim) or (anim.upper() == "NONE")
        if clearing:
            events.pop(event, None)
        else:
            events[event] = {"animation": anim, "button_map": bmap}
        if events:
            profile["events"] = events
        elif "events" in profile:
            profile.pop("events", None)
        # Keep legacy fields synchronized for start/end/default paths.
        if event == "GAME_START":
            profile["fx_on_start"] = "" if clearing else anim
        elif event == "GAME_QUIT":
            profile["fx_on_end"] = "" if clearing else anim
        elif event == "DEFAULT":
            profile["default_fx"] = "" if clearing else anim
        entry["profile"] = profile
        self.game_db[self.gm_selected_rom] = entry
        self._save_game_db()
        # Update legacy fields for compatibility.
        if event == "GAME_START":
            self.gm_fields["fx_on_start"].set("NONE" if clearing else anim)
        elif event == "GAME_QUIT":
            self.gm_fields["fx_on_end"].set("NONE" if clearing else anim)
        elif event == "DEFAULT":
            self.gm_fields["default_fx"].set("NONE" if clearing else anim)
        self._on_gm_select()
        if "preview_status" in self.gm_fields:
            if clearing:
                self.gm_fields["preview_status"].set(f"Cleared: {event}")
            else:
                self.gm_fields["preview_status"].set(f"Assigned: {event} -> {anim} ({bmap})")
    def _gm_assign_event(self):
        if not self.gm_selected_rom:
            messagebox.showinfo("Assign", "Select a game first.")
            return
        if "btn_map_list" not in self.gm_fields or "anim_list" not in self.gm_fields or "event_list" not in self.gm_fields:
            return
        ev_sel = self.gm_fields["event_list"].curselection()
        anim_sel = self.gm_fields["anim_list"].curselection()
        map_sel = self.gm_fields["btn_map_list"].curselection()
        if not ev_sel or not anim_sel:
            messagebox.showinfo("Assign", "Select an Event and Effect/Animation.")
            return
        event = self.gm_fields["event_list"].get(ev_sel[0])
        anim = self.gm_fields["anim_list"].get(anim_sel[0])
        bmap = self.gm_fields["btn_map_list"].get(map_sel[0]) if map_sel else "Current Deck"
        self._gm_assign_event_values(event, anim, bmap)
    def gm_reload_db(self):
        self.game_db = self._load_game_db()
        self._refresh_gm_list()
        self._refresh_game_list()

    def game_export(self):
        if not hasattr(self, "game_list"):
            messagebox.showinfo("Export Game", "Game list is not available.")
            return
        sel = self.game_list.curselection()
        if not sel:
            messagebox.showinfo("Export Game", "Select a game to export.")
            return
        title = self.game_list.get(sel[0])
        row = None
        title_key = self.game_title_key
        if self.game_rows and title_key:
            for r in self.game_rows:
                if r.get(title_key, "") == title:
                    row = r
                    break
        if not row:
            messagebox.showinfo("Export Game", "Catalog entry not found.")
            return
        rom_key = self._row_rom_key(row, self.game_col_map, title_key)
        entry = self.game_db.get(rom_key, {})
        fx_effect = None
        fx_id = entry.get("fx_id")
        if fx_id and self.fx_library:
            fx_effect = self.fx_library.get_fx_by_id(fx_id)
        payload = {
            "rom_key": rom_key,
            "catalog": row,
            "profile": entry.get("profile", {}),
            "controls": entry.get("controls", {}),
            "fx": entry.get("fx", {}),
            "speed": entry.get("speed", 1.0),
            "fx_id": entry.get("fx_id", ""),
            "fx_name": (fx_effect or {}).get("name", "") if fx_effect else "",
            "fx_effect": fx_effect or {},
            "override_enabled": entry.get("override_enabled", True),
            "catalog_override": entry.get("catalog_override", {}),
        }
        path = filedialog.asksaveasfilename(
            title="Export Game",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        messagebox.showinfo("Exported", f"Exported to:\n{path}")

    def game_import(self):
        path = filedialog.askopenfilename(
            title="Import Game",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as e:
            messagebox.showerror("Import Failed", f"Could not read file:\n{e}")
            return
        if not isinstance(payload, dict):
            messagebox.showerror("Import Failed", "Invalid game file format.")
            return
        rom_key = payload.get("rom_key") or self._rom_key_from_title((payload.get("catalog") or {}).get("title", ""))
        if not rom_key:
            messagebox.showerror("Import Failed", "Missing rom_key/title in game file.")
            return
        entry = self.game_db.get(rom_key, {})
        entry["controls"] = payload.get("controls", entry.get("controls", {}))
        entry["profile"] = payload.get("profile", entry.get("profile", {}))
        entry["fx"] = payload.get("fx", entry.get("fx", {}))
        entry["speed"] = payload.get("speed", entry.get("speed", 1.0))
        entry["override_enabled"] = payload.get("override_enabled", entry.get("override_enabled", True))
        if payload.get("catalog_override"):
            entry["catalog_override"] = payload.get("catalog_override")
        # Resolve FX library effect by name, create if missing
        fx_effect = payload.get("fx_effect") or {}
        fx_name = payload.get("fx_name") or fx_effect.get("name", "")
        if fx_name and self.fx_library:
            existing = self.fx_library.get_fx_by_name(fx_name)
            if existing:
                entry["fx_id"] = existing.get("fx_id")
            else:
                fx_effect = dict(fx_effect) if isinstance(fx_effect, dict) else {}
                fx_effect["fx_id"] = ""
                fx_effect["name"] = fx_name
                fx_effect.setdefault("entrance", {})
                fx_effect.setdefault("main", {})
                fx_effect.setdefault("exit", {})
                fx_effect.setdefault("audio_path", "")
                fx_effect.setdefault("applied_to", [])
                fx_effect.setdefault("meta", {})
                new_id = self.fx_library.save_fx(fx_effect)
                entry["fx_id"] = new_id
        else:
            # Keep any fx_id if provided (may be local)
            if payload.get("fx_id"):
                entry["fx_id"] = payload.get("fx_id")
        self.game_db[rom_key] = entry
        self._save_game_db()
        # Optional: add to catalog cache if provided
        catalog = payload.get("catalog")
        if isinstance(catalog, dict):
            if not self.game_rows:
                self.game_rows = []
            title_key = self.game_title_key or "title"
            existing = any(r.get(title_key, "") == catalog.get(title_key, "") for r in self.game_rows)
            if not existing:
                self.game_rows.append(catalog)
        self._refresh_game_list()
        messagebox.showinfo("Imported", f"Imported '{rom_key}'.")

    def apply_game_profile(self, rom_key, event=None):
        # Apply controls to deck + emulator, load FX settings to UI, optionally trigger start/end event
        if not rom_key:
            return
        entry = self.game_db.get(rom_key, {}) if hasattr(self, "game_db") else {}
        controls = entry.get("controls", {}) or {}
        # Apply controls to control deck state
        if hasattr(self, "led_state"):
            for n, d in self.led_state.items():
                d['primary'] = (0, 0, 0)
                d['secondary'] = (0, 0, 0)
                d['colors'] = [(0, 0, 0)] * 4
                d['pulse'] = False
            for bid, val in controls.items():
                if bid not in self.led_state:
                    continue
                hex_c = self._alu_parse_color(val)
                rgb = _hex_to_rgb(hex_c) if hex_c else (0, 0, 0)
                d = self.led_state[bid]
                d['primary'] = rgb
                d['secondary'] = (0, 0, 0)
                d['colors'] = [rgb, (0, 0, 0), (0, 0, 0), (0, 0, 0)]
                d['pulse'] = False
            self.refresh_gui_from_state()
            self.apply_settings_to_hardware()
        # Apply to ALU emulator view
        if hasattr(self, "alu_emulator"):
            self._alu_preview_from_rom(rom_key)
        # Load FX settings into UI
        if hasattr(self, "fx_vars"):
            fx_data = entry.get("fx", {})
            for k, v in self.fx_vars.items():
                v.set(bool(fx_data.get(k, False)))
            if self.fx_speed is not None:
                try:
                    self.fx_speed.set(entry.get("speed", 1.0))
                except Exception:
                    pass
        fx_id = entry.get("fx_id")
        if fx_id and self.fx_library:
            fx = self.fx_library.get_fx_by_id(fx_id)
            if fx:
                self.fx_lib_selected_id = fx_id
                if hasattr(self, "_fx_tab_library_sync_selection"):
                    self._fx_tab_library_sync_selection(fx_id)
                self._fx_apply_effect_to_ui(fx)
        # Trigger event if requested and defined
        if event:
            profile = entry.get("profile", {}) or {}
            if event == "start":
                fx = profile.get("fx_on_start", "")
                if fx:
                    self.preview_animation(fx)
            elif event == "end":
                fx = profile.get("fx_on_end", "")
                if fx:
                    self.preview_animation(fx)
        self._refresh_fx_list()
        if hasattr(self, "status_var"):
            self.status_var.set(f"Loaded profile: {rom_key}")
    def gm_save_changes(self):
        title = self.gm_fields["title"].get().strip()
        rom_key = self.gm_fields["rom_key"].get().strip() or self._rom_key_from_title(title)
        if not title:
            messagebox.showinfo("Missing Title", "Enter a game title before saving.")
            return
        if not rom_key:
            messagebox.showinfo("Missing ROM Key", "Unable to generate ROM key.")
            return
        entry = self.game_db.get(rom_key, {})
        entry.setdefault("profile", {})
        entry["vendor"] = self.gm_fields["vendor"].get().strip()
        entry["profile"]["controller_mode"] = self.gm_fields["controller_mode"].get()
        entry["profile"]["lighting_policy"] = self.gm_fields["lighting_policy"].get()
        entry["profile"]["default_fx"] = "" if self.gm_fields["default_fx"].get() == "NONE" else self.gm_fields["default_fx"].get()
        entry["profile"]["fx_on_start"] = "" if self.gm_fields["fx_on_start"].get() == "NONE" else self.gm_fields["fx_on_start"].get()
        entry["profile"]["fx_on_end"] = "" if self.gm_fields["fx_on_end"].get() == "NONE" else self.gm_fields["fx_on_end"].get()
        metadata = entry.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        metadata["players"] = self.gm_fields["players"].get().strip()
        metadata["input_buttons"] = self.gm_fields["input_buttons"].get().strip()
        metadata["input_control"] = self.gm_fields["input_control"].get().strip()
        metadata["source"] = self.gm_fields["source"].get().strip()
        metadata["description"] = self.gm_fields["description"].get().strip()
        entry["metadata"] = metadata
        entry["override_enabled"] = bool(self.override_enabled_var.get())
        entry["catalog_override"] = {
            "title": self.gm_fields["title"].get().strip(),
            "developer": self.gm_fields["developer"].get().strip(),
            "year": self.gm_fields["year"].get().strip(),
            "genre": self.gm_fields["genre"].get().strip(),
            "platforms": self.gm_fields["platform"].get().strip(),
            "rec_platform": self.gm_fields["rec_platform"].get().strip(),
            "rank": self.gm_fields["rank"].get().strip(),
        }
        if "catalog_base" not in entry:
            base_row = self._find_catalog_row_by_rom(rom_key) or {}
            entry["catalog_base"] = {
                "title": base_row.get(self.game_col_map.get("title", ""), ""),
                "developer": base_row.get(self.game_col_map.get("developer", ""), ""),
                "year": base_row.get(self.game_col_map.get("year", ""), ""),
                "genre": base_row.get(self.game_col_map.get("genres", ""), ""),
                "platforms": base_row.get(self.game_col_map.get("platforms", ""), ""),
                "rec_platform": base_row.get(self.game_col_map.get("rec_platform", ""), ""),
                "rank": base_row.get(self.game_col_map.get("rank", ""), ""),
            }
        self.game_db[rom_key] = entry
        self._save_game_db()
        try:
            self._upsert_catalog_row({
                "title": self.gm_fields["title"].get().strip(),
                "developer": self.gm_fields["developer"].get().strip(),
                "year": self.gm_fields["year"].get().strip(),
                "genre": self.gm_fields["genre"].get().strip(),
                "platform": self.gm_fields["platform"].get().strip(),
                "rec_platform": self.gm_fields["rec_platform"].get().strip(),
                "rank": self.gm_fields["rank"].get().strip(),
            })
        except Exception as e:
            messagebox.showwarning("Catalog Update Failed", str(e))
        self.gm_selected_rom = rom_key
        self.gm_fields["rom_key"].set(rom_key)
        self._refresh_game_list()
        self._refresh_gm_list()
        # Keep the saved ROM selected in Game Manager so changes remain visible.
        row = self._find_catalog_row_by_rom(rom_key)
        title_key = self.gm_title_key
        saved_title = row.get(title_key, "") if isinstance(row, dict) and title_key else ""
        if saved_title and hasattr(self, "gm_list"):
            for i in range(self.gm_list.size()):
                if str(self.gm_list.get(i)).strip() == str(saved_title).strip():
                    self.gm_list.selection_clear(0, tk.END)
                    self.gm_list.selection_set(i)
                    self.gm_list.activate(i)
                    self.gm_list.see(i)
                    self._on_gm_select()
                    break
        self._refresh_fx_list()
        messagebox.showinfo("Saved", f"Game '{rom_key}' saved.")
    def gm_delete_game(self):
        if not hasattr(self, "gm_fields"):
            return
        rom_key = self.gm_fields["rom_key"].get().strip()
        title = self.gm_fields["title"].get().strip() or rom_key
        if not rom_key:
            messagebox.showinfo("Delete Game", "Select a game first.")
            return
        if rom_key not in self.game_db:
            messagebox.showinfo("Delete Game", f"'{title}' was not found in the JSON database.")
            return
        if not messagebox.askyesno(
            "Delete Game",
            f"Delete '{title}' ({rom_key}) from the game database?\n\nThis cannot be undone.",
        ):
            return
        del self.game_db[rom_key]
        self._save_game_db()
        # Rebuild shared list caches so deletion is reflected on all tabs.
        self.game_rows, self.game_col_map = self._load_game_catalog()
        self.game_title_key = self.game_col_map.get("title")
        self.gm_rows = list(self.game_rows)
        self.gm_title_key = self.game_title_key
        self._refresh_game_list()
        self._refresh_gm_list()
        self._refresh_fx_list()
        if hasattr(self, "_alu_refresh_list"):
            self._alu_refresh_list()
        self.gm_new_game()
        messagebox.showinfo("Deleted", f"Game '{title}' removed.")
    def gm_delete_override(self):
        # Legacy alias: catalog/override data is now unified in one JSON DB.
        self.gm_delete_game()
    def _refresh_fx_list(self, _evt=None):
        if not hasattr(self, "fx_list"):
            return
        q = self.fx_search.get().strip().lower()
        self.fx_list.delete(0, tk.END)
        title_key = self.game_title_key
        self.fx_title_to_rom = {}
        titles = []
        for row in self.game_rows:
            title = row.get(title_key, "") if title_key else ""
            if not title:
                continue
            if q and q not in title.lower():
                continue
            rom_key = self._row_rom_key(row, self.game_col_map, title_key)
            if not rom_key:
                continue
            label = title
            # Keep labels unique so selection resolves deterministically.
            if label in self.fx_title_to_rom and self.fx_title_to_rom[label] != rom_key:
                label = f"{title} [{rom_key}]"
            self.fx_title_to_rom[label] = rom_key
            titles.append(label)
        for label in sorted(titles, key=lambda s: str(s).lower()):
            self.fx_list.insert(tk.END, label)
        if self.fx_list.size() > 0:
            self.fx_list.selection_set(0)
            self._on_fx_select()
    def _on_fx_select(self, _evt=None):
        if not hasattr(self, "fx_list"):
            return
        sel = self.fx_list.curselection()
        if not sel:
            return
        title = self.fx_list.get(sel[0])
        rom_key = ""
        if isinstance(getattr(self, "fx_title_to_rom", None), dict):
            rom_key = self.fx_title_to_rom.get(title, "")
        if not rom_key:
            rom_key = self._rom_key_from_title(title)
        self.fx_selected_rom = rom_key
        entry = self.game_db.get(rom_key, {})
        self._load_controls_into_commander_preview(entry.get("controls", {}) or {}, apply_hardware=False)
        self._alu_preview_from_rom(rom_key)
        profile = entry.get("profile", {})
        self.fx_on_start_var.set(profile.get("fx_on_start", "") or "NONE")
        self.fx_on_end_var.set(profile.get("fx_on_end", "") or "NONE")
    def fx_apply_to_game(self):
        if not self.fx_selected_rom:
            messagebox.showinfo("No Game Selected", "Select a game to apply FX.")
            return
        entry = self.game_db.get(self.fx_selected_rom, {})
        entry["fx"] = {k: v.get() for k, v in self.fx_vars.items()}
        if self.fx_speed is not None:
            try:
                entry["speed"] = float(self.fx_speed.get())
            except Exception:
                entry["speed"] = 1.0
        self.game_db[self.fx_selected_rom] = entry
        self._save_game_db()
        messagebox.showinfo("Saved", f"FX saved for '{self.fx_selected_rom}'.")
    def fx_load_from_game(self):
        if not self.fx_selected_rom:
            messagebox.showinfo("No Game Selected", "Select a game to load FX.")
            return
        entry = self.game_db.get(self.fx_selected_rom, {})
        fx_id = entry.get("fx_id")
        if fx_id and self.fx_library:
            fx = self.fx_library.get_fx_by_id(fx_id)
            if fx:
                self.fx_lib_selected_id = fx_id
                self._fx_tab_library_sync_selection(fx_id)
                self.fx_editor_state["selected_fx"] = fx
                self._fx_apply_effect_to_ui(fx)
                editor_state = fx.get("main", {}).get("editor_state") if isinstance(fx.get("main", {}), dict) else None
                if not editor_state:
                    editor_state = (fx.get("meta", {}) or {}).get("editor_state")
                if editor_state:
                    self._fx_editor_apply_state(editor_state)
                selected = set(fx.get("applied_to") or [])
                if "grid_buttons" in self.fx_editor_state:
                    self.fx_editor_state["selected_buttons"] = set()
                    for k, btn in self.fx_editor_state.get("grid_buttons", {}).items():
                        is_sel = k in selected
                        if is_sel:
                            self.fx_editor_state["selected_buttons"].add(k)
                        if hasattr(btn, "set_selected"):
                            btn.set_selected(is_sel)
                if self.fx_editor_window and self.fx_editor_window.winfo_exists():
                    self._fx_library_refresh()
                    self._fx_editor_draw_preview()
                return
        fx_data = entry.get("fx", {})
        for k, v in self.fx_vars.items():
            v.set(bool(fx_data.get(k, False)))
        if self.fx_speed is not None:
            self.fx_speed.set(entry.get("speed", 1.0))
    def fx_save_start_end(self):
        if not self.fx_selected_rom:
            messagebox.showinfo("No Game Selected", "Select a game to save start/end FX.")
            return
        entry = self.game_db.get(self.fx_selected_rom, {})
        profile = entry.get("profile", {})
        start_fx = self.fx_on_start_var.get()
        end_fx = self.fx_on_end_var.get()
        profile["fx_on_start"] = "" if start_fx == "NONE" else start_fx
        profile["fx_on_end"] = "" if end_fx == "NONE" else end_fx
        entry["profile"] = profile
        self.game_db[self.fx_selected_rom] = entry
        self._save_game_db()
        messagebox.showinfo("Saved", f"Start/End FX saved for '{self.fx_selected_rom}'.")

    def apply_random_fx(self):
        if not hasattr(self, "fx_vars"):
            return
        try:
            intensity = float(self.random_fx_var.get())
        except Exception:
            intensity = 0.0
        keys = list(self.fx_vars.keys())
        if not keys:
            return
        if intensity <= 0.0:
            for v in self.fx_vars.values():
                v.set(False)
            return
        import random
        count = max(1, int(round(intensity * len(keys))))
        count = min(len(keys), count)
        random.shuffle(keys)
        chosen = set(keys[:count])
        for k, v in self.fx_vars.items():
            v.set(k in chosen)
        if self.fx_speed is not None:
            try:
                speed = random.uniform(0.5, 0.5 + (4.5 * intensity))
                self.fx_speed.set(round(speed, 2))
            except Exception:
                pass
    def _prepare_audio_wav(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext == ".wav":
            return path, None
        ffmpeg = shutil.which("ffmpeg")
        local_ffmpeg = asset_path("ffmpeg.exe") if os.name == "nt" else asset_path("ffmpeg")
        if os.path.exists(local_ffmpeg):
            ffmpeg = local_ffmpeg
        if not ffmpeg:
            raise RuntimeError("ffmpeg not found. Place ffmpeg.exe in assets or install ffmpeg.")
        try:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            wav_path = tmp.name
            tmp.close()
        except Exception as e:
            raise RuntimeError(f"Could not create temp WAV: {e}")
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            path,
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "44100",
            "-ac",
            "2",
            wav_path,
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception as e:
            try:
                os.unlink(wav_path)
            except Exception:
                pass
            raise RuntimeError(f"ffmpeg convert failed: {e}")
        return wav_path, wav_path
    def _cleanup_trimmed_preview_audio(self):
        if getattr(self, "audio_trim_preview_path", None):
            try:
                os.unlink(self.audio_trim_preview_path)
            except Exception:
                pass
            self.audio_trim_preview_path = None
            self.audio_trim_preview_key = None
    def _prepare_trimmed_preview_wav(self):
        wav_path = self.audio_wav_path
        if not wav_path or not os.path.exists(wav_path):
            return None
        start_ratio, end_ratio = self._fx_editor_trim_bounds()
        if start_ratio <= 0.0005 and end_ratio >= 0.9995:
            return wav_path
        trim_key = (os.path.abspath(wav_path), round(start_ratio, 5), round(end_ratio, 5))
        if self.audio_trim_preview_path and self.audio_trim_preview_key == trim_key and os.path.exists(self.audio_trim_preview_path):
            return self.audio_trim_preview_path
        self._cleanup_trimmed_preview_audio()
        # Deterministic trim path: direct frame slice from prepared WAV.
        try:
            with wave.open(wav_path, "rb") as src:
                fr = src.getframerate()
                total = src.getnframes()
                if total <= 0:
                    return None
                s_frame = int(start_ratio * total)
                e_frame = int(end_ratio * total)
                s_frame = max(0, min(total - 1, s_frame))
                e_frame = max(s_frame + 1, min(total, e_frame))
                if s_frame == 0 and e_frame >= total:
                    return wav_path
                src.setpos(s_frame)
                frames = src.readframes(e_frame - s_frame)
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                out_path = tmp.name
                tmp.close()
                with wave.open(out_path, "wb") as dst:
                    dst.setnchannels(src.getnchannels())
                    dst.setsampwidth(src.getsampwidth())
                    dst.setframerate(fr)
                    dst.writeframes(frames)
                self.audio_trim_preview_path = out_path
                self.audio_trim_preview_key = trim_key
                return out_path
        except Exception:
            return None
    def audio_load_wav(self):
        if not AUDIOFX_AVAILABLE:
            messagebox.showerror("Error", "AudioFXEngine not available.")
            return
        path = filedialog.askopenfilename(
            title="Select Audio/Video File",
            filetypes=[
                ("Audio/Video", "*.wav *.mp3 *.mp4"),
                ("WAV files", "*.wav"),
                ("MP3 files", "*.mp3"),
                ("MP4 files", "*.mp4"),
            ],
        )
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        if ext != ".wav":
            ffmpeg = shutil.which("ffmpeg")
            local_ffmpeg = asset_path("ffmpeg.exe") if os.name == "nt" else asset_path("ffmpeg")
            if os.path.exists(local_ffmpeg):
                ffmpeg = local_ffmpeg
            if not ffmpeg:
                self._cleanup_trimmed_preview_audio()
                self.audio_source_path = path
                self.audio_wav_path = None
                self.audio_tmp_path = None
                self.audio_analysis = None
                self.audio_sequence = None
                msg = f"Audio loaded (preview only): {os.path.basename(path)}"
                if hasattr(self, "audio_status"):
                    self.audio_status.set(msg)
                if "wave_status" in self.fx_editor_state:
                    self.fx_editor_state["wave_status"].set(msg)
                messagebox.showinfo("Preview Only", "ffmpeg not found. MP3/MP4 will preview only. Install ffmpeg or load a WAV to analyze.")
                return
        if self.audio_tmp_path:
            try:
                os.unlink(self.audio_tmp_path)
            except Exception:
                pass
            self.audio_tmp_path = None
        self._cleanup_trimmed_preview_audio()
        try:
            wav_path, tmp_path = self._prepare_audio_wav(path)
        except Exception as e:
            messagebox.showerror("Error", f"Unable to load audio:\n{e}")
            return
        self.audio_source_path = path
        self.audio_wav_path = wav_path
        self.audio_tmp_path = tmp_path
        self.audio_analysis = None
        self.audio_sequence = None
        if hasattr(self, "audio_status"):
            self.audio_status.set(f"Audio loaded: {os.path.basename(path)}")
        if "wave_status" in self.fx_editor_state:
            self.fx_editor_state["wave_status"].set(f"Audio loaded: {os.path.basename(path)}")
        # Build waveform preview immediately
        if self.audio_engine and self.audio_wav_path:
            try:
                self.audio_analysis = self.audio_engine.analyze_wav(self.audio_wav_path)
                if "wave_status" in self.fx_editor_state:
                    self.fx_editor_state["wave_status"].set("Waveform ready. Click BUILD SEQ for analysis.")
                if self.fx_editor_window and self.fx_editor_window.winfo_exists():
                    self._fx_editor_draw_waveform()
            except Exception:
                self.audio_analysis = None
    def audio_build_sequence(self):
        if not AUDIOFX_AVAILABLE or not self.audio_engine:
            messagebox.showerror("Error", "AudioFXEngine not available.")
            return
        if not self.audio_wav_path:
            if self.audio_source_path:
                messagebox.showinfo("Conversion Needed", "Load a WAV or install ffmpeg to analyze MP3/MP4.")
            else:
                messagebox.showinfo("No Audio", "Load an audio file first.")
            return
        try:
            self.audio_analysis = self.audio_engine.analyze_wav(self.audio_wav_path)
            trimmed = self._fx_editor_trim_analysis(self.audio_analysis)
            frame_count = len(trimmed.get("rms", []) or [])
            if frame_count < 2:
                messagebox.showinfo("Trim Too Small", "Selected trim range is too small. Increase trim window and try again.")
                return
            self.audio_sequence = self.audio_engine.build_sequence(trimmed)
            start, end = self._fx_editor_trim_bounds()
            meta = self.audio_sequence.get("meta", {}) if isinstance(self.audio_sequence.get("meta", {}), dict) else {}
            meta["trim_start_pct"] = round(start * 100.0, 2)
            meta["trim_end_pct"] = round(end * 100.0, 2)
            meta["trim_frames"] = int(frame_count)
            self.audio_sequence["meta"] = meta
            if hasattr(self, "audio_status"):
                self.audio_status.set(f"Sequence built from trimmed audio ({start*100:.1f}% - {end*100:.1f}%).")
            if "wave_status" in self.fx_editor_state:
                self.fx_editor_state["wave_status"].set(
                    f"Sequence built from trimmed audio ({start*100:.1f}% - {end*100:.1f}%), {frame_count} frames."
                )
            if self.fx_editor_window and self.fx_editor_window.winfo_exists():
                self._fx_editor_draw_waveform()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to analyze audio:\n{e}")
    def audio_save_to_game(self):
        if not self.fx_selected_rom:
            messagebox.showinfo("No Game Selected", "Select a game to save audio sequence.")
            return
        if not self.audio_sequence:
            messagebox.showinfo("No Sequence", "Build a sequence first.")
            return
        if not self.fx_library:
            messagebox.showerror("Error", "FX Library not available.")
            return
        name = simpledialog.askstring("Save Audio FX", "Effect name:")
        if not name:
            return
        effect = FXEffect(
            fx_id="",
            name=name,
            entrance=self.audio_sequence.get("entrance", {}),
            main=self.audio_sequence.get("main", {}),
            exit=self.audio_sequence.get("exit", {}),
            audio_path=os.path.basename(self.audio_source_path) if self.audio_source_path else (os.path.basename(self.audio_wav_path) if self.audio_wav_path else ""),
            applied_to=list(self.fx_assignments.keys()),
            meta={"source": "audio_sequence"},
        )
        fx_id = self.fx_library.save_fx(effect)
        entry = self.game_db.get(self.fx_selected_rom, {})
        entry["fx_id"] = fx_id
        self.game_db[self.fx_selected_rom] = entry
        self._save_game_db()
        self.fx_lib_selected_id = fx_id
        self._fx_tab_library_refresh()
        if hasattr(self, "audio_status"):
            self.audio_status.set(f"Saved audio FX '{name}' to library and assigned.")
    def open_fx_editor(self):
        if hasattr(self, "notebook") and hasattr(self, "tab_fx_editor"):
            self.notebook.select(self.tab_fx_editor)
    def build_fx_editor_tab(self):
        wrap = tk.Frame(self.tab_fx_editor, bg=COLORS["BG"])
        wrap.pack(fill="both", expand=True)
        self.fx_editor_window = self.tab_fx_editor
        self.fx_editor_state = {}
        self._build_fx_editor_ui(wrap)
    def build_controller_config_tab(self):
        wrap = tk.Frame(self.tab_controller, bg=COLORS["BG"])
        wrap.pack(fill="both", expand=True)

        header = tk.Frame(wrap, bg=COLORS["BG"])
        header.pack(fill="x", padx=20, pady=(16, 8))
        tk.Label(header, text="CONTROLLER CONFIG", bg=COLORS["BG"], fg=COLORS["SYS"],
                 font=("Segoe UI", 14, "bold")).pack(side="left")
        tk.Label(header, text="Tell us what hardware you have installed", bg=COLORS["BG"],
                 fg=COLORS["TEXT_DIM"], font=("Segoe UI", 9)).pack(side="left", padx=10)

        body = tk.Frame(wrap, bg=COLORS["BG"])
        body.pack(fill="both", expand=True, padx=20, pady=10)
        body.columnconfigure(0, weight=2)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)
        body.rowconfigure(2, weight=1)

        form = tk.LabelFrame(body, text=" CONFIGURATION ", bg=COLORS["CHARCOAL"], fg=COLORS["P1"],
                             font=("Segoe UI", 9, "bold"), padx=12, pady=10)
        form.grid(row=0, column=0, rowspan=3, sticky="nsew", padx=(0, 10))

        summary = tk.LabelFrame(body, text=" SUMMARY ", bg=COLORS["CHARCOAL"], fg=COLORS["SUCCESS"],
                                font=("Segoe UI", 9, "bold"), padx=12, pady=10)
        summary.grid(row=0, column=1, sticky="nsew")
        
        app_cfg = tk.LabelFrame(body, text=" APP SETTINGS ", bg=COLORS["CHARCOAL"], fg=COLORS["SYS"],
                                font=("Segoe UI", 9, "bold"), padx=12, pady=10)
        app_cfg.grid(row=1, column=1, sticky="nsew", pady=(10, 0))

        future_cfg = tk.LabelFrame(body, text=" FUTURE ENHANCEMENTS ", bg=COLORS["CHARCOAL"], fg=COLORS["P1"],
                                   font=("Segoe UI", 9, "bold"), padx=12, pady=10)
        future_cfg.grid(row=2, column=1, sticky="nsew", pady=(10, 0))

        cfg = self.controller_config or {}
        self.controller_vars = {
            "controller_type": tk.StringVar(value=cfg.get("controller_type", "PicoCTR")),
            "controller_style": tk.StringVar(value=cfg.get("controller_style", "Arcade Panel")),
            "players": tk.StringVar(value=str(cfg.get("players", 2))),
            "max_players": tk.StringVar(value=str(cfg.get("max_players", 8))),
            "buttons_per_player": tk.StringVar(value=str(cfg.get("buttons_per_player", 6))),
            "sticks_per_player": tk.StringVar(value=str(cfg.get("sticks_per_player", 1))),
            "triggers_per_player": tk.StringVar(value=str(cfg.get("triggers_per_player", 0))),
            "dpad_per_player": tk.StringVar(value=str(cfg.get("dpad_per_player", 1))),
            "include_start": tk.BooleanVar(value=cfg.get("include_start", True)),
            "include_coin": tk.BooleanVar(value=cfg.get("include_coin", True)),
            "trackball": tk.BooleanVar(value=cfg.get("trackball", True)),
            "spinner": tk.BooleanVar(value=cfg.get("spinner", False)),
            "pinball_left_flipper": tk.BooleanVar(value=cfg.get("pinball_left_flipper", False)),
            "pinball_left_nudge": tk.BooleanVar(value=cfg.get("pinball_left_nudge", False)),
            "pinball_right_flipper": tk.BooleanVar(value=cfg.get("pinball_right_flipper", False)),
            "pinball_right_nudge": tk.BooleanVar(value=cfg.get("pinball_right_nudge", False)),
            "led_enabled": tk.BooleanVar(value=cfg.get("led_enabled", True)),
        }

        self.app_config_vars = {
            "skip_splash": tk.BooleanVar(value=bool(self.app_settings.get("skip_splash", False))),
            "skip_startup_sound": tk.BooleanVar(value=bool(self.app_settings.get("skip_startup_sound", False))),
            "fx_editor_video_enabled": tk.BooleanVar(value=bool(self.app_settings.get("fx_editor_video_enabled", True))),
            "fx_editor_video_audio_enabled": tk.BooleanVar(value=bool(self.app_settings.get("fx_editor_video_audio_enabled", True))),
            "effects_enabled": tk.BooleanVar(value=bool(self.app_settings.get("effects_enabled", True))),
            "effects_preset_id": tk.StringVar(value=str(self.app_settings.get("effects_preset_id", "showroom_default"))),
        }
        preset_map = self.effects_preset_map if isinstance(self.effects_preset_map, dict) else {}
        preset_ids = list(preset_map.keys()) if preset_map else ["showroom_default"]
        preset_name_to_id = {p.name: pid for pid, p in preset_map.items()} if preset_map else {"Showroom Default": "showroom_default"}
        preset_id_to_name = {pid: p.name for pid, p in preset_map.items()} if preset_map else {"showroom_default": "Showroom Default"}
        if self.app_config_vars["effects_preset_id"].get() not in preset_ids:
            self.app_config_vars["effects_preset_id"].set("showroom_default")
        self.effects_preset_name_var = tk.StringVar(
            value=preset_id_to_name.get(self.app_config_vars["effects_preset_id"].get(), "Showroom Default")
        )
        self.effects_preset_desc_var = tk.StringVar(value="")

        def _refresh_preset_description():
            preset_id = self.app_config_vars["effects_preset_id"].get()
            preset = preset_map.get(preset_id) if preset_map else None
            if preset is None:
                self.effects_preset_desc_var.set("Preset unavailable.")
            else:
                self.effects_preset_desc_var.set(preset.description)

        def _save_app_settings():
            selected_name = self.effects_preset_name_var.get()
            selected_id = preset_name_to_id.get(selected_name, self.app_config_vars["effects_preset_id"].get())
            self.app_config_vars["effects_preset_id"].set(selected_id)
            data = {k: v.get() for k, v in self.app_config_vars.items()}
            self.app_settings.update(data)
            self.save_settings(data)
            self.effects_enabled = bool(data.get("effects_enabled", True))
            preset_id = str(data.get("effects_preset_id", "showroom_default"))
            if hasattr(self, "effects_engine") and self.effects_engine:
                self._apply_effects_preset(preset_id)
            _refresh_preset_description()
            if hasattr(self, "controller_status"):
                self.controller_status.config(text="App settings saved.")

        tk.Checkbutton(
            app_cfg, text="Skip splash screen",
            variable=self.app_config_vars["skip_splash"],
            bg=COLORS["CHARCOAL"], fg="white", selectcolor=COLORS["CHARCOAL"],
            command=_save_app_settings,
        ).pack(anchor="w", pady=2)
        tk.Checkbutton(
            app_cfg, text="Skip startup WAV",
            variable=self.app_config_vars["skip_startup_sound"],
            bg=COLORS["CHARCOAL"], fg="white", selectcolor=COLORS["CHARCOAL"],
            command=_save_app_settings,
        ).pack(anchor="w", pady=2)
        tk.Checkbutton(
            app_cfg, text="FX tab: play intro video",
            variable=self.app_config_vars["fx_editor_video_enabled"],
            bg=COLORS["CHARCOAL"], fg="white", selectcolor=COLORS["CHARCOAL"],
            command=_save_app_settings,
        ).pack(anchor="w", pady=2)
        tk.Checkbutton(
            app_cfg, text="FX tab: play intro audio",
            variable=self.app_config_vars["fx_editor_video_audio_enabled"],
            bg=COLORS["CHARCOAL"], fg="white", selectcolor=COLORS["CHARCOAL"],
            command=_save_app_settings,
        ).pack(anchor="w", pady=2)
        tk.Checkbutton(
            app_cfg, text="Enable default effects engine",
            variable=self.app_config_vars["effects_enabled"],
            bg=COLORS["CHARCOAL"], fg="white", selectcolor=COLORS["CHARCOAL"],
            command=_save_app_settings,
        ).pack(anchor="w", pady=(6, 2))
        tk.Label(
            app_cfg,
            text="Default effects preset",
            bg=COLORS["CHARCOAL"],
            fg=COLORS["TEXT_DIM"],
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w", pady=(6, 2))
        preset_combo = ttk.Combobox(
            app_cfg,
            textvariable=self.effects_preset_name_var,
            values=list(preset_name_to_id.keys()),
            state="readonly",
            width=24,
            font=("Consolas", 9),
        )
        preset_combo.pack(anchor="w", fill="x")
        preset_combo.bind("<<ComboboxSelected>>", lambda _e: _save_app_settings())
        tk.Label(
            app_cfg,
            textvariable=self.effects_preset_desc_var,
            bg=COLORS["CHARCOAL"],
            fg=COLORS["SYS"],
            wraplength=280,
            justify="left",
            font=("Segoe UI", 8),
        ).pack(anchor="w", fill="x", pady=(6, 0))
        _refresh_preset_description()

        future_wrap = tk.Frame(future_cfg, bg=COLORS["CHARCOAL"])
        future_wrap.pack(fill="both", expand=True)
        future_list = tk.Listbox(
            future_wrap,
            bg=COLORS["CHARCOAL"],
            fg="white",
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
            height=6,
            font=("Segoe UI", 9),
        )
        future_list.pack(side="left", fill="both", expand=True)
        future_scroll = tk.Scrollbar(future_wrap, orient="vertical", command=future_list.yview)
        self._style_scrollbar(future_scroll)
        future_scroll.pack(side="right", fill="y")
        future_list.configure(yscrollcommand=future_scroll.set)
        for line in (
            "\u2022 IPAC2 Controller Support",
            "\u2022 4 Player Control Decks",
            "\u2022 Enhanced Emulator Layout Tools",
            "\u2022 Auto-detect Controller Type",
            "\u2022 Per-Player Templates",
            "\u2022 Input Test Mode",
            "\u2022 Backup/Restore Config",
            "\u2022 Conflict Checker",
            "\u2022 Per-Emulator Overrides",
            "\u2022 Shift/Alt Button Layers",
            "\u2022 Deadzone/Sensitivity Tuning",
            "\u2022 LED Profile Linking",
            "\u2022 Cloud-Synced Profiles",
            "\u2022 Accessibility Options",
            "\u2022 Safe Mode Fallback",
        ):
            future_list.insert("end", line)

        def add_row(label, widget, row):
            tk.Label(form, text=label, bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"],
                     font=("Segoe UI", 9, "bold"), anchor="w", width=18).grid(row=row, column=0, sticky="w", pady=4)
            widget.grid(row=row, column=1, sticky="w", pady=4)

        ctrl_combo = ttk.Combobox(
            form,
            textvariable=self.controller_vars["controller_type"],
            values=("PicoCTR", "PicTor", "IPAC", "iPac2", "iPac4", "ALU 2P", "Keyboard Encoder", "Other"),
            state="readonly",
            width=18,
            font=("Consolas", 9),
        )
        add_row("Controller", ctrl_combo, 0)

        style_combo = ttk.Combobox(
            form,
            textvariable=self.controller_vars["controller_style"],
            values=("Arcade Panel", "Xbox/PS Style", "Hybrid", "Custom"),
            state="readonly",
            width=18,
            font=("Consolas", 9),
        )
        add_row("Style", style_combo, 1)

        players_combo = ttk.Combobox(
            form,
            textvariable=self.controller_vars["players"],
            values=("1", "2", "3", "4", "5", "6", "7", "8"),
            state="readonly",
            width=6,
            font=("Consolas", 9),
        )
        add_row("Players", players_combo, 2)

        max_players_combo = ttk.Combobox(
            form,
            textvariable=self.controller_vars["max_players"],
            values=("2", "4", "6", "8"),
            state="readonly",
            width=6,
            font=("Consolas", 9),
        )
        add_row("Max Players", max_players_combo, 3)

        buttons_combo = ttk.Combobox(
            form,
            textvariable=self.controller_vars["buttons_per_player"],
            values=("6", "8", "10"),
            state="readonly",
            width=6,
            font=("Consolas", 9),
        )
        add_row("Buttons/Player", buttons_combo, 4)

        sticks_combo = ttk.Combobox(
            form,
            textvariable=self.controller_vars["sticks_per_player"],
            values=("0", "1", "2"),
            state="readonly",
            width=6,
            font=("Consolas", 9),
        )
        add_row("Sticks/Player", sticks_combo, 5)

        triggers_combo = ttk.Combobox(
            form,
            textvariable=self.controller_vars["triggers_per_player"],
            values=("0", "2"),
            state="readonly",
            width=6,
            font=("Consolas", 9),
        )
        add_row("Triggers/Player", triggers_combo, 6)

        dpad_combo = ttk.Combobox(
            form,
            textvariable=self.controller_vars["dpad_per_player"],
            values=("0", "1"),
            state="readonly",
            width=6,
            font=("Consolas", 9),
        )
        add_row("D-Pad/Player", dpad_combo, 7)

        tk.Checkbutton(
            form, text="Include START buttons",
            variable=self.controller_vars["include_start"],
            bg=COLORS["CHARCOAL"], fg="white", selectcolor=COLORS["CHARCOAL"]
        ).grid(row=8, column=0, columnspan=2, sticky="w", pady=2)
        tk.Checkbutton(
            form, text="Include COIN buttons",
            variable=self.controller_vars["include_coin"],
            bg=COLORS["CHARCOAL"], fg="white", selectcolor=COLORS["CHARCOAL"]
        ).grid(row=9, column=0, columnspan=2, sticky="w", pady=2)

        extras = tk.LabelFrame(form, text=" EXTRAS ", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"],
                               font=("Segoe UI", 8, "bold"), padx=8, pady=6)
        extras.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(6, 4))
        tk.Checkbutton(extras, text="Trackball", variable=self.controller_vars["trackball"],
                       bg=COLORS["CHARCOAL"], fg="white", selectcolor=COLORS["CHARCOAL"]).grid(row=0, column=0, sticky="w")
        tk.Checkbutton(extras, text="Spinner", variable=self.controller_vars["spinner"],
                       bg=COLORS["CHARCOAL"], fg="white", selectcolor=COLORS["CHARCOAL"]).grid(row=0, column=1, sticky="w", padx=(10, 0))
        tk.Checkbutton(extras, text="L Flipper", variable=self.controller_vars["pinball_left_flipper"],
                       bg=COLORS["CHARCOAL"], fg="white", selectcolor=COLORS["CHARCOAL"]).grid(row=1, column=0, sticky="w")
        tk.Checkbutton(extras, text="L Nudge", variable=self.controller_vars["pinball_left_nudge"],
                       bg=COLORS["CHARCOAL"], fg="white", selectcolor=COLORS["CHARCOAL"]).grid(row=1, column=1, sticky="w", padx=(10, 0))
        tk.Checkbutton(extras, text="R Flipper", variable=self.controller_vars["pinball_right_flipper"],
                       bg=COLORS["CHARCOAL"], fg="white", selectcolor=COLORS["CHARCOAL"]).grid(row=2, column=0, sticky="w")
        tk.Checkbutton(extras, text="R Nudge", variable=self.controller_vars["pinball_right_nudge"],
                       bg=COLORS["CHARCOAL"], fg="white", selectcolor=COLORS["CHARCOAL"]).grid(row=2, column=1, sticky="w", padx=(10, 0))

        tk.Checkbutton(
            form, text="Buttons are LED enabled",
            variable=self.controller_vars["led_enabled"],
            bg=COLORS["CHARCOAL"], fg="white", selectcolor=COLORS["CHARCOAL"]
        ).grid(row=11, column=0, columnspan=2, sticky="w", pady=(4, 0))

        tk.Label(form, text="Notes", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"],
                 font=("Segoe UI", 9, "bold")).grid(row=12, column=0, sticky="nw", pady=(8, 0))
        self.controller_notes = tk.Text(form, height=5, bg=COLORS["SURFACE"], fg="white", borderwidth=0, wrap="word")
        self.controller_notes.grid(row=12, column=1, sticky="ew", pady=(8, 0))
        self.controller_notes.insert("1.0", cfg.get("notes", ""))

        form.columnconfigure(1, weight=1)

        btn_row = tk.Frame(summary, bg=COLORS["CHARCOAL"])
        btn_row.pack(side="bottom", fill="x", pady=(8, 0))
        ModernButton(btn_row, text="SAVE CONFIG", bg=COLORS["SYS"], fg="black", width=12,
                     font=("Segoe UI", 8, "bold"), command=self.save_controller_config).pack(side="left")
        ModernButton(btn_row, text="RELOAD", bg=COLORS["SURFACE_LIGHT"], fg="white", width=10,
                     font=("Segoe UI", 8, "bold"), command=self._controller_reload).pack(side="left", padx=6)
        self.controller_status = tk.Label(btn_row, text="", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8))
        self.controller_status.pack(side="left", padx=8)

        self.controller_summary = tk.StringVar(value="")
        tk.Label(summary, textvariable=self.controller_summary, bg=COLORS["CHARCOAL"], fg="white",
                 font=("Segoe UI", 9), justify="left", anchor="nw").pack(fill="both", expand=True)

        for v in self.controller_vars.values():
            v.trace_add("write", lambda *_: self._controller_update_summary())
        self._controller_update_summary()

    def _controller_reload(self):
        self.controller_config = self.load_controller_config()
        cfg = self.controller_config
        for k, var in self.controller_vars.items():
            if isinstance(var, tk.BooleanVar):
                var.set(bool(cfg.get(k, var.get())))
            else:
                var.set(str(cfg.get(k, var.get())))
        if hasattr(self, "controller_notes"):
            self.controller_notes.delete("1.0", "end")
            self.controller_notes.insert("1.0", cfg.get("notes", ""))
        if hasattr(self, "controller_status"):
            self.controller_status.config(text="Reloaded.")

    def _controller_update_summary(self):
        if not hasattr(self, "controller_vars"):
            return
        try:
            players = int(self.controller_vars["players"].get())
            max_players = int(self.controller_vars["max_players"].get())
            buttons = int(self.controller_vars["buttons_per_player"].get())
            sticks = int(self.controller_vars["sticks_per_player"].get())
            triggers = int(self.controller_vars["triggers_per_player"].get())
            dpad = int(self.controller_vars["dpad_per_player"].get())
        except Exception:
            players, max_players, buttons, sticks, triggers, dpad = 0, 0, 0, 0, 0, 0
        start = players if self.controller_vars["include_start"].get() else 0
        coin = players if self.controller_vars["include_coin"].get() else 0
        extras = []
        if self.controller_vars["trackball"].get(): extras.append("Trackball")
        if self.controller_vars["spinner"].get(): extras.append("Spinner")
        if self.controller_vars["pinball_left_flipper"].get(): extras.append("L Flipper")
        if self.controller_vars["pinball_left_nudge"].get(): extras.append("L Nudge")
        if self.controller_vars["pinball_right_flipper"].get(): extras.append("R Flipper")
        if self.controller_vars["pinball_right_nudge"].get(): extras.append("R Nudge")
        total_buttons = (players * buttons) + start + coin + len(extras)
        total_axes = (players * sticks * 2) + (players * triggers)
        total_dpads = players * dpad
        extras_text = ", ".join(extras) if extras else "None"
        led_text = "Yes" if self.controller_vars["led_enabled"].get() else "No"
        self.controller_summary.set(
            f"Controller: {self.controller_vars['controller_type'].get()}\n"
            f"Style: {self.controller_vars['controller_style'].get()}\n"
            f"Players: {players}\n"
            f"Max Players: {max_players}\n"
            f"Buttons/Player: {buttons}\n"
            f"Sticks/Player: {sticks}\n"
            f"Triggers/Player: {triggers}\n"
            f"D-Pad/Player: {dpad}\n"
            f"Start buttons: {start}\n"
            f"Coin buttons: {coin}\n"
            f"Extras: {extras_text}\n"
            f"LED Enabled: {led_text}\n"
            f"Estimated buttons: {total_buttons}\n"
            f"Estimated axes: {total_axes}\n"
            f"Estimated dpads: {total_dpads}"
        )
    def _build_fx_editor_ui(self, parent):
        body = tk.Frame(parent, bg=COLORS["BG"])
        body.pack(fill="both", expand=True, padx=16, pady=(8, 10))
        body.columnconfigure(0, weight=2)
        body.columnconfigure(1, weight=2, minsize=280)
        body.rowconfigure(0, weight=1)

        sidebar = None

        controls = tk.LabelFrame(body, text=" MODULATION ", bg=COLORS["CHARCOAL"], fg=COLORS["FX"], font=("Segoe UI", 9, "bold"), padx=10, pady=8)
        controls.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        assign = tk.LabelFrame(body, text=" ASSIGNMENTS ", bg=COLORS["CHARCOAL"], fg=COLORS["SUCCESS"], font=("Segoe UI", 9, "bold"), padx=10, pady=8)
        assign.grid(row=0, column=1, sticky="nsew")

        # Modulation content is intentionally non-scrollable per UI request.

        # FX Library + Game Library (moved into Assignments)
        libs = tk.Frame(assign, bg=COLORS["CHARCOAL"])
        libs.pack(fill="x")
        lib_box = tk.LabelFrame(libs, text=" LIBRARY ", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"],
                                font=("Segoe UI", 8, "bold"), padx=6, pady=6)
        lib_box.pack(side="left", fill="both", expand=True, padx=(0, 8))
        lib_notebook = ttk.Notebook(lib_box)
        lib_notebook.pack(fill="both", expand=True)
        fx_box = tk.Frame(lib_notebook, bg=COLORS["CHARCOAL"])
        anim_tab = tk.Frame(lib_notebook, bg=COLORS["CHARCOAL"])
        lib_notebook.add(fx_box, text="Effects")
        lib_notebook.add(anim_tab, text="Animations")
        self.fx_editor_state["lib_search_var"] = tk.StringVar(value="")
        self.fx_editor_state["lib_filter_var"] = tk.StringVar(value="all")
        sb_search = tk.Frame(fx_box, bg=COLORS["CHARCOAL"])
        sb_search.pack(fill="x", pady=(0, 6))
        tk.Entry(sb_search, textvariable=self.fx_editor_state["lib_search_var"], bg=COLORS["SURFACE_LIGHT"], fg="white",
                 borderwidth=0, font=("Consolas", 9)).pack(side="left", fill="x", expand=True)
        ttk.Combobox(
            sb_search,
            textvariable=self.fx_editor_state["lib_filter_var"],
            values=("all", "audio", "presets"),
            state="readonly",
            width=10,
            font=("Consolas", 8),
        ).pack(side="right", padx=(6, 0))
        ModernButton(sb_search, text="REFRESH", bg=COLORS["SURFACE_LIGHT"], fg="white", width=8,
                     font=("Segoe UI", 8, "bold"), command=self._fx_library_refresh).pack(side="right", padx=(6, 0))

        lib_actions = tk.Frame(fx_box, bg=COLORS["CHARCOAL"])
        lib_actions.pack(fill="x", pady=(0, 6))
        ModernButton(lib_actions, text="IMPORT", bg=COLORS["SURFACE_LIGHT"], fg="white", width=8,
                     font=("Segoe UI", 8, "bold"), command=self._fx_library_import).pack(side="left", padx=(0, 6))
        ModernButton(lib_actions, text="EXPORT", bg=COLORS["SURFACE_LIGHT"], fg="white", width=8,
                     font=("Segoe UI", 8, "bold"), command=self._fx_library_export).pack(side="left", padx=(0, 6))
        ModernButton(lib_actions, text="DELETE", bg=COLORS["DANGER"], fg="white", width=8,
                     font=("Segoe UI", 8, "bold"), command=self._fx_library_delete).pack(side="left")

        sb_list_wrap = tk.Frame(fx_box, bg=COLORS["CHARCOAL"], height=120)
        sb_list_wrap.pack(fill="x", pady=(0, 2))
        sb_list_wrap.pack_propagate(False)
        self.fx_editor_state["lib_list"] = tk.Listbox(
            sb_list_wrap, bg=COLORS["SURFACE_LIGHT"], fg="white", borderwidth=0, highlightthickness=0,
            selectbackground=COLORS["P1"], selectforeground="black", font=("Segoe UI", 9), height=5
        )
        self.fx_editor_state["lib_list"].pack(side="left", fill="both", expand=True)
        sb_vsb = ttk.Scrollbar(sb_list_wrap, orient="vertical", style="AC.Vertical.TScrollbar", command=self.fx_editor_state["lib_list"].yview)
        self._style_scrollbar(sb_vsb)
        sb_vsb.pack(side="right", fill="y")
        self.fx_editor_state["lib_list"].configure(yscrollcommand=sb_vsb.set)
        self.fx_editor_state["lib_list"].bind("<<ListboxSelect>>", self._fx_library_select)
        self.fx_editor_state["lib_list"].bind("<Double-Button-1>", self._fx_editor_load_selected_fx)
        self.fx_editor_state["lib_list"].bind("<Button-3>", self._fx_library_context_menu)
        self.fx_editor_state["lib_list"].bind("<Button-1>", self._fx_library_start_drag)
        self.fx_editor_state["lib_list"].bind("<B1-Motion>", self._fx_library_drag_motion)
        self.fx_editor_state["lib_list"].bind("<ButtonRelease-1>", self._fx_library_drop)
        self.fx_editor_state["lib_search_var"].trace_add("write", lambda *_: self._fx_library_refresh())
        self.fx_editor_state["lib_filter_var"].trace_add("write", lambda *_: self._fx_library_refresh())

        sb_actions = tk.Frame(fx_box, bg=COLORS["CHARCOAL"])
        sb_actions.pack(fill="x", pady=(6, 0))
        ModernButton(
            sb_actions,
            text="LOAD",
            bg=COLORS["SYS"],
            fg="black",
            width=8,
            font=("Segoe UI", 8, "bold"),
            command=self._fx_editor_load_selected_fx,
        ).pack(side="left")
        ModernButton(
            sb_actions,
            text="PREVIEW",
            bg=COLORS["P1"],
            fg="black",
            width=8,
            font=("Segoe UI", 8, "bold"),
            command=self._fx_editor_preview_selected_fx,
        ).pack(side="left", padx=(6, 0))

        game_box = tk.LabelFrame(assign, text=" GAME LIBRARY ", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"],
                                 font=("Segoe UI", 8, "bold"), padx=6, pady=6)
        game_box.pack(side="bottom", fill="x", pady=(8, 0))
        self.fx_search = tk.Entry(game_box, bg=COLORS["SURFACE_LIGHT"], fg="white", borderwidth=0, font=("Consolas", 9))
        self.fx_search.pack(fill="x", pady=(0, 6))
        self.fx_search.bind("<KeyRelease>", self._refresh_fx_list)
        game_list_wrap = tk.Frame(game_box, bg=COLORS["CHARCOAL"], height=120)
        game_list_wrap.pack(fill="x")
        game_list_wrap.pack_propagate(False)
        self.fx_list = tk.Listbox(game_list_wrap, bg=COLORS["SURFACE_LIGHT"], fg="white", borderwidth=0, highlightthickness=0,
                                  selectbackground=COLORS["P1"], selectforeground="black", font=("Segoe UI", 9), height=5)
        self.fx_list.pack(side="left", fill="x", expand=True)
        game_vsb = ttk.Scrollbar(game_list_wrap, orient="vertical", style="AC.Vertical.TScrollbar", command=self.fx_list.yview)
        self._style_scrollbar(game_vsb)
        game_vsb.pack(side="right", fill="y")
        self.fx_list.configure(yscrollcommand=game_vsb.set)
        self.fx_list.bind("<<ListboxSelect>>", self._on_fx_select)

        game_btns = tk.Frame(game_box, bg=COLORS["CHARCOAL"])
        game_btns.pack(fill="x", pady=(6, 0))
        ModernButton(game_btns, text="APPLY FX", bg=COLORS["SYS"], fg="black", width=8,
                     font=("Segoe UI", 8, "bold"), command=self.fx_apply_to_game).pack(side="left", padx=(0, 6))
        ModernButton(game_btns, text="LOAD FX", bg=COLORS["SURFACE_LIGHT"], fg="white", width=8,
                     font=("Segoe UI", 8, "bold"), command=self.fx_load_from_game).pack(side="left")

        assign_game = tk.Frame(game_box, bg=COLORS["CHARCOAL"])
        assign_game.pack(fill="x", pady=(8, 0))
        tk.Label(assign_game, text="FX Start:", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            assign_game,
            textvariable=self.fx_on_start_var,
            values=("NONE",) + self._get_shared_effect_options(),
            state="readonly",
            font=("Consolas", 8),
            width=14,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))
        tk.Label(assign_game, text="FX End:", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Combobox(
            assign_game,
            textvariable=self.fx_on_end_var,
            values=("NONE",) + self._get_shared_effect_options(),
            state="readonly",
            font=("Consolas", 8),
            width=14,
        ).grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=(6, 0))
        assign_game.columnconfigure(1, weight=1)
        ModernButton(
            assign_game,
            text="SAVE START/END",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=14,
            font=("Segoe UI", 8, "bold"),
            command=self.fx_save_start_end,
        ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        # Timeline canvas + scrubber (compact)
        tl_canvas = tk.Canvas(controls, bg=COLORS["SURFACE"], highlightthickness=0, height=54)
        tl_canvas.pack(fill="x", pady=(0, 8))
        self.fx_editor_state["timeline_canvas"] = tl_canvas
        self.fx_editor_state["scrub_x"] = 20
        self._fx_editor_draw_timeline()
        tl_canvas.bind("<Button-1>", self._fx_editor_scrub)
        tl_canvas.bind("<B1-Motion>", self._fx_editor_scrub)
        tl_canvas.bind("<Configure>", lambda _e: self._fx_editor_draw_timeline())
        # Preview controls: split to two rows so controls don't clip.
        tl_controls = tk.Frame(controls, bg=COLORS["CHARCOAL"])
        tl_controls.pack(fill="x", pady=(8, 0))
        tl_controls_row1 = tk.Frame(tl_controls, bg=COLORS["CHARCOAL"])
        tl_controls_row1.pack(fill="x")
        tl_controls_row2 = tk.Frame(tl_controls, bg=COLORS["CHARCOAL"])
        tl_controls_row2.pack(fill="x", pady=(6, 0))
        self.fx_editor_state["play_wav_var"] = tk.BooleanVar(value=False)
        tk.Checkbutton(
            tl_controls_row1,
            text="Play WAV on Preview",
            variable=self.fx_editor_state["play_wav_var"],
            bg=COLORS["CHARCOAL"],
            fg="white",
            selectcolor=COLORS["CHARCOAL"],
            font=("Segoe UI", 8),
        ).pack(side="left")
        ModernButton(tl_controls_row1, text="PREVIEW", bg=COLORS["P1"], fg="black", width=10,
                     font=("Segoe UI", 8, "bold"), command=self._fx_editor_preview_button).pack(side="left", padx=6)
        ModernButton(tl_controls_row1, text="ALL OFF", bg=COLORS["DANGER"], fg="white", width=10,
                     font=("Segoe UI", 8, "bold"), command=self._fx_editor_all_off).pack(side="left")
        ModernButton(tl_controls_row1, text="GLOBAL OFF", bg=COLORS["DANGER"], fg="white", width=11,
                     font=("Segoe UI", 8, "bold"), command=self._fx_editor_all_off_global).pack(side="left", padx=(6, 0))
        tk.Label(tl_controls_row2, text="Color Mode", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(side="left", padx=(0, 6))
        self.fx_editor_state["preview_color_mode"] = tk.StringVar(value="Assigned Cycle")
        ttk.Combobox(
            tl_controls_row2,
            textvariable=self.fx_editor_state["preview_color_mode"],
            values=("Audio", "Assigned Cycle", "Assigned Pulse", "Assigned Random", "Primary Only"),
            state="readonly",
            font=("Consolas", 8),
            width=24,
        ).pack(side="left", fill="x", expand=True)
        self.fx_editor_state["preview_duration"] = 6.0

        # Waveform + WAV controls (merged into Modulation)
        wf_top = tk.Frame(controls, bg=COLORS["CHARCOAL"])
        wf_top.pack(fill="x", pady=(0, 6))
        ModernButton(
            wf_top,
            text="LOAD WAV",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=10,
            font=("Segoe UI", 8, "bold"),
            command=self.audio_load_wav,
        ).pack(side="left")
        ModernButton(
            wf_top,
            text="BUILD SEQ",
            bg=COLORS["SYS"],
            fg="black",
            width=10,
            font=("Segoe UI", 8, "bold"),
            command=self.audio_build_sequence,
        ).pack(side="left", padx=(6, 0))
        ModernButton(
            wf_top,
            text="SAVE TO LIB",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=12,
            font=("Segoe UI", 8, "bold"),
            command=self.fx_save_to_library,
        ).pack(side="left", padx=(6, 0))
        self.fx_editor_state["wave_status"] = tk.StringVar(value="No WAV loaded.")
        tk.Label(wf_top, textvariable=self.fx_editor_state["wave_status"], bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8)).pack(side="right")

        wf_canvas = tk.Canvas(controls, bg=COLORS["SURFACE"], highlightthickness=0, height=102)
        wf_canvas.pack(fill="x", pady=(0, 8))
        self.fx_editor_state["wave_canvas"] = wf_canvas
        self._fx_editor_draw_waveform()
        wf_canvas.bind("<Configure>", lambda _e: self._fx_editor_draw_waveform())

        trim_row = tk.Frame(controls, bg=COLORS["CHARCOAL"])
        trim_row.pack(fill="x", pady=(0, 8))
        self.fx_editor_state["trim_start_var"] = tk.DoubleVar(value=0.0)
        self.fx_editor_state["trim_end_var"] = tk.DoubleVar(value=100.0)
        tk.Label(trim_row, text="Trim Start", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(side="left")
        trim_start = tk.Scale(
            trim_row,
            from_=0.0,
            to=100.0,
            resolution=1.0,
            orient="horizontal",
            bg=COLORS["CHARCOAL"],
            fg="white",
            showvalue=0,
            length=140,
            variable=self.fx_editor_state["trim_start_var"],
            command=self._fx_editor_set_trim_start,
        )
        trim_start.pack(side="left", padx=(6, 10))
        tk.Label(trim_row, text="Trim End", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(side="left")
        trim_end = tk.Scale(
            trim_row,
            from_=0.0,
            to=100.0,
            resolution=1.0,
            orient="horizontal",
            bg=COLORS["CHARCOAL"],
            fg="white",
            showvalue=0,
            length=140,
            variable=self.fx_editor_state["trim_end_var"],
            command=self._fx_editor_set_trim_end,
        )
        trim_end.pack(side="left", padx=(6, 0))

        # Waveform types + preview graphs
        types = tk.LabelFrame(controls, text=" WAVE TYPES ", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"],
                              font=("Segoe UI", 8, "bold"), padx=8, pady=6)
        types.pack(fill="x", pady=(0, 8))
        types.columnconfigure(0, weight=1, uniform="wave_cols")
        types.columnconfigure(1, weight=1, uniform="wave_cols")
        self.fx_editor_state["wave_types"] = [
            ("Sine", "Pure, smooth, and mellow.", "Low-frequency hums, soft bubbles, or gentle UI \"pings.\""),
            ("Square", "Hollow, \"woody,\" and buzzy.", "Classic 8-bit NES-style melodies and lead synth sounds."),
            ("Sawtooth", "Harsh, bright, and biting.", "Aggressive \"power-up\" sounds, sirens, or heavy engine roars."),
            ("Triangle", "Muted and flute-like.", "Soft basslines or \"sub\" impacts that aren't as harsh as square waves."),
            ("Noise", "Static, chaotic, and \"shhh\" sound.", "Explosions, wind, footsteps, and snare drum effects."),
        ]
        self.fx_editor_state["wave_type_var"] = tk.StringVar(value="Sine")
        self.fx_editor_state["anim_wave_type_var"] = tk.StringVar(value="Sine")

        fx_wave_panel = tk.Frame(types, bg=COLORS["CHARCOAL"])
        fx_wave_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        tk.Label(fx_wave_panel, text="FX WAVE", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        ttk.Combobox(
            fx_wave_panel,
            textvariable=self.fx_editor_state["wave_type_var"],
            values=[t[0] for t in self.fx_editor_state["wave_types"]],
            state="readonly",
            font=("Consolas", 8),
            width=12,
        ).pack(anchor="w", pady=(2, 2))
        fx_type_info = tk.Label(fx_wave_panel, text="", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8))
        fx_type_info.pack(anchor="w")
        self.fx_editor_state["wave_type_info"] = fx_type_info
        fx_type_canvas = tk.Canvas(fx_wave_panel, bg=COLORS["SURFACE"], width=260, height=55, highlightthickness=0)
        fx_type_canvas.pack(fill="x", pady=(2, 0))
        self.fx_editor_state["wave_type_canvas"] = fx_type_canvas

        anim_wave_panel = tk.Frame(types, bg=COLORS["CHARCOAL"])
        anim_wave_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        tk.Label(anim_wave_panel, text="ANIMATION WAVE", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        ttk.Combobox(
            anim_wave_panel,
            textvariable=self.fx_editor_state["anim_wave_type_var"],
            values=[t[0] for t in self.fx_editor_state["wave_types"]],
            state="readonly",
            font=("Consolas", 8),
            width=12,
        ).pack(anchor="w", pady=(2, 2))
        anim_type_info = tk.Label(anim_wave_panel, text="", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8))
        anim_type_info.pack(anchor="w")
        self.fx_editor_state["anim_wave_type_info"] = anim_type_info
        anim_type_canvas = tk.Canvas(anim_wave_panel, bg=COLORS["SURFACE"], width=260, height=55, highlightthickness=0)
        anim_type_canvas.pack(fill="x", pady=(2, 0))
        self.fx_editor_state["anim_wave_type_canvas"] = anim_type_canvas

        fx_type_canvas.bind("<Configure>", lambda _e: self._fx_editor_draw_wave_type())
        anim_type_canvas.bind("<Configure>", lambda _e: self._fx_editor_draw_wave_type())
        self.fx_editor_state["wave_type_var"].trace_add("write", lambda *_: self._fx_editor_apply_wave_defaults("fx"))
        self.fx_editor_state["anim_wave_type_var"].trace_add("write", lambda *_: self._fx_editor_apply_wave_defaults("anim"))
        self._fx_editor_draw_wave_type()

        sliders = tk.Frame(controls, bg=COLORS["CHARCOAL"])
        sliders.pack(fill="x", pady=(4, 0))
        sliders.columnconfigure(0, weight=1, uniform="fx_sliders")
        sliders.columnconfigure(1, weight=1, uniform="fx_sliders")

        fx_sliders = tk.Frame(sliders, bg=COLORS["CHARCOAL"])
        fx_sliders.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        tk.Label(fx_sliders, text="EFFECTS", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 2))
        anim_sliders = tk.Frame(sliders, bg=COLORS["CHARCOAL"])
        anim_sliders.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        tk.Label(anim_sliders, text="ANIMATION", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 2))

        # Presets apply to FX effect settings (left column).
        preset_slot = tk.Frame(fx_sliders, bg=COLORS["CHARCOAL"], height=28)
        preset_slot.pack(fill="x", pady=(0, 6))
        preset_slot.pack_propagate(False)
        preset_row = tk.Frame(preset_slot, bg=COLORS["CHARCOAL"])
        preset_row.pack(fill="both", expand=True)
        tk.Label(preset_row, text="Preset", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(side="left")
        self.fx_editor_state["preset_var"] = tk.StringVar(value="")
        preset_combo = ttk.Combobox(
            preset_row,
            textvariable=self.fx_editor_state["preset_var"],
            values=tuple(self.fx_presets.keys()),
            state="readonly",
            font=("Consolas", 8),
            width=14,
        )
        preset_combo.pack(side="left", padx=6, fill="x", expand=True)
        ModernButton(preset_row, text="APPLY", bg=COLORS["SYS"], fg="black", width=6,
                     font=("Segoe UI", 8, "bold"), command=self._fx_editor_apply_preset).pack(side="right")

        # Keep right column vertically aligned with left (preset row lives on FX side).
        anim_top_spacer = tk.Frame(anim_sliders, bg=COLORS["CHARCOAL"], height=28)
        anim_top_spacer.pack(fill="x", pady=(0, 6))
        anim_top_spacer.pack_propagate(False)

        self.fx_editor_state["rate_var"] = tk.DoubleVar(value=1.0)
        self.fx_editor_state["intensity_var"] = tk.DoubleVar(value=1.0)
        self.fx_editor_state["stagger_var"] = tk.DoubleVar(value=0.0)
        self.fx_editor_state["width_var"] = tk.DoubleVar(value=0.50)
        self.fx_editor_state["bias_var"] = tk.DoubleVar(value=0.00)
        self.fx_editor_state["width_bias_lock_var"] = tk.BooleanVar(value=False)
        fx_dials = tk.Frame(fx_sliders, bg=COLORS["CHARCOAL"])
        fx_dials.pack(fill="x", pady=(0, 4))
        CompactDial(
            fx_dials,
            text="Rate",
            variable=self.fx_editor_state["rate_var"],
            from_=0.1,
            to=3.0,
            resolution=0.1,
            accent=COLORS["P1"],
        ).pack(side="left", padx=(0, 8))
        CompactDial(
            fx_dials,
            text="Intensity",
            variable=self.fx_editor_state["intensity_var"],
            from_=0.1,
            to=2.0,
            resolution=0.1,
            accent=COLORS["SYS"],
        ).pack(side="left")
        tk.Scale(fx_sliders, from_=0.0, to=1.0, resolution=0.05, orient="horizontal",
                 label="Stagger", variable=self.fx_editor_state["stagger_var"], bg=COLORS["CHARCOAL"], fg="white").pack(fill="x", pady=(0, 6))
        tk.Scale(fx_sliders, from_=0.05, to=0.95, resolution=0.05, orient="horizontal",
                 label="Width", variable=self.fx_editor_state["width_var"], bg=COLORS["CHARCOAL"], fg="white").pack(fill="x", pady=(0, 6))
        tk.Scale(fx_sliders, from_=0.0, to=0.80, resolution=0.05, orient="horizontal",
                 label="Bias", variable=self.fx_editor_state["bias_var"], bg=COLORS["CHARCOAL"], fg="white").pack(fill="x", pady=(0, 6))
        tk.Checkbutton(
            fx_sliders,
            text="Lock Width/Bias",
            variable=self.fx_editor_state["width_bias_lock_var"],
            bg=COLORS["CHARCOAL"],
            fg="white",
            selectcolor=COLORS["CHARCOAL"],
            font=("Segoe UI", 8),
            command=self._fx_editor_draw_wave_type,
        ).pack(anchor="w", pady=(0, 4))
        tk.Label(fx_sliders, text="Curve", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(4, 2))
        self.fx_editor_state["curve_var"] = tk.StringVar(value="Linear")
        ttk.Combobox(
            fx_sliders,
            textvariable=self.fx_editor_state["curve_var"],
            values=("Linear", "Ease-In", "Bounce"),
            state="readonly",
            font=("Consolas", 8),
        ).pack(fill="x")

        self.fx_editor_state["anim_rate_var"] = tk.DoubleVar(value=1.0)
        self.fx_editor_state["anim_intensity_var"] = tk.DoubleVar(value=1.0)
        self.fx_editor_state["anim_stagger_var"] = tk.DoubleVar(value=0.0)
        self.fx_editor_state["anim_width_var"] = tk.DoubleVar(value=0.50)
        self.fx_editor_state["anim_bias_var"] = tk.DoubleVar(value=0.00)
        self.fx_editor_state["anim_width_bias_lock_var"] = tk.BooleanVar(value=False)
        anim_dials = tk.Frame(anim_sliders, bg=COLORS["CHARCOAL"])
        anim_dials.pack(fill="x", pady=(0, 4))
        CompactDial(
            anim_dials,
            text="Rate",
            variable=self.fx_editor_state["anim_rate_var"],
            from_=0.1,
            to=3.0,
            resolution=0.1,
            accent=COLORS["P2"],
        ).pack(side="left", padx=(0, 8))
        CompactDial(
            anim_dials,
            text="Intensity",
            variable=self.fx_editor_state["anim_intensity_var"],
            from_=0.1,
            to=2.0,
            resolution=0.1,
            accent=COLORS["SYS"],
        ).pack(side="left")
        tk.Scale(anim_sliders, from_=0.0, to=1.0, resolution=0.05, orient="horizontal",
                 label="Stagger", variable=self.fx_editor_state["anim_stagger_var"], bg=COLORS["CHARCOAL"], fg="white").pack(fill="x", pady=(0, 6))
        tk.Scale(anim_sliders, from_=0.05, to=0.95, resolution=0.05, orient="horizontal",
                 label="Width", variable=self.fx_editor_state["anim_width_var"], bg=COLORS["CHARCOAL"], fg="white").pack(fill="x", pady=(0, 6))
        tk.Scale(anim_sliders, from_=0.0, to=0.80, resolution=0.05, orient="horizontal",
                 label="Bias", variable=self.fx_editor_state["anim_bias_var"], bg=COLORS["CHARCOAL"], fg="white").pack(fill="x", pady=(0, 6))
        tk.Checkbutton(
            anim_sliders,
            text="Lock Width/Bias",
            variable=self.fx_editor_state["anim_width_bias_lock_var"],
            bg=COLORS["CHARCOAL"],
            fg="white",
            selectcolor=COLORS["CHARCOAL"],
            font=("Segoe UI", 8),
            command=self._fx_editor_draw_wave_type,
        ).pack(anchor="w", pady=(0, 4))
        tk.Label(anim_sliders, text="Curve", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(4, 2))
        self.fx_editor_state["anim_curve_var"] = tk.StringVar(value="Linear")
        ttk.Combobox(
            anim_sliders,
            textvariable=self.fx_editor_state["anim_curve_var"],
            values=("Linear", "Ease-In", "Bounce"),
            state="readonly",
            font=("Consolas", 8),
        ).pack(fill="x")
        self.fx_editor_state["width_var"].trace_add("write", lambda *_: self._fx_editor_draw_wave_type())
        self.fx_editor_state["bias_var"].trace_add("write", lambda *_: self._fx_editor_draw_wave_type())
        self.fx_editor_state["anim_width_var"].trace_add("write", lambda *_: self._fx_editor_draw_wave_type())
        self.fx_editor_state["anim_bias_var"].trace_add("write", lambda *_: self._fx_editor_draw_wave_type())
        self._fx_editor_apply_wave_defaults("fx", force=True)
        self._fx_editor_apply_wave_defaults("anim", force=True)
        # QUICK FX controls were removed from FX Editor.
        # Quick templates now live in FX Library (RAINBOW/BREATH/STROBE/FADE).

        # Assignment grid
        assign_top = tk.Frame(assign, bg=COLORS["CHARCOAL"])
        assign_top.pack(fill="x")
        tk.Label(assign_top, text="Assign To:", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(side="left")
        self.fx_editor_state["assign_var"] = tk.StringVar(value="Full Range")
        ttk.Combobox(
            assign_top,
            textvariable=self.fx_editor_state["assign_var"],
            values=("Bass", "Mid", "Treble", "Sine", "Full Range"),
            state="readonly",
            font=("Consolas", 8),
            width=10,
        ).pack(side="left", padx=6)
        tk.Label(assign_top, text="Group:", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(side="left", padx=(10, 4))
        self.fx_editor_state["assign_group_var"] = tk.StringVar(value="All")
        ttk.Combobox(
            assign_top,
            textvariable=self.fx_editor_state["assign_group_var"],
            values=("Selected", "Player 1", "Player 2", "Admin", "All"),
            state="readonly",
            font=("Consolas", 8),
            width=10,
        ).pack(side="left")
        ModernButton(assign_top, text="ASSIGN", bg=COLORS["SYS"], fg="black", width=8,
                     font=("Segoe UI", 8, "bold"), command=self._fx_editor_assign).pack(side="left", padx=6)
        ModernButton(assign_top, text="PREVIEW", bg=COLORS["P1"], fg="black", width=8,
                     font=("Segoe UI", 8, "bold"), command=self._fx_editor_assign_preview).pack(side="left")
        tk.Label(
            assign_top,
            text="Button colors are set on Commander Tab",
            bg=COLORS["CHARCOAL"],
            fg=COLORS["SYS"],
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left", padx=(8, 0))

        grid = tk.Frame(assign, bg=COLORS["CHARCOAL"])
        grid.pack(fill="x", expand=False, pady=8)
        self.fx_editor_state["grid_buttons"] = {}
        keys = []
        if hasattr(self, "cab"):
            raw_keys = list(self.cab.LEDS.keys())
            p1_order = ["P1_A", "P1_B", "P1_C", "P1_X", "P1_Y", "P1_Z", "P1_START"]
            p2_order = ["P2_A", "P2_B", "P2_C", "P2_X", "P2_Y", "P2_Z", "P2_START"]
            sys_order = ["MENU", "REWIND", "TRACKBALL"]
            ordered = [k for k in (p1_order + p2_order + sys_order) if k in raw_keys]
            remaining = [k for k in raw_keys if k not in ordered]
            keys = ordered + remaining
        for i, key in enumerate(keys):
            r, c = divmod(i, 6)
            label = key.replace("P1_", "").replace("P2_", "")
            btn = MultiColorButton(grid, text=label, width=8, height=1, bg=COLORS["SURFACE_LIGHT"])
            if key in self.led_state:
                self._ensure_color_slots(key)
                cols = [self._rgb_to_hex(*c) for c in self.led_state[key]['colors']]
                btn.set_colors(cols)
            btn.grid(row=r, column=c, padx=4, pady=4, sticky="nsew")
            btn.bind("<Button-1>", lambda e, k=key: self._fx_editor_toggle_button(k))
            btn.bind("<Button-3>", lambda e, k=key: self.show_context_menu(e, k))
            btn.canvas.bind("<Button-1>", lambda e, k=key: self._fx_editor_toggle_button(k))
            btn.canvas.bind("<Button-3>", lambda e, k=key: self.show_context_menu(e, k))
            self.fx_editor_state["grid_buttons"][key] = btn
        for c in range(6):
            grid.columnconfigure(c, weight=1)

        # FX Quick Test (LED-only preview)
        quick = tk.LabelFrame(assign, text=" FX QUICK TEST ", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"],
                              font=("Segoe UI", 9, "bold"), padx=10, pady=8)
        quick.pack(fill="x", pady=(0, 8))
        preview_canvas = tk.Canvas(quick, height=190, bg=COLORS["SURFACE"], highlightthickness=0)
        preview_canvas.pack(fill="x")
        self.fx_editor_state["preview_canvas"] = preview_canvas
        preview_canvas.bind("<Configure>", lambda _e: self._fx_editor_draw_preview())
        self._fx_editor_draw_preview()

        # Animation library/editor in unified Library -> Animations tab.
        anim_catalog = tk.LabelFrame(anim_tab, text=" ANIMATION CATALOG ", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"],
                                     font=("Segoe UI", 9, "bold"), padx=10, pady=8)
        anim_catalog.pack(fill="both", expand=True, pady=(2, 2))
        anim_cols = tk.Frame(anim_catalog, bg=COLORS["CHARCOAL"])
        anim_cols.pack(fill="x")
        left_col = tk.Frame(anim_cols, bg=COLORS["CHARCOAL"])
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right_col = tk.Frame(anim_cols, bg=COLORS["CHARCOAL"])
        right_col.pack(side="left", fill="both", expand=True)

        # Built-in animation catalog (registry)
        catalog_list = tk.Listbox(left_col, bg=COLORS["SURFACE_LIGHT"], fg="white", borderwidth=0, highlightthickness=0,
                                  selectbackground=COLORS["P1"], selectforeground="black", font=("Segoe UI", 9), height=5)
        catalog_list.pack(side="left", fill="both", expand=True, padx=(0, 6))
        catalog_vsb = tk.Scrollbar(left_col, orient="vertical", command=catalog_list.yview)
        catalog_vsb.pack(side="right", fill="y")
        catalog_list.configure(yscrollcommand=catalog_vsb.set)
        catalog_info = tk.Label(left_col, text="", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8),
                                wraplength=260, justify="left")
        catalog_info.pack(fill="x", pady=(6, 0))
        self.fx_editor_state["anim_catalog_list"] = catalog_list

        # Animation library (custom)
        lib_label = tk.Label(right_col, text="LIBRARY", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold"))
        lib_label.pack(anchor="w")
        anim_lib_list = tk.Listbox(right_col, bg=COLORS["SURFACE_LIGHT"], fg="white", borderwidth=0, highlightthickness=0,
                                   selectbackground=COLORS["P1"], selectforeground="black", font=("Segoe UI", 9), height=5)
        anim_lib_list.pack(side="left", fill="both", expand=True, padx=(0, 6))
        anim_lib_vsb = tk.Scrollbar(right_col, orient="vertical", command=anim_lib_list.yview)
        anim_lib_vsb.pack(side="right", fill="y")
        anim_lib_list.configure(yscrollcommand=anim_lib_vsb.set)
        self.fx_editor_state["anim_lib_list"] = anim_lib_list

        btn_row = tk.Frame(anim_catalog, bg=COLORS["CHARCOAL"])
        btn_row.pack(fill="x", pady=(6, 0))
        ModernButton(
            btn_row,
            text="APPLY ANIM",
            bg=COLORS["SYS"],
            fg="black",
            width=10,
            font=("Segoe UI", 8, "bold"),
            command=self._fx_editor_apply_anim_from_catalog,
        ).pack(side="left")

        tk.Label(btn_row, text="Event", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(side="left", padx=(10, 4))
        self.fx_editor_state["event_type_var"] = tk.StringVar(value="GAME_START")
        ttk.Combobox(
            btn_row,
            textvariable=self.fx_editor_state["event_type_var"],
            values=(
                "FE_START",
                "FE_QUIT",
                "SCREENSAVER_START",
                "SCREENSAVER_STOP",
                "LIST_CHANGE",
                "GAME_START",
                "GAME_QUIT",
                "GAME_PAUSE",
                "AUDIO_ANIMATION",
                "SPEAK_CONTROLS",
                "DEFAULT",
            ),
            state="readonly",
            width=12,
            font=("Consolas", 8),
        ).pack(side="left")
        tk.Label(btn_row, text="Anim", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(side="left", padx=(10, 4))
        self.fx_editor_state["event_anim_var"] = tk.StringVar(value="RAINBOW")
        ttk.Combobox(
            btn_row,
            textvariable=self.fx_editor_state["event_anim_var"],
            values=self._get_shared_effect_options(),
            state="readonly",
            width=14,
            font=("Consolas", 8),
        ).pack(side="left")
        tk.Label(btn_row, text="Dur(s)", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(side="left", padx=(10, 4))
        self.fx_editor_state["event_dur_var"] = tk.DoubleVar(value=3.0)
        tk.Entry(btn_row, textvariable=self.fx_editor_state["event_dur_var"], width=8, bg=COLORS["SURFACE_LIGHT"], fg="white",
                 font=("Consolas", 8), borderwidth=0).pack(side="left")
        ModernButton(
            btn_row,
            text="ADD TO ANIM",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=11,
            font=("Segoe UI", 8, "bold"),
            command=self._fx_editor_add_event_to_animation,
        ).pack(side="left", padx=(8, 0))
        ModernButton(
            btn_row,
            text="TRIGGER",
            bg=COLORS["P1"],
            fg="black",
            width=8,
            font=("Segoe UI", 8, "bold"),
            command=self._fx_editor_trigger_event_preview,
        ).pack(side="left", padx=(6, 0))
        ModernButton(
            btn_row,
            text="BAKE AUDIO",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=10,
            font=("Segoe UI", 8, "bold"),
            command=self._fx_editor_bake_audio_to_animation,
        ).pack(side="left", padx=(6, 0))

        name_row = tk.Frame(anim_catalog, bg=COLORS["CHARCOAL"])
        name_row.pack(fill="x", pady=(6, 0))
        tk.Label(name_row, text="Animation Name", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).pack(side="left")
        self.fx_editor_state["anim_name_var"] = tk.StringVar(value="")
        tk.Entry(name_row, textvariable=self.fx_editor_state["anim_name_var"], bg=COLORS["SURFACE_LIGHT"], fg="white",
                 font=("Consolas", 8), borderwidth=0).pack(side="left", fill="x", expand=True, padx=(6, 6))
        ModernButton(
            name_row,
            text="SAVE ANIM",
            bg=COLORS["SYS"],
            fg="black",
            width=10,
            font=("Segoe UI", 8, "bold"),
            command=self._fx_editor_save_animation,
        ).pack(side="left")

        def _catalog_select(_evt=None):
            sel = catalog_list.curselection()
            if not sel:
                return
            key = catalog_list.get(sel[0])
            aliases = list_aliases(key) if ANIM_REGISTRY_AVAILABLE else []
            alias_txt = ", ".join(aliases) if aliases else "â€”"
            catalog_info.config(text=f"Aliases: {alias_txt}")

        def _anim_lib_select(_evt=None):
            sel = anim_lib_list.curselection()
            if not sel:
                return
            name = anim_lib_list.get(sel[0])
            self.fx_editor_state["selected_animation_name"] = name
            self._fx_editor_draw_timeline()

        catalog_list.bind("<<ListboxSelect>>", _catalog_select)
        anim_lib_list.bind("<<ListboxSelect>>", _anim_lib_select)
        items = list_supported(None) if ANIM_REGISTRY_AVAILABLE else SUPPORTED_ANIMATIONS
        for k in items:
            catalog_list.insert(tk.END, k)
        self._fx_editor_refresh_animation_library()

        # Preview block removed (redundant)
        self._fx_library_refresh()
        self._fx_library_bind_hover()
        self._refresh_fx_list()
    def _fx_editor_draw_timeline(self):
        c = self.fx_editor_state.get("timeline_canvas")
        if not c:
            return
        c.delete("all")
        w = c.winfo_width() if c.winfo_width() > 1 else 600
        h = c.winfo_height() if c.winfo_height() > 1 else 24
        compact = h < 40
        thirds = [0, w * 0.25, w * 0.75, w]
        # If an animation is selected, compute segment widths from durations
        anim_name = self.fx_editor_state.get("selected_animation_name")
        if anim_name and isinstance(self.animation_library, dict):
            anim = self.animation_library.get(anim_name, {})
            events = anim.get("events", {})
            start_dur = sum(e.get("duration", 0) for e in events.get("GAME_START", [])) + sum(e.get("duration", 0) for e in events.get("FE_START", []))
            end_dur = sum(e.get("duration", 0) for e in events.get("GAME_QUIT", [])) + sum(e.get("duration", 0) for e in events.get("FE_QUIT", []))
            main_dur = sum(e.get("duration", 0) for e in events.get("DEFAULT", [])) + sum(e.get("duration", 0) for e in events.get("SCREENSAVER_START", []))
            total = max(0.1, start_dur + main_dur + end_dur)
            thirds = [0, w * (start_dur / total), w * ((start_dur + main_dur) / total), w]
        top = 4 if compact else 10
        bottom = h - 4 if compact else h - 10
        c.create_rectangle(thirds[0], top, thirds[1], bottom, fill="#303030", outline="")
        c.create_rectangle(thirds[1], top, thirds[2], bottom, fill="#3a3a3a", outline="")
        c.create_rectangle(thirds[2], top, thirds[3], bottom, fill="#303030", outline="")
        label_font = ("Segoe UI", 8 if not compact else 7, "bold")
        c.create_text((thirds[0] + thirds[1]) / 2.0, (top + bottom) / 2.0, anchor="center",
                      text="Entrance", fill=COLORS["TEXT_DIM"], font=label_font)
        c.create_text((thirds[1] + thirds[2]) / 2.0, (top + bottom) / 2.0, anchor="center",
                      text="Main", fill=COLORS["TEXT_DIM"], font=label_font)
        c.create_text((thirds[2] + thirds[3]) / 2.0, (top + bottom) / 2.0, anchor="center",
                      text="Exit", fill=COLORS["TEXT_DIM"], font=label_font)
        if self.fx_editor_state.get("preview_active"):
            start_ts = self.fx_editor_state.get("preview_start_ts", time.time())
            duration = float(self.fx_editor_state.get("preview_duration", 6.0))
            elapsed = max(0.0, time.time() - start_ts)
            if not compact:
                c.create_text(w - 8, 18, anchor="ne",
                              text=f"Preview {elapsed:.1f}s / {duration:.1f}s",
                              fill=COLORS["SYS"], font=("Segoe UI", 8, "bold"))
        x = self.fx_editor_state.get("scrub_x", 20)
        c.create_line(x, top, x, bottom, fill=COLORS["SYS"], width=2)
        if compact:
            c.create_oval(x - 3, top - 1, x + 3, top + 5, fill=COLORS["SYS"], outline="")
        else:
            c.create_oval(x - 4, 6, x + 4, 14, fill=COLORS["SYS"], outline="")
    def _fx_editor_scrub(self, event):
        c = self.fx_editor_state.get("timeline_canvas")
        if not c:
            return
        w = c.winfo_width()
        x = max(10, min(w - 10, event.x))
        self.fx_editor_state["scrub_x"] = x
        self._fx_editor_draw_timeline()
    def _fx_editor_set_trim_start(self, val):
        try:
            v = float(val) / 100.0
        except Exception:
            return
        end = float(self.fx_editor_state.get("trim_end_var").get()) / 100.0 if "trim_end_var" in self.fx_editor_state else 1.0
        if v >= end:
            v = max(0.0, end - 0.01)
            self.fx_editor_state["trim_start_var"].set(v * 100.0)
        self._cleanup_trimmed_preview_audio()
        self._fx_editor_draw_waveform()
    def _fx_editor_set_trim_end(self, val):
        try:
            v = float(val) / 100.0
        except Exception:
            return
        start = float(self.fx_editor_state.get("trim_start_var").get()) / 100.0 if "trim_start_var" in self.fx_editor_state else 0.0
        if v <= start:
            v = min(1.0, start + 0.01)
            self.fx_editor_state["trim_end_var"].set(v * 100.0)
        self._cleanup_trimmed_preview_audio()
        self._fx_editor_draw_waveform()
    def _fx_editor_trim_bounds(self):
        start = float(self.fx_editor_state.get("trim_start_var").get()) / 100.0 if "trim_start_var" in self.fx_editor_state else 0.0
        end = float(self.fx_editor_state.get("trim_end_var").get()) / 100.0 if "trim_end_var" in self.fx_editor_state else 1.0
        start = max(0.0, min(1.0, start))
        end = max(0.0, min(1.0, end))
        if end <= start:
            end = min(1.0, start + 0.01)
        return start, end
    def _fx_editor_trim_analysis(self, analysis):
        if not analysis:
            return analysis
        rms = analysis.get("rms", [])
        if not rms:
            return analysis
        n = len(rms)
        start, end = self._fx_editor_trim_bounds()
        s_idx = int(start * n)
        e_idx = int(end * n)
        s_idx = max(0, min(n - 1, s_idx))
        e_idx = max(s_idx + 1, min(n, e_idx))
        if e_idx <= s_idx:
            e_idx = min(n, s_idx + 1)
        def _slice(arr):
            if not arr:
                return []
            return arr[s_idx:e_idx]
        trimmed = dict(analysis)
        trimmed["rms"] = _slice(analysis.get("rms", []))
        trimmed["bass"] = _slice(analysis.get("bass", []))
        trimmed["mid"] = _slice(analysis.get("mid", []))
        trimmed["treble"] = _slice(analysis.get("treble", []))
        onsets = [i - s_idx for i in analysis.get("onsets", []) if s_idx <= i < e_idx]
        beats = [i - s_idx for i in analysis.get("beats", []) if s_idx <= i < e_idx]
        trimmed["onsets"] = onsets
        trimmed["beats"] = beats
        return trimmed
    def _fx_editor_draw_waveform(self):
        c = self.fx_editor_state.get("wave_canvas")
        if not c:
            return
        c.delete("all")
        w = c.winfo_width() if c.winfo_width() > 1 else 600
        h = c.winfo_height() if c.winfo_height() > 1 else 200
        c.create_text(10, 10, anchor="nw", text="Load a WAV to visualize waveform", fill=COLORS["TEXT_DIM"], font=("Segoe UI", 8))
        if not self.audio_analysis:
            return
        rms = self.audio_analysis.get("rms", [])
        bass = self.audio_analysis.get("bass", [])
        mid = self.audio_analysis.get("mid", [])
        treble = self.audio_analysis.get("treble", [])
        if not rms:
            return
        def draw_series(series, color):
            step = max(1, int(len(series) / w))
            pts = []
            for i in range(0, len(series), step):
                x = int((i / max(1, len(series) - 1)) * (w - 20)) + 10
                y = h - 10 - int(series[i] * (h - 30))
                pts.append((x, y))
            for i in range(1, len(pts)):
                c.create_line(pts[i - 1][0], pts[i - 1][1], pts[i][0], pts[i][1], fill=color, width=1)
        start, end = self._fx_editor_trim_bounds()
        left_x = int(start * (w - 20)) + 10
        right_x = int(end * (w - 20)) + 10
        # Shade trimmed-out area
        if left_x > 10:
            c.create_rectangle(10, 0, left_x, h, fill="#000000", stipple="gray50", outline="")
        if right_x < w - 10:
            c.create_rectangle(right_x, 0, w - 10, h, fill="#000000", stipple="gray50", outline="")
        c.create_text(
            w - 10,
            10,
            anchor="ne",
            text=f"Trim {start*100:.1f}% - {end*100:.1f}%",
            fill=COLORS["SYS"],
            font=("Segoe UI", 8, "bold"),
        )
        draw_series(rms, "#888888")
        draw_series(bass, "#00E5FF")
        draw_series(mid, "#FFB300")
        draw_series(treble, "#FF0055")
        # Trim markers
        c.create_line(left_x, 8, left_x, h - 8, fill=COLORS["SYS"], width=2)
        c.create_line(right_x, 8, right_x, h - 8, fill=COLORS["SYS"], width=2)
    def _fx_editor_draw_wave_type(self):
        tname = self.fx_editor_state.get("wave_type_var").get() if self.fx_editor_state else "Sine"
        anim_tname = self.fx_editor_state.get("anim_wave_type_var").get() if self.fx_editor_state else "Sine"
        types = {t[0]: t for t in self.fx_editor_state.get("wave_types", [])}
        fx_info = types.get(tname)
        anim_info = types.get(anim_tname)
        if fx_info and "wave_type_info" in self.fx_editor_state:
            self.fx_editor_state["wave_type_info_full"] = f"{fx_info[1]} - {fx_info[2]}"
        if anim_info and "anim_wave_type_info" in self.fx_editor_state:
            self.fx_editor_state["anim_wave_type_info_full"] = f"{anim_info[1]} - {anim_info[2]}"

        fx_width = float(self.fx_editor_state.get("width_var").get()) if "width_var" in self.fx_editor_state else 0.5
        fx_bias = float(self.fx_editor_state.get("bias_var").get()) if "bias_var" in self.fx_editor_state else 0.0
        anim_width = float(self.fx_editor_state.get("anim_width_var").get()) if "anim_width_var" in self.fx_editor_state else 0.5
        anim_bias = float(self.fx_editor_state.get("anim_bias_var").get()) if "anim_bias_var" in self.fx_editor_state else 0.0

        def _draw_canvas(canvas, wave_name, width=0.5, bias=0.0):
            if not canvas:
                return
            canvas.delete("all")
            w = canvas.winfo_width() if canvas.winfo_width() > 1 else 260
            h = canvas.winfo_height() if canvas.winfo_height() > 1 else 110
            canvas.create_line(8, h // 2, w - 8, h // 2, fill="#333333")
            pts = []
            left = 8
            right = max(left + 1, w - 8)
            span = right - left
            for x in range(left, right + 1):
                phase = (x - left) / max(1, span)
                v = self._fx_editor_modulation_value(
                    phase,
                    index=0,
                    rate=1.0,
                    intensity=1.0,
                    stagger=0.0,
                    curve_type="Linear",
                    wave_type=wave_name,
                    width=width,
                    bias=bias,
                )
                y = int((h - 12) - (v * (h - 24)))
                pts.extend([x, y])
            if len(pts) >= 4:
                canvas.create_line(*pts, fill="#00E5FF", width=2, smooth=(wave_name != "Square"))

        _draw_canvas(self.fx_editor_state.get("wave_type_canvas"), tname, fx_width, fx_bias)
        _draw_canvas(self.fx_editor_state.get("anim_wave_type_canvas"), anim_tname, anim_width, anim_bias)
        self._fx_editor_tick_wave_info_marquee()
    def _fx_editor_wave_defaults(self, wave_name):
        name = str(wave_name or "Sine").strip().title()
        defaults = {
            "Sine": (0.65, 0.20),
            "Square": (0.78, 0.24),
            "Sawtooth": (0.70, 0.18),
            "Triangle": (0.64, 0.18),
            "Noise": (0.78, 0.26),
        }
        return defaults.get(name, (0.65, 0.20))
    def _fx_editor_apply_wave_defaults(self, scope="fx", force=False):
        if scope == "anim":
            wave = self.fx_editor_state.get("anim_wave_type_var").get() if "anim_wave_type_var" in self.fx_editor_state else "Sine"
            width_var = self.fx_editor_state.get("anim_width_var")
            bias_var = self.fx_editor_state.get("anim_bias_var")
            lock_var = self.fx_editor_state.get("anim_width_bias_lock_var")
        else:
            wave = self.fx_editor_state.get("wave_type_var").get() if "wave_type_var" in self.fx_editor_state else "Sine"
            width_var = self.fx_editor_state.get("width_var")
            bias_var = self.fx_editor_state.get("bias_var")
            lock_var = self.fx_editor_state.get("width_bias_lock_var")
        if (not force) and lock_var is not None and bool(lock_var.get()):
            self._fx_editor_draw_wave_type()
            return
        width, bias = self._fx_editor_wave_defaults(wave)
        try:
            if width_var is not None:
                width_var.set(float(width))
            if bias_var is not None:
                bias_var.set(float(bias))
        except Exception:
            pass
        self._fx_editor_draw_wave_type()

    def _fx_editor_tick_wave_info_marquee(self):
        fx_label = self.fx_editor_state.get("wave_type_info")
        anim_label = self.fx_editor_state.get("anim_wave_type_info")
        fx_text = self.fx_editor_state.get("wave_type_info_full", "")
        anim_text = self.fx_editor_state.get("anim_wave_type_info_full", "")

        def _scroll_text(label, full_text, key):
            if not label:
                return
            if not full_text:
                label.config(text="")
                return
            width_chars = max(24, int(label.winfo_width() / 7)) if label.winfo_width() > 0 else 48
            if len(full_text) <= width_chars:
                label.config(text=full_text)
                self.fx_editor_state[key] = 0
                return
            offset = int(self.fx_editor_state.get(key, 0))
            padded = full_text + "    "
            roll = padded + padded
            start = offset % len(padded)
            label.config(text=roll[start:start + width_chars])
            self.fx_editor_state[key] = offset + 1

        _scroll_text(fx_label, fx_text, "wave_type_info_offset")
        _scroll_text(anim_label, anim_text, "anim_wave_type_info_offset")

        win = self.fx_editor_window
        if win and win.winfo_exists():
            if self.fx_editor_state.get("wave_info_marquee_job"):
                try:
                    win.after_cancel(self.fx_editor_state.get("wave_info_marquee_job"))
                except Exception:
                    pass
            self.fx_editor_state["wave_info_marquee_job"] = win.after(220, self._fx_editor_tick_wave_info_marquee)
    def _fx_editor_modulation_value(
        self,
        t,
        index=0,
        rate=1.0,
        intensity=1.0,
        stagger=0.0,
        curve_type="Linear",
        wave_type="Sine",
        width=0.5,
        bias=0.0,
    ):
        phase = (t * rate + index * stagger) % 1.0
        width = max(0.05, min(0.95, float(width)))
        bias = max(0.0, min(0.9, float(bias)))

        # Width controls duty/shape by allocating more phase time to the "high" section.
        if phase < width:
            shaped_phase = 0.5 * (phase / width)
        else:
            shaped_phase = 0.5 + 0.5 * ((phase - width) / max(1e-6, (1.0 - width)))

        if wave_type == "Square":
            v = 1.0 if phase < width else 0.0
        elif wave_type == "Sawtooth":
            v = shaped_phase
        elif wave_type == "Triangle":
            v = 2 * shaped_phase if shaped_phase < 0.5 else 2 * (1 - shaped_phase)
        elif wave_type == "Noise":
            v = random.random()
        else:
            v = (math.sin(shaped_phase * 2 * math.pi) + 1.0) / 2.0

        if curve_type == "Ease-In":
            v = v * v
        elif curve_type == "Bounce":
            v = abs(math.sin(v * math.pi))

        v = max(0.0, min(1.0, v * intensity))
        # Bias lifts the floor so LEDs never drop fully dark.
        v = bias + (1.0 - bias) * v
        v = max(0.0, min(1.0, v))
        return v

    def _fx_editor_get_fx_modulation(self):
        wave_type = (self.fx_editor_state.get("wave_type_var").get() if "wave_type_var" in self.fx_editor_state else "Sine")
        curve_type = (self.fx_editor_state.get("curve_var").get() if "curve_var" in self.fx_editor_state else "Linear")
        rate = float(self.fx_editor_state.get("rate_var").get()) if "rate_var" in self.fx_editor_state else 1.0
        intensity = float(self.fx_editor_state.get("intensity_var").get()) if "intensity_var" in self.fx_editor_state else 1.0
        stagger = float(self.fx_editor_state.get("stagger_var").get()) if "stagger_var" in self.fx_editor_state else 0.0
        width = float(self.fx_editor_state.get("width_var").get()) if "width_var" in self.fx_editor_state else 0.5
        bias = float(self.fx_editor_state.get("bias_var").get()) if "bias_var" in self.fx_editor_state else 0.0
        return rate, intensity, stagger, curve_type, wave_type, width, bias

    def _fx_editor_get_anim_modulation(self):
        wave_type = (self.fx_editor_state.get("anim_wave_type_var").get() if "anim_wave_type_var" in self.fx_editor_state else "Sine")
        curve_type = (self.fx_editor_state.get("anim_curve_var").get() if "anim_curve_var" in self.fx_editor_state else "Linear")
        rate = float(self.fx_editor_state.get("anim_rate_var").get()) if "anim_rate_var" in self.fx_editor_state else 1.0
        intensity = float(self.fx_editor_state.get("anim_intensity_var").get()) if "anim_intensity_var" in self.fx_editor_state else 1.0
        stagger = float(self.fx_editor_state.get("anim_stagger_var").get()) if "anim_stagger_var" in self.fx_editor_state else 0.0
        width = float(self.fx_editor_state.get("anim_width_var").get()) if "anim_width_var" in self.fx_editor_state else 0.5
        bias = float(self.fx_editor_state.get("anim_bias_var").get()) if "anim_bias_var" in self.fx_editor_state else 0.0
        return rate, intensity, stagger, curve_type, wave_type, width, bias

    def _fx_editor_apply_modulation(self, col, mod_value):
        if not col or not isinstance(col, str) or not col.startswith("#") or len(col) != 7:
            return col
        try:
            r0 = int(col[1:3], 16); g0 = int(col[3:5], 16); b0 = int(col[5:7], 16)
            r = int(max(0, min(255, r0 * mod_value)))
            g = int(max(0, min(255, g0 * mod_value)))
            b = int(max(0, min(255, b0 * mod_value)))
            return self._rgb_to_hex(r, g, b)
        except Exception:
            return col
    def _fx_editor_audio_drive_level(self, bass, mid, treble, brightness=1.0, assignment="full range"):
        try:
            b = max(0.0, min(1.0, float(bass)))
            m = max(0.0, min(1.0, float(mid)))
            t = max(0.0, min(1.0, float(treble)))
            br = max(0.0, min(1.0, float(brightness)))
        except Exception:
            return 0.0
        a = str(assignment or "").strip().lower()
        if a == "bass":
            raw = b
        elif a == "mid":
            raw = m
        elif a == "treble":
            raw = t
        else:
            # Full-range: blend average + peak so transients and body both show.
            raw = (b + m + t) / 3.0
            raw = max(raw, max(b, m, t) * 0.85)
        # Compand + gain + floor to keep lights visibly driven by audio.
        companded = math.sqrt(max(0.0, raw))
        boosted = min(1.0, companded * 1.45)
        floor = 0.18
        driven = floor + (1.0 - floor) * boosted
        return max(0.0, min(1.0, driven * br))
    def _fx_editor_toggle_button(self, key):
        selected = self.fx_editor_state.setdefault("selected_buttons", set())
        if key in selected:
            selected.remove(key)
            if hasattr(self.fx_editor_state["grid_buttons"][key], "set_selected"):
                self.fx_editor_state["grid_buttons"][key].set_selected(False)
        else:
            selected.add(key)
            if hasattr(self.fx_editor_state["grid_buttons"][key], "set_selected"):
                self.fx_editor_state["grid_buttons"][key].set_selected(True)
    def _fx_editor_assign(self, notify=True):
        selected = self.fx_editor_state.get("selected_buttons", set())
        group = self.fx_editor_state["assign_var"].get()
        group_sel = self.fx_editor_state.get("assign_group_var").get() if "assign_group_var" in self.fx_editor_state else "Selected"
        if group_sel == "Player 1":
            selected = {k for k in self.fx_editor_state.get("grid_buttons", {}).keys() if k.startswith("P1_")}
        elif group_sel == "Player 2":
            selected = {k for k in self.fx_editor_state.get("grid_buttons", {}).keys() if k.startswith("P2_")}
        elif group_sel == "Admin":
            selected = {k for k in self.fx_editor_state.get("grid_buttons", {}).keys() if not k.startswith("P1_") and not k.startswith("P2_")}
        elif group_sel == "All":
            selected = set(self.fx_editor_state.get("grid_buttons", {}).keys())
        if not selected:
            if notify:
                messagebox.showinfo("No Selection", "Select buttons to assign.")
            return
        for k in selected:
            self.fx_assignments[k] = group
        if notify:
            messagebox.showinfo("Assigned", f"Assigned {len(selected)} buttons to {group}.")

    def _fx_editor_assign_preview(self):
        self._fx_editor_assign(notify=False)
        self.fx_editor_state["force_mod_preview_once"] = True
        self._fx_editor_preview_button()
    def _fx_editor_apply_preset(self):
        name = self.fx_editor_state.get("preset_var").get() if self.fx_editor_state else ""
        if not name or name not in self.fx_presets:
            messagebox.showinfo("Preset", "Select a preset to apply.")
            return
        selected = self.fx_editor_state.get("selected_buttons", set())
        if not selected:
            messagebox.showinfo("No Selection", "Select buttons to apply preset colors.")
            return
        preset = self.fx_presets.get(name, {})
        colors = preset.get("colors", [])
        for key in selected:
            for idx, hex_color in enumerate(colors[:4]):
                try:
                    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
                    self._set_slot_color(key, idx, (r, g, b))
                except:
                    pass
        if "rate_var" in self.fx_editor_state:
            self.fx_editor_state["rate_var"].set(float(preset.get("rate", self.fx_editor_state["rate_var"].get())))
        if "intensity_var" in self.fx_editor_state:
            self.fx_editor_state["intensity_var"].set(float(preset.get("intensity", self.fx_editor_state["intensity_var"].get())))
        if "stagger_var" in self.fx_editor_state:
            self.fx_editor_state["stagger_var"].set(float(preset.get("stagger", self.fx_editor_state["stagger_var"].get())))
        if "curve_var" in self.fx_editor_state and "curve" in preset:
            self.fx_editor_state["curve_var"].set(preset.get("curve"))
        if "width_var" in self.fx_editor_state:
            self.fx_editor_state["width_var"].set(float(preset.get("width", self.fx_editor_state["width_var"].get())))
        if "bias_var" in self.fx_editor_state:
            self.fx_editor_state["bias_var"].set(float(preset.get("bias", self.fx_editor_state["bias_var"].get())))
    def _fx_editor_collect_state(self):
        state = {
            "rate": float(self.fx_editor_state.get("rate_var").get()) if "rate_var" in self.fx_editor_state else 1.0,
            "intensity": float(self.fx_editor_state.get("intensity_var").get()) if "intensity_var" in self.fx_editor_state else 1.0,
            "stagger": float(self.fx_editor_state.get("stagger_var").get()) if "stagger_var" in self.fx_editor_state else 0.0,
            "width": float(self.fx_editor_state.get("width_var").get()) if "width_var" in self.fx_editor_state else 0.5,
            "bias": float(self.fx_editor_state.get("bias_var").get()) if "bias_var" in self.fx_editor_state else 0.0,
            "width_bias_lock": bool(self.fx_editor_state.get("width_bias_lock_var").get()) if "width_bias_lock_var" in self.fx_editor_state else False,
            "curve": self.fx_editor_state.get("curve_var").get() if "curve_var" in self.fx_editor_state else "Linear",
            "wave_type": self.fx_editor_state.get("wave_type_var").get() if "wave_type_var" in self.fx_editor_state else "Sine",
            "anim_rate": float(self.fx_editor_state.get("anim_rate_var").get()) if "anim_rate_var" in self.fx_editor_state else 1.0,
            "anim_intensity": float(self.fx_editor_state.get("anim_intensity_var").get()) if "anim_intensity_var" in self.fx_editor_state else 1.0,
            "anim_stagger": float(self.fx_editor_state.get("anim_stagger_var").get()) if "anim_stagger_var" in self.fx_editor_state else 0.0,
            "anim_width": float(self.fx_editor_state.get("anim_width_var").get()) if "anim_width_var" in self.fx_editor_state else 0.5,
            "anim_bias": float(self.fx_editor_state.get("anim_bias_var").get()) if "anim_bias_var" in self.fx_editor_state else 0.0,
            "anim_width_bias_lock": bool(self.fx_editor_state.get("anim_width_bias_lock_var").get()) if "anim_width_bias_lock_var" in self.fx_editor_state else False,
            "anim_curve": self.fx_editor_state.get("anim_curve_var").get() if "anim_curve_var" in self.fx_editor_state else "Linear",
            "anim_wave_type": self.fx_editor_state.get("anim_wave_type_var").get() if "anim_wave_type_var" in self.fx_editor_state else "Sine",
            "selected_buttons": sorted(list(self.fx_editor_state.get("selected_buttons", set()))),
            "assignments": dict(self.fx_assignments),
            "anim_preview_mode": self.fx_editor_state.get("anim_preview_mode"),
            "trim_start": float(self.fx_editor_state.get("trim_start_var").get()) if "trim_start_var" in self.fx_editor_state else 0.0,
            "trim_end": float(self.fx_editor_state.get("trim_end_var").get()) if "trim_end_var" in self.fx_editor_state else 100.0,
        }
        return state
    def _fx_editor_apply_state(self, state):
        if not isinstance(state, dict):
            return
        if "rate_var" in self.fx_editor_state and "rate" in state:
            self.fx_editor_state["rate_var"].set(float(state.get("rate", 1.0)))
        if "intensity_var" in self.fx_editor_state and "intensity" in state:
            self.fx_editor_state["intensity_var"].set(float(state.get("intensity", 1.0)))
        if "stagger_var" in self.fx_editor_state and "stagger" in state:
            self.fx_editor_state["stagger_var"].set(float(state.get("stagger", 0.0)))
        if "width_var" in self.fx_editor_state and "width" in state:
            self.fx_editor_state["width_var"].set(float(state.get("width", 0.5)))
        if "bias_var" in self.fx_editor_state and "bias" in state:
            self.fx_editor_state["bias_var"].set(float(state.get("bias", 0.0)))
        if "width_bias_lock_var" in self.fx_editor_state and "width_bias_lock" in state:
            self.fx_editor_state["width_bias_lock_var"].set(bool(state.get("width_bias_lock", False)))
        if "curve_var" in self.fx_editor_state and "curve" in state:
            self.fx_editor_state["curve_var"].set(state.get("curve") or "Linear")
        if "wave_type_var" in self.fx_editor_state and "wave_type" in state:
            self.fx_editor_state["wave_type_var"].set(state.get("wave_type") or "Sine")
        if "anim_wave_type_var" in self.fx_editor_state:
            self.fx_editor_state["anim_wave_type_var"].set(state.get("anim_wave_type") or state.get("wave_type") or "Sine")
        if "anim_rate_var" in self.fx_editor_state and "anim_rate" in state:
            self.fx_editor_state["anim_rate_var"].set(float(state.get("anim_rate", 1.0)))
        if "anim_intensity_var" in self.fx_editor_state and "anim_intensity" in state:
            self.fx_editor_state["anim_intensity_var"].set(float(state.get("anim_intensity", 1.0)))
        if "anim_stagger_var" in self.fx_editor_state and "anim_stagger" in state:
            self.fx_editor_state["anim_stagger_var"].set(float(state.get("anim_stagger", 0.0)))
        if "anim_width_var" in self.fx_editor_state and "anim_width" in state:
            self.fx_editor_state["anim_width_var"].set(float(state.get("anim_width", 0.5)))
        if "anim_bias_var" in self.fx_editor_state and "anim_bias" in state:
            self.fx_editor_state["anim_bias_var"].set(float(state.get("anim_bias", 0.0)))
        if "anim_width_bias_lock_var" in self.fx_editor_state and "anim_width_bias_lock" in state:
            self.fx_editor_state["anim_width_bias_lock_var"].set(bool(state.get("anim_width_bias_lock", False)))
        if "anim_curve_var" in self.fx_editor_state and "anim_curve" in state:
            self.fx_editor_state["anim_curve_var"].set(state.get("anim_curve") or "Linear")
        selected = set(state.get("selected_buttons") or [])
        self.fx_editor_state["selected_buttons"] = set()
        for k, btn in self.fx_editor_state.get("grid_buttons", {}).items():
            is_sel = k in selected
            if is_sel:
                self.fx_editor_state["selected_buttons"].add(k)
            if hasattr(btn, "set_selected"):
                btn.set_selected(is_sel)
        assignments = state.get("assignments") or {}
        if isinstance(assignments, dict):
            self.fx_assignments = dict(assignments)
        self.fx_editor_state["anim_preview_mode"] = state.get("anim_preview_mode")
        if "trim_start_var" in self.fx_editor_state and "trim_start" in state:
            self.fx_editor_state["trim_start_var"].set(float(state.get("trim_start", 0.0)))
        if "trim_end_var" in self.fx_editor_state and "trim_end" in state:
            self.fx_editor_state["trim_end_var"].set(float(state.get("trim_end", 100.0)))
        self._fx_editor_draw_waveform()
    def _fx_editor_draw_preview(self):
        c = self.fx_editor_state.get("preview_canvas")
        if not c:
            return
        c.delete("all")
        # Force full 17-button set for FX editor preview
        keys = [
            "P1_A", "P1_B", "P1_C", "P1_X", "P1_Y", "P1_Z",
            "P1_START",
            "P2_A", "P2_B", "P2_C", "P2_X", "P2_Y", "P2_Z",
            "P2_START",
            "MENU", "REWIND", "TRACKBALL",
        ]
        w = c.winfo_width() if c.winfo_width() > 1 else 600
        pad = 24
        radius = 14
        gap = 16
        # Group buttons: Player 1, Admin, Player 2 with fixed layout
        p1_order = ["P1_X", "P1_Y", "P1_Z", "P1_A", "P1_B", "P1_C"]
        p2_order = ["P2_X", "P2_Y", "P2_Z", "P2_A", "P2_B", "P2_C"]
        admin_order = ["P1_START", "P2_START", "REWIND", "MENU"]
        p1_keys = [k for k in p1_order if k in keys]
        p2_keys = [k for k in p2_order if k in keys]
        admin_keys = [k for k in admin_order if k in keys]
        trackball_key = "TRACKBALL" if "TRACKBALL" in keys else None

        groups = [
            {"label": "PLAYER 1", "keys": p1_keys, "cols": 3},
            {"label": "ADMIN", "keys": admin_keys, "cols": max(1, len(admin_keys))},
            {"label": "PLAYER 2", "keys": p2_keys, "cols": 3},
        ]

        top = 40
        left_x = pad
        # compute group widths with custom spacing
        player_gap = 20
        admin_gap = gap
        p1_cell_w = radius * 2 + player_gap
        admin_cell_w = radius * 2 + admin_gap
        p2_cell_w = radius * 2 + player_gap
        p1_w = groups[0]["cols"] * p1_cell_w
        admin_w = groups[1]["cols"] * admin_cell_w
        p2_w = groups[2]["cols"] * p2_cell_w
        admin_x = max(left_x + p1_w + 48, int((w - admin_w) / 2))
        p2_x = max(admin_x + admin_w + 48, w - pad - p2_w)
        group_positions = [left_x, admin_x, p2_x]

        leds = []
        for gi, group in enumerate(groups):
            gkeys = group["keys"]
            if not gkeys:
                continue
            x = group_positions[gi]
            cols = group["cols"]
            cell_w = p1_cell_w if group["label"] == "PLAYER 1" else (p2_cell_w if group["label"] == "PLAYER 2" else admin_cell_w)
            c.create_text(x, top - 22, anchor="nw", text=group["label"], fill=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold"))
            for i, k in enumerate(gkeys):
                r = i // cols
                col = i % cols
                cx = int(x + col * cell_w + radius)
                cy = int(top + r * (radius * 2 + gap) + radius)
                glow = c.create_oval(cx - radius - 5, cy - radius - 5, cx + radius + 5, cy + radius + 5,
                                     fill="", outline="", state="hidden")
                lens = c.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                                     fill=COLORS["SURFACE_LIGHT"], outline="#222", width=1)
                leds.append((k, glow, lens))

            # Draw group box
            rows = (len(gkeys) + cols - 1) // cols
            box_w = cols * cell_w
            box_h = rows * (radius * 2 + gap)
            c.create_rectangle(
                x - 8, top - 26, x + box_w + 8, top + box_h + 8,
                outline=COLORS["SURFACE_LIGHT"]
            )

        # Trackball centered and larger
        if trackball_key:
            tb_r = int(radius * 2.6)
            tb_cx = int(w / 2)
            tb_cy = int(top + (radius * 2 + gap) * 1.4 + tb_r)
            tb_glow = c.create_oval(tb_cx - tb_r - 6, tb_cy - tb_r - 6, tb_cx + tb_r + 6, tb_cy + tb_r + 6,
                                    fill="", outline="", state="hidden")
            tb_lens = c.create_oval(tb_cx - tb_r, tb_cy - tb_r, tb_cx + tb_r, tb_cy + tb_r,
                                    fill=COLORS["SURFACE_LIGHT"], outline="#222", width=1)
            leds.append((trackball_key, tb_glow, tb_lens))
            c.create_text(tb_cx, tb_cy, text="TB", fill=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold"))
            # Box around trackball
            c.create_rectangle(
                tb_cx - tb_r - 14, tb_cy - tb_r - 14, tb_cx + tb_r + 14, tb_cy + tb_r + 14,
                outline=COLORS["SURFACE_LIGHT"]
            )
        self.fx_editor_state["preview_leds"] = leds
        # Set static colors from current led_state
        for k, glow, lens in leds:
            col = None
            if k in self.led_state:
                col = self._rgb_to_hex(*self.led_state[k].get("primary", (0, 0, 0)))
            if col:
                # Emulate translucent lens/glow (similar to emulator)
                c.itemconfigure(lens, fill=col, outline=col, stipple="gray25")
                c.itemconfigure(glow, fill=col, state="normal", stipple="gray50")
    def _fx_editor_preview_toggle(self):
        active = self.fx_editor_state.get("preview_active", False)
        self.fx_editor_state["preview_active"] = not active
        if not active:
            self.fx_editor_state["preview_start_ts"] = time.time()
            self._fx_editor_start_preview_audio()
            self._fx_editor_preview_tick()
        else:
            self._fx_editor_stop_preview_audio()
    def _fx_editor_preview_button(self):
        was_active = self.fx_editor_state.get("preview_active", False)
        force_mod_preview = bool(self.fx_editor_state.pop("force_mod_preview_once", False))
        mode = (self.fx_editor_state.get("preview_color_mode").get() if self.fx_editor_state.get("preview_color_mode") else "Audio")
        mode_key = str(mode).strip().lower().replace(" ", "_")
        if not was_active:
            # Always clear stale preview sequence so trim changes apply immediately.
            self.fx_editor_state["preview_audio_sequence"] = None
        if mode_key in ("assigned_cycle", "assigned_random", "assigned_pulse", "primary_only"):
            # Non-audio color modes should preview independently from any audio-sequence timing.
            self.fx_editor_state["preview_audio_sequence"] = None
            self.fx_editor_state["preview_duration"] = max(6.0, float(self.fx_editor_state.get("preview_duration", 6.0)))
        # PREVIEW button always drives FX modulation preview so Rate/Width/Bias controls are authoritative.
        # Animation-specific preview remains available via the animation trigger flow.
        # FX preview should override animation preview while active.
        self.fx_editor_state["anim_preview_active"] = False
        # Ensure preview respects current trim bounds even if a previous sequence was built.
        if mode_key == "audio" and not was_active and self.audio_engine and (self.audio_analysis or self.audio_wav_path):
            try:
                if not self.audio_analysis and self.audio_wav_path:
                    self.audio_analysis = self.audio_engine.analyze_wav(self.audio_wav_path)
                trimmed = self._fx_editor_trim_analysis(self.audio_analysis)
                # Build a preview-only sequence that maps exactly to the trimmed range.
                seq = self.audio_engine.build_sequence(trimmed, entrance_sec=0.0, exit_sec=0.0, loop_main=False)
                if seq:
                    self.fx_editor_state["preview_audio_sequence"] = seq
                    frame_time = float((seq.get("meta", {}) or {}).get("frame_time", 0.05)) or 0.05
                    frames = (seq.get("main", {}) or {}).get("frames", [])
                    self.fx_editor_state["preview_duration"] = max(frame_time, len(frames) * frame_time)
            except Exception:
                pass
        self._fx_editor_preview_toggle()
        # Stay on FX Editor; preview is local-only
    def _fx_editor_preview_tick(self):
        if not self.fx_editor_state.get("preview_active"):
            return
        start_ts = self.fx_editor_state.get("preview_start_ts", time.time())
        duration = float(self.fx_editor_state.get("preview_duration", 6.0))
        elapsed = max(0.0, time.time() - start_ts)
        mode = (self.fx_editor_state.get("preview_color_mode").get() if self.fx_editor_state.get("preview_color_mode") else "Audio")
        mode_key = str(mode).strip().lower().replace(" ", "_")
        duration_driven_modes = ("audio",)
        if duration > 0:
            if mode_key in duration_driven_modes:
                progress = min(1.0, elapsed / duration)
            else:
                progress = (elapsed % duration) / duration
            c = self.fx_editor_state.get("timeline_canvas")
            if c and c.winfo_width() > 1:
                w = c.winfo_width()
                x = 10 + int((w - 20) * progress)
                self.fx_editor_state["scrub_x"] = x
                self._fx_editor_draw_timeline()
            if mode_key in duration_driven_modes and progress >= 1.0:
                self.fx_editor_state["preview_active"] = False
                self._fx_editor_stop_preview_audio()
                return
        c = self.fx_editor_state.get("preview_canvas")
        if not c:
            return
        leds = self.fx_editor_state.get("preview_leds", [])
        fx_rate, fx_intensity, fx_stagger, fx_curve, fx_wave, fx_width, fx_bias = self._fx_editor_get_fx_modulation()
        def _button_colors(key, keep_black=False):
            slots = self._get_button_color_slots(key, keep_black=keep_black)
            if not slots:
                return [COLORS["SURFACE_LIGHT"]]
            return [self._rgb_to_hex(*c) for c in slots]
        # Audio-driven preview if analysis exists
        if mode_key == "assigned_cycle":
            if leds:
                cycle_speed = max(2.0, fx_rate * 4.0)
                for i, (k, glow, lens) in enumerate(leds):
                    col = self._slot_cycle_color_hex(k, elapsed, speed=cycle_speed, phase_offset=i, keep_black=False)
                    c.itemconfigure(lens, fill=col, outline=col, stipple="gray25")
                    c.itemconfigure(glow, fill=col, state="normal", stipple="gray50")
            win = self.fx_editor_window
            if win and win.winfo_exists():
                win.after(60, self._fx_editor_preview_tick)
            return

        seq = self.fx_editor_state.get("preview_audio_sequence")
        if not seq and self.audio_analysis:
            try:
                trimmed = self._fx_editor_trim_analysis(self.audio_analysis)
                seq = self.audio_engine.build_sequence(trimmed, entrance_sec=0.0, exit_sec=0.0, loop_main=False) if self.audio_engine else None
                if seq:
                    self.fx_editor_state["preview_audio_sequence"] = seq
            except Exception:
                seq = None
        if seq:
            frames = []
            for phase in ("entrance", "main", "exit"):
                phase_frames = (seq.get(phase, {}) or {}).get("frames", [])
                if phase_frames:
                    frames.extend(phase_frames)
            if not frames:
                frames = (seq.get("main", {}) or {}).get("frames", [])
            meta = seq.get("meta", {})
            frame_time = float(meta.get("frame_time", 0.05)) or 0.05
            if frames:
                duration = float(len(frames) * frame_time)
                self.fx_editor_state["preview_duration"] = duration
                idx = min(len(frames) - 1, int(elapsed / frame_time))
                frame = frames[idx]
                br = float(frame.get("brightness", 1.0))
                b = float(frame.get("bass", 0.0))
                m = float(frame.get("mid", 0.0))
                t = float(frame.get("treble", 0.0))
                if leds:
                    for i, (k, glow, lens) in enumerate(leds):
                        if mode_key in ("assigned_cycle", "assigned_random", "assigned_pulse"):
                            cols = _button_colors(k, keep_black=True)
                        else:
                            cols = _button_colors(k)
                        col = cols[0]
                        audio_drive_val = 0.0
                        if mode_key == "assigned_cycle":
                            cycle_speed = max(2.0, fx_rate * 4.0)
                            col = self._slot_cycle_color_hex(k, elapsed, speed=cycle_speed, phase_offset=i, keep_black=False)
                        elif mode_key == "assigned_random":
                            col = cols[int((elapsed * 5 + i) % len(cols))]
                        elif mode_key == "assigned_pulse":
                            base = cols[0]
                            try:
                                r0 = int(base[1:3], 16); g0 = int(base[3:5], 16); b0 = int(base[5:7], 16)
                                pulse = (math.sin(elapsed * 4 + i) + 1.0) / 2.0
                                col = self._rgb_to_hex(int(r0 * pulse), int(g0 * pulse), int(b0 * pulse))
                            except Exception:
                                pass
                        elif mode_key == "primary_only":
                            col = cols[0]
                        else:  # Audio
                            # Respect per-button audio assignment in FX Editor mapping.
                            assignment = str(self.fx_assignments.get(k, "")).strip().lower()
                            if assignment == "bass":
                                audio_drive_val = self._fx_editor_audio_drive_level(b, m, t, br, "bass")
                                col = self._fx_editor_apply_modulation(col, audio_drive_val)
                            elif assignment == "mid":
                                audio_drive_val = self._fx_editor_audio_drive_level(b, m, t, br, "mid")
                                col = self._fx_editor_apply_modulation(col, audio_drive_val)
                            elif assignment == "treble":
                                audio_drive_val = self._fx_editor_audio_drive_level(b, m, t, br, "treble")
                                col = self._fx_editor_apply_modulation(col, audio_drive_val)
                            elif assignment == "sine":
                                sine_v = self._fx_editor_modulation_value(
                                    elapsed,
                                    i,
                                    rate=fx_rate,
                                    intensity=1.0,
                                    stagger=fx_stagger,
                                    curve_type=fx_curve,
                                    wave_type=fx_wave,
                                    width=fx_width,
                                    bias=fx_bias,
                                )
                                col = self._fx_editor_apply_modulation(col, sine_v)
                            elif assignment == "full range":
                                audio_drive_val = self._fx_editor_audio_drive_level(b, m, t, br, "full range")
                                col = self._fx_editor_apply_modulation(col, audio_drive_val)
                            else:
                                # Legacy default: tint by all three bands.
                                try:
                                    r0 = int(col[1:3], 16); g0 = int(col[3:5], 16); b0 = int(col[5:7], 16)
                                    audio_drive_val = self._fx_editor_audio_drive_level(b, m, t, br, "full range")
                                    r = int(r0 * min(1.0, t * 1.35 + 0.12))
                                    g = int(g0 * min(1.0, m * 1.35 + 0.12))
                                    bcol = int(b0 * min(1.0, b * 1.35 + 0.12))
                                    col = self._rgb_to_hex(r, g, bcol)
                                    col = self._fx_editor_apply_modulation(col, audio_drive_val)
                                except Exception:
                                    pass
                        mod_val = self._fx_editor_modulation_value(
                            elapsed,
                            i,
                            rate=fx_rate,
                            intensity=fx_intensity,
                            stagger=fx_stagger,
                            curve_type=fx_curve,
                            wave_type=fx_wave,
                            width=fx_width,
                            bias=fx_bias,
                        )
                        if mode_key == "audio":
                            # Avoid double-dimming when audio already drove the color.
                            mod_val = max(mod_val, audio_drive_val)
                        elif mode_key == "assigned_cycle":
                            # Keep cycle clearly visible; don't suppress by modulation waveform.
                            mod_val = 1.0
                        col = self._fx_editor_apply_modulation(col, mod_val)
                        c.itemconfigure(lens, fill=col, outline=col, stipple="gray25")
                        c.itemconfigure(glow, fill=col, state="normal", stipple="gray50")
                if progress >= 1.0:
                    self.fx_editor_state["preview_active"] = False
                    self._fx_editor_stop_preview_audio()
                    return
        else:
            t = time.time()
            if leds:
                for i, (k, glow, lens) in enumerate(leds):
                    phase = elapsed * fx_rate + i * fx_stagger
                    v = self._fx_editor_modulation_value(
                        t,
                        i,
                        rate=fx_rate,
                        intensity=fx_intensity,
                        stagger=fx_stagger,
                        curve_type=fx_curve,
                        wave_type=fx_wave,
                        width=fx_width,
                        bias=fx_bias,
                    )
                    if mode_key in ("assigned_cycle", "assigned_random", "assigned_pulse"):
                        cols = _button_colors(k, keep_black=True)
                    else:
                        cols = _button_colors(k)
                    if mode_key == "assigned_cycle":
                        cycle_speed = max(2.0, fx_rate * 4.0)
                        col = self._slot_cycle_color_hex(k, elapsed, speed=cycle_speed, phase_offset=i, keep_black=False)
                    elif mode_key == "assigned_random":
                        col = cols[int((phase) % len(cols))]
                    else:
                        col = cols[0]
                    if mode_key == "assigned_cycle":
                        col = self._fx_editor_apply_modulation(col, 1.0)
                    else:
                        col = self._fx_editor_apply_modulation(col, v)
                    c.itemconfigure(lens, fill=col, outline=col, stipple="gray25")
                    c.itemconfigure(glow, fill=col, state="normal", stipple="gray50")
        # FX Editor preview is local-only; do not push to hardware.
        win = self.fx_editor_window
        if win and win.winfo_exists():
            win.after(60, self._fx_editor_preview_tick)

    def _fx_editor_refresh_animation_library(self):
        lb = self.fx_editor_state.get("anim_lib_list")
        if not lb:
            return
        lb.delete(0, tk.END)
        for name in sorted(self.animation_library.keys()):
            lb.insert(tk.END, name)

    def _fx_editor_add_event_to_animation(self):
        name = self.fx_editor_state.get("anim_name_var").get().strip()
        if not name:
            messagebox.showinfo("Missing Name", "Enter an animation name first.")
            return
        event = self.fx_editor_state.get("event_type_var").get()
        anim = self.fx_editor_state.get("event_anim_var").get()
        try:
            duration = float(self.fx_editor_state.get("event_dur_var").get())
        except Exception:
            duration = 1.0
        entry = self.animation_library.setdefault(name, {"events": {}})
        events = entry.setdefault("events", {})
        events.setdefault(event, [])
        events[event].append({"anim": anim, "duration": max(0.1, duration)})
        self._save_animation_library()
        self._fx_editor_refresh_animation_library()
        self.fx_editor_state["selected_animation_name"] = name
        self._fx_editor_draw_timeline()

    def _fx_editor_save_animation(self):
        name = self.fx_editor_state.get("anim_name_var").get().strip()
        if not name:
            messagebox.showinfo("Missing Name", "Enter an animation name first.")
            return
        if name not in self.animation_library:
            self.animation_library[name] = {"events": {}}
        self._save_animation_library()
        self._fx_editor_refresh_animation_library()
        self.fx_editor_state["selected_animation_name"] = name
        self._fx_editor_draw_timeline()
        messagebox.showinfo("Saved", f"Animation '{name}' saved.")

    def _fx_editor_trigger_event_preview(self):
        event = self.fx_editor_state.get("event_type_var").get()
        anim_name = self.fx_editor_state.get("selected_animation_name")
        if not anim_name:
            messagebox.showinfo("No Animation", "Select an animation from the library.")
            return
        # Ensure animation preview has ownership of the canvas.
        self.fx_editor_state["preview_active"] = False
        self._fx_editor_stop_preview_audio()
        anim = self.animation_library.get(anim_name, {})
        if anim.get("audio_sequence"):
            self._fx_editor_preview_audio_sequence(anim.get("audio_sequence"), event)
            return
        events = anim.get("events", {})
        seq = events.get(event, [])
        if not seq:
            messagebox.showinfo("No Event", f"No {event} events defined for this animation.")
            return
        self._fx_editor_start_anim_sequence(seq)

    def _fx_editor_all_off(self):
        # Local-only: stop preview animations and clear FX editor preview LEDs
        self.fx_editor_state["preview_active"] = False
        self.fx_editor_state["anim_preview_active"] = False
        self._fx_editor_stop_preview_audio()
        c = self.fx_editor_state.get("preview_canvas")
        leds = self.fx_editor_state.get("preview_leds", [])
        if c and leds:
            for _k, glow, lens in leds:
                c.itemconfigure(lens, fill=COLORS["SURFACE_LIGHT"], outline="#222")
                c.itemconfigure(glow, fill="", state="hidden")
    def _fx_editor_all_off_global(self):
        # Global off: stop local preview and clear live controller/emulator outputs.
        self._fx_editor_all_off()
        self.all_off()

    def _fx_editor_apply_anim_from_catalog(self):
        lb = self.fx_editor_state.get("anim_catalog_list")
        if not lb or not lb.curselection():
            return
        # Ensure animation preview has ownership of the canvas.
        self.fx_editor_state["preview_active"] = False
        self._fx_editor_stop_preview_audio()
        anim = lb.get(lb.curselection()[0])
        self.fx_editor_state["anim_preview_mode"] = anim
        self.fx_editor_state["anim_preview_active"] = True
        self.fx_editor_state["anim_preview_start_ts"] = time.time()
        self.fx_editor_state["anim_preview_queue"] = []
        self.fx_editor_state["anim_preview_queue_index"] = 0
        self._fx_editor_anim_preview_tick()

    def _fx_editor_start_anim_sequence(self, seq):
        if not isinstance(seq, list) or not seq:
            return
        queue = []
        for step in seq:
            if not isinstance(step, dict):
                continue
            mode = step.get("anim")
            if not mode:
                continue
            try:
                duration = float(step.get("duration", 2.0))
            except Exception:
                duration = 2.0
            queue.append({"anim": mode, "duration": max(0.1, duration)})
        if not queue:
            return
        self.fx_editor_state["anim_preview_queue"] = queue
        self.fx_editor_state["anim_preview_queue_index"] = 0
        first = queue[0]
        self.fx_editor_state["anim_preview_mode"] = first.get("anim")
        self.fx_editor_state["anim_preview_active"] = True
        self.fx_editor_state["anim_preview_start_ts"] = time.time()
        self.fx_editor_state["anim_preview_until"] = time.time() + float(first.get("duration", 2.0))
        self._fx_editor_anim_preview_tick()

    def _fx_editor_anim_preview_tick(self):
        if not self.fx_editor_state.get("anim_preview_active"):
            return
        until = self.fx_editor_state.get("anim_preview_until")
        if until and time.time() >= until:
            queue = self.fx_editor_state.get("anim_preview_queue") or []
            idx = int(self.fx_editor_state.get("anim_preview_queue_index", 0)) + 1
            if idx < len(queue):
                step = queue[idx]
                self.fx_editor_state["anim_preview_queue_index"] = idx
                self.fx_editor_state["anim_preview_mode"] = step.get("anim")
                self.fx_editor_state["anim_preview_start_ts"] = time.time()
                self.fx_editor_state["anim_preview_until"] = time.time() + float(step.get("duration", 2.0))
            else:
                self.fx_editor_state["anim_preview_active"] = False
                return
        # If the main preview is active, let it drive the LEDs.
        if self.fx_editor_state.get("preview_active"):
            return
        c = self.fx_editor_state.get("preview_canvas")
        leds = self.fx_editor_state.get("preview_leds", [])
        if not c or not leds:
            return
        mode = (self.fx_editor_state.get("anim_preview_mode") or "").upper()
        t = time.time() - self.fx_editor_state.get("anim_preview_start_ts", time.time())
        anim_rate, anim_intensity, anim_stagger, anim_curve, anim_wave, anim_width, anim_bias = self._fx_editor_get_anim_modulation()
        for i, (k, glow, lens) in enumerate(leds):
            if mode == "RAINBOW":
                hue = (t * 0.5 + i * 0.08) % 1.0
                r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                col = self._rgb_to_hex(int(r * 255), int(g * 255), int(b * 255))
            elif mode == "PULSE_RED":
                v = (math.sin(t * 4.0) + 1.0) / 2.0
                col = self._rgb_to_hex(int(255 * v), 0, 0)
            elif mode == "PULSE_BLUE":
                v = (math.sin(t * 4.0) + 1.0) / 2.0
                col = self._rgb_to_hex(0, 0, int(255 * v))
            elif mode == "PULSE_GREEN":
                v = (math.sin(t * 4.0) + 1.0) / 2.0
                col = self._rgb_to_hex(0, int(255 * v), 0)
            elif mode == "HYPER_STROBE":
                on = int(t * 12) % 2 == 0
                col = "#FFFFFF" if on else "#111111"
            else:
                col = COLORS["SURFACE_LIGHT"]
            mod_val = self._fx_editor_modulation_value(
                t,
                i,
                rate=anim_rate,
                intensity=anim_intensity,
                stagger=anim_stagger,
                curve_type=anim_curve,
                wave_type=anim_wave,
                width=anim_width,
                bias=anim_bias,
            )
            col = self._fx_editor_apply_modulation(col, mod_val)
            c.itemconfigure(lens, fill=col, outline=col, stipple="gray25")
            c.itemconfigure(glow, fill=col, state="normal", stipple="gray50")
        win = self.fx_editor_window
        if win and win.winfo_exists():
            win.after(40, self._fx_editor_anim_preview_tick)

    def _fx_editor_bake_audio_to_animation(self):
        if not self.audio_sequence:
            messagebox.showinfo("No Audio", "Build an audio sequence first.")
            return
        name = self.fx_editor_state.get("anim_name_var").get().strip()
        if not name:
            name = simpledialog.askstring("Bake Audio", "Animation name:")
        if not name:
            return
        self.animation_library[name] = {
            "events": {"START": [], "END": [], "IDLE": []},
            "audio_sequence": self.audio_sequence,
            "meta": {"source": "audio_bake"},
        }
        self._save_animation_library()
        self._fx_editor_refresh_animation_library()
        self.fx_editor_state["selected_animation_name"] = name
        self._fx_editor_draw_timeline()
        messagebox.showinfo("Baked", f"Audio baked into animation '{name}'.")

    def _fx_editor_preview_audio_sequence(self, sequence, event):
        if not sequence:
            return
        phase = "main"
        if event == "START":
            phase = "entrance"
        elif event == "END":
            phase = "exit"
        frames = (sequence.get(phase, {}) or {}).get("frames", [])
        if not frames:
            return
        self.fx_editor_state["audio_preview_frames"] = frames
        self.fx_editor_state["audio_preview_index"] = 0
        self.fx_editor_state["audio_preview_frame_time"] = float(sequence.get("meta", {}).get("frame_time", 0.05)) or 0.05
        self.fx_editor_state["audio_preview_scope"] = "anim"
        self.fx_editor_state["audio_preview_active"] = True
        self._fx_editor_audio_preview_tick()
    def _fx_editor_trim_duration_seconds(self):
        start, end = self._fx_editor_trim_bounds()
        if end <= start:
            return 0.0
        try:
            if isinstance(self.audio_analysis, dict):
                rms = self.audio_analysis.get("rms", []) or []
                frame_time = float(self.audio_analysis.get("frame_time", 0.0) or 0.0)
                if rms and frame_time > 0.0:
                    total = float(len(rms)) * frame_time
                    return max(0.0, (end - start) * total)
        except Exception:
            pass
        wav_path = self.audio_wav_path
        if wav_path and os.path.exists(wav_path):
            try:
                with wave.open(wav_path, "rb") as wf:
                    fr = wf.getframerate()
                    frames = wf.getnframes()
                    if fr > 0 and frames > 0:
                        total = float(frames) / float(fr)
                        return max(0.0, (end - start) * total)
            except Exception:
                pass
        return 0.0

    def _fx_editor_audio_preview_tick(self):
        if not self.fx_editor_state.get("audio_preview_active"):
            return
        frames = self.fx_editor_state.get("audio_preview_frames") or []
        if not frames:
            self.fx_editor_state["audio_preview_active"] = False
            return
        idx = int(self.fx_editor_state.get("audio_preview_index", 0))
        if idx >= len(frames):
            self.fx_editor_state["audio_preview_active"] = False
            return
        frame = frames[idx]
        b = float(frame.get("bass", 0.0))
        m = float(frame.get("mid", 0.0))
        t = float(frame.get("treble", 0.0))
        br = float(frame.get("brightness", 1.0))
        drive = self._fx_editor_audio_drive_level(b, m, t, br, "full range")
        r = int(max(0, min(255, t * 255 * drive)))
        g = int(max(0, min(255, m * 255 * drive)))
        bcol = int(max(0, min(255, b * 255 * drive)))
        col = self._rgb_to_hex(r, g, bcol)
        c = self.fx_editor_state.get("preview_canvas")
        leds = self.fx_editor_state.get("preview_leds", [])
        if c and leds:
            t_now = time.time()
            scope = self.fx_editor_state.get("audio_preview_scope", "fx")
            if scope == "anim":
                rate, intensity, stagger, curve, wave, width, bias = self._fx_editor_get_anim_modulation()
            else:
                rate, intensity, stagger, curve, wave, width, bias = self._fx_editor_get_fx_modulation()
            for i, (_k, glow, lens) in enumerate(leds):
                mod_val = self._fx_editor_modulation_value(
                    t_now,
                    i,
                    rate=rate,
                    intensity=intensity,
                    stagger=stagger,
                    curve_type=curve,
                    wave_type=wave,
                    width=width,
                    bias=bias,
                )
                mod_val = max(mod_val, drive)
                mod_col = self._fx_editor_apply_modulation(col, mod_val)
                c.itemconfigure(lens, fill=mod_col, outline=mod_col, stipple="gray25")
                c.itemconfigure(glow, fill=mod_col, state="normal", stipple="gray50")
        self.fx_editor_state["audio_preview_index"] = idx + 1
        win = self.fx_editor_window
        delay = int(self.fx_editor_state.get("audio_preview_frame_time", 0.05) * 1000)
        if win and win.winfo_exists():
            win.after(max(10, delay), self._fx_editor_audio_preview_tick)
    def _fx_editor_start_preview_audio(self):
        if not PYGAME_AVAILABLE:
            return
        if not self.fx_editor_state.get("play_wav_var") or not self.fx_editor_state["play_wav_var"].get():
            return
        start, end = self._fx_editor_trim_bounds()
        partial_trim = not (start <= 0.0005 and end >= 0.9995)
        audio_path = self._prepare_trimmed_preview_wav()
        if not audio_path and not partial_trim:
            audio_path = self.audio_wav_path or self.audio_source_path
        if not audio_path:
            if "wave_status" in self.fx_editor_state:
                if partial_trim:
                    self.fx_editor_state["wave_status"].set("Trimmed preview unavailable for this source. Load WAV or enable ffmpeg.")
                else:
                    self.fx_editor_state["wave_status"].set("No WAV/audio source loaded.")
            return
        try:
            if self.fx_editor_state.get("preview_audio_stop_job") and self.fx_editor_window and self.fx_editor_window.winfo_exists():
                try:
                    self.fx_editor_window.after_cancel(self.fx_editor_state.get("preview_audio_stop_job"))
                except Exception:
                    pass
                self.fx_editor_state["preview_audio_stop_job"] = None
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
            self.fx_editor_state["audio_playing"] = True
            trim_dur = self._fx_editor_trim_duration_seconds()
            if trim_dur > 0.0 and self.fx_editor_window and self.fx_editor_window.winfo_exists():
                self.fx_editor_state["preview_audio_stop_job"] = self.fx_editor_window.after(
                    max(20, int(trim_dur * 1000.0)),
                    self._fx_editor_stop_preview_audio,
                )
            if "wave_status" in self.fx_editor_state:
                trimmed_note = "trimmed" if self.audio_trim_preview_path and os.path.abspath(audio_path) == os.path.abspath(self.audio_trim_preview_path) else "full"
                self.fx_editor_state["wave_status"].set(
                    f"Playing {trimmed_note} preview ({start*100:.1f}% - {end*100:.1f}%): {os.path.basename(self.audio_source_path or audio_path)}"
                )
        except Exception as e:
            self.fx_editor_state["audio_playing"] = False
            if "wave_status" in self.fx_editor_state:
                self.fx_editor_state["wave_status"].set(f"Audio preview failed: {e}")
    def _fx_editor_stop_preview_audio(self):
        if not PYGAME_AVAILABLE:
            return
        if self.fx_editor_state.get("preview_audio_stop_job") and self.fx_editor_window and self.fx_editor_window.winfo_exists():
            try:
                self.fx_editor_window.after_cancel(self.fx_editor_state.get("preview_audio_stop_job"))
            except Exception:
                pass
            self.fx_editor_state["preview_audio_stop_job"] = None
        if self.fx_editor_state.get("audio_playing"):
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
            self.fx_editor_state["audio_playing"] = False
    def _fx_library_refresh(self):
        if not self.fx_library or "lib_list" not in self.fx_editor_state:
            return
        q = self.fx_editor_state["lib_search_var"].get().strip().lower()
        filter_mode = (self.fx_editor_state.get("lib_filter_var").get().strip().lower() if self.fx_editor_state.get("lib_filter_var") else "all")
        fx_items = list(self.fx_library._db.get("fx", {}).values())
        fav = [f for f in fx_items if f.get("starred")]
        rest = [f for f in fx_items if not f.get("starred")]
        ordered = fav + rest
        self.fx_library_cache = ordered
        lb = self.fx_editor_state["lib_list"]
        lb.delete(0, tk.END)
        for fx in ordered:
            name = fx.get("name", "Unnamed")
            is_audio = bool(fx.get("audio_path"))
            if not self._fx_library_matches_filter(fx, filter_mode):
                continue
            meta = fx.get("meta", {}) if isinstance(fx.get("meta", {}), dict) else {}
            if meta.get("source") == "effects_preset":
                icon = "E"
            else:
                icon = "A" if is_audio else "P"
            if q and q not in name.lower():
                continue
            lb.insert(tk.END, f"[{icon}] {name}")
    def _fx_library_matches_filter(self, fx, filter_mode):
        mode = str(filter_mode or "all").strip().lower()
        if mode in ("", "all"):
            return True
        meta = fx.get("meta", {}) if isinstance(fx.get("meta", {}), dict) else {}
        if mode == "audio":
            return bool(fx.get("audio_path"))
        if mode == "presets":
            return meta.get("source") == "effects_preset"
        return True
    def _legacy_effect_editor_profile(self, key):
        profiles = {
            "rainbow": {"rate": 1.0, "intensity": 1.0, "stagger": 0.10, "curve": "Linear", "wave_type": "Sine"},
            "breath": {"rate": 0.6, "intensity": 1.0, "stagger": 0.06, "curve": "Ease-In", "wave_type": "Sine"},
            "strobe": {"rate": 2.6, "intensity": 1.0, "stagger": 0.00, "curve": "Linear", "wave_type": "Square"},
            "fade": {"rate": 0.8, "intensity": 1.0, "stagger": 0.04, "curve": "Linear", "wave_type": "Triangle"},
            "pulse_red": {"rate": 1.2, "intensity": 1.0, "stagger": 0.05, "curve": "Ease-In", "wave_type": "Sine"},
            "pulse_green": {"rate": 1.2, "intensity": 1.0, "stagger": 0.05, "curve": "Ease-In", "wave_type": "Sine"},
            "pulse_blue": {"rate": 1.2, "intensity": 1.0, "stagger": 0.05, "curve": "Ease-In", "wave_type": "Sine"},
            "hyper_strobe": {"rate": 3.0, "intensity": 1.0, "stagger": 0.00, "curve": "Linear", "wave_type": "Square"},
        }
        return dict(profiles.get(str(key or "").strip().lower().replace(" ", "_"), profiles["rainbow"]))

    def _build_editor_state_from_legacy_fx(self, fx):
        if not isinstance(fx, dict):
            return None
        main = fx.get("main", {}) if isinstance(fx.get("main", {}), dict) else {}
        fx_flags = main.get("fx_flags", {}) if isinstance(main.get("fx_flags", {}), dict) else {}
        primary_key = None
        for k in ("rainbow", "breath", "strobe", "fade"):
            if bool(fx_flags.get(k)):
                primary_key = k
                break
        if not primary_key:
            primary_key = str(fx.get("name", "")).strip().lower().replace(" ", "_")
        base = self._legacy_effect_editor_profile(primary_key)
        try:
            legacy_speed = float(main.get("speed", base["rate"]))
        except Exception:
            legacy_speed = float(base["rate"])
        legacy_speed = max(0.1, min(5.0, legacy_speed))
        base["rate"] = legacy_speed
        state = {
            "rate": float(base["rate"]),
            "intensity": float(base["intensity"]),
            "stagger": float(base["stagger"]),
            "width": 0.50,
            "bias": 0.00,
            "width_bias_lock": False,
            "curve": str(base["curve"]),
            "wave_type": str(base["wave_type"]),
            "anim_rate": float(base["rate"]),
            "anim_intensity": float(base["intensity"]),
            "anim_stagger": float(base["stagger"]),
            "anim_width": 0.50,
            "anim_bias": 0.00,
            "anim_width_bias_lock": False,
            "anim_curve": str(base["curve"]),
            "anim_wave_type": str(base["wave_type"]),
            "selected_buttons": [],
            "assignments": {},
            "anim_preview_mode": None,
            "trim_start": 0.0,
            "trim_end": 100.0,
        }
        return state

    def _upgrade_legacy_fx_to_editor_state(self, fx):
        if not isinstance(fx, dict):
            return False
        main = fx.get("main", {}) if isinstance(fx.get("main", {}), dict) else {}
        meta = fx.get("meta", {}) if isinstance(fx.get("meta", {}), dict) else {}
        if isinstance(main.get("editor_state"), dict) or isinstance(meta.get("editor_state"), dict):
            return False
        state = self._build_editor_state_from_legacy_fx(fx)
        if not state:
            return False
        main["editor_state"] = state
        fx["main"] = main
        meta["editor_state"] = state
        meta["upgraded_from_legacy"] = True
        fx["meta"] = meta
        return True

    def _ensure_quick_fx_library_entries(self):
        if not self.fx_library:
            return
        quick_defs = [
            ("RAINBOW", "rainbow"),
            ("BREATH", "breath"),
            ("STROBE", "strobe"),
            ("FADE", "fade"),
        ]
        existing_by_name = {}
        for fx in self.fx_library._db.get("fx", {}).values():
            nm = str(fx.get("name", "")).strip().lower()
            if nm:
                existing_by_name[nm] = fx
        existing = set(existing_by_name.keys())
        changed = False
        for display_name, flag_key in quick_defs:
            if display_name.lower() in existing:
                fx = existing_by_name.get(display_name.lower())
                if fx and self._upgrade_legacy_fx_to_editor_state(fx):
                    self.fx_library.save_fx(fx)
                    changed = True
                continue
            fx_flags = {k: False for k in ("rainbow", "breath", "strobe", "fade")}
            fx_flags[flag_key] = True
            editor_state = self._build_editor_state_from_legacy_fx(
                {"name": display_name, "main": {"fx_flags": fx_flags, "speed": 1.0}}
            )
            effect = FXEffect(
                fx_id="",
                name=display_name,
                entrance={},
                main={"fx_flags": fx_flags, "speed": 1.0, "editor_state": editor_state},
                exit={},
                audio_path="",
                applied_to=[],
                meta={"source": "quick_fx_template", "quick_fx": True, "editor_state": editor_state},
            )
            self.fx_library.save_fx(effect)
            changed = True
        if changed and hasattr(self, "fx_lib_list"):
            self._fx_tab_library_refresh()
    def _effects_preset_editor_state(self, preset_id):
        base = self._legacy_effect_editor_profile("rainbow")
        presets = {
            "showroom_default": {"rate": 1.0, "intensity": 1.0, "stagger": 0.08, "curve": "Linear", "wave_type": "Sine"},
            "classic_static": {"rate": 0.2, "intensity": 0.6, "stagger": 0.0, "curve": "Linear", "wave_type": "Sine"},
            "neon_minimal": {"rate": 0.9, "intensity": 0.9, "stagger": 0.04, "curve": "Ease-In", "wave_type": "Sine"},
            "party_mode": {"rate": 1.6, "intensity": 1.0, "stagger": 0.10, "curve": "Linear", "wave_type": "Triangle"},
            "tease": {"rate": 1.0, "intensity": 1.0, "stagger": 0.10, "curve": "Linear", "wave_type": "Sine"},
            "tease_independent": {"rate": 1.1, "intensity": 1.0, "stagger": 0.14, "curve": "Linear", "wave_type": "Sine"},
        }
        cfg = presets.get(str(preset_id), base)
        return {
            "rate": float(cfg.get("rate", 1.0)),
            "intensity": float(cfg.get("intensity", 1.0)),
            "stagger": float(cfg.get("stagger", 0.0)),
            "width": float(cfg.get("width", 0.50)),
            "bias": float(cfg.get("bias", 0.00)),
            "width_bias_lock": bool(cfg.get("width_bias_lock", False)),
            "curve": str(cfg.get("curve", "Linear")),
            "wave_type": str(cfg.get("wave_type", "Sine")),
            "anim_rate": float(cfg.get("rate", 1.0)),
            "anim_intensity": float(cfg.get("intensity", 1.0)),
            "anim_stagger": float(cfg.get("stagger", 0.0)),
            "anim_width": float(cfg.get("anim_width", cfg.get("width", 0.50))),
            "anim_bias": float(cfg.get("anim_bias", cfg.get("bias", 0.00))),
            "anim_width_bias_lock": bool(cfg.get("anim_width_bias_lock", cfg.get("width_bias_lock", False))),
            "anim_curve": str(cfg.get("curve", "Linear")),
            "anim_wave_type": str(cfg.get("wave_type", "Sine")),
            "selected_buttons": [],
            "assignments": {},
            "anim_preview_mode": None,
            "trim_start": 0.0,
            "trim_end": 100.0,
        }
    def _ensure_effects_preset_library_entries(self):
        if not self.fx_library:
            return
        preset_map = self.effects_preset_map if isinstance(self.effects_preset_map, dict) else {}
        if not preset_map:
            return
        existing_by_name = {}
        for fx in self.fx_library._db.get("fx", {}).values():
            nm = str(fx.get("name", "")).strip().lower()
            if nm:
                existing_by_name[nm] = fx
        changed = False
        for preset_id, preset in preset_map.items():
            entry_name = f"EFFECTS: {preset.name.upper()}"
            existing = existing_by_name.get(entry_name.lower())
            editor_state = self._effects_preset_editor_state(preset_id)
            fx_flags = {"rainbow": preset_id in ("showroom_default", "party_mode"), "breath": preset_id == "neon_minimal", "strobe": False, "fade": preset_id == "classic_static"}
            main_payload = {
                "fx_flags": fx_flags,
                "speed": float(editor_state.get("rate", 1.0)),
                "editor_state": editor_state,
            }
            meta_payload = {
                "source": "effects_preset",
                "managed": True,
                "effects_preset_id": str(preset_id),
                "description": str(getattr(preset, "description", "")),
                "editor_state": editor_state,
            }
            if existing:
                meta = existing.get("meta", {}) if isinstance(existing.get("meta", {}), dict) else {}
                needs_update = (
                    meta.get("effects_preset_id") != str(preset_id)
                    or str(meta.get("description", "")) != str(getattr(preset, "description", ""))
                )
                if needs_update:
                    existing["name"] = entry_name
                    existing["main"] = main_payload
                    existing["meta"] = meta_payload
                    self.fx_library.save_fx(existing)
                    changed = True
                continue
            effect = FXEffect(
                fx_id="",
                name=entry_name,
                entrance={},
                main=main_payload,
                exit={},
                audio_path="",
                applied_to=[],
                meta=meta_payload,
            )
            self.fx_library.save_fx(effect)
            changed = True
        if changed:
            if "lib_list" in self.fx_editor_state:
                self._fx_library_refresh()
            if hasattr(self, "fx_lib_list"):
                self._fx_tab_library_refresh()
    def _fx_library_select(self, _evt=None):
        lb = self.fx_editor_state.get("lib_list")
        if not lb:
            return
        sel = lb.curselection()
        if not sel:
            return
        idx = sel[0]
        fx = self._fx_library_item_from_index(idx)
        if fx:
            self.fx_editor_state["selected_fx"] = fx
    def _fx_library_item_from_index(self, idx):
        q = self.fx_editor_state["lib_search_var"].get().strip().lower()
        filter_mode = (self.fx_editor_state.get("lib_filter_var").get().strip().lower() if self.fx_editor_state.get("lib_filter_var") else "all")
        filtered = []
        for fx in self.fx_library_cache:
            name = fx.get("name", "Unnamed")
            if q and q not in name.lower():
                continue
            if not self._fx_library_matches_filter(fx, filter_mode):
                continue
            filtered.append(fx)
        if idx < 0 or idx >= len(filtered):
            return None
        return filtered[idx]
    def _fx_editor_load_selected_fx(self, _evt=None):
        lb = self.fx_editor_state.get("lib_list")
        fx = self.fx_editor_state.get("selected_fx")
        if not fx and lb:
            sel = lb.curselection()
            if sel:
                fx = self._fx_library_item_from_index(sel[0])
        if not fx:
            messagebox.showinfo("No FX Selected", "Select an FX from the library first.")
            return
        if self._upgrade_legacy_fx_to_editor_state(fx):
            if self.fx_library:
                self.fx_library.save_fx(fx)
            self._fx_library_refresh()
            if hasattr(self, "fx_lib_list"):
                self._fx_tab_library_refresh()
        self.fx_editor_state["selected_fx"] = fx
        self._fx_apply_effect_to_ui(fx)
        meta = fx.get("meta", {}) if isinstance(fx.get("meta", {}), dict) else {}
        preset_id = str(meta.get("effects_preset_id", "")).strip()
        if preset_id and self.effects_engine:
            if self._apply_effects_preset(preset_id):
                self.effects_enabled = True
                self.app_settings["effects_enabled"] = True
                self.app_settings["effects_preset_id"] = preset_id
                self.save_settings({"effects_enabled": True, "effects_preset_id": preset_id})
                if hasattr(self, "app_config_vars") and isinstance(self.app_config_vars, dict):
                    if "effects_enabled" in self.app_config_vars:
                        try:
                            self.app_config_vars["effects_enabled"].set(True)
                        except Exception:
                            pass
                    if "effects_preset_id" in self.app_config_vars:
                        try:
                            self.app_config_vars["effects_preset_id"].set(preset_id)
                        except Exception:
                            pass
                if hasattr(self, "effects_preset_name_var"):
                    try:
                        preset = self.effects_preset_map.get(preset_id) if isinstance(self.effects_preset_map, dict) else None
                        if preset:
                            self.effects_preset_name_var.set(preset.name)
                    except Exception:
                        pass
        editor_state = fx.get("main", {}).get("editor_state") if isinstance(fx.get("main", {}), dict) else None
        if not editor_state:
            editor_state = (fx.get("meta", {}) or {}).get("editor_state")
        if editor_state:
            self._fx_editor_apply_state(editor_state)
        selected = set(fx.get("applied_to") or [])
        self.fx_editor_state["selected_buttons"] = set()
        for k, btn in self.fx_editor_state.get("grid_buttons", {}).items():
            is_sel = k in selected
            if is_sel:
                self.fx_editor_state["selected_buttons"].add(k)
            if hasattr(btn, "set_selected"):
                btn.set_selected(is_sel)
        audio_name = fx.get("audio_path") or ""
        if audio_name:
            audio_path = asset_path(audio_name)
            if os.path.exists(audio_path):
                self._cleanup_trimmed_preview_audio()
                try:
                    if self.audio_tmp_path:
                        try:
                            os.unlink(self.audio_tmp_path)
                        except Exception:
                            pass
                        self.audio_tmp_path = None
                    wav_path, tmp_path = self._prepare_audio_wav(audio_path)
                    self.audio_source_path = audio_path
                    self.audio_wav_path = wav_path
                    self.audio_tmp_path = tmp_path
                    self.audio_analysis = None
                    if self.audio_engine and self.audio_wav_path:
                        try:
                            self.audio_analysis = self.audio_engine.analyze_wav(self.audio_wav_path)
                        except Exception:
                            self.audio_analysis = None
                    msg = f"Audio loaded: {os.path.basename(audio_path)}"
                except Exception as e:
                    self.audio_source_path = audio_path
                    self.audio_wav_path = audio_path if audio_path.lower().endswith(".wav") else None
                    self.audio_tmp_path = None
                    self.audio_analysis = None
                    msg = f"Audio loaded (no trim analysis): {os.path.basename(audio_path)} [{e}]"
            else:
                msg = f"Audio missing: {audio_name}"
            if "wave_status" in self.fx_editor_state:
                self.fx_editor_state["wave_status"].set(msg)
        else:
            if "wave_status" in self.fx_editor_state:
                self.fx_editor_state["wave_status"].set(f"Loaded FX: {fx.get('name', 'Unnamed')}")
        self._fx_editor_draw_preview()
    def _fx_editor_preview_selected_fx(self):
        self._fx_editor_load_selected_fx()
        self._fx_editor_preview_button()
    def _fx_library_context_menu(self, event):
        fx = None
        lb = self.fx_editor_state.get("lib_list")
        if lb:
            idx = lb.nearest(event.y)
            lb.selection_clear(0, tk.END)
            lb.selection_set(idx)
            fx = self._fx_library_item_from_index(idx)
            self.fx_editor_state["selected_fx"] = fx
        if not fx:
            return
        m = tk.Menu(self.fx_editor_window, tearoff=0, bg=COLORS["SURFACE_LIGHT"], fg="white")
        m.add_command(label="Rename", command=self._fx_library_rename)
        m.add_command(label="Duplicate", command=self._fx_library_duplicate)
        m.add_command(label="Export", command=self._fx_library_export)
        m.add_command(label="Delete", command=self._fx_library_delete)
        m.add_separator()
        m.add_command(label="Star/Unstar", command=self._fx_library_toggle_star)
        m.post(event.x_root, event.y_root)
    def _fx_library_rename(self):
        fx = self.fx_editor_state.get("selected_fx")
        if not fx:
            return
        new_name = simpledialog.askstring("Rename FX", "New name:")
        if not new_name:
            return
        fx["name"] = new_name
        self.fx_library.save_fx(fx)
        self._fx_library_refresh()
    def _fx_library_duplicate(self):
        fx = self.fx_editor_state.get("selected_fx")
        if not fx:
            return
        new_name = simpledialog.askstring("Duplicate FX", "New effect name:")
        if not new_name:
            return
        self.fx_library.clone_fx(fx.get("fx_id"), new_name)
        self._fx_library_refresh()
    def _fx_library_import(self):
        if not self.fx_library:
            messagebox.showinfo("FX Library", "FX Library unavailable.")
            return
        path = filedialog.askopenfilename(
            title="Import FX",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Import Failed", f"Could not read FX file:\n{e}")
            return
        if not isinstance(data, dict) or "name" not in data:
            messagebox.showerror("Import Failed", "Invalid FX file format.")
            return
        data = dict(data)
        data["fx_id"] = ""
        data.setdefault("applied_to", [])
        data.setdefault("meta", {})
        fx_id = self.fx_library.save_fx(data)
        self.fx_editor_state["selected_fx"] = self.fx_library.get_fx_by_id(fx_id)
        self._fx_library_refresh()
        if hasattr(self, "fx_lib_list"):
            self.fx_lib_selected_id = fx_id
            self._fx_tab_library_refresh()
        messagebox.showinfo("Imported", f"Imported FX '{data.get('name','FX')}'.")
    def _fx_library_export(self):
        fx = self.fx_editor_state.get("selected_fx")
        if not fx:
            return
        path = filedialog.asksaveasfilename(
            title="Export FX",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(fx, f, indent=2)
        messagebox.showinfo("Exported", f"Exported to:\n{path}")
    def _fx_library_delete(self):
        fx = self.fx_editor_state.get("selected_fx")
        if not fx:
            return
        if messagebox.askyesno("Delete FX", f"Delete '{fx.get('name','FX')}'?"):
            fx_id = fx.get("fx_id")
            if fx_id and fx_id in self.fx_library._db.get("fx", {}):
                del self.fx_library._db["fx"][fx_id]
                self.fx_library._save()
            self._fx_library_refresh()
    def _fx_library_toggle_star(self):
        fx = self.fx_editor_state.get("selected_fx")
        if not fx:
            return
        fx["starred"] = not bool(fx.get("starred"))
        self.fx_library.save_fx(fx)
        self._fx_library_refresh()
    def _fx_library_start_drag(self, event):
        lb = self.fx_editor_state.get("lib_list")
        if not lb:
            return
        idx = lb.nearest(event.y)
        lb.selection_clear(0, tk.END)
        lb.selection_set(idx)
        fx = self._fx_library_item_from_index(idx)
        self.fx_editor_state["drag_fx"] = fx
    def _fx_library_drag_motion(self, _event):
        pass
    def _fx_library_drop(self, event):
        fx = self.fx_editor_state.get("drag_fx")
        if not fx:
            return
        widget = event.widget.winfo_containing(event.x_root, event.y_root)
        target_key = None
        for k, btn in self.fx_editor_state.get("grid_buttons", {}).items():
            if widget == btn:
                target_key = k
                break
        if target_key:
            self.fx_assignments[target_key] = fx.get("name", "FX")
            btn = self.fx_editor_state["grid_buttons"][target_key]
            btn.set_base_bg(COLORS["P2"])
            messagebox.showinfo("Assigned", f"Assigned '{fx.get('name','FX')}' to {target_key}.")
        self.fx_editor_state["drag_fx"] = None
    def _fx_library_bind_hover(self):
        lb = self.fx_editor_state.get("lib_list")
        if not lb:
            return
        # Disable auto-preview on hover; preview should be explicit via button.
        lb.unbind("<Motion>")
    def _fx_library_hover(self, event):
        lb = self.fx_editor_state.get("lib_list")
        if not lb:
            return
        idx = lb.nearest(event.y)
        fx = self._fx_library_item_from_index(idx)
        if not fx:
            return
        last = self.fx_editor_state.get("hover_fx_id")
        if last == fx.get("fx_id"):
            return
        self.fx_editor_state["hover_fx_id"] = fx.get("fx_id")
        self._fx_editor_preview_toggle()
    def _ensure_banner_image(self):
        if not hasattr(self, "banner_frame"):
            return
        if self.banner_label and self.banner_label.winfo_exists():
            return
        path = asset_path("ArcadeCommanderBanner.png")
        if os.path.exists(path) and PIL_AVAILABLE:
            try:
                self._banner_img = ImageTk.PhotoImage(Image.open(path))
                self.banner_label = tk.Label(self.banner_frame, image=self._banner_img, bg=COLORS["BG"])
                self.banner_label.pack(anchor="w")
            except Exception:
                pass
    def _play_fx_editor_video_once(self):
        if not self.app_settings.get("fx_editor_video_enabled", True):
            return
        if self.fx_video_playing:
            return
        if self.fx_video_played:
            return
        if not CV2_AVAILABLE or not PIL_AVAILABLE:
            return
        path = asset_path("Video_Generation_Complete.mp4")
        if not os.path.exists(path):
            return
        if hasattr(self, "banner_frame"):
            if not getattr(self, "banner_visible", True):
                self.banner_frame.pack(before=self.main_content, fill="x", padx=30, pady=(0,10))
                self.banner_visible = True
            if self.banner_label and self.banner_label.winfo_exists():
                self.banner_label.destroy()
                self.banner_label = None
        self.fx_video_cap = cv2.VideoCapture(path)
        if not self.fx_video_cap or not self.fx_video_cap.isOpened():
            return
        self.fx_video_playing = True
        self.fx_video_played = True
        self._start_fx_video_audio(path)
        if hasattr(self, "banner_frame"):
            self.fx_video_label = tk.Label(self.banner_frame, bg=COLORS["BG"])
            self.fx_video_label.pack(anchor="w")
        self._fx_video_tick()
    def _fx_video_tick(self):
        if not self.fx_video_playing or not self.fx_video_cap:
            return
        ret, frame = self.fx_video_cap.read()
        if not ret:
            self._stop_fx_editor_video(hide_after=False)
            return
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if hasattr(self, "banner_frame") and self.banner_frame.winfo_width() > 10:
            w = self.banner_frame.winfo_width()
            h = self.banner_frame.winfo_height() if self.banner_frame.winfo_height() > 10 else frame.shape[0]
            img = Image.fromarray(frame)
            img = img.resize((w, h))
        else:
            img = Image.fromarray(frame)
        self._fx_video_img = ImageTk.PhotoImage(img)
        if self.fx_video_label and self.fx_video_label.winfo_exists():
            self.fx_video_label.configure(image=self._fx_video_img)
        fps = self.fx_video_cap.get(cv2.CAP_PROP_FPS) or 30
        delay = int(1000 / max(1, int(fps)))
        self.root.after(delay, self._fx_video_tick)
    def _stop_fx_editor_video(self, hide_after=False):
        self.fx_video_playing = False
        if self.fx_video_cap:
            try:
                self.fx_video_cap.release()
            except Exception:
                pass
            self.fx_video_cap = None
        if self.fx_video_label and self.fx_video_label.winfo_exists():
            self.fx_video_label.destroy()
            self.fx_video_label = None
        self._stop_fx_video_audio()
        if hide_after and hasattr(self, "banner_frame"):
            self.banner_frame.pack_forget()
            self.banner_visible = False
        elif hasattr(self, "banner_frame"):
            if not getattr(self, "banner_visible", True):
                self.banner_frame.pack(before=self.main_content, fill="x", padx=30, pady=(0,10))
                self.banner_visible = True
            self._ensure_banner_image()

    def _start_fx_video_audio(self, video_path):
        if not self.app_settings.get("fx_editor_video_audio_enabled", True):
            return
        if not PYGAME_AVAILABLE:
            print("DEBUG: pygame not available. Video audio disabled.")
            return
        mp3_path = asset_path("arcade-gaming.mp3")
        if os.path.exists(mp3_path):
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                pygame.mixer.music.load(mp3_path)
                pygame.mixer.music.play()
                if self.fx_video_audio_stop_id:
                    try:
                        self.root.after_cancel(self.fx_video_audio_stop_id)
                    except Exception:
                        pass
                self.fx_video_audio_stop_id = self.root.after(14000, self._stop_fx_video_audio)
                return
            except Exception as e:
                print(f"DEBUG: mp3 play failed: {e}")
        audio_path = None
        sidecar = os.path.splitext(video_path)[0] + ".wav"
        if os.path.exists(sidecar):
            audio_path = sidecar
        else:
            ffmpeg = shutil.which("ffmpeg")
            local_ffmpeg = asset_path("ffmpeg.exe") if os.name == "nt" else asset_path("ffmpeg")
            if os.path.exists(local_ffmpeg):
                ffmpeg = local_ffmpeg
            if not ffmpeg:
                print("DEBUG: ffmpeg not found. Video audio disabled.")
                return
            try:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                audio_path = tmp.name
                tmp.close()
            except Exception:
                return
            cmd = [
                ffmpeg,
                "-y",
                "-i",
                video_path,
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                "44100",
                "-ac",
                "2",
                audio_path,
            ]
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            except Exception as e:
                try:
                    os.unlink(audio_path)
                except Exception:
                    pass
                print(f"DEBUG: ffmpeg audio extract failed: {e}")
                return
        self.fx_video_audio_path = audio_path
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.fx_video_audio_sound = pygame.mixer.Sound(audio_path)
            self.fx_video_audio_channel = self.fx_video_audio_sound.play()
        except Exception as e:
            print(f"DEBUG: pygame audio play failed: {e}")

    def _stop_fx_video_audio(self):
        if self.fx_video_audio_stop_id:
            try:
                self.root.after_cancel(self.fx_video_audio_stop_id)
            except Exception:
                pass
            self.fx_video_audio_stop_id = None
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass
        if self.fx_video_audio_channel:
            try:
                self.fx_video_audio_channel.stop()
            except Exception:
                pass
        self.fx_video_audio_channel = None
        self.fx_video_audio_sound = None
        if self.fx_video_audio_path:
            try:
                os.unlink(self.fx_video_audio_path)
            except Exception:
                pass
        self.fx_video_audio_path = None
    def _fx_tab_library_refresh(self, _evt=None):
        if not self.fx_library or not hasattr(self, "fx_lib_list"):
            return
        q = (self.fx_lib_search.get().strip().lower() if hasattr(self, "fx_lib_search") else "")
        filter_mode = (self.fx_lib_filter.get().strip().lower() if hasattr(self, "fx_lib_filter") else "all")
        fx_items = list(self.fx_library._db.get("fx", {}).values())
        fav = [f for f in fx_items if f.get("starred")]
        rest = [f for f in fx_items if not f.get("starred")]
        ordered = fav + rest
        self.fx_library_cache = ordered
        self.fx_lib_list.delete(0, tk.END)
        for fx in ordered:
            name = fx.get("name", "Unnamed")
            if q and q not in name.lower():
                continue
            if not self._fx_library_matches_filter(fx, filter_mode):
                continue
            meta = fx.get("meta", {}) if isinstance(fx.get("meta", {}), dict) else {}
            if meta.get("source") == "effects_preset":
                icon = "E"
            else:
                icon = "A" if fx.get("audio_path") else "P"
            self.fx_lib_list.insert(tk.END, f"[{icon}] {name}")
        if self.fx_lib_selected_id:
            self._fx_tab_library_sync_selection(self.fx_lib_selected_id)
    def _fx_tab_library_select(self, _evt=None):
        if not hasattr(self, "fx_lib_list"):
            return
        sel = self.fx_lib_list.curselection()
        if not sel:
            return
        fx = self._fx_tab_library_item_from_index(sel[0])
        if fx:
            self.fx_lib_selected_id = fx.get("fx_id")
    def _fx_tab_library_item_from_index(self, idx):
        q = (self.fx_lib_search.get().strip().lower() if hasattr(self, "fx_lib_search") else "")
        filter_mode = (self.fx_lib_filter.get().strip().lower() if hasattr(self, "fx_lib_filter") else "all")
        filtered = []
        for fx in self.fx_library_cache:
            name = fx.get("name", "Unnamed")
            if q and q not in name.lower():
                continue
            if not self._fx_library_matches_filter(fx, filter_mode):
                continue
            filtered.append(fx)
        if idx < 0 or idx >= len(filtered):
            return None
        return filtered[idx]
    def _fx_tab_library_sync_selection(self, fx_id):
        if not hasattr(self, "fx_lib_list"):
            return
        q = (self.fx_lib_search.get().strip().lower() if hasattr(self, "fx_lib_search") else "")
        filter_mode = (self.fx_lib_filter.get().strip().lower() if hasattr(self, "fx_lib_filter") else "all")
        filtered = []
        for fx in self.fx_library_cache:
            name = fx.get("name", "Unnamed")
            if q and q not in name.lower():
                continue
            if not self._fx_library_matches_filter(fx, filter_mode):
                continue
            filtered.append(fx)
        for i, fx in enumerate(filtered):
            if fx.get("fx_id") == fx_id:
                self.fx_lib_list.selection_clear(0, tk.END)
                self.fx_lib_list.selection_set(i)
                break
    def fx_save_to_library(self):
        if not self.fx_library:
            messagebox.showerror("Error", "FX Library not available.")
            return
        name = simpledialog.askstring("Save FX", "Effect name:")
        if not name:
            return
        editor_state = self._fx_editor_collect_state()
        if self.audio_sequence:
            effect = FXEffect(
                fx_id="",
                name=name,
                entrance=self.audio_sequence.get("entrance", {}),
                main=self.audio_sequence.get("main", {}),
                exit=self.audio_sequence.get("exit", {}),
                audio_path=os.path.basename(self.audio_wav_path) if self.audio_wav_path else "",
                applied_to=list(self.fx_assignments.keys()),
                meta={"source": "audio_sequence", "editor_state": editor_state},
            )
        else:
            effect = FXEffect(
                fx_id="",
                name=name,
                entrance={},
                main={
                    "fx_flags": {k: v.get() for k, v in self.fx_vars.items()},
                    "speed": float(self.fx_speed.get()) if self.fx_speed is not None else 1.0,
                    "editor_state": editor_state,
                },
                exit={},
                audio_path=os.path.basename(self.audio_wav_path) if self.audio_wav_path else "",
                applied_to=list(self.fx_assignments.keys()),
                meta={"source": "fx_flags"},
            )
        fx_id = self.fx_library.save_fx(effect)
        self.fx_lib_selected_id = fx_id
        self._fx_tab_library_refresh()
        if self.fx_editor_window and self.fx_editor_window.winfo_exists():
            self._fx_library_refresh()
        messagebox.showinfo("Saved", f"FX '{name}' saved to library.")
    def _fx_tab_library_export(self):
        if not self.fx_library:
            messagebox.showinfo("FX Library", "FX Library unavailable.")
            return
        if not self.fx_lib_selected_id:
            messagebox.showinfo("No FX Selected", "Select an FX to export.")
            return
        fx = self.fx_library.get_fx_by_id(self.fx_lib_selected_id)
        if not fx:
            messagebox.showinfo("No FX Selected", "Select an FX to export.")
            return
        path = filedialog.asksaveasfilename(
            title="Export FX",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(fx, f, indent=2)
        messagebox.showinfo("Exported", f"Exported to:\n{path}")
    def _fx_tab_library_import(self):
        if not self.fx_library:
            messagebox.showinfo("FX Library", "FX Library unavailable.")
            return
        path = filedialog.askopenfilename(
            title="Import FX",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Import Failed", f"Could not read FX file:\n{e}")
            return
        if not isinstance(data, dict) or "name" not in data:
            messagebox.showerror("Import Failed", "Invalid FX file format.")
            return
        data = dict(data)
        data["fx_id"] = ""
        data.setdefault("applied_to", [])
        data.setdefault("meta", {})
        fx_id = self.fx_library.save_fx(data)
        self.fx_lib_selected_id = fx_id
        self._fx_tab_library_refresh()
        if self.fx_editor_window and self.fx_editor_window.winfo_exists():
            self._fx_library_refresh()
        messagebox.showinfo("Imported", f"Imported FX '{data.get('name','FX')}'.")
    def _fx_tab_library_delete(self):
        if not self.fx_library:
            messagebox.showinfo("FX Library", "FX Library unavailable.")
            return
        if not self.fx_lib_selected_id:
            messagebox.showinfo("No FX Selected", "Select an FX to delete.")
            return
        fx = self.fx_library.get_fx_by_id(self.fx_lib_selected_id)
        name = fx.get("name", "FX") if fx else "FX"
        if messagebox.askyesno("Delete FX", f"Delete '{name}'?"):
            if self.fx_lib_selected_id in self.fx_library._db.get("fx", {}):
                del self.fx_library._db["fx"][self.fx_lib_selected_id]
                self.fx_library._save()
            self.fx_lib_selected_id = None
            self._fx_tab_library_refresh()
            if self.fx_editor_window and self.fx_editor_window.winfo_exists():
                self._fx_library_refresh()
    def fx_apply_library_to_game(self):
        if not self.fx_selected_rom:
            messagebox.showinfo("No Game Selected", "Select a game to apply FX.")
            return
        if not self.fx_lib_selected_id:
            messagebox.showinfo("No FX Selected", "Select a library FX.")
            return
        entry = self.game_db.get(self.fx_selected_rom, {})
        entry["fx_id"] = self.fx_lib_selected_id
        self.game_db[self.fx_selected_rom] = entry
        self._save_game_db()
        messagebox.showinfo("Applied", f"Applied FX to '{self.fx_selected_rom}'.")
    def _fx_apply_effect_to_ui(self, fx):
        main = fx.get("main", {})
        fx_flags = main.get("fx_flags")
        if fx_flags:
            for k, v in self.fx_vars.items():
                v.set(bool(fx_flags.get(k, False)))
        if self.fx_speed is not None and "speed" in main:
            try:
                self.fx_speed.set(float(main.get("speed", 1.0)))
            except Exception:
                pass
    def apply_game_start_fx(self, rom_key):
        entry = self.game_db.get(rom_key, {})
        if not entry.get("override_enabled", True):
            return
        fx = entry.get("profile", {}).get("fx_on_start", "")
        if fx:
            self.preview_animation(fx)
    def apply_game_end_fx(self, rom_key):
        entry = self.game_db.get(rom_key, {})
        if not entry.get("override_enabled", True):
            return
        fx = entry.get("profile", {}).get("fx_on_end", "")
        if fx:
            self.preview_animation(fx)
    def _notebook_tab_text_at_xy(self, x, y):
        if not hasattr(self, "notebook"):
            return ""
        try:
            idx = self.notebook.index(f"@{int(x)},{int(y)}")
            return str(self.notebook.tab(idx, "text") or "")
        except Exception:
            pass
        try:
            end = int(self.notebook.index("end"))
        except Exception:
            return ""
        for idx in range(end):
            try:
                bx, by, bw, bh = self.notebook.bbox(idx)
            except Exception:
                continue
            if bw <= 0 or bh <= 0:
                continue
            if bx <= x < (bx + bw) and by <= y < (by + bh):
                try:
                    return str(self.notebook.tab(idx, "text") or "")
                except Exception:
                    return ""
        return ""
    def _show_tab_help_tooltip_at(self, x_root, y_root, tab_text):
        if not tab_text:
            self._hide_tab_help_tooltip()
            return
        short = (self.tab_help_map.get(tab_text, {}) or {}).get("short", "").strip()
        if not short:
            self._hide_tab_help_tooltip()
            return
        if self._tab_help_tip and self._tab_help_tip.winfo_exists() and self._tab_help_tip_tab == tab_text:
            try:
                self._tab_help_tip.geometry(f"+{int(x_root) + 12}+{int(y_root) + 14}")
            except Exception:
                pass
            return
        self._hide_tab_help_tooltip()
        tip = tk.Toplevel(self.root)
        tip.overrideredirect(True)
        tip.attributes("-topmost", True)
        tip.configure(bg=COLORS["SURFACE_LIGHT"])
        lbl = tk.Label(
            tip,
            text=short,
            bg=COLORS["SURFACE_LIGHT"],
            fg=COLORS["TEXT"],
            font=("Segoe UI", 8),
            justify="left",
            anchor="w",
            padx=8,
            pady=5,
        )
        lbl.pack()
        try:
            tip.geometry(f"+{int(x_root) + 12}+{int(y_root) + 14}")
        except Exception:
            pass
        self._tab_help_tip = tip
        self._tab_help_tip_label = lbl
        self._tab_help_tip_tab = tab_text
    def _show_tab_help_tooltip(self, event, tab_text):
        self._show_tab_help_tooltip_at(getattr(event, "x_root", 0), getattr(event, "y_root", 0), tab_text)
    def _hide_tab_help_tooltip(self):
        try:
            if self._tab_help_tip and self._tab_help_tip.winfo_exists():
                self._tab_help_tip.destroy()
        except Exception:
            pass
        self._tab_help_tip = None
        self._tab_help_tip_label = None
        self._tab_help_tip_tab = ""
    def _cancel_tab_help_hover_poll(self):
        try:
            if self._tab_help_hover_poll_id and hasattr(self, "root"):
                self.root.after_cancel(self._tab_help_hover_poll_id)
        except Exception:
            pass
        self._tab_help_hover_poll_id = None
    def _poll_notebook_tab_hover(self):
        self._tab_help_hover_poll_id = None
        if not hasattr(self, "notebook") or not self.notebook.winfo_exists():
            self._hide_tab_help_tooltip()
            return
        try:
            px = self.notebook.winfo_pointerx()
            py = self.notebook.winfo_pointery()
            x = px - self.notebook.winfo_rootx()
            y = py - self.notebook.winfo_rooty()
            tab_text = self._notebook_tab_text_at_xy(x, y)
            if tab_text:
                self._show_tab_help_tooltip_at(px, py, tab_text)
            else:
                self._hide_tab_help_tooltip()
        except Exception:
            self._hide_tab_help_tooltip()
            return
        try:
            self._tab_help_hover_poll_id = self.root.after(160, self._poll_notebook_tab_hover)
        except Exception:
            self._tab_help_hover_poll_id = None
    def _on_notebook_tab_enter(self, _event=None):
        self._cancel_tab_help_hover_poll()
        try:
            self._tab_help_hover_poll_id = self.root.after(40, self._poll_notebook_tab_hover)
        except Exception:
            self._tab_help_hover_poll_id = None
    def _on_notebook_tab_hover(self, event):
        tab_text = self._notebook_tab_text_at_xy(event.x, event.y)
        if tab_text:
            self._show_tab_help_tooltip(event, tab_text)
        else:
            self._hide_tab_help_tooltip()
    def _on_notebook_tab_leave(self, _event=None):
        self._cancel_tab_help_hover_poll()
        self._hide_tab_help_tooltip()
    def _on_notebook_tab_right_click(self, event):
        tab_text = self._notebook_tab_text_at_xy(event.x, event.y)
        if not tab_text:
            return
        self._hide_tab_help_tooltip()
        full = (self.tab_help_map.get(tab_text, {}) or {}).get("full", "").strip()
        if not full:
            return
        messagebox.showinfo(f"{tab_text} Summary", full)
        return "break"
    def _update_notebook_theme(self, _evt=None):
        self._cancel_tab_help_hover_poll()
        self._hide_tab_help_tooltip()
        current = self.notebook.select()
        tab_text = self.notebook.tab(current, "text") if current else ""
        show_banner = bool(current and hasattr(self, "tab_main") and current == str(self.tab_main))
        if hasattr(self, "banner_frame"):
            if show_banner:
                self._stop_fx_editor_video()
                if not getattr(self, "banner_visible", True):
                    self.banner_frame.pack(before=self.main_content, fill="x", padx=30, pady=(0,10))
                    self.banner_visible = True
                self._ensure_banner_image()
                self.fx_video_played = False
            else:
                if getattr(self, "banner_visible", True):
                    self.banner_frame.pack_forget()
                    self.banner_visible = False
        if "FX EDITOR" in tab_text:
            self._play_fx_editor_video_once()
        if "GAME MANAGER" in tab_text:
            self.nb_style.configure("AC.TNotebook", background=COLORS["CHARCOAL"])
            self.nb_style.map("AC.TNotebook.Tab",
                              background=[("selected", COLORS["TAB_GREEN"]), ("!selected", COLORS["SURFACE"])],
                              foreground=[("selected", "black"), ("!selected", COLORS["TEXT"])])
        else:
            self.nb_style.configure("AC.TNotebook", background=COLORS["CHARCOAL"])
            self.nb_style.map("AC.TNotebook.Tab",
                              background=[("selected", COLORS["TAB_BLUE"]), ("!selected", COLORS["SURFACE"])],
                              foreground=[("selected", "black"), ("!selected", COLORS["TEXT"])])
    def open_game_manager(self):
        if not GM_AVAILABLE:
            messagebox.showerror("Error", "ACGameManager.py not found.")
            return
        if self.gm_window and self.gm_window.winfo_exists():
            self.gm_window.lift()
            return
        self.gm_window = tk.Toplevel(self.root)
        def on_gm_close():
            self.gm_window.destroy()
            self.gm_window = None
        self.gm_window.protocol("WM_DELETE_WINDOW", on_gm_close)
        StableStealthManager(self.gm_window)
    def show_help(self):
        if not HELP_AVAILABLE:
            messagebox.showerror("Error", "AMHelp.py not found.")
            return
        if self.help_window and self.help_window.winfo_exists():
            self.help_window.lift()
            return
        self.help_window = tk.Toplevel(self.root)
        def on_help_close():
            self.help_window.destroy()
            self.help_window = None
        self.help_window.protocol("WM_DELETE_WINDOW", on_help_close)
        ArcadeCommanderHelp(self.help_window)
    def quit_now(self):
        self.force_exit = True
        self.on_close()
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
                        upd = True
                        d['phase'] += 0.1 * d.get('speed', 1.0)
                        colors = d.get('colors', [])
                        active = []
                        if colors:
                            active.append(colors[0])
                            for c in colors[1:4]:
                                if isinstance(c, (list, tuple)) and tuple(c) != (0, 0, 0):
                                    active.append(c)
                        if len(active) < 1:
                            active = [d.get('primary', (0, 0, 0))]
                        if len(active) == 1:
                            c = active[0]
                            self.cab.set(n, (int(c[0]), int(c[1]), int(c[2])))
                        else:
                            t = d['phase'] % len(active)
                            i = int(t)
                            f = t - i
                            c1 = active[i]
                            c2 = active[(i + 1) % len(active)]
                            self.cab.set(
                                n,
                                (int(c1[0] + (c2[0] - c1[0]) * f),
                                 int(c1[1] + (c2[1] - c1[1]) * f),
                                 int(c1[2] + (c2[2] - c1[2]) * f)),
                            )
                if upd: self.cab.show()
                if upd:
                    self._sync_alu_emulator()
                else:
                    if getattr(self, "alu_static_preview_lock", False):
                        self._sync_alu_emulator()
                    else:
                        self._tick_effects_engine()
            if not self.force_exit: self.root.after(30, loop)
        loop()

    def note_activity(self):
        self.last_activity_ts = time.time()
        if self.attract_active:
            self.attract_active = False; self.apply_settings_to_hardware()

    def apply_settings_to_hardware(self):
        self.animating = False; self.attract_active = False
        if not self.is_connected():
            try:
                if not (hasattr(self, "cab") and hasattr(self.cab, "reconnect")):
                    return
                try:
                    ok = bool(self.cab.reconnect(getattr(self, "port", None), timeout=0.35))
                except TypeError:
                    ok = bool(self.cab.reconnect(getattr(self, "port", None)))
                if not ok:
                    return
            except Exception:
                return
        hw_ready = self._ensure_hw_ready()
        if not hw_ready and hasattr(self, "status_var"):
            self.status_var.set("Control Deck hardware offline; update sent to ACLighter and will apply after reconnect.")
        try:
            self.cab.set_all((0,0,0))
            for n, d in self.led_state.items():
                if hasattr(self, "cab") and hasattr(self.cab, "LEDS"):
                    if n not in self.cab.LEDS:
                        continue
                self.cab.set(n, d['primary'])
            self.cab.show()
        except Exception:
            # Last-chance reconnect + retry if transport dropped between set/show.
            try:
                if hasattr(self, "cab") and hasattr(self.cab, "reconnect"):
                    try:
                        self.cab.reconnect(getattr(self, "port", None), timeout=0.35)
                    except TypeError:
                        self.cab.reconnect(getattr(self, "port", None))
                    self.cab.set_all((0,0,0))
                    for n, d in self.led_state.items():
                        if hasattr(self, "cab") and hasattr(self.cab, "LEDS") and n not in self.cab.LEDS:
                            continue
                        self.cab.set(n, d['primary'])
                    self.cab.show()
            except Exception:
                pass
        self._sync_alu_emulator()

    def all_off(self):
        self.animating = False
        self.attract_active = False
        if hasattr(self, "effects_enabled"):
            self.effects_enabled = False
        if hasattr(self, "app_config_vars") and isinstance(self.app_config_vars, dict):
            v = self.app_config_vars.get("effects_enabled")
            if v is not None:
                try:
                    v.set(False)
                except Exception:
                    pass
        if hasattr(self, "led_state"):
            for n in self.led_state:
                self.led_state[n]['pulse'] = False
                self.led_state[n]['fx_mode'] = None
                self.led_state[n]['phase'] = 0.0
        if hasattr(self, "pulse_controls"):
            for k, ctrl in self.pulse_controls.items():
                v = ctrl.get('var')
                if v is not None:
                    try:
                        v.set(False)
                    except Exception:
                        pass
        if hasattr(self, "cab"):
            try:
                self.cab.set_all((0, 0, 0))
                self.cab.show()
            except Exception:
                pass
        if hasattr(self, "refresh_gui_from_state"):
            self.refresh_gui_from_state()
        if hasattr(self, "cab") and hasattr(self.cab, "LEDS"):
            off_frame = {name: (0, 0, 0) for name in self.cab.LEDS.keys()}
            self._sync_alu_emulator(off_frame)
        else:
            self._sync_alu_emulator()

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
        elapsed = self._cycle_step * 0.08
        frame_override = {}
        for i, k in enumerate(self.cab.LEDS.keys()):
            col = self._slot_cycle_color_rgb(k, elapsed, speed=2.2, phase_offset=i * 0.35)
            self.cab.set(k, col)
            frame_override[k] = col
        self.cab.show()
        self._sync_alu_emulator(frame_override)
        self._cycle_step += 1
        self.root.after(80, self._run_cycle)

    def start_demo_mode(self): self.animating = True; self._run_demo()
    def _run_demo(self):
        if not self.animating: return
        import random
        frame_override = {}
        for k in self.cab.LEDS:
            col = (random.randint(0,255), random.randint(0,255), random.randint(0,255))
            self.cab.set(k, col)
            frame_override[k] = col
        self.cab.show()
        self._sync_alu_emulator(frame_override)
        self.root.after(150, self._run_demo)

    def start_idle_watchdog(self): self.idle_watchdog_loop()
    def idle_watchdog_loop(self):
        test_active = (self.test_window and self.test_window.winfo_exists())
        if not any([test_active, self.diag_mode]):
            if not (self.effects_enabled and self.effects_engine):
                if time.time() - self.last_activity_ts > 600 and not self.attract_active: self.start_attract_mode()
        if not self.force_exit: self.root.after(5000, self.idle_watchdog_loop)

    def start_attract_mode(self):
        if not self.is_connected(): return
        self.attract_active = True; self.animating = False; self._attract_offset = 0; self.attract_tick()

    def attract_tick(self):
        if not self.attract_active or not self.is_connected(): return
        off = self._attract_offset
        frame_override = {}
        keys = list(self.cab.LEDS.keys())
        for i in range(min(12, len(keys))):
            col = wheel((i*20 + off)%255)
            self.cab.pixels[i] = col
            frame_override[keys[i]] = col
        pulse = int((math.sin(time.time()*3)+1)*127.5)
        self.cab.set("P1_START", (pulse,0,0)); self.cab.set("P2_START", (0,0,pulse))
        frame_override["P1_START"] = (pulse, 0, 0)
        frame_override["P2_START"] = (0, 0, pulse)
        self.cab.show()
        self._sync_alu_emulator(frame_override)
        self._attract_offset = (off+2)%255
        self.root.after(30, self.attract_tick)

    def _get_runtime_mode(self):
        try:
            if "network" in str(APP_VERSION).lower():
                return "Networked"
            port = str(getattr(self.cab, "port", "")).lower()
            if "network" in port:
                return "Networked"
        except Exception:
            pass
        return "Standalone"

    def _get_node_count(self):
        cab = getattr(self, "cab", None)
        if cab is None:
            return 0
        for attr in ("nodes", "clients", "connected_nodes", "connected_clients"):
            try:
                v = getattr(cab, attr, None)
                if isinstance(v, dict):
                    return len(v)
                if isinstance(v, (list, tuple, set)):
                    return len(v)
            except Exception:
                pass
        try:
            return 1 if self.is_connected() else 0
        except Exception:
            return 0

    def _get_app_info(self):
        arch_raw = str(platform.machine() or "").lower()
        arch = "x64" if ("64" in arch_raw or arch_raw in ("amd64", "x86_64")) else (arch_raw or "unknown")
        os_name = "Windows" if os.name == "nt" else (platform.system() or "Unknown")
        return {
            "name": APP_NAME,
            "subtitle": APP_SUBTITLE,
            "semver": APP_SEMVER,
            "channel": APP_CHANNEL,
            "build_date": APP_BUILD_DATE,
            "arch": arch,
            "os": os_name,
            "mode": self._get_runtime_mode(),
            "nodes": self._get_node_count(),
            "copyright": APP_COPYRIGHT,
        }

    def _resolve_text_file_path(self, filename):
        candidates = []
        if getattr(sys, "frozen", False):
            candidates.append(os.path.join(os.path.dirname(sys.executable), filename))
            candidates.append(os.path.join(getattr(sys, "_MEIPASS", ""), filename))
        candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), filename))
        candidates.append(os.path.join(os.getcwd(), filename))
        ap = asset_path(filename)
        if ap:
            candidates.append(ap)
        seen = set()
        for p in candidates:
            if not p:
                continue
            n = os.path.normpath(p)
            if n in seen:
                continue
            seen.add(n)
            if os.path.isfile(n):
                return n
        return None

    def _read_text_file_with_fallback(self, filename, fallback_text):
        path = self._resolve_text_file_path(filename)
        if not path:
            print(f"WARN: {filename} not found. Using embedded fallback text.")
            return fallback_text, None
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(), path
        except Exception as exc:
            print(f"WARN: Failed to read {filename} from {path}: {exc}. Using fallback text.")
            return fallback_text, path

    def _show_text_viewer(self, title, text):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=COLORS["BG"])
        win.geometry("860x680")
        win.transient(self.root)
        win.grab_set()

        hdr = tk.Frame(win, bg=COLORS["CHARCOAL"])
        hdr.pack(fill="x")
        tk.Label(
            hdr,
            text=title,
            bg=COLORS["CHARCOAL"],
            fg=COLORS["P1"],
            font=("Segoe UI", 11, "bold"),
            padx=10,
            pady=8,
        ).pack(side="left")

        wrap = tk.Frame(win, bg=COLORS["BG"])
        wrap.pack(fill="both", expand=True, padx=10, pady=10)
        txt = tk.Text(
            wrap,
            wrap="word",
            bg=COLORS["SURFACE_LIGHT"],
            fg=COLORS["TEXT"],
            insertbackground=COLORS["TEXT"],
            borderwidth=0,
            highlightthickness=0,
            padx=12,
            pady=10,
            font=("Consolas", 10),
        )
        txt.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(wrap, orient="vertical", command=txt.yview)
        sb.pack(side="right", fill="y")
        txt.configure(yscrollcommand=sb.set)
        txt.insert("1.0", text or "")
        txt.config(state="disabled")

        btn_row = tk.Frame(win, bg=COLORS["BG"])
        btn_row.pack(fill="x", padx=10, pady=(0, 10))
        ModernButton(
            btn_row,
            text="Close",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=10,
            font=("Segoe UI", 9, "bold"),
            command=win.destroy,
        ).pack(side="right")

    def _show_aclighter_setup_info(self):
        msg = (
            "ACLighter Setup Information\n\n"
            "Required artifact names (any one):\n"
            "- ACLighter.exe\n"
            "- ACLighter.dll\n"
            "- aclighter.py\n\n"
            "Detection order:\n"
            "1) Configured ACLighter path in app settings (if present)\n"
            "2) Same folder as Arcade Commander executable\n"
            "3) .\\tools\\ACLighter\\\n"
            "4) %ProgramFiles%\\ACLighter\\\n"
            "5) %LOCALAPPDATA%\\ACLighter\\\n\n"
            "Recommended:\n"
            "- Place ACLighter.exe beside ArcadeCommander.exe\n"
            "- Or set an explicit ACLighter path in app settings."
        )
        messagebox.showinfo("ACLighter Setup Info", msg)

    def _copy_system_info(self, acl):
        info = self._get_app_info()
        acl_status = "Detected" if acl.get("detected") else "Not Detected"
        acl_version = acl.get("version") or "Unknown"
        acl_path = acl.get("path") or "â€”"
        text = (
            f"{APP_NAME}\n"
            f"Version: {info['semver']} (ALPHA)\n"
            f"Build: {info['build_date']} | Arch: {info['arch']} | OS: {info['os']}\n"
            f"ACLighter: {acl_status}\n"
            f"ACLighter Version: {acl_version}\n"
            f"ACLighter Path: {acl_path}\n"
            f"Mode: {info['mode']}\n"
            f"Nodes: {info['nodes']}\n"
        )
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            messagebox.showinfo("Copied", "System info copied to clipboard.")
        except Exception:
            messagebox.showerror("Copy Failed", "Unable to copy system info to clipboard.")

    def show_about(self):
        if self.about_window and self.about_window.winfo_exists():
            self.about_window.lift()
            return

        info = self._get_app_info()
        dlg = tk.Toplevel(self.root)
        self.about_window = dlg
        dlg.title(f"About {APP_NAME}")
        dlg.configure(bg=COLORS["BG"])
        dlg.geometry("820x700")
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.resizable(False, False)

        def _close_about():
            try:
                dlg.grab_release()
            except Exception:
                pass
            dlg.destroy()
            self.about_window = None

        dlg.protocol("WM_DELETE_WINDOW", _close_about)

        # Header
        head = tk.Frame(dlg, bg=COLORS["CHARCOAL"], padx=14, pady=10)
        head.pack(fill="x")
        tk.Frame(head, bg=COLORS["P1"], height=2).pack(fill="x", pady=(0, 8))
        tk.Label(head, text=info["name"], bg=COLORS["CHARCOAL"], fg=COLORS["TEXT"], font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(head, text=info["subtitle"], bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 10)).pack(anchor="w")
        tk.Label(
            head,
            text=f"Version: {info['semver']}   |   Channel: {info['channel']}   |   Build: {info['build_date']} | Arch: {info['arch']} | OS: {info['os']}",
            bg=COLORS["CHARCOAL"],
            fg=COLORS["SYS"],
            font=("Consolas", 9, "bold"),
        ).pack(anchor="w", pady=(8, 0))

        body = tk.Frame(dlg, bg=COLORS["BG"], padx=14, pady=12)
        body.pack(fill="both", expand=True)

        # Alpha notice
        alpha_box = tk.Frame(body, bg=COLORS["SURFACE_LIGHT"], padx=10, pady=8)
        alpha_box.pack(fill="x", pady=(0, 10))
        tk.Label(
            alpha_box,
            text="ALPHA BUILD: Intended for testing. Features may change and stability is not guaranteed.",
            bg=COLORS["SURFACE_LIGHT"],
            fg=COLORS["SYS"],
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")
        tk.Label(
            alpha_box,
            text="Not intended for production arcade environments.",
            bg=COLORS["SURFACE_LIGHT"],
            fg=COLORS["TEXT"],
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(2, 0))

        # Description
        tk.Label(
            body,
            text="Network-enabled arcade lighting and control platform for per-game profiles, controller mapping, and synchronized GRB LED effects.",
            bg=COLORS["BG"],
            fg=COLORS["TEXT"],
            justify="left",
            wraplength=770,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(0, 10))

        # Capabilities
        cap_box = tk.LabelFrame(body, text=" KEY CAPABILITIES ", bg=COLORS["CHARCOAL"], fg=COLORS["P1"], font=("Segoe UI", 9, "bold"), padx=10, pady=8)
        cap_box.pack(fill="x", pady=(0, 10))
        for line in (
            "\u2022 Per-Game Profiles",
            "\u2022 Player 1 / System / Player 2 Zones",
            "\u2022 GRB LED Effects Engine",
            "\u2022 Network Sync & Remote Nodes",
            "\u2022 Emulator / Game Mapping",
            "\u2022 FX Editor",
            "\u2022 Controller Config",
        ):
            tk.Label(cap_box, text=line, bg=COLORS["CHARCOAL"], fg=COLORS["TEXT"], anchor="w", font=("Segoe UI", 9)).pack(fill="x")

        # Required components
        req = tk.LabelFrame(body, text=" REQUIRED COMPONENTS ", bg=COLORS["CHARCOAL"], fg=COLORS["SYS"], font=("Segoe UI", 9, "bold"), padx=10, pady=8)
        req.pack(fill="x", pady=(0, 10))
        tk.Label(req, text="ACLighter â€” REQUIRED", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT"], font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")

        acl_status_var = tk.StringVar(value="Checking...")
        acl_version_var = tk.StringVar(value="Checking...")
        acl_path_var = tk.StringVar(value="Checking...")
        acl_warn_var = tk.StringVar(value="")
        acl_result = {"detected": False, "version": None, "path": None, "note": None}

        tk.Label(req, text="Status:", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).grid(row=1, column=0, sticky="w", pady=(6, 0))
        acl_status_lbl = tk.Label(req, textvariable=acl_status_var, bg=COLORS["CHARCOAL"], fg=COLORS["TEXT"], font=("Segoe UI", 8, "bold"))
        acl_status_lbl.grid(row=1, column=1, sticky="w", pady=(6, 0), padx=(8, 0))
        tk.Label(req, text="Version:", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).grid(row=2, column=0, sticky="w")
        tk.Label(req, textvariable=acl_version_var, bg=COLORS["CHARCOAL"], fg=COLORS["TEXT"], font=("Consolas", 8)).grid(row=2, column=1, sticky="w", padx=(8, 0))
        tk.Label(req, text="Location:", bg=COLORS["CHARCOAL"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 8, "bold")).grid(row=3, column=0, sticky="w")
        tk.Label(req, textvariable=acl_path_var, bg=COLORS["CHARCOAL"], fg=COLORS["TEXT"], font=("Consolas", 8), wraplength=620, justify="left").grid(row=3, column=1, sticky="w", padx=(8, 0))
        acl_warn_lbl = tk.Label(req, textvariable=acl_warn_var, bg=COLORS["CHARCOAL"], fg=COLORS["SYS"], font=("Segoe UI", 8, "bold"))
        acl_warn_lbl.grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))
        setup_btn = ModernButton(
            req,
            text="ACLighter Setup Info",
            bg=COLORS["SURFACE_LIGHT"],
            fg="white",
            width=18,
            font=("Segoe UI", 8, "bold"),
            command=self._show_aclighter_setup_info,
        )
        setup_btn.grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 0))
        setup_btn.grid_remove()

        req.columnconfigure(1, weight=1)

        # Credits
        credits = tk.Frame(body, bg=COLORS["BG"])
        credits.pack(fill="x", pady=(4, 8))
        tk.Label(credits, text=info["copyright"], bg=COLORS["BG"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(credits, text="Released under the MIT License.", bg=COLORS["BG"], fg=COLORS["TEXT_DIM"], font=("Segoe UI", 9)).pack(anchor="w")

        # Buttons
        btn_row = tk.Frame(body, bg=COLORS["BG"])
        btn_row.pack(fill="x", pady=(8, 0))

        def _view_license():
            text, _path = self._read_text_file_with_fallback("LICENSE.txt", MIT_LICENSE_FALLBACK)
            self._show_text_viewer("MIT License", text)

        def _view_third_party():
            text, _path = self._read_text_file_with_fallback("THIRD_PARTY_NOTICES.txt", THIRD_PARTY_NOTICES_FALLBACK)
            self._show_text_viewer("Third-Party Notices", text)

        ModernButton(btn_row, text="View License", bg=COLORS["SURFACE_LIGHT"], fg="white", width=14, font=("Segoe UI", 9, "bold"), command=_view_license).pack(side="left")
        ModernButton(btn_row, text="Third-Party Notices", bg=COLORS["SURFACE_LIGHT"], fg="white", width=18, font=("Segoe UI", 9, "bold"), command=_view_third_party).pack(side="left", padx=(8, 0))
        ModernButton(btn_row, text="Copy System Info", bg=COLORS["P1"], fg="black", width=16, font=("Segoe UI", 9, "bold"), command=lambda: self._copy_system_info(acl_result)).pack(side="left", padx=(8, 0))
        ModernButton(btn_row, text="Close", bg=COLORS["DANGER"], fg="white", width=10, font=("Segoe UI", 9, "bold"), command=_close_about).pack(side="right")

        def _apply_acl_result(res):
            acl_result.update(res or {})
            detected = bool(acl_result.get("detected"))
            status = "Detected" if detected else "Not Detected"
            version = acl_result.get("version") or "Unknown"
            path = acl_result.get("path") or "\u2014"
            acl_status_var.set(status)
            acl_version_var.set(version)
            acl_path_var.set(path)
            if detected:
                acl_status_lbl.config(fg=COLORS["SUCCESS"])
                acl_warn_var.set("")
                setup_btn.grid_remove()
            else:
                acl_status_lbl.config(fg=COLORS["SYS"])
                acl_warn_var.set("ACLighter not detected. Lighting features will be unavailable.")
                setup_btn.grid()

        if self._aclighter_detect_cache is not None:
            _apply_acl_result(self._aclighter_detect_cache)
        else:
            def _worker():
                res = DetectACLighter(self.app_settings)
                self._aclighter_detect_cache = res
                try:
                    if dlg.winfo_exists():
                        self.root.after(0, lambda: _apply_acl_result(res))
                except Exception:
                    pass
            threading.Thread(target=_worker, daemon=True).start()
    
    def create_default_profile(self):
        defaults = {}
        for k in self.cab.LEDS.keys():
            primary, secondary, colors = self._default_colors_for(k)
            defaults[k] = {
                'primary': primary,
                'secondary': secondary,
                'colors': list(colors),
                'fx':[None,None,None,None],
                'pulse': False,
                'speed': 1.0
            }
        try:
            target = getattr(self, "default_profile_path", profile_file("default.json"))
            with open(target, "w") as f:
                json.dump({"leds": defaults}, f, indent=4)
            self.load_profile_internal(target, silent=True)
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
                    colors = s.get('colors')
                    if not colors:
                        colors = [
                            tuple(s.get('primary', (0,0,0))),
                            tuple(s.get('secondary', (0,0,0))),
                            (0,0,0),
                            (0,0,0),
                        ]
                    self.led_state[n].update({
                        'primary': tuple(s.get('primary', colors[0])), 
                        'secondary': tuple(s.get('secondary', colors[1])), 
                        'colors': [tuple(c) for c in colors],
                        'fx': s.get('fx', [None, None, None, None]),
                        'pulse': bool(s.get('pulse', False)), 
                        'speed': float(s.get('speed', 1.0)),
                        'fx_mode': s.get('fx_mode'),
                        'phase': float(s.get('phase', 0.0)),
                    })
            self.refresh_gui_from_state()
            if self.is_connected(): self.apply_settings_to_hardware()
            self.update_last_profile_path(filename)
            if not silent: messagebox.showinfo("Loaded", "Profile Loaded")
        except: pass
    def refresh_gui_from_state(self):
        for n, btn in self.buttons.items():
            if n in self.led_state:
                self._ensure_color_slots(n)
                cols = [self._rgb_to_hex(*c) for c in self.led_state[n]['colors']]
                if hasattr(btn, "set_colors"):
                    btn.set_colors(cols)
                else:
                    btn.set_base_bg(cols[0])
        for ref in self.master_refs:
            self._apply_group_button_colors(ref.get('btn'), ref.get('group'), ref.get('mode'))
        for k, ctrl in self.pulse_controls.items():
            first_btn = ctrl['buttons'][0]
            if first_btn in self.led_state:
                is_pulsing = self.led_state[first_btn]['pulse']
                speed = self.led_state[first_btn]['speed']
                v = ctrl.get('var')
                if v is not None:
                    v.set(is_pulsing)
                s = ctrl.get('scale')
                if s is not None:
                    s.set(speed)
                speed_scale = ctrl.get('speed_scale')
                if speed_scale is not None:
                    speed_scale.set(speed)
                mode_vars = ctrl.get('mode_vars')
                if mode_vars is not None:
                    fx_mode = self.led_state[first_btn].get('fx_mode')
                    for m, var in mode_vars.items():
                        var.set(m == fx_mode)
                    ctrl['current_mode'] = fx_mode if fx_mode in mode_vars else None

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
            if getattr(self, "audio_tmp_path", None):
                try: os.unlink(self.audio_tmp_path)
                except: pass
                self.audio_tmp_path = None
            self._cleanup_trimmed_preview_audio()
            if getattr(self, "fx_video_audio_path", None):
                try: os.unlink(self.fx_video_audio_path)
                except: pass
                self.fx_video_audio_path = None
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

