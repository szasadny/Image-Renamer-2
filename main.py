import os
import re
import time
import random
import datetime
import logging
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
import threading
import piexif
from PIL import Image
import exifread
from datetime import datetime, timedelta
import shutil
import sys

class ImageProcessor:
    def __init__(self, root_path, target_folder_name, log_callback=None):
        self.root_path = root_path
        self.target_folder_name = target_folder_name
        self.log_callback = log_callback
        self.setup_logging()
        self.stop_requested = False

    def setup_logging(self):
        self.logger = logging.getLogger('ImageProcessor')
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # File handler
        file_handler = logging.FileHandler('image_processor.log')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Custom handler for GUI logs
        if self.log_callback:
            class GUIHandler(logging.Handler):
                def __init__(self, callback):
                    super().__init__()
                    self.callback = callback
                
                def emit(self, record):
                    log_entry = self.format(record)
                    self.callback(log_entry)
            
            gui_handler = GUIHandler(self.log_callback)
            gui_handler.setFormatter(formatter)
            self.logger.addHandler(gui_handler)

    def log(self, message, level=logging.INFO):
        if level == logging.INFO:
            self.logger.info(message)
        elif level == logging.WARNING:
            self.logger.warning(message)
        elif level == logging.ERROR:
            self.logger.error(message)
        elif level == logging.DEBUG:
            self.logger.debug(message)

    def find_target_folders(self):
        """Find all folders with the target name."""
        target_folders = []
        self.log(f"Starting search for folders named '{self.target_folder_name}' in {self.root_path}")
        
        for root, dirs, _ in os.walk(self.root_path):
            if self.stop_requested:
                break
                
            for dir_name in dirs:
                if dir_name == self.target_folder_name:
                    full_path = os.path.join(root, dir_name)
                    target_folders.append(full_path)
                    self.log(f"Found target folder: {full_path}")
        
        self.log(f"Found {len(target_folders)} target folders")
        return target_folders
    
    def extract_code_from_filename(self, filename):
        """Extract the numeric code from IMG_XXXX.JPG format."""
        match = re.match(r'IMG_(\d+)\.JPG', filename, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None
    
    def get_image_files(self, folder_path):
        """Get all IMG_XXXX.JPG files from a folder and sort them by code."""
        image_files = []
        
        for filename in os.listdir(folder_path):
            if self.stop_requested:
                break
                
            if re.match(r'IMG_\d+\.JPG', filename, re.IGNORECASE):
                code = self.extract_code_from_filename(filename)
                if code is not None:
                    image_files.append((code, filename))
        
        # Sort by the numeric code
        image_files.sort(key=lambda x: x[0])
        return image_files
    
    def get_exif_creation_date(self, image_path):
        """Extract the creation date from EXIF data."""
        try:
            with open(image_path, 'rb') as f:
                tags = exifread.process_file(f)
                if 'EXIF DateTimeOriginal' in tags:
                    date_str = str(tags['EXIF DateTimeOriginal'])
                    return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
            return None
        except Exception as e:
            self.log(f"Error reading EXIF date from {image_path}: {str(e)}", logging.ERROR)
            return None
    
    def set_image_metadata(self, image_path, new_date):
        """Set all date metadata for the image."""
        try:
            # Format the date string for EXIF
            date_str = new_date.strftime("%Y:%m:%d %H:%M:%S")
            
            # Set EXIF dates with piexif
            try:
                exif_dict = piexif.load(image_path)
                
                # Set DateTimeOriginal, CreateDate, ModifyDate
                exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = date_str
                exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = date_str
                exif_dict['0th'][piexif.ImageIFD.DateTime] = date_str
                
                # Save the EXIF data back to the file
                exif_bytes = piexif.dump(exif_dict)
                piexif.insert(exif_bytes, image_path)
                
                # Set file modification and creation times
                timestamp = time.mktime(new_date.timetuple())
                os.utime(image_path, (timestamp, timestamp))
                
                return True
            except Exception as e:
                self.log(f"Error setting EXIF metadata: {str(e)}", logging.ERROR)
                return False
                
        except Exception as e:
            self.log(f"Error setting file metadata for {image_path}: {str(e)}", logging.ERROR)
            return False
    
    def process_folder(self, folder_path):
        """Process a single target folder."""
        self.log(f"Processing folder: {folder_path}")
        
        # Get all image files sorted by code
        image_files = self.get_image_files(folder_path)
        if not image_files:
            self.log(f"No IMG_*.JPG files found in {folder_path}")
            return
        
        self.log(f"Found {len(image_files)} image files")
        
        # Get the base date from the first image
        lowest_code = image_files[0][0]
        lowest_code_file = os.path.join(folder_path, image_files[0][1])
        
        base_date = self.get_exif_creation_date(lowest_code_file)
        if not base_date:
            self.log(f"Could not read creation date from {lowest_code_file}, using current time", logging.WARNING)
            base_date = datetime.now()
        
        self.log(f"Base date for metadata: {base_date}")
        
        # First, rename all files to temporary names to avoid conflicts
        temp_mappings = {}
        for code, filename in image_files:
            if self.stop_requested:
                break
                
            original_path = os.path.join(folder_path, filename)
            temp_filename = f"TEMP_{code}.JPG"
            temp_path = os.path.join(folder_path, temp_filename)
            
            try:
                os.rename(original_path, temp_path)
                temp_mappings[code] = temp_filename
                self.log(f"Renamed {filename} to {temp_filename}")
            except Exception as e:
                self.log(f"Error renaming {filename} to temporary name: {str(e)}", logging.ERROR)
        
        # Now rename to the final sequential names and update metadata
        new_codes = list(range(lowest_code, lowest_code + len(image_files)))
        
        # Calculate all the dates first, making sure they are strictly ascending
        date_increments = []
        current_date = base_date
        
        for i in range(len(image_files)):
            seconds_to_add = random.randint(30, 60)
            date_increments.append(current_date)
            current_date = current_date + timedelta(seconds=seconds_to_add)
        
        # Now apply the renames and date changes with the pre-calculated dates
        for i, (old_code, _) in enumerate(image_files):
            if self.stop_requested:
                break
                
            temp_filename = temp_mappings.get(old_code)
            if not temp_filename:
                continue
                
            temp_path = os.path.join(folder_path, temp_filename)
            new_code = new_codes[i]
            new_filename = f"IMG_{new_code:04d}.JPG"
            new_path = os.path.join(folder_path, new_filename)
            
            # Get the pre-calculated date for this image
            new_date = date_increments[i]
            
            try:
                # Rename the file
                os.rename(temp_path, new_path)
                self.log(f"Renamed {temp_filename} to {new_filename}")
                
                # Update metadata
                if self.set_image_metadata(new_path, new_date):
                    self.log(f"Updated metadata for {new_filename} to {new_date}")
                else:
                    self.log(f"Failed to update metadata for {new_filename}", logging.WARNING)
            except Exception as e:
                self.log(f"Error processing {temp_filename}: {str(e)}", logging.ERROR)
    
    def run(self):
        """Run the full processing operation."""
        start_time = time.time()
        self.log(f"Starting processing operation from root path: {self.root_path}")
        
        # Find all target folders
        target_folders = self.find_target_folders()
        
        # Process each folder
        for folder in target_folders:
            if self.stop_requested:
                self.log("Operation stopped by user")
                break
            self.process_folder(folder)
        
        elapsed_time = time.time() - start_time
        self.log(f"Processing completed in {elapsed_time:.2f} seconds")
        return len(target_folders)

    def stop(self):
        """Request the processing to stop."""
        self.stop_requested = True
        self.log("Stop requested, finishing current operation...")


class ImageProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Processor")
        self.root.geometry("800x600")
        self.root.minsize(600, 500)
        
        self.processor = None
        self.processing_thread = None
        
        self.create_widgets()
    
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Input frame
        input_frame = ttk.LabelFrame(main_frame, text="Settings", padding="10")
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
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.start_button = ttk.Button(button_frame, text="Start Processing", command=self.start_processing)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_processing, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Logs", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def browse_root_path(self):
        directory = filedialog.askdirectory()
        if directory:
            self.root_path_var.set(directory)
    
    def update_log(self, message):
        def _update():
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        
        self.root.after(0, _update)
    
    def start_processing(self):
        root_path = self.root_path_var.get()
        target_folder = self.target_folder_var.get()
        
        if not root_path or not target_folder:
            tk.messagebox.showerror("Error", "Please provide both root path and target folder name")
            return
        
        if not os.path.isdir(root_path):
            tk.messagebox.showerror("Error", f"The root path '{root_path}' is not a valid directory")
            return
        
        # Disable start button and enable stop button
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # Update status
        self.status_var.set("Processing...")
        
        # Create processor
        self.processor = ImageProcessor(root_path, target_folder, self.update_log)
        
        # Start processing in a separate thread
        self.processing_thread = threading.Thread(target=self.run_processing)
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
    def run_processing(self):
        try:
            folders_processed = self.processor.run()
            
            def on_complete():
                self.start_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)
                self.status_var.set(f"Completed - Processed {folders_processed} folders")
                tk.messagebox.showinfo("Processing Complete", f"Successfully processed {folders_processed} folders.")
            
            self.root.after(0, on_complete)
        except Exception as e:
            def on_error():
                self.start_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)
                self.status_var.set("Error occurred")
                self.update_log(f"ERROR: {str(e)}")
                tk.messagebox.showerror("Error", f"An error occurred: {str(e)}")
            
            self.root.after(0, on_error)
    
    def stop_processing(self):
        if self.processor:
            self.processor.stop()
            self.status_var.set("Stopping...")
            self.stop_button.config(state=tk.DISABLED)


def main():
    root = tk.Tk()
    app = ImageProcessorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()