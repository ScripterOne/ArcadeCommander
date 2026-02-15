import socket
import json
import time

# CONFIGURATION
ACLIGHTER_HOST = "127.0.0.1"
ACLIGHTER_PORT = 6006

# --- MAPPING (Index -> Name) ---
PIN_MAP = {
    0: "P1_A", 1: "P1_B", 2: "P1_C", 3: "P1_X", 4: "P1_Y", 5: "P1_Z",
    6: "P2_A", 7: "P2_B", 8: "P2_C", 9: "P2_X", 10: "P2_Y", 11: "P2_Z",
    12: "REWIND", 13: "P1_START", 14: "MENU", 15: "P2_START", 16: "TRACKBALL"
}

# --- HELPER FUNCTIONS ---
def available_ports():
    return ["AC Service (Port 6006)"]

def wheel(pos):
    if pos < 85: return (pos * 3, 255 - pos * 3, 0)
    elif pos < 170: pos -= 85; return (255 - pos * 3, 0, pos * 3)
    else: pos -= 170; return (0, pos * 3, 255 - pos * 3)

# --- THE IMPOSTER CLASS ---
class Arcade:
    def __init__(self, port=None):
        self.pixels = {} 
        self.connected = False
        self.port = "Network" 
        self.LEDS = {v: k for k, v in PIN_MAP.items()} 
        self._last_probe_ts = 0.0
        self.last_status = None
        self.reconnect()

    def reconnect(self, port=None, timeout=0.35):
        was_connected = bool(self.connected)
        self._last_probe_ts = time.time()
        try:
            with socket.create_connection((ACLIGHTER_HOST, ACLIGHTER_PORT), timeout=timeout):
                self.connected = True
                if not was_connected:
                    print("[Adapter] Connected to ACLighter.")
                return True
        except:
            self.connected = False
            return False

    def is_connected(self):
        # Keep this fast/non-blocking; reconnection is attempted at send sites.
        return self.connected

    def set(self, index_or_name, color):
        target = index_or_name
        if isinstance(index_or_name, int):
            target = PIN_MAP.get(index_or_name)
        
        if target:
            if isinstance(color, (tuple, list)):
                c_str = f"{int(color[0])},{int(color[1])},{int(color[2])}"
            else:
                c_str = "0,0,0"
            self.pixels[target] = c_str

    def set_all(self, color):
        if isinstance(color, (tuple, list)):
            c_str = f"{int(color[0])},{int(color[1])},{int(color[2])}"
        else:
            c_str = "0,0,0"
        for name in PIN_MAP.values():
            self.pixels[name] = c_str

    def show(self):
        if not self.pixels:
            return
        if not self.connected:
            if not self.reconnect(timeout=0.25):
                return
        payload = {
            "command": "STATE_UPDATE",
            "mode": "GAME",
            "data": self.pixels.copy()
        }
        if not self._send_packet(payload):
            # One retry path for transient socket/service hiccups.
            if self.reconnect(timeout=0.35):
                self._send_packet(payload)

    def _send_packet(self, data):
        try:
            with socket.create_connection((ACLIGHTER_HOST, ACLIGHTER_PORT), timeout=0.35) as sock:
                sock.sendall(json.dumps(data).encode('utf-8'))
                self.connected = True
                self._last_probe_ts = time.time()
                return True
        except:
            self.connected = False
            return False

    def get_status(self, timeout=0.5):
        was_connected = bool(self.connected)
        payload = {"command": "PING"}
        try:
            with socket.create_connection((ACLIGHTER_HOST, ACLIGHTER_PORT), timeout=timeout) as sock:
                sock.sendall(json.dumps(payload).encode("utf-8"))
                sock.shutdown(socket.SHUT_WR)
                raw = sock.recv(4096).decode("utf-8").strip()
            if not raw:
                # Backward-compat: older ACLighter builds may not respond to PING.
                self.connected = True
                return None
            info = json.loads(raw)
            if isinstance(info, dict):
                self.connected = True
                self._last_probe_ts = time.time()
                self.last_status = info
                return info
        except:
            # Status probing must never flap a previously good connection.
            self.connected = was_connected
        return None

    def request_driver_reconnect(self, timeout=2.5):
        was_connected = bool(self.connected)
        payload = {"command": "RECONNECT_DRIVER"}
        try:
            with socket.create_connection((ACLIGHTER_HOST, ACLIGHTER_PORT), timeout=timeout) as sock:
                sock.sendall(json.dumps(payload).encode("utf-8"))
                sock.shutdown(socket.SHUT_WR)
                raw = sock.recv(4096).decode("utf-8").strip()
            if raw:
                info = json.loads(raw)
                if isinstance(info, dict):
                    self.connected = True
                    self._last_probe_ts = time.time()
                    self.last_status = info
                    return info
            self.connected = True
        except:
            self.connected = was_connected
        return None

    def close(self):
        pass
