# ArcadeTester.py
# Hardware validation & demo utility for PicoCTR + WS2812B 30ch adapter
# NOTE:
#   - Physical board pins are 1..30
#   - Internally we map Pin N -> index (N-1)

from ArcadeDriver import Arcade, wheel
import time
import math

PHYSICAL_PINS = 30


def pin_to_index(pin: int) -> int:
    """Convert physical pin number (1..30) to Python index (0..29)."""
    return pin - 1


def all_off(cab: Arcade):
    cab.send_frame([(0, 0, 0)] * PHYSICAL_PINS)


# ------------------------------------------------------------
# DIAGNOSTIC: PIN MAPPER
# ------------------------------------------------------------
def pin_mapper(cab: Arcade):
    """
    Lights up each pin individually for 1 second.
    Useful for verifying physical pin layout matches firmware mapping.
    """
    print("\n[Pin Mapper Diagnostic]")
    print("Each pin will light WHITE for 1 second.\n")
    
    for pin in range(1, PHYSICAL_PINS + 1):
        frame = [(0, 0, 0)] * PHYSICAL_PINS
        frame[pin_to_index(pin)] = (255, 255, 255)
        print(f"Lighting Pin {pin:02d}...")
        cab.send_frame(frame)
        time.sleep(1.0)
    
    all_off(cab)
    print("Pin mapper complete.\n")


# ------------------------------------------------------------
# QUICK SANITY TEST
# ------------------------------------------------------------
def quick_sanity_test(cab: Arcade):
    print("\n[Quick Sanity Test]")
    print("• Pin 1  -> RED")
    print("• Pin 17 -> BLUE (Trackball)")
    print("• Then green chase across Pin 1..30\n")

    frame = [(0, 0, 0)] * PHYSICAL_PINS

    frame[pin_to_index(1)] = (255, 0, 0)     # Pin 1
    frame[pin_to_index(17)] = (0, 0, 255)    # Pin 17 (Trackball)

    cab.send_frame(frame)
    time.sleep(2)

    print("Green chase...")
    for pin in range(1, PHYSICAL_PINS + 1):
        frame = [(0, 0, 0)] * PHYSICAL_PINS
        frame[pin_to_index(pin)] = (0, 255, 0)
        print(f"Pin {pin:02d}")
        cab.send_frame(frame)
        time.sleep(0.20)

    all_off(cab)
    print("Sanity test complete.\n")


# ------------------------------------------------------------
# BUTTON / PIN FINDER
# ------------------------------------------------------------
def button_finder(cab: Arcade, delay_per_color=0.35):
    """
    For each physical pin (1..30), cycle:
      RED -> GREEN -> BLUE -> WHITE
    Then move to the next pin.
    """
    print("\n[Button / Pin Finder]")
    print("Each pin cycles: RED → GREEN → BLUE → WHITE")
    print("Press Ctrl+C to stop.\n")

    colors = [
        ("RED", (255, 0, 0)),
        ("GREEN", (0, 255, 0)),
        ("BLUE", (0, 0, 255)),
        ("WHITE", (255, 255, 255)),
    ]

    try:
        for pin in range(1, PHYSICAL_PINS + 1):
            idx = pin_to_index(pin)
            for name, rgb in colors:
                frame = [(0, 0, 0)] * PHYSICAL_PINS
                frame[idx] = rgb
                print(f"Pin {pin:02d} -> {name}")
                cab.send_frame(frame)
                time.sleep(delay_per_color)

    except KeyboardInterrupt:
        print("\nFinder stopped by user.\n")
    finally:
        all_off(cab)


# ------------------------------------------------------------
# ATTRACT / DEMO MODE
# ------------------------------------------------------------
def attract_demo(cab: Arcade):
    """
    Attract mode using physical pin mapping:

    Pins:
      1–12  : Player buttons (P1 + P2)
      13    : REWIND
      14    : P1_START
      15    : MENU
      16    : P2_START
      17    : TRACKBALL
    """
    print("\n[Attract Mode]")
    print("• Rainbow wave on player buttons (Pins 1–12)")
    print("• Pulsing admin buttons")
    print("• Cycling trackball (Pin 17)")
    print("Press Ctrl+C to stop.\n")

    offset = 0

    try:
        while True:
            frame = [(0, 0, 0)] * PHYSICAL_PINS

            # Player buttons (Pins 1–12)
            for pin in range(1, 13):
                frame[pin_to_index(pin)] = wheel((pin * 20 + offset) % 255)

            # Pulsing admin buttons
            pulse = int((math.sin(time.time() * 3) + 1) * 127.5)
            frame[pin_to_index(14)] = (pulse, 0, 0)     # P1_START
            frame[pin_to_index(16)] = (0, 0, pulse)     # P2_START
            frame[pin_to_index(15)] = (0, pulse, 0)     # MENU
            frame[pin_to_index(13)] = (pulse, pulse, 0) # REWIND

            # Trackball (Pin 17)
            frame[pin_to_index(17)] = wheel((offset * 2) % 255)

            cab.send_frame(frame)

            offset += 2
            time.sleep(0.03)

    except KeyboardInterrupt:
        print("\nStopping attract mode...\n")
    finally:
        all_off(cab)


# ------------------------------------------------------------
# MAIN MENU
# ------------------------------------------------------------
def main():
    cab = Arcade()
    if not getattr(cab, "ser", None):
        print("\nERROR: Could not open serial connection.")
        print("Check COM port, cable, and that no other app is using it.\n")
        return

    while True:
        print("=== ARCADE HARDWARE TESTER ===")
        print("1) Quick sanity test")
        print("2) Button / pin finder (RGBW cycle)")
        print("3) Attract / demo mode")
        print("4) All off")
        print("Q) Quit")
        choice = input("> ").strip().lower()

        if choice == "1":
            quick_sanity_test(cab)
        elif choice == "2":
            button_finder(cab)
        elif choice == "3":
            attract_demo(cab)
        elif choice == "4":
            all_off(cab)
        elif choice == "q":
            break
        else:
            print("Invalid choice.\n")

    all_off(cab)
    cab.close()
    print("Tester closed cleanly.")


if __name__ == "__main__":
    main()
