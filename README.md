🎮 Arcade Commander

Arcade Commander is a Windows application for controlling addressable RGB LEDs (WS2812B) in arcade cabinets using the Adalight protocol. It is designed specifically for the AtGames Legends Ultimate (ALU) when paired with the PicoCTR USB controller and WS2812B RGB adapter, but is architected for future frontend and driver integration.

This project fills a long-standing gap: there is no native Windows Adalight driver or unified LED controller for modern arcade frontends. Arcade Commander provides that missing layer.

✨ Features

🎨 Per-button RGB control

Primary & secondary colors

Individual overrides

Group color assignment (Player-wide)

💓 Pulse animation engine

Adjustable speed

Smooth color blending

Hardware-timed updates

🧪 Built-in LED Tester

Hardware validation mode

RGB + white cycling

Button-by-button verification

🎮 Input Mapping & Diagnostics

Pygame joystick capture

Visual LED feedback on press

Mapping persistence

🧠 Profile system

Save / load lighting profiles

Auto-load last profile on startup

Safe handling of legacy profiles

🖥️ Modern GUI

Animated title effects

Accent-colored player cards

High-contrast, cabinet-friendly layout

🧩 Hardware Compatibility
Supported (Primary Target)

AtGames Legends Ultimate (ALU)

PicoCTR USB Controller

Drop-in replacement encoder

Built-in WS2812B RGB controller

WS2812B RGB Adapter – 30 RGB

GRB color order

Supports up to 30 RGB channels

Notes

PicoCTR operates USB-only (no Bluetooth)

LEDs are addressed logically (not GPIO-based)

Trackball LEDs supported (labeled as BALL)

🔌 Communication Details

Protocol: Adalight

Connection: USB Serial (COM port)

Default Baud Rate: 230400

LED Count: 30 (configurable in driver)

All LED logic is centralized to ensure future compatibility with:

Native Windows drivers

Frontend DLLs (LaunchBox, HyperSpin, MAME, etc.)

Third-party LED tools (LEDSpicer-style integration)

🗂️ Project Structure
Arcade-Commander/
│
├── ArcadeCommanderv5.py     # Main application
├── ArcadeDriver.py          # Hardware abstraction layer
├── assets/                  # UI graphics & banner art
├── input_map.json           # Saved controller mappings
├── last_profile.cfg         # Auto-load pointer
├── README.md
└── LICENSE

🚀 Getting Started
Requirements

Windows 10 / 11

Python 3.10+

PicoCTR connected via USB

Python Dependencies
pip install pyserial pygame pillow

Run
python ArcadeCommanderv5.py


On first launch:

Select the correct COM port if prompted

Configure button mapping

Save your first lighting profile

🧪 Tester & Diagnostics

Right-click any button → Hardware Test

Test Mode lights LEDs on input press

Cycle / Demo modes validate full LED chain

These tools are designed to verify wiring, order, and color accuracy before frontend integration.

🛣️ Roadmap

Planned (not yet implemented):

Windows DLL / API layer for arcade frontends

LaunchBox / HyperSpin integration

Per-game lighting profiles

Audio-reactive lighting modes

Linux support (experimental)

📜 License

This project is released under the MIT License.

You are free to:

Use

Modify

Distribute

Embed in commercial or non-commercial projects

Attribution is appreciated but not required.

🙌 Credits

PicoCTR hardware by ACustomArcade

Adalight protocol by the open-source community

UI & software by ScripterOne
