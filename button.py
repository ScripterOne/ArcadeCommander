import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import json
import os

# --- CONFIGURATION ---
COLORS = {
    "BG": "#0A0A0A", 
    "SURFACE": "#161616", 
    "P1": "#39FF14", 
    "P2": "#FF5F1F",
    "SYS": "#00E5FF",
    "TEXT": "#E0E0E0"
}

# Adjusted Coordinates for the new blacked-out image
# Format: "ID": (X, Y, Radius, "Label", "Label_Position")
ALU_MAP = {
    # PLAYER 1 (Left Side)
    "P1_A": (273, 275, 22, "A", "BELOW"), 
    "P1_B": (323, 275, 22, "B", "BELOW"), 
    "P1_C": (373, 275, 22, "C", "BELOW"),
    "P1_X": (273, 335, 22, "X", "BELOW"), 
    "P1_Y": (323, 335, 22, "Y", "BELOW"), 
    "P1_Z": (373, 335, 22, "Z", "BELOW"),
    
    # PLAYER 2 (Right Side)
    "P2_A": (627, 275, 22, "A", "BELOW"), 
    "P2_B": (677, 275, 22, "B", "BELOW"), 
    "P2_C": (727, 275, 22, "C", "BELOW"),
    "P2_X": (627, 335, 22, "X", "BELOW"), 
    "P2_Y": (677, 335, 22, "Y", "BELOW"), 
    "P2_Z": (727, 335, 22, "Z", "BELOW"),
    
    # SYSTEM (Top Row)
    "REWIND": (375, 85, 18, "«", "INSIDE"),
    "P1_START": (445, 85, 18, "P1", "INSIDE"),
    "MENU": (500, 85, 18, "≡", "INSIDE"),
    "P2_START": (555, 85, 18, "P2", "INSIDE"),
    "REWIND_ALT": (625, 85, 18, "»", "INSIDE"), 
    
    # TRACKBALL
    "TRACKBALL": (500, 360, 48, "", "NONE")
}

class VirtualLED:
    def __init__(self, canvas, x, y, radius, label, label_type):
        self.canvas = canvas
        self.glow = canvas.create_oval(x-radius-6, y-radius-6, x+radius+6, y+radius+6, fill="", outline="", state="hidden")
        self.bezel = canvas.create_oval(x-radius, y-radius, x+radius, y+radius, outline="#111", width=2)
        # Default lens color matches the black hole in your PNG
        self.lens = canvas.create_oval(x-radius+2, y-radius+2, x+radius-2, y+radius-2, fill="#050505", outline="#222", width=1)
        self.reflection = canvas.create_oval(x-radius*0.4, y-radius*0.6, x+radius*0.1, y-radius*0.3, fill="#AAAAAA", outline="", stipple="gray25")

        self.text_id = None
        if label_type == "INSIDE":
            self.text_id = canvas.create_text(x, y, text=label, fill="#888", font=("Segoe UI", 8, "bold"))
        elif label_type == "BELOW":
            canvas.create_text(x, y+radius+12, text=label, fill="#AAA", font=("Segoe UI", 7, "bold"))

    def set_color(self, hex_color):
        if not hex_color or hex_color == COLORS["SURFACE"]:
            self.canvas.itemconfigure(self.glow, state="hidden")
            self.canvas.itemconfigure(self.lens, fill="#050505", outline="#222")
            if self.text_id: self.canvas.itemconfigure(self.text_id, fill="#888")
        else:
            self.canvas.itemconfigure(self.glow, state="normal", fill=hex_color, stipple="gray50")
            self.canvas.itemconfigure(self.lens, fill=hex_color, outline=hex_color)
            if self.text_id: self.canvas.itemconfigure(self.text_id, fill="black")

class EmulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AC V2.0 - CONSOLE VISUALIZER")
        self.root.geometry("1100x700")
        self.root.configure(bg=COLORS["BG"])
        
        self.leds = {}
        self.db_path = "AC_GameData.json"
        
        main = tk.Frame(root, bg=COLORS["BG"])
        main.pack(fill="both", expand=True)

        sidebar = tk.Frame(main, bg=COLORS["BG"], width=200)
        sidebar.pack(side="left", fill="y", padx=10, pady=10)
        
        tk.Label(sidebar, text="GAME LIBRARY", fg=COLORS["P1"], bg=COLORS["BG"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.listbox = tk.Listbox(sidebar, bg="#161616", fg="#EEE", borderwidth=0, height=20)
        self.listbox.pack(fill="x", pady=5)
        self.listbox.bind("<<ListboxSelect>>", self.load_profile)
        
        self.canvas = tk.Canvas(main, bg="black", highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        # IMAGE PATH UPDATE
        img_path = os.path.join("assets", "Consol.png")
        if os.path.exists(img_path):
            img = Image.open(img_path)
            self.bg_img = ImageTk.PhotoImage(img.resize((900, 450), Image.Resampling.LANCZOS))
            self.canvas.create_image(0, 0, anchor="nw", image=self.bg_img)
        else:
            print(f"Warning: Image not found at {img_path}")
        
        for bid, data in ALU_MAP.items():
            self.leds[bid] = VirtualLED(self.canvas, *data)
            
        self.load_db_list()

    def load_db_list(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r") as f:
                    data = json.load(f)
                    for rom in sorted(data.keys()):
                        self.listbox.insert(tk.END, rom)
            except: pass

    def load_profile(self, _):
        if not self.listbox.curselection(): return
        rom = self.listbox.get(self.listbox.curselection())
        
        for led in self.leds.values(): led.set_color(None)
        
        try:
            with open(self.db_path, "r") as f:
                data = json.load(f).get(rom, {}).get("controls", {})
                
            for bid, val in data.items():
                if bid in self.leds:
                    color = val.split('|')[0] if "|" in val else val
                    self.leds[bid].set_color(color)
        except: pass

if __name__ == "__main__":
    root = tk.Tk()
    app = EmulatorApp(root)
    root.mainloop()