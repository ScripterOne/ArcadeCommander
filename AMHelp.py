import tkinter as tk
from tkinter import messagebox
import os
import sys

# Color Palette matching Arcade Commander V2
COLORS = {
    "BG": "#121212", "SURFACE": "#1E1E1E", "SURFACE_LIGHT": "#2C2C2C",
    "P1": "#00E5FF", "TEXT": "#FFFFFF", "TEXT_DIM": "#888888", "DANGER": "#D50000"
}

class ArcadeCommanderHelp:
    def __init__(self, root):
        self.root = root
        self.root.title("ARCADE COMMANDER 2.0 - OFFICIAL MANUAL")
        self.root.geometry("1050x800")
        self.root.configure(bg=COLORS["BG"])

        # --- VERBOSE MANUAL CONTENT ---
        self.manual_data = {
            "1. Architecture Overview": (
                "Arcade Commander V2.0 utilizes a Service-Oriented Architecture (SOA). "
                "The core hardware driver runs as a background service ('The Brain') that owns "
                "the USB/Serial connection to your LED hardware.\n\n"
                "This design allows the Dashboard GUI and automation tools (like ACDispatch) "
                "to send commands simultaneously via local network sockets, eliminating "
                "'COM Port Busy' errors."
            ),
            "2. Front-End Integration": (
                "To integrate with Front-Ends (LaunchBox, BigBox, Hyperspin), use 'ACDispatch.exe'. "
                "This lightweight tool sends commands to the background service and exits immediately.\n\n"
                "COMMAND EXAMPLES:\n"
                "• Load Game Profile: ACDispatch.exe <rom_name>\n"
                "• Run Animation: ACDispatch.exe --anim <type>\n"
                "• All Off/Idle: ACDispatch.exe --idle"
            ),
            "3. LEDBlinky Integration": (
                "Arcade Commander is designed to work alongside LEDBlinky for advanced automation.\n\n"
                "1. In LEDBlinky, set the 'External LED Controller' path to 'ACDispatch.exe'.\n"
                "2. ACDispatch translates LEDBlinky commands into JSON packets for the service.\n"
                "3. This allows you to leverage LEDBlinky's logic with Arcade Commander's 60 FPS animations."
            ),
            "4. Hardware Pinout (17-LED)": (
                "Optimized for a 17-LED strip configuration.\n\n"
                "• 00-05: Player 1 Buttons (A, B, C, X, Y, Z)\n"
                "• 06-11: Player 2 Buttons (A, B, C, X, Y, Z)\n"
                "• 12-13: Start 1 & Start 2\n"
                "• 14-15: Menu & Rewind\n"
                "• 16: Trackball / Global Effect"
            ),
            "5. About & Credits": (
                "ARCADE COMMANDER V2.0\n"
                "Developed by: Mark Abraham\n"
                "Location: Olathe, Kansas\n\n"
                "Created for the arcade community to provide a high-performance, "
                "extensible LED control solution for modern and retro gaming cabinets."
            ),
            "6. MIT License": (
                "Copyright (c) 2026 Mark Abraham\n\n"
                "Permission is hereby granted, free of charge, to any person obtaining a copy "
                "of this software and associated documentation files (the 'Software'), to deal "
                "in the Software without restriction, including without limitation the rights "
                "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell "
                "copies of the Software, and to permit persons to whom the Software is "
                "furnished to do so, subject to the following conditions:\n\n"
                "The above copyright notice and this permission notice shall be included in all "
                "copies or substantial portions of the Software.\n\n"
                "THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR "
                "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, "
                "FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE "
                "AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER "
                "LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, "
                "OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE "
                "SOFTWARE."
            )
        }
        
        self.build_ui()

    def build_ui(self):
        # Search Bar
        sf = tk.Frame(self.root, bg=COLORS["SURFACE"], pady=15)
        sf.pack(fill="x")
        tk.Label(sf, text=" SEARCH: ", font=("Segoe UI", 10, "bold"), bg=COLORS["SURFACE"], fg=COLORS["TEXT_DIM"]).pack(side="left", padx=20)
        self.search_entry = tk.Entry(sf, bg=COLORS["SURFACE_LIGHT"], fg="white", font=("Consolas", 12), borderwidth=0, insertbackground="white")
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 30))
        self.search_entry.bind("<KeyRelease>", lambda e: self.update_index(self.search_entry.get()))

        cp = tk.Frame(self.root, bg=COLORS["BG"])
        cp.pack(expand=True, fill="both", padx=20, pady=10)

        # Index List
        idx_frame = tk.Frame(cp, bg=COLORS["SURFACE"], width=250)
        idx_frame.pack(side="left", fill="y", padx=(0, 10))
        self.idx_list = tk.Listbox(idx_frame, bg=COLORS["SURFACE"], fg=COLORS["P1"], font=("Segoe UI", 11), selectbackground=COLORS["P1"], selectforeground="black", borderwidth=0, highlightthickness=0)
        self.idx_list.pack(expand=True, fill="both", padx=5, pady=5)
        self.idx_list.bind("<<ListboxSelect>>", self.on_select)

        # Viewer
        v_frame = tk.Frame(cp, bg=COLORS["SURFACE_LIGHT"])
        v_frame.pack(side="right", expand=True, fill="both")
        self.viewer = tk.Text(v_frame, wrap="word", bg=COLORS["SURFACE_LIGHT"], fg="white", font=("Segoe UI", 11), padx=30, pady=30, borderwidth=0)
        self.viewer.pack(expand=True, fill="both")

        # Footer
        footer = tk.Frame(self.root, bg=COLORS["BG"], pady=20)
        footer.pack(fill="x", padx=30)
        tk.Label(footer, text="V2.0 | Olathe, KS", bg=COLORS["BG"], fg=COLORS["TEXT_DIM"]).pack(side="left")

        self.update_index()
        self.display_topic("1. Architecture Overview")

    def display_topic(self, topic):
        self.viewer.config(state="normal")
        self.viewer.delete("1.0", tk.END)
        self.viewer.insert("1.0", f"{topic.upper()}\n\n", "header")
        self.viewer.insert(tk.END, self.manual_data[topic])
        self.viewer.tag_configure("header", font=("Segoe UI", 16, "bold"), foreground=COLORS["P1"])
        self.viewer.config(state="disabled")

    def on_select(self, evt):
        if self.idx_list.curselection():
            self.display_topic(self.idx_list.get(self.idx_list.curselection()))

    def update_index(self, q=""):
        self.idx_list.delete(0, tk.END)
        for topic in self.manual_data.keys():
            if q.lower() in topic.lower() or q.lower() in self.manual_data[topic].lower():
                self.idx_list.insert(tk.END, topic)

if __name__ == "__main__":
    root = tk.Tk()
    app = ArcadeCommanderHelp(root)
    root.mainloop()