import sys
import json
import socket
import os
import argparse

from vendor_palette import get_vendor_colors
from app_paths import game_db_file, keymap_dir, migrate_legacy_runtime_files

# CONFIGURATION
ACLIGHTER_HOST = "127.0.0.1"
ACLIGHTER_PORT = 6006
migrate_legacy_runtime_files()
DB_FILE = game_db_file()
KEYMAP_DIR = keymap_dir()

# DEFAULTS
DEFAULT_ACTION_COLOR = "40,40,40"
ACTION_BUTTONS = ["P1_A", "P1_B", "P1_C", "P1_X", "P1_Y", "P1_Z", "P2_A", "P2_B", "P2_C", "P2_X", "P2_Y", "P2_Z"]
SYSTEM_DEFAULTS = {"P1_START": "255,255,255", "P2_START": "255,255,255", "MENU": "255,255,255", "REWIND": "255,0,0", "TRACKBALL": "0,0,0"}

EVENT_TYPES = {
    "FE_START", "FE_QUIT", "SCREENSAVER_START", "SCREENSAVER_STOP", "LIST_CHANGE",
    "GAME_START", "GAME_QUIT", "GAME_PAUSE", "AUDIO_ANIMATION", "SPEAK_CONTROLS", "DEFAULT"
}
EVENT_ALIASES = {
    "FRONTEND_START": "FE_START",
    "FRONTEND_STOP": "FE_QUIT",
    "FRONTEND_QUIT": "FE_QUIT",
    "ATTRACT_START": "SCREENSAVER_START",
    "ATTRACT_STOP": "SCREENSAVER_STOP",
    "SCREEN_SAVER_START": "SCREENSAVER_START",
    "SCREEN_SAVER_STOP": "SCREENSAVER_STOP",
}

def _normalize_color(val):
    if not val:
        return None
    raw = str(val)
    if "|" in raw:
        raw = raw.split("|", 1)[0]
    raw = raw.strip()

    if raw.startswith("#") and len(raw) == 7:
        try:
            r = int(raw[1:3], 16)
            g = int(raw[3:5], 16)
            b = int(raw[5:7], 16)
            return f"{r},{g},{b}"
        except:
            return None

    raw = raw.replace("[", "").replace("]", "").replace(" ", "")
    parts = raw.split(",")
    if len(parts) == 3:
        try:
            r = int(parts[0]); g = int(parts[1]); b = int(parts[2])
            return f"{r},{g},{b}"
        except:
            return None
    return None

def _normalize_event(name):
    if not name:
        return ""
    raw = str(name).strip().upper().replace(" ", "_").replace("-", "_")
    raw = EVENT_ALIASES.get(raw, raw)
    return raw

def _load_keymap(name):
    if not name or name == "Current Deck":
        return None
    path = os.path.join(KEYMAP_DIR, f"{name}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("controls") or {}
    except:
        return None

def send_packet(payload):
    try:
        with socket.create_connection((ACLIGHTER_HOST, ACLIGHTER_PORT), timeout=0.5) as sock:
            sock.sendall(json.dumps(payload).encode('utf-8'))
        return True
    except Exception as e:
        print(f"[Dispatch] Connect Error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Arcade Commander Dispatcher")
    # We use nargs='?' so the ROM argument is optional
    parser.add_argument("rom", nargs="?", help="ROM Name (e.g. pacman)")
    parser.add_argument("--anim", help="Trigger Animation (rainbow, pulse_red, plasma, hyper_strobe)")
    parser.add_argument("--event", help="Trigger Event Type (FE_START, GAME_START, etc)")
    args = parser.parse_args()

    # Normalize event input if provided
    event_arg = _normalize_event(args.event) if args.event else ""

    # SCENARIO 1: TRIGGER ANIMATION (LEDBlinky Event)
    if args.anim:
        anim_name = _normalize_event(args.anim)
        if anim_name in EVENT_TYPES:
            event_arg = anim_name
        else:
            anim_name = args.anim.upper()
            print(f"[Dispatch] Triggering Animation: {anim_name}")
            send_packet({"command": "ANIMATION", "type": anim_name})
            return

    # SCENARIO 1B: TRIGGER EVENT (LEDBlinky Event Types)
    if event_arg:
        print(f"[Dispatch] Triggering Event: {event_arg}")
        rom_name = (args.rom or "").lower().replace(".zip", "").strip()
        entry = {}
        if os.path.exists(DB_FILE) and rom_name:
            try:
                with open(DB_FILE, "r") as f:
                    db = json.load(f)
                entry = db.get(rom_name, {})
            except:
                entry = {}
        profile = entry.get("profile", {})
        event_map = profile.get("events") or entry.get("events") or {}
        if not isinstance(event_map, dict):
            event_map = {}
        mapping = event_map.get(event_arg)
        if isinstance(mapping, dict):
            anim = mapping.get("animation") or ""
            bmap = mapping.get("button_map") or ""
            keymap = _load_keymap(bmap)
            if keymap:
                send_packet({"command": "STATE_UPDATE", "mode": "GAME", "data": keymap})
            if anim and anim.upper() != "NONE":
                send_packet({"command": "ANIMATION", "type": anim.upper()})
                return
            if keymap:
                return
        # fallback to idle if no mapping
        send_packet({"command": "STATE_UPDATE", "mode": "IDLE"})
        return

    # SCENARIO 2: GAME EXIT (No Args)
    if not args.rom:
        print("[Dispatch] Sending IDLE state.")
        send_packet({"command": "STATE_UPDATE", "mode": "IDLE"})
        return

    # SCENARIO 3: GAME LAUNCH (Profile Load)
    rom_name = args.rom.lower().replace(".zip", "").strip()
    controller_mode = "ARCADE_PANEL"
    lighting_policy = "AUTO"
    default_fx = ""

    # Build Profile
    final_colors = {btn: DEFAULT_ACTION_COLOR for btn in ACTION_BUTTONS}
    final_colors.update(SYSTEM_DEFAULTS)

    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                db = json.load(f)
            if rom_name in db:
                profile = db[rom_name].get("profile", {})
                controller_mode = profile.get("controller_mode", "ARCADE_PANEL")
                lighting_policy = profile.get("lighting_policy", "AUTO")
                default_fx = profile.get("default_fx", "")
                controls = db[rom_name].get("controls", {})
                overridden = set()
                for btn, color_str in controls.items():
                    norm = _normalize_color(color_str)
                    if norm:
                        final_colors[btn] = norm
                        overridden.add(btn)
                print(f"[Dispatch] Loaded profile for '{rom_name}'")
                vendor = db[rom_name].get("vendor")
                if not vendor:
                    metadata = db[rom_name].get("metadata", {}) if isinstance(db[rom_name], dict) else {}
                    if isinstance(metadata, dict):
                        vendor = metadata.get("manufacturer", "") or metadata.get("developer", "")
                vendor_colors = get_vendor_colors(vendor)
                if vendor_colors:
                    for btn in ACTION_BUTTONS:
                        if btn in overridden:
                            continue
                        if final_colors.get(btn) != DEFAULT_ACTION_COLOR:
                            continue
                        if btn.startswith("P1_"):
                            final_colors[btn] = vendor_colors["p1"]
                        elif btn.startswith("P2_"):
                            final_colors[btn] = vendor_colors["p2"]
                    
                    sys_col = vendor_colors.get("system")
                    if sys_col:
                        for sys_btn in ["MENU", "REWIND", "TRACKBALL"]:
                            if sys_btn not in overridden:
                                final_colors[sys_btn] = sys_col
        except: pass
    if controller_mode == "ARCADE_PANEL":
        send_packet({"command": "STATE_UPDATE", "mode": "GAME", "data": final_colors})
        return

    policy = str(lighting_policy or "AUTO").upper()
    fx_name = str(default_fx or "").strip()
    if policy == "FX_ONLY" or (policy == "AUTO" and fx_name):
        send_packet({"command": "ANIMATION", "type": fx_name.upper()})
    else:
        send_packet({"command": "STATE_UPDATE", "mode": "IDLE"})

if __name__ == "__main__":
    main()
