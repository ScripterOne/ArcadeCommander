"""
Arcade Commander V2.0 - Serial Driver (Dynamic Fix)
---------------------------------------------------
INTELLIGENCE:
1. Dynamic LED Count: Automatically adjusts header based on how many pixels exist.
"""

import struct
import time
import serial

try:
    from serial.tools import list_ports
    _HAS_LIST_PORTS = True
except Exception:
    _HAS_LIST_PORTS = False

# --- CONFIGURATION ---
DEFAULT_PORT = "COM3"
DEFAULT_BAUD = 230400
DEFAULT_LEDS = 30  # Default only, overridden by usage

# --- HARDWARE QUIRKS ---
BUTTON_ORDER = "BRG"     
TRACKBALL_ORDER = "GRB"  

# --- PIN MAPPING ---
PIN_MAP = {
    "P1_A": 0, "P1_B": 1, "P1_C": 2, "P1_X": 3, "P1_Y": 4, "P1_Z": 5,
    "P2_A": 6, "P2_B": 7, "P2_C": 8, "P2_X": 9, "P2_Y": 10, "P2_Z": 11,
    "REWIND": 12, "P1_START": 13, "MENU": 14, "P2_START": 15, "TRACKBALL": 16,
}

def available_ports():
    ports = []
    if _HAS_LIST_PORTS:
        for p in list_ports.comports():
            if getattr(p, "device", None): ports.append(p.device)
    return ports

def wheel(pos):
    if pos < 85: return (pos * 3, 255 - pos * 3, 0)
    elif pos < 170: pos -= 85; return (255 - pos * 3, 0, pos * 3)
    else: pos -= 170; return (0, pos * 3, 255 - pos * 3)

class Arcade:
    def __init__(self, port=None, baud=DEFAULT_BAUD, led_count=DEFAULT_LEDS):
        self.LEDS = PIN_MAP
        self.mode = "NONE"
        self.ser = None
        # Initialize pixels with the requested count
        self.pixels = [(0,0,0)] * led_count
        self.baud = baud or DEFAULT_BAUD
        self.reconnect(port)

    def reconnect(self, port=None):
        self.close()
        self.mode = "SERIAL"
        self._connect_serial(port, self.baud)

    def is_connected(self): return self.mode != "NONE"

    def _connect_serial(self, port, baud):
        if not port:
            ports = available_ports()
            port = ports[0] if ports else DEFAULT_PORT
            
        try:
            self.ser = serial.Serial(port, baud, timeout=1)
            self.ser.dtr = False 
            time.sleep(1) 
            print(f"[Driver] Opened {port} @ {baud}")
        except Exception as e: print(f"[Driver] Serial Error: {e}")

    def set(self, n, c):
        idx = n if isinstance(n, int) else PIN_MAP.get(n, -1)
        if 0 <= idx < len(self.pixels):
            self.pixels[idx] = c

    def set_all(self, c):
        # Keep the current length, just update colors
        self.pixels = [c] * len(self.pixels)

    def show(self):
        if self.mode == "SERIAL": self._serial_write()

    def close(self):
        if self.ser: self.ser.close()
        self.mode = "NONE"

    def _serial_write(self):
        if not self.ser: return
        
        # --- DYNAMIC COUNT FIX ---
        # We calculate count based on the ACTUAL buffer size, not a hardcoded constant
        num_leds = len(self.pixels)
        count = num_leds - 1
        
        # Checksum logic (Standard Adalight)
        checksum = ((count >> 8) & 0xFF) ^ (count & 0xFF) ^ 0x55
        header = struct.pack(">3sBBB", b"Ada", (count >> 8) & 0xFF, count & 0xFF, checksum)
        
        payload = bytearray()
        for i, (r, g, b) in enumerate(self.pixels):
            # Quirk Logic
            if i == 16: mode = TRACKBALL_ORDER
            else: mode = BUTTON_ORDER
            
            if mode == "GRB": payload.extend((g, r, b))
            elif mode == "BRG": payload.extend((b, r, g))
            else: payload.extend((r, g, b)) 
            
        try:
            self.ser.write(header + payload)
        except: pass
