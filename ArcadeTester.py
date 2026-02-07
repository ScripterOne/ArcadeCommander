import time
import math

def quick_sanity_test(cab):
    """
    Flashes Pin 0 (P1_A) and Pin 16 (TRACKBALL).
    Matches your hardware requirement: 
    Pin 1 -> RED, Pin 17 -> BLUE
    """
    print("[Tester] Running Quick Sanity Test...")
    
    # We use indices 0 and 16 to ensure compatibility with ServiceAdapter
    for _ in range(3):
        # Step 1: Pin 1 (Index 0) -> RED
        cab.set(0, (255, 0, 0))
        # Step 2: Pin 17 (Index 16) -> BLUE
        cab.set(16, (0, 0, 255))
        cab.show()
        time.sleep(0.5)
        
        # Step 3: All Off
        cab.set_all((0, 0, 0))
        cab.show()
        time.sleep(0.5)
    
    print("[Tester] Starting Green Chase across all pins...")
    # Step 4: Green chase across Pin 1..17
    for i in range(17):
        cab.set(i, (0, 255, 0))
        cab.show()
        time.sleep(0.1)
        cab.set(i, (0, 0, 0))
        cab.show()

def button_finder(cab):
    """Green chase across all buttons."""
    print("[Tester] Running Pin Finder (Green Chase)...")
    for i in range(17):
        cab.set(i, (0, 255, 0))
        cab.show()
        time.sleep(0.1)
        cab.set(i, (0, 0, 0))
        cab.show()

def attract_demo(cab):
    """Rainbow wave on buttons 1-12, Pulsing Admin, Cycling Trackball."""
    print("[Tester] Running Attract Mode... (Ctrl+C in console to stop)")
    
    def wheel(pos):
        if pos < 85: return (pos * 3, 255 - pos * 3, 0)
        elif pos < 170: pos -= 85; return (255 - pos * 3, 0, pos * 3)
        else: pos -= 170; return (0, pos * 3, 255 - pos * 3)

    try:
        offset = 0
        while True:
            # 1. Rainbow on Player Buttons (0-11)
            for i in range(12):
                cab.set(i, wheel((i * 20 + offset) % 255))
            
            # 2. Pulsing Admin (12-15)
            # Use math.sin for the pulse effect
            pulse = int(((math.sin(time.time() * 5) + 1) / 2) * 255)
            for i in range(12, 16):
                cab.set(i, (pulse, pulse, pulse))
                
            # 3. Cycling Trackball (16)
            cab.set(16, wheel((offset) % 255))
            
            cab.show()
            offset = (offset + 5) % 255
            time.sleep(0.03)
    except (KeyboardInterrupt, Exception):
        print("[Tester] Attract Mode Stopped.")
        cab.set_all((0,0,0))
        cab.show()