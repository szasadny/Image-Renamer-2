import tkinter as tk
from tkinter import ttk, messagebox
import os
import threading

from image_processor import ImageProcessor
from gui.edit_all_tab import EditAllTab
from gui.edit_picture_tab import EditPictureTab

class ImageProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Processor")
        self.root.geometry("800x600")
        self.root.minsize(600, 500)
        
        self.processor = None
        self.processing_thread = None
        
        # Create a processor instance with empty values for now
        self.processor = ImageProcessor("", "", self.update_log)
        
        self.create_widgets()
        self.setup_bindings()
    
    def create_widgets(self):
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Edit All (renamed from "Rename All")
        self.edit_all_tab = EditAllTab(self.notebook, self.processor, self)
        self.notebook.add(self.edit_all_tab, text="Edit All")
        
        # Tab 2: Edit Picture
        self.edit_picture_tab = EditPictureTab(self.notebook, self.processor, self)
        self.notebook.add(self.edit_picture_tab, text="Edit Picture")
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_bindings(self):
        # Configure canvas update when window is resized
        self.root.bind('<Configure>', self.on_resize)
    
    def on_resize(self, event):
        # Only reload preview if we're on the Edit Picture tab and have an image loaded
        if (self.notebook.index(self.notebook.select()) == 1 and 
            hasattr(self.edit_picture_tab, 'current_image_path') and 
            self.edit_picture_tab.current_image_path):
            self.edit_picture_tab.load_image_preview()
    
    def update_log(self, message):
        """Update the log in the Edit All tab"""
        def _update():
            if hasattr(self, 'edit_all_tab'):
                self.edit_all_tab.update_log(message)
        
        self.root.after(0, _update)
    
    def set_status(self, message):
        """Update the status bar message"""
        self.status_var.set(message)
    
    def start_processing(self, root_path, target_folder):
        """
        Start the image processing operation
        This is called from the Edit All tab
        """
        if not root_path or not target_folder:
            messagebox.showerror("Error", "Please provide both root path and target folder name")
            return
        
        if not os.path.isdir(root_path):
            messagebox.showerror("Error", f"The root path '{root_path}' is not a valid directory")
            return
        
        # Update UI state in the edit_all_tab
        self.edit_all_tab.set_processing_state(True)
        
        # Update status
        self.set_status("Processing...")
        
        # Create processor
        self.processor = ImageProcessor(root_path, target_folder, self.update_log)
        
        # Start processing in a separate thread
        self.processing_thread = threading.Thread(target=self.run_processing)
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
    def run_processing(self):
        """Run the processing operation in a separate thread"""
        try:
            folders_processed = self.processor.run()
            
            def on_complete():
                self.edit_all_tab.set_processing_state(False)
                self.set_status(f"Completed - Processed {folders_processed} folders")
                messagebox.showinfo("Processing Complete", f"Successfully processed {folders_processed} folders.")
            
            self.root.after(0, on_complete)
        except Exception as e:
            def on_error():
                self.edit_all_tab.set_processing_state(False)
                self.set_status("Error occurred")
                self.update_log(f"ERROR: {str(e)}")
                messagebox.showerror("Error", f"An error occurred: {str(e)}")
            
            self.root.after(0, on_error)
    
    def stop_processing(self):
        """Stop the processing operation"""
        if self.processor:
            self.processor.stop()
            self.set_status("Stopping...")
            self.edit_all_tab.stop_button.config(state=tk.DISABLED)