import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox
from PIL import Image, ImageTk
import json
import os

BUTTON_IDS = [
    "P1_A", "P1_B", "P1_C", "P1_X", "P1_Y", "P1_Z",
    "P2_A", "P2_B", "P2_C", "P2_X", "P2_Y", "P2_Z",
    "REWIND", "P1_START", "MENU", "P2_START", "REWIND_ALT", "TRACKBALL",
    "L_FLIPPER", "L_NUDGE", "R_FLIPPER", "R_NUDGE",
]

TEMPLATES = {
    "ALU": {"image": "Consol.png", "layout": "layout.json"},
    "4P": {"image": "4PlayerDeck.jpg", "layout": "layout_4p.json"},
}

class LayoutDesigner:
    def __init__(self, parent, assets_dir="assets", target_w=1320, show_sidebar=True, hw_connected=None):
        self.parent = parent
        self.root = parent if isinstance(parent, tk.Tk) else parent.winfo_toplevel()
        self.container = tk.Frame(parent, bg="#222")
        if isinstance(parent, tk.Tk):
            self.root.title("AC V2.0 - LAYOUT DESIGNER")
            self.root.geometry("1350x950") 
            self.root.configure(bg="#222")
        self.container.pack(fill="both", expand=True)

        self.layout_data = {} 
        self.temp_items = {} 
        self.current_selection = None
        self.dragging_id = None
        self.assets_dir = assets_dir
        self.target_w = target_w
        self.show_sidebar = show_sidebar
        self.template_name = "ALU"
        self.layout_path = None
        self.hw_connected = hw_connected
        self._conn_bg_id = None
        self._conn_text_id = None
        self._conn_status_job = None
        self._load_layout_config()

        self.setup_ui()
        self.root.after(100, self.load_image)

    def setup_ui(self):
        main = tk.Frame(self.container, bg="#222")
        main.pack(fill="both", expand=True)
        if isinstance(self.parent, tk.Tk):
            tk.Button(
                main,
                text="QUIT",
                bg="#D50000",
                fg="white",
                relief="flat",
                command=self.root.destroy,
                font=("Segoe UI", 8, "bold"),
            ).place(relx=1.0, x=-10, y=10, anchor="ne")
        if self.show_sidebar:
            panel = tk.Frame(main, bg="#333", width=250)
            panel.pack(side="left", fill="y", padx=10, pady=10)
            panel.pack_propagate(False)
            
            tk.Label(panel, text="1. SELECT ID", fg="#00E5FF", bg="#333", font=("Segoe UI", 10, "bold")).pack(pady=5)
            self.id_list = tk.Listbox(panel, bg="#111", fg="white", height=18)
            self.id_list.pack(fill="x", padx=5)
            for bid in BUTTON_IDS: self.id_list.insert(tk.END, bid)
            self.id_list.bind("<<ListboxSelect>>", self.on_id_select)

            tk.Label(panel, text="2. LABEL TYPE", fg="#00E5FF", bg="#333", font=("Segoe UI", 10, "bold")).pack(pady=(20,5))
            self.label_var = tk.StringVar(value="BELOW")
            self.led_var = tk.BooleanVar(value=True)
            
            tk.Radiobutton(panel, text="Below (A, B, C)", variable=self.label_var, value="BELOW", bg="#333", fg="white", selectcolor="#444").pack(anchor="w", padx=5)
            tk.Radiobutton(panel, text="Above (X, Y, Z)", variable=self.label_var, value="ABOVE", bg="#333", fg="white", selectcolor="#444").pack(anchor="w", padx=5)
            tk.Radiobutton(panel, text="Inside (Symbols)", variable=self.label_var, value="INSIDE", bg="#333", fg="white", selectcolor="#444").pack(anchor="w", padx=5)
            tk.Radiobutton(panel, text="None (Trackball)", variable=self.label_var, value="NONE", bg="#333", fg="white", selectcolor="#444").pack(anchor="w", padx=5)

            tk.Label(panel, text="3. LED MODE", fg="#00E5FF", bg="#333", font=("Segoe UI", 10, "bold")).pack(pady=(18,5))
            tk.Checkbutton(panel, text="LED Enabled", variable=self.led_var, bg="#333", fg="white", selectcolor="#444",
                           command=self._apply_led_flag).pack(anchor="w", padx=5)

            tk.Button(panel, text="SAVE LAYOUT JSON", bg="#00C853", fg="black", font=("Segoe UI", 11, "bold"), 
                      command=self.save_layout).pack(fill="x", pady=20, padx=5)
        else:
            self.label_var = tk.StringVar(value="BELOW")
            self.led_var = tk.BooleanVar(value=True)
            self.id_list = None
            topbar = tk.Frame(main, bg="#222")
            topbar.pack(fill="x", padx=8, pady=6)
            tk.Label(topbar, text="DECK", fg="#00E5FF", bg="#222", font=("Segoe UI", 9, "bold")).pack(side="left")
            self.deck_var = tk.StringVar(value=self.template_name)
            ttk.Combobox(topbar, textvariable=self.deck_var, values=tuple(TEMPLATES.keys()),
                         state="readonly", width=6).pack(side="left", padx=6)
            self.deck_var.trace_add("write", lambda *_: self._on_template_change())
            tk.Label(topbar, text="ID", fg="#00E5FF", bg="#222", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(10, 0))
            self.id_combo = tk.StringVar(value=BUTTON_IDS[0])
            ttk.Combobox(topbar, textvariable=self.id_combo, values=BUTTON_IDS, state="readonly", width=12).pack(side="left", padx=6)
            tk.Label(topbar, text="LABEL", fg="#00E5FF", bg="#222", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(10, 0))
            ttk.Combobox(topbar, textvariable=self.label_var, values=("BELOW","ABOVE","INSIDE","NONE"), state="readonly", width=8).pack(side="left", padx=6)
            tk.Checkbutton(topbar, text="LED", variable=self.led_var, bg="#222", fg="#DDD", selectcolor="#222",
                           command=self._apply_led_flag).pack(side="left", padx=(10, 0))
            tk.Button(topbar, text="SAVE", bg="#00C853", fg="black", font=("Segoe UI", 9, "bold"), command=self.save_layout).pack(side="left", padx=10)
            self.id_combo.trace_add("write", lambda *_: self._sync_selection_from_combo())
            self.label_var.trace_add("write", lambda *_: self._apply_label_change())
        
        self.canvas = tk.Canvas(main, bg="black", cursor="crosshair")
        self.canvas.pack(side="right", fill="both", expand=True, padx=0, pady=0)
        
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
        
        scale = min(self.target_w / orig_w, canvas_w / orig_w, canvas_h / orig_h)
        self.display_w = int(orig_w * scale)
        self.display_h = int(orig_h * scale)
        
        self.tk_img = ImageTk.PhotoImage(pil_img.resize((self.display_w, self.display_h), Image.Resampling.LANCZOS))
        self.img_x_offset = 0
        self.img_y_offset = 0

        self.canvas.delete("all")
        self._conn_bg_id = None
        self._conn_text_id = None
        self.canvas.config(width=self.display_w, height=self.display_h)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        self.load_existing_layout()
        self._update_connection_status()

    def load_existing_layout(self):
        path = self.layout_path or os.path.join("assets", "layout.json")
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    self.layout_data = json.load(f)
                for bid in self.layout_data: self.draw_marker(bid)
            except: pass
        self._ensure_all_buttons()
    def _load_layout_config(self):
        cfg_path = os.path.join(self.assets_dir, "layout_config.json")
        cfg = {}
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r") as f:
                    cfg = json.load(f)
            except Exception:
                cfg = {}
        name = cfg.get("template") or "ALU"
        if name not in TEMPLATES:
            name = "ALU"
        self.template_name = name
        img_name = TEMPLATES[name]["image"]
        layout_name = TEMPLATES[name]["layout"]
        self.img_path = os.path.join(self.assets_dir, img_name)
        if not os.path.exists(self.img_path):
            self.img_path = img_name
        self.layout_path = os.path.join(self.assets_dir, layout_name)

    def _save_layout_config(self):
        cfg_path = os.path.join(self.assets_dir, "layout_config.json")
        cfg = {"template": self.template_name}
        try:
            with open(cfg_path, "w") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass

    def _on_template_change(self):
        name = self.deck_var.get()
        if name not in TEMPLATES:
            return
        self.template_name = name
        img_name = TEMPLATES[name]["image"]
        layout_name = TEMPLATES[name]["layout"]
        self.img_path = os.path.join(self.assets_dir, img_name)
        if not os.path.exists(self.img_path):
            self.img_path = img_name
        self.layout_path = os.path.join(self.assets_dir, layout_name)
        self.layout_data = {}
        self.temp_items = {}
        self.current_selection = None
        self._save_layout_config()
        self.load_image()

    def _default_label_type(self, bid):
        if "TRACKBALL" in bid:
            return "NONE"
        if any(x in bid for x in ["START", "MENU", "REWIND"]):
            return "INSIDE"
        if any(x in bid for x in ["_X", "_Y", "_Z"]):
            return "ABOVE"
        return "BELOW"

    def _default_led_enabled(self, bid):
        return True

    def _get_connection_status(self):
        if callable(self.hw_connected):
            try:
                return bool(self.hw_connected())
            except Exception:
                return False
        return False

    def _update_connection_status(self):
        self._conn_status_job = None
        if not hasattr(self, "canvas"):
            return
        is_connected = self._get_connection_status()
        label = "CONSOLE CONNECTED" if is_connected else "CONSOLE DISCONNECTED"
        color = "#39FF14" if is_connected else "#FF5555"
        x = int(self.display_w * 0.03)
        y = int(self.display_h * 0.05)
        w = 220
        h = 22
        if self._conn_bg_id is None:
            self._conn_bg_id = self.canvas.create_rectangle(x, y, x + w, y + h, fill="#0B1116", outline="#1C1C1C")
            self._conn_text_id = self.canvas.create_text(
                x + 8, y + (h // 2), anchor="w", text=label, fill=color, font=("Segoe UI", 9, "bold")
            )
        else:
            self.canvas.coords(self._conn_bg_id, x, y, x + w, y + h)
            self.canvas.coords(self._conn_text_id, x + 8, y + (h // 2))
            self.canvas.itemconfigure(self._conn_text_id, text=label, fill=color)
        self.canvas.tag_raise(self._conn_bg_id)
        self.canvas.tag_raise(self._conn_text_id)
        self._conn_status_job = self.root.after(1000, self._update_connection_status)

    def _ensure_all_buttons(self):
        if not hasattr(self, "display_w") or not hasattr(self, "display_h"):
            return
        missing = [bid for bid in BUTTON_IDS if bid not in self.layout_data]
        if not missing:
            return
        cols = 6
        pad_x = 40
        pad_y = 40
        spacing = 50
        start_x = pad_x
        start_y = self.display_h - pad_y
        for i, bid in enumerate(missing):
            col = i % cols
            row = i // cols
            x = start_x + (col * spacing)
            y = start_y - (row * spacing)
            x = max(20, min(self.display_w - 20, x))
            y = max(20, min(self.display_h - 20, y))
            r = 18
            self.layout_data[bid] = {
                "rel_x": x / self.display_w,
                "rel_y": y / self.display_h,
                "rel_r": r / self.display_w,
                "label_type": self._default_label_type(bid),
                "led_enabled": self._default_led_enabled(bid),
            }
            self.draw_marker(bid)

    def on_id_select(self, _):
        if self.id_list.curselection():
            sel = self.id_list.get(self.id_list.curselection())
            self._set_current_selection(sel)
            
            # AUTO-SELECT LABEL TYPE
            if "TRACKBALL" in sel: self.label_var.set("NONE")
            elif any(x in sel for x in ["START", "MENU", "REWIND"]): self.label_var.set("INSIDE")
            elif any(x in sel for x in ["_X", "_Y", "_Z"]): self.label_var.set("ABOVE") # Auto Above
            else: self.label_var.set("BELOW")
            if sel in self.layout_data:
                self.led_var.set(bool(self.layout_data[sel].get("led_enabled", True)))
            
            if sel in self.layout_data: self.draw_marker(sel)
    def _sync_selection_from_combo(self):
        if hasattr(self, "id_combo"):
            self._set_current_selection(self.id_combo.get())

    def _set_current_selection(self, bid):
        self.current_selection = bid
        if self.id_list:
            try:
                idx = BUTTON_IDS.index(bid)
                self.id_list.selection_clear(0, tk.END)
                self.id_list.selection_set(idx)
                self.id_list.see(idx)
            except ValueError:
                pass
        if hasattr(self, "id_combo"):
            self.id_combo.set(bid)
        if bid in self.layout_data:
            self.led_var.set(bool(self.layout_data[bid].get("led_enabled", True)))
            self.label_var.set(self.layout_data[bid].get("label_type", self._default_label_type(bid)))

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
            "label_type": self.label_var.get(),
            "led_enabled": bool(self.led_var.get()),
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
        if not data.get("led_enabled", True):
            color = "#666666" if bid == self.current_selection else "#888888"
        c_id = self.canvas.create_oval(px-pr, py-pr, px+pr, py+pr, outline=color, width=2)
        t_id = self.canvas.create_text(px, py, text=bid, fill="white", font=("Arial", 8, "bold"))
        self.temp_items[bid] = [c_id, t_id]

    def _apply_led_flag(self):
        if not self.current_selection:
            return
        bid = self.current_selection
        if bid in self.layout_data:
            self.layout_data[bid]["led_enabled"] = bool(self.led_var.get())
            self.draw_marker(bid)

    def _apply_label_change(self):
        if not self.current_selection:
            return
        bid = self.current_selection
        if bid in self.layout_data:
            self.layout_data[bid]["label_type"] = self.label_var.get()
            self.draw_marker(bid)

    def _hit_test(self, x, y):
        for bid, data in self.layout_data.items():
            px = (data["rel_x"] * self.display_w) + self.img_x_offset
            py = (data["rel_y"] * self.display_h) + self.img_y_offset
            if ((x - px) ** 2 + (y - py) ** 2) ** 0.5 <= (data["rel_r"] * self.display_w):
                return bid
        return None

    def on_click(self, event):
        hit = self._hit_test(event.x, event.y)
        if hit:
            self._set_current_selection(hit)
            self.dragging_id = hit
            return
        self.dragging_id = None
        self.update_marker(event.x, event.y)

    def on_drag(self, event):
        if self.dragging_id:
            prev = self.current_selection
            self.current_selection = self.dragging_id
            self.update_marker(event.x, event.y)
            self.current_selection = prev
        else:
            self.update_marker(event.x, event.y)
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
        path = self.layout_path or os.path.join("assets", "layout.json")
        with open(path, "w") as f: json.dump(self.layout_data, f, indent=4)
        messagebox.showinfo("Success", "Layout saved!")

if __name__ == "__main__":
    root = tk.Tk()
    app = LayoutDesigner(root)
    root.mainloop()
