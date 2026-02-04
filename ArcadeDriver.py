"""
Arcade Commander - ArcadeDriver (v5.3+ port-init patch)

Key improvements:
- Arcade(port=..., baud=...) supported (keyword args accepted)
- reconnect(port) method to switch COM ports without restarting the app
- available_ports() helper for GUI port picker
- send_frame(frame) for direct 30-LED frame writes (used by ArcadeTester / attract)
- wheel(pos) color helper

This module keeps the Adalight header format and your per-index color order rules.
"""

import struct
import time

import serial
from serial import SerialTimeoutException

try:
    from serial.tools import list_ports
    _HAS_LIST_PORTS = True
except Exception:
    _HAS_LIST_PORTS = False


# --- DEFAULT CONFIGURATION ---
DEFAULT_PORT = "COM3"
DEFAULT_BAUD = 230400
NUM_LEDS = 30

# 0.02 = 50 FPS cap (smooth + safer on serial)
THROTTLE = 0.02

# --- COLOR ORDER CONFIGURATION ---
BUTTON_ORDER = "BRG"     # most button channels
TRACKBALL_ORDER = "GRB"  # pin 17 / index 16


def available_ports():
    """Return a list of COM port device names like ['COM3','COM7']."""
    if not _HAS_LIST_PORTS:
        return []
    ports = []
    for p in list_ports.comports():
        # On Windows p.device is like 'COM3'
        if getattr(p, "device", None):
            ports.append(p.device)
    return ports


def wheel(pos: int):
    """Color wheel helper (0..255)."""
    pos = int(pos) % 256
    if pos < 85:
        return (pos * 3, 255 - pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (255 - pos * 3, 0, pos * 3)
    pos -= 170
    return (0, pos * 3, 255 - pos * 3)


class Arcade:
    """
    Adalight-compatible WS2812B controller driver for PicoCTR + WS2812B adapter.

    Note: Many older builds hard-coded DEFAULT_PORT in __init__.
    This version keeps defaults but allows overriding port/baud safely.
    """

    LEDS = {
        # Player 1
        "P1_A": 0, "P1_B": 1, "P1_C": 2,
        "P1_X": 3, "P1_Y": 4, "P1_Z": 5,

        # Player 2
        "P2_A": 6, "P2_B": 7, "P2_C": 8,
        "P2_X": 9, "P2_Y": 10, "P2_Z": 11,

        # Admin / Starts
        "REWIND": 12,
        "P1_START": 13,
        "MENU": 14,
        "P2_START": 15,

        # Trackball (Pin 17) -> index 16
        "TRACKBALL": 16,
    }

    def __init__(self, port: str | None = None, baud: int | None = None):
        self.port = port or DEFAULT_PORT
        self.baud = int(baud or DEFAULT_BAUD)
        self.ser = None
        self.pixels = [(0, 0, 0)] * NUM_LEDS
        self._last_write = 0.0

        self._open_serial(self.port, self.baud)

    # ---------------- Connection ----------------
    def _open_serial(self, port: str, baud: int):
        try:
            # write_timeout prevents infinite hangs if a frame stalls
            self.ser = serial.Serial(port, baud, timeout=1, write_timeout=0.1)
            self.port = port
            self.baud = int(baud)
            time.sleep(2)  # allow MCU boot/reset
            print(f"Arcade Controller Connected on {self.port} @ {self.baud}bps")
        except Exception as e:
            print(f"Hardware Connection Failed: {e}")
            self.ser = None

    def reconnect(self, port: str | None = None, baud: int | None = None):
        """Close and reopen serial on a new COM port / baud."""
        new_port = port or self.port or DEFAULT_PORT
        new_baud = int(baud or self.baud or DEFAULT_BAUD)
        try:
            if self.ser:
                try:
                    self.ser.close()
                except Exception:
                    pass
        finally:
            self.ser = None

        self._open_serial(new_port, new_baud)

    def is_connected(self) -> bool:
        return self.ser is not None

    # ---------------- Pixel State ----------------
    def set(self, name: str, color: tuple[int, int, int]):
        if name in self.LEDS:
            self.pixels[self.LEDS[name]] = tuple(map(int, color))

    def set_all(self, color: tuple[int, int, int]):
        c = tuple(map(int, color))
        self.pixels = [c] * NUM_LEDS

    def send_frame(self, frame):
        """
        Immediately write a full 30-LED frame to hardware.
        frame: iterable of 30 tuples (r,g,b)
        """
        if not frame:
            return
        # normalize length
        pixels = list(frame)[:NUM_LEDS]
        if len(pixels) < NUM_LEDS:
            pixels += [(0, 0, 0)] * (NUM_LEDS - len(pixels))
        self.pixels = [tuple(map(int, c)) for c in pixels]
        self.show()

    # ---------------- Adalight Write ----------------
    def show(self):
        if not self.ser:
            return

        # throttle writes to avoid overruns
        now = time.time()
        if (now - self._last_write) < THROTTLE:
            return
        self._last_write = now

        count = NUM_LEDS - 1
        checksum = ((count >> 8) & 0xFF) ^ (count & 0xFF) ^ 0x55
        header = struct.pack(">3sBBB", b"Ada", (count >> 8) & 0xFF, count & 0xFF, checksum)

        payload = bytearray()
        for i, (r, g, b) in enumerate(self.pixels):
            if i == 16:
                mode = TRACKBALL_ORDER.strip().upper()
            else:
                mode = BUTTON_ORDER.strip().upper()

            if mode == "GRB":
                payload.extend((g, r, b))
            elif mode == "BGR":
                payload.extend((b, g, r))
            elif mode == "RBG":
                payload.extend((r, b, g))
            elif mode == "GBR":
                payload.extend((g, b, r))
            elif mode == "BRG":
                payload.extend((b, r, g))
            else:
                payload.extend((r, g, b))

        try:
            self.ser.write(header + payload)
        except SerialTimeoutException:
            # Skip this frame. Do not crash the app.
            print("Serial Write Timeout - Skipping Frame")
            try:
                self.ser.reset_output_buffer()
            except Exception:
                pass
        except Exception as e:
            print(f"Serial Error: {e}")

    def close(self):
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None
