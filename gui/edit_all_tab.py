import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import os

class EditAllTab(ttk.Frame):
    def __init__(self, parent, processor, app):
        super().__init__(parent, padding="10")
        self.processor = processor
        self.app = app
        
        self.create_widgets()
    
    def create_widgets(self):
        # Input frame
        input_frame = ttk.LabelFrame(self, text="Settings", padding="10")
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Root path selection
        ttk.Label(input_frame, text="Root Path:").grid(column=0, row=0, sticky=tk.W, padx=5, pady=5)
        self.root_path_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.root_path_var, width=50).grid(column=1, row=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Button(input_frame, text="Browse...", command=self.browse_root_path).grid(column=2, row=0, padx=5, pady=5)
        
        # Target folder name
        ttk.Label(input_frame, text="Target Folder Name:").grid(column=0, row=1, sticky=tk.W, padx=5, pady=5)
        self.target_folder_var = tk.StringVar(value="01. Foto's")  # Set default value
        ttk.Entry(input_frame, textvariable=self.target_folder_var, width=50).grid(column=1, row=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Action buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.start_button = ttk.Button(button_frame, text="Start Processing", command=self.start_processing)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_processing, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Log area
        log_frame = ttk.LabelFrame(self, text="Logs", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
    
    def browse_root_path(self):
        directory = filedialog.askdirectory()
        if directory:
            self.root_path_var.set(directory)
    
    def update_log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def start_processing(self):
        root_path = self.root_path_var.get()
        target_folder = self.target_folder_var.get()
        self.app.start_processing(root_path, target_folder)
    
    def stop_processing(self):
        self.app.stop_processing()
    
    def set_processing_state(self, is_processing):
        """Update UI state based on whether processing is active"""
        if is_processing:
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
        else:
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)