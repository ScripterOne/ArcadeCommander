import sys
import json
import socket
import os
import argparse

# CONFIGURATION
NEXUS_HOST = "127.0.0.1"
NEXUS_PORT = 6006
DB_FILE = "AC_GameData.json"

# DEFAULTS
DEFAULT_ACTION_COLOR = "40,40,40"
ACTION_BUTTONS = ["P1_A", "P1_B", "P1_C", "P1_X", "P1_Y", "P1_Z", "P2_A", "P2_B", "P2_C", "P2_X", "P2_Y", "P2_Z"]
SYSTEM_DEFAULTS = {"P1_START": "255,255,255", "P2_START": "255,255,255", "MENU": "255,255,255", "REWIND": "50,0,0"}

def send_packet(payload):
    try:
        with socket.create_connection((NEXUS_HOST, NEXUS_PORT), timeout=0.5) as sock:
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
    args = parser.parse_args()

    # SCENARIO 1: TRIGGER ANIMATION (LEDBlinky Event)
    if args.anim:
        anim_name = args.anim.upper()
        print(f"[Dispatch] Triggering Animation: {anim_name}")
        send_packet({"command": "ANIMATION", "type": anim_name})
        return

    # SCENARIO 2: GAME EXIT (No Args)
    if not args.rom:
        print("[Dispatch] Sending IDLE state.")
        send_packet({"command": "STATE_UPDATE", "mode": "IDLE"})
        return

    # SCENARIO 3: GAME LAUNCH (Profile Load)
    rom_name = args.rom.lower().replace(".zip", "").strip()
    
    # Build Profile
    final_colors = {btn: DEFAULT_ACTION_COLOR for btn in ACTION_BUTTONS}
    final_colors.update(SYSTEM_DEFAULTS)

    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                db = json.load(f)
            if rom_name in db:
                for btn, color_str in db[rom_name].get("controls", {}).items():
                    final_colors[btn] = color_str.replace("[", "").replace("]", "").replace(" ", "")
                print(f"[Dispatch] Loaded profile for '{rom_name}'")
        except: pass

    send_packet({"command": "STATE_UPDATE", "mode": "GAME", "data": final_colors})

if __name__ == "__main__":
    main()