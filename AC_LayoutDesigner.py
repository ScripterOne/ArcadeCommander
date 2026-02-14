import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import json
import os

BUTTON_IDS = [
    "P1_A", "P1_B", "P1_C", "P1_X", "P1_Y", "P1_Z",
    "P2_A", "P2_B", "P2_C", "P2_X", "P2_Y", "P2_Z",
    "REWIND", "P1_START", "MENU", "P2_START", "REWIND_ALT", "TRACKBALL"
]

class LayoutDesigner:
    def __init__(self, root):
        self.root = root
        self.root.title("AC V2.0 - LAYOUT DESIGNER")
        self.root.geometry("1350x950") 
        self.root.configure(bg="#222")

        self.layout_data = {} 
        self.temp_items = {} 
        self.current_selection = None
        self.img_path = os.path.join("assets", "Consol.png")
        if not os.path.exists(self.img_path): self.img_path = "Consol.png"

        self.setup_ui()
        self.root.after(100, self.load_image)

    def setup_ui(self):
        panel = tk.Frame(self.root, bg="#333", width=250)
        panel.pack(side="left", fill="y", padx=10, pady=10)
        panel.pack_propagate(False)
        
        tk.Label(panel, text="1. SELECT ID", fg="#00E5FF", bg="#333", font=("Segoe UI", 10, "bold")).pack(pady=5)
        self.id_list = tk.Listbox(panel, bg="#111", fg="white", height=18)
        self.id_list.pack(fill="x", padx=5)
        for bid in BUTTON_IDS: self.id_list.insert(tk.END, bid)
        self.id_list.bind("<<ListboxSelect>>", self.on_id_select)

        tk.Label(panel, text="2. LABEL TYPE", fg="#00E5FF", bg="#333", font=("Segoe UI", 10, "bold")).pack(pady=(20,5))
        self.label_var = tk.StringVar(value="BELOW")
        
        tk.Radiobutton(panel, text="Below (A, B, C)", variable=self.label_var, value="BELOW", bg="#333", fg="white", selectcolor="#444").pack(anchor="w", padx=5)
        tk.Radiobutton(panel, text="Above (X, Y, Z)", variable=self.label_var, value="ABOVE", bg="#333", fg="white", selectcolor="#444").pack(anchor="w", padx=5)
        tk.Radiobutton(panel, text="Inside (Symbols)", variable=self.label_var, value="INSIDE", bg="#333", fg="white", selectcolor="#444").pack(anchor="w", padx=5)
        tk.Radiobutton(panel, text="None (Trackball)", variable=self.label_var, value="NONE", bg="#333", fg="white", selectcolor="#444").pack(anchor="w", padx=5)

        tk.Button(panel, text="SAVE LAYOUT JSON", bg="#00C853", fg="black", font=("Segoe UI", 11, "bold"), 
                  command=self.save_layout).pack(fill="x", pady=20, padx=5)
        
        self.canvas = tk.Canvas(self.root, bg="black", cursor="crosshair")
        self.canvas.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<MouseWheel>", self.on_scroll)
        self.canvas.bind("<Button-4>", self.on_scroll)
        self.canvas.bind("<Button-5>", self.on_scroll)
        self.canvas.bind("<Button-3>", self.on_right_click)

    def load_image(self):
        if not os.path.exists(self.img_path):
            messagebox.showerror("Error", f"Could not find image at {self.img_path}")
            return
        pil_img = Image.open(self.img_path)
        orig_w, orig_h = pil_img.size
        canvas_w = self.canvas.winfo_width() if self.canvas.winfo_width() > 100 else 1000
        canvas_h = self.canvas.winfo_height() if self.canvas.winfo_height() > 100 else 800
        
        scale = min(canvas_w / orig_w, canvas_h / orig_h)
        self.display_w = int(orig_w * scale)
        self.display_h = int(orig_h * scale)
        
        self.tk_img = ImageTk.PhotoImage(pil_img.resize((self.display_w, self.display_h), Image.Resampling.LANCZOS))
        self.img_x_offset = (canvas_w - self.display_w) // 2
        self.img_y_offset = (canvas_h - self.display_h) // 2

        self.canvas.delete("all")
        self.canvas.create_image(self.img_x_offset, self.img_y_offset, anchor="nw", image=self.tk_img)
        self.load_existing_layout()

    def load_existing_layout(self):
        path = os.path.join("assets", "layout.json")
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    self.layout_data = json.load(f)
                for bid in self.layout_data: self.draw_marker(bid)
            except: pass

    def on_id_select(self, _):
        if self.id_list.curselection():
            self.current_selection = self.id_list.get(self.id_list.curselection())
            sel = self.current_selection
            if "TRACKBALL" in sel: self.label_var.set("NONE")
            elif any(x in sel for x in ["START", "MENU", "REWIND"]): self.label_var.set("INSIDE")
            elif any(x in sel for x in ["_X", "_Y", "_Z"]): self.label_var.set("ABOVE")
            else: self.label_var.set("BELOW")
            if sel in self.layout_data: self.draw_marker(sel)

    def update_marker(self, x, y, r=None):
        if not self.current_selection: return
        bid = self.current_selection
        rel_x_px = x - self.img_x_offset
        rel_y_px = y - self.img_y_offset
        if rel_x_px < 0 or rel_x_px > self.display_w or rel_y_px < 0 or rel_y_px > self.display_h: return

        if r is None:
            r = self.layout_data[bid]["rel_r"] * self.display_w if bid in self.layout_data else 20

        self.layout_data[bid] = {
            "rel_x": rel_x_px / self.display_w,
            "rel_y": rel_y_px / self.display_h,
            "rel_r": r / self.display_w,
            "label_type": self.label_var.get()
        }
        self.draw_marker(bid)

    def draw_marker(self, bid):
        if bid in self.temp_items:
            for item in self.temp_items[bid]: self.canvas.delete(item)
        data = self.layout_data[bid]
        px = (data["rel_x"] * self.display_w) + self.img_x_offset
        py = (data["rel_y"] * self.display_h) + self.img_y_offset
        pr = data["rel_r"] * self.display_w
        color = "#00FF00" if bid == self.current_selection else "#00FFFF"
        c_id = self.canvas.create_oval(px-pr, py-pr, px+pr, py+pr, outline=color, width=2)
        t_id = self.canvas.create_text(px, py, text=bid, fill="white", font=("Arial", 8, "bold"))
        self.temp_items[bid] = [c_id, t_id]

    def on_click(self, event): self.update_marker(event.x, event.y)
    def on_drag(self, event): self.update_marker(event.x, event.y)
    def on_scroll(self, event):
        if not self.current_selection or self.current_selection not in self.layout_data: return
        data = self.layout_data[self.current_selection]
        current_r = data["rel_r"] * self.display_w
        if event.num == 5 or event.delta < 0: current_r = max(5, current_r - 1)
        else: current_r += 1
        px = (data["rel_x"] * self.display_w) + self.img_x_offset
        py = (data["rel_y"] * self.display_h) + self.img_y_offset
        self.update_marker(px, py, current_r)

    def on_right_click(self, event):
        for bid, data in list(self.layout_data.items()):
            px = (data["rel_x"] * self.display_w) + self.img_x_offset
            py = (data["rel_y"] * self.display_h) + self.img_y_offset
            if ((event.x-px)**2 + (event.y-py)**2)**0.5 < (data["rel_r"] * self.display_w):
                del self.layout_data[bid]
                for item in self.temp_items[bid]: self.canvas.delete(item)
                del self.temp_items[bid]
                break

    def save_layout(self):
        if not os.path.exists("assets"): os.makedirs("assets")
        with open(os.path.join("assets", "layout.json"), "w") as f: json.dump(self.layout_data, f, indent=4)
        messagebox.showinfo("Success", "Layout saved!")

if __name__ == "__main__":
    root = tk.Tk()
    app = LayoutDesigner(root)
    root.mainloop()
