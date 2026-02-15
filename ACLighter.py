import threading
import socket
import json
import time
import sys
import math
import random
import os
from PIL import Image, ImageDraw
from AnimationRegistry import resolve_animation

# --- DEPENDENCIES ---
try:
    from ArcadeDriver import Arcade
except ImportError:
    print("[CRITICAL] ArcadeDriver.py not found.")
    sys.exit(1)

try:
    import pystray
    from pystray import MenuItem as item
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

CONFIG_PORT = 6006
LED_COUNT = 17 

def normalize_color(value):
    if value is None:
        return None
    if isinstance(value, (tuple, list)) and len(value) == 3:
        try:
            r, g, b = int(value[0]), int(value[1]), int(value[2])
            return (r, g, b)
        except:
            return None

    raw = str(value)
    if "|" in raw:
        raw = raw.split("|", 1)[0]
    raw = raw.strip()

    if raw.startswith("#") and len(raw) == 7:
        try:
            r = int(raw[1:3], 16)
            g = int(raw[3:5], 16)
            b = int(raw[5:7], 16)
            return (r, g, b)
        except:
            return None

    raw = raw.replace("[", "").replace("]", "").replace(" ", "")
    parts = raw.split(",")
    if len(parts) == 3:
        try:
            r = int(parts[0]); g = int(parts[1]); b = int(parts[2])
            return (r, g, b)
        except:
            return None
    return None

class StateManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.running = True
        self.connected = False
        self.port_name = "Searching..."
        self.service_pid = os.getpid()
        self.listener_bound = False
        self.listener_error = ""
        self.state_update_count = 0
        self.animation_update_count = 0
        
        self.current_state = {
            "mode": "IDLE",       
            "anim_type": None,    
            "leds": {},           
            "phase": 0.0          
        }

        self.driver = Arcade()
        # Force optimized count
        if hasattr(self.driver, 'pixels'):
            self.driver.pixels = [(0,0,0)] * LED_COUNT

        self._check_connection()

        self.net_thread = threading.Thread(target=self._listener_loop, daemon=True)
        self.net_thread.start()

        self.brain_thread = threading.Thread(target=self._brain_loop, daemon=True)
        self.brain_thread.start()

    def _check_connection(self):
        if self.driver.is_connected():
            self.connected = True
            self.port_name = getattr(self.driver, 'ser', None) and self.driver.ser.portstr or "Connected"
        else:
            self.connected = False
            self.port_name = "No Hardware"

    def _listener_loop(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Enforce single ACLighter owner of port 6006.
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                server.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            else:
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('127.0.0.1', CONFIG_PORT))
            server.listen(5)
            self.listener_bound = True
            self.listener_error = ""
            print(f"[ACLighter] Listening on 127.0.0.1:{CONFIG_PORT} (pid={self.service_pid})")
        except Exception as e:
            self.listener_bound = False
            self.listener_error = str(e)
            print(f"[ACLighter] Listener bind failed on port {CONFIG_PORT}: {e}")
            self.running = False
            try:
                server.close()
            except Exception:
                pass
            return

        while self.running:
            try:
                client, addr = server.accept()
                threading.Thread(target=self._handle_client, args=(client,), daemon=True).start()
            except: pass
        try:
            server.close()
        except Exception:
            pass

    def _handle_client(self, client):
        try:
            raw = client.recv(4096).decode('utf-8').strip()
            if not raw: return
            package = json.loads(raw)
            
            with self.lock:
                cmd = package.get('command')
                if cmd == 'PING':
                    status = {
                        "ok": True,
                        "service": "ACLighter",
                        "pid": self.service_pid,
                        "listener_bound": bool(self.listener_bound),
                        "listener_error": self.listener_error,
                        "state_updates": int(self.state_update_count),
                        "animation_updates": int(self.animation_update_count),
                        "connected": bool(self.connected),
                        "driver_connected": bool(self.driver.is_connected()),
                        "port": self.port_name,
                        "mode": self.current_state.get("mode", "IDLE"),
                    }
                    try:
                        client.sendall(json.dumps(status).encode("utf-8"))
                    except:
                        pass
                    return

                elif cmd == 'RECONNECT_DRIVER':
                    ok = False
                    try:
                        ok = bool(self.driver.reconnect())
                    except:
                        ok = False
                    self._check_connection()
                    status = {
                        "ok": ok,
                        "service": "ACLighter",
                        "pid": self.service_pid,
                        "listener_bound": bool(self.listener_bound),
                        "listener_error": self.listener_error,
                        "state_updates": int(self.state_update_count),
                        "animation_updates": int(self.animation_update_count),
                        "connected": bool(self.connected),
                        "driver_connected": bool(self.driver.is_connected()),
                        "port": self.port_name,
                        "mode": self.current_state.get("mode", "IDLE"),
                    }
                    try:
                        client.sendall(json.dumps(status).encode("utf-8"))
                    except:
                        pass
                    return

                if cmd == 'STATE_UPDATE':
                    self.current_state['mode'] = package.get('mode', 'IDLE')
                    raw_data = package.get('data', {})
                    new_leds = {}
                    for k, v in raw_data.items():
                        color = normalize_color(v)
                        if color is not None:
                            new_leds[k] = color
                    self.current_state['leds'] = new_leds
                    self.state_update_count += 1

                elif cmd == 'ANIMATION':
                    self.current_state['mode'] = 'ANIMATION'
                    anim = resolve_animation(package.get('type', 'RAINBOW')) or 'RAINBOW'
                    self.current_state['anim_type'] = anim
                    self.current_state['phase'] = 0.0
                    self.animation_update_count += 1
                    print(f"[ACLighter] Started Intensity Mode: {self.current_state['anim_type']}")
        except: pass
        finally: client.close()

    def _brain_loop(self):
        while self.running:
            if not self.driver.is_connected():
                self.driver.reconnect(); self._check_connection(); time.sleep(2); continue
            
            self._check_connection()

            with self.lock:
                mode = self.current_state['mode']
                
                if mode == "GAME":
                    for name, color in self.current_state['leds'].items():
                        self.driver.set(name, color)
                    self.driver.show()

                elif mode == "ANIMATION":
                    anim = self.current_state['anim_type']
                    self.current_state['phase'] += 0.2
                    phase = self.current_state['phase']

                    if anim == "RAINBOW":
                        for i in range(LED_COUNT):
                            hue = int((i * 10 + phase * 5) % 255)
                            self.driver.set(i, self._wheel(hue))
                            
                    elif anim == "PULSE_RED":
                        b = int(255 * ((math.sin(phase) + 1) / 2))
                        self.driver.set_all((b, 0, 0))
                        
                    elif anim == "PULSE_BLUE":
                        b = int(255 * ((math.sin(phase) + 1) / 2))
                        self.driver.set_all((0, 0, b))
                    elif anim == "PULSE_GREEN":
                        b = int(255 * ((math.sin(phase) + 1) / 2))
                        self.driver.set_all((0, b, 0))

                    # --- INTENSITY TEST 1: PLASMA ---
                    # Calculates complex sine wave interference per pixel
                    elif anim == "PLASMA":
                        t = phase * 0.5
                        for i in range(LED_COUNT):
                            # Combine two sine waves
                            v = math.sin(t + i * 0.5) + math.sin(t * 2 + i * 0.2)
                            # Map to RGB
                            r = int((math.sin(v) + 1) * 127)
                            g = int((math.cos(v) + 1) * 127)
                            b = int((math.sin(v + 1) + 1) * 127)
                            self.driver.set(i, (r, g, b))

                    # --- INTENSITY TEST 2: HYPER STROBE ---
                    # Flashes full brightness on/off every frame
                    elif anim == "HYPER_STROBE":
                        # Modulo 2 on an integer counter creates a 0, 1, 0, 1 pattern
                        frame_tick = int(time.time() * 20) # 20 Hz Strobe
                        if frame_tick % 2 == 0:
                            self.driver.set_all((255, 255, 255))
                        else:
                            self.driver.set_all((0, 0, 0))

                    self.driver.show()

                elif mode == "IDLE":
                    self.driver.set_all((0,0,0))
                    self.driver.show()

            # 60 FPS Lock
            time.sleep(0.016)

    def _wheel(self, pos):
        if pos < 85: return (pos * 3, 255 - pos * 3, 0)
        elif pos < 170: pos -= 85; return (255 - pos * 3, 0, pos * 3)
        else: pos -= 170; return (0, pos * 3, 255 - pos * 3)

    def stop(self):
        self.running = False
        if self.driver: self.driver.close()

class TrayApp:
    def __init__(self, manager):
        self.mgr = manager
        self.icon = None

    def create_image(self, color):
        image = Image.new('RGB', (64, 64), (30, 30, 30))
        ImageDraw.Draw(image).rectangle((16, 16, 48, 48), fill=color)
        return image

    def update_icon(self):
        if not self.icon: return
        while self.mgr.running:
            color = "#00C853" if self.mgr.connected else "#D50000"
            self.icon.icon = self.create_image(color)
            self.icon.title = f"AC Lighter: {self.mgr.port_name} (17 LEDs)"
            time.sleep(1)

    def on_exit(self, icon, item):
        self.mgr.stop(); icon.stop(); os._exit(0)

    def trigger_anim(self, name):
        with self.mgr.lock:
            self.mgr.current_state['mode'] = "ANIMATION"
            self.mgr.current_state['anim_type'] = name

    def run(self):
        if not TRAY_AVAILABLE:
            try:
                while True: time.sleep(1)
            except KeyboardInterrupt: self.mgr.stop()
            return
        
        menu = pystray.Menu(
            item("STRESS: Plasma", lambda: self.trigger_anim("PLASMA")),
            item("STRESS: Hyper Strobe", lambda: self.trigger_anim("HYPER_STROBE")),
            pystray.Menu.SEPARATOR,
            item("Test: Rainbow", lambda: self.trigger_anim("RAINBOW")),
            item("Reset (Off)", lambda: self.trigger_anim("IDLE")),
            item("Exit", self.on_exit)
        )
        self.icon = pystray.Icon("ACLighter", self.create_image("#D50000"), "Init...", menu)
        threading.Thread(target=self.update_icon, daemon=True).start()
        self.icon.run()

if __name__ == "__main__":
    app_logic = StateManager()
    gui = TrayApp(app_logic)
    gui.run()
