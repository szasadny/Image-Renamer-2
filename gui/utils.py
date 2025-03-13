# gui/utils.py
import tkinter as tk
from tkinter import ttk
import os

def create_tooltip(widget, text):
    """Create a tooltip for a widget"""
    def on_enter(event):
        x, y, _, _ = widget.bbox("insert")
        x += widget.winfo_rootx() + 25
        y += widget.winfo_rooty() + 25
        
        # Create a toplevel window
        tip = tk.Toplevel(widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        
        label = ttk.Label(tip, text=text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)
        
        widget.tooltip = tip
    
    def on_leave(event):
        if hasattr(widget, "tooltip"):
            widget.tooltip.destroy()
    
    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)

def is_valid_folder_path(path):
    """Check if a path exists and is a directory"""
    return os.path.exists(path) and os.path.isdir(path)

def is_valid_image_path(path):
    """Check if a path exists and is a valid image file"""
    return os.path.exists(path) and os.path.isfile(path) and is_image_file(path)

def is_image_file(filename):
    """Check if a filename has a valid image extension"""
    return filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'))