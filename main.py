import os
import re
import time
import random
import datetime
import logging
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk, messagebox
import threading
import piexif
import exifread
from datetime import datetime, timedelta
from tkcalendar import DateEntry
import PIL.Image
import PIL.ImageTk

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
    
    def is_jpg_file(self, filename):
        """Check if the file is a JPG image."""
        return filename.lower().endswith(('.jpg', '.jpeg'))
    
    def get_image_files(self, folder_path):
        """Get all JPG files from a folder, identifying IMG_XXXX.JPG and other JPGs."""
        standard_images = []  # IMG_XXXX.JPG format
        other_images = []     # Other JPG files
        
        for filename in os.listdir(folder_path):
            if self.stop_requested:
                break
                
            if re.match(r'IMG_\d+\.JPG', filename, re.IGNORECASE):
                code = self.extract_code_from_filename(filename)
                if code is not None:
                    standard_images.append((code, filename))
            elif self.is_jpg_file(filename):
                other_images.append(filename)
        
        # Sort standard images by the numeric code
        standard_images.sort(key=lambda x: x[0])
        return standard_images, other_images
    
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
    
    def get_all_exif_dates(self, image_path):
        """Get all date metadata from an image file."""
        date_info = {
            'DateTimeOriginal': None,
            'DateTimeDigitized': None, 
            'DateTime': None,
            'FileModificationTime': None
        }
        
        try:
            # Get EXIF dates
            with open(image_path, 'rb') as f:
                tags = exifread.process_file(f)
                if 'EXIF DateTimeOriginal' in tags:
                    date_info['DateTimeOriginal'] = str(tags['EXIF DateTimeOriginal'])
                if 'EXIF DateTimeDigitized' in tags:
                    date_info['DateTimeDigitized'] = str(tags['EXIF DateTimeDigitized'])
                if 'Image DateTime' in tags:
                    date_info['DateTime'] = str(tags['Image DateTime'])
            
            # Get file modification time
            mod_time = os.path.getmtime(image_path)
            date_info['FileModificationTime'] = datetime.fromtimestamp(mod_time).strftime('%Y:%m:%d %H:%M:%S')
            
            return date_info
        except Exception as e:
            self.log(f"Error getting date metadata: {str(e)}", logging.ERROR)
            return date_info
    
    def parse_datetime_str(self, datetime_str):
        """Parse datetime string in format 'YYYY:MM:DD HH:MM:SS'."""
        try:
            return datetime.strptime(datetime_str, '%Y:%m:%d %H:%M:%S')
        except:
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
    
    def set_specific_metadata(self, image_path, metadata_changes):
        """
        Set specific metadata fields for an image.
        
        Args:
            image_path: Path to the image file
            metadata_changes: Dictionary with keys 'DateTimeOriginal', 'DateTimeDigitized', 
                             'DateTime', 'FileModificationTime' and datetime values
        """
        try:
            # Set EXIF dates with piexif if any are specified
            if any(k in metadata_changes for k in ['DateTimeOriginal', 'DateTimeDigitized', 'DateTime']):
                try:
                    exif_dict = piexif.load(image_path)
                    
                    # Set individual EXIF fields if specified
                    if 'DateTimeOriginal' in metadata_changes and metadata_changes['DateTimeOriginal']:
                        date_str = metadata_changes['DateTimeOriginal'].strftime("%Y:%m:%d %H:%M:%S")
                        exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = date_str
                    
                    if 'DateTimeDigitized' in metadata_changes and metadata_changes['DateTimeDigitized']:
                        date_str = metadata_changes['DateTimeDigitized'].strftime("%Y:%m:%d %H:%M:%S")
                        exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = date_str
                    
                    if 'DateTime' in metadata_changes and metadata_changes['DateTime']:
                        date_str = metadata_changes['DateTime'].strftime("%Y:%m:%d %H:%M:%S")
                        exif_dict['0th'][piexif.ImageIFD.DateTime] = date_str
                    
                    # Save the EXIF data back to the file
                    exif_bytes = piexif.dump(exif_dict)
                    piexif.insert(exif_bytes, image_path)
                    
                except Exception as e:
                    self.log(f"Error setting EXIF metadata: {str(e)}", logging.ERROR)
                    return False, f"Error setting EXIF metadata: {str(e)}"
            
            # Set file modification time if specified
            if 'FileModificationTime' in metadata_changes and metadata_changes['FileModificationTime']:
                timestamp = time.mktime(metadata_changes['FileModificationTime'].timetuple())
                os.utime(image_path, (timestamp, timestamp))
            
            return True, "Successfully updated image metadata"
                
        except Exception as e:
            self.log(f"Error setting file metadata for {image_path}: {str(e)}", logging.ERROR)
            return False, f"Error: {str(e)}"
    
    def process_folder(self, folder_path):
        """Process a single target folder."""
        self.log(f"Processing folder: {folder_path}")
        
        # Get all image files, separating standard IMG_XXXX.JPG and other JPGs
        standard_images, other_images = self.get_image_files(folder_path)
        
        total_images = len(standard_images) + len(other_images)
        if total_images == 0:
            self.log(f"No JPG files found in {folder_path}")
            return
        
        self.log(f"Found {len(standard_images)} IMG_XXXX.JPG files and {len(other_images)} other JPG files")
        
        # Determine the starting code for renaming
        if standard_images:
            # If we have IMG_XXXX.JPG files, use the lowest existing code
            lowest_code = standard_images[0][0]
            self.log(f"Using existing lowest code: {lowest_code}")
            # Get base date from the first standard image
            lowest_code_file = os.path.join(folder_path, standard_images[0][1])
            base_date = self.get_exif_creation_date(lowest_code_file)
        else:
            # If no standard images, generate a random starting code between 1000 and 2000
            lowest_code = random.randint(1000, 2000)
            self.log(f"No IMG_XXXX.JPG files found, using random starting code: {lowest_code}")
            base_date = None
            
            # Try to get a base date from the first other JPG
            if other_images:
                first_other_file = os.path.join(folder_path, other_images[0])
                base_date = self.get_exif_creation_date(first_other_file)
        
        if not base_date:
            self.log(f"Could not read creation date, using current time", logging.WARNING)
            base_date = datetime.now()
        
        self.log(f"Base date for metadata: {base_date}")
        
        # First, rename all files to temporary names to avoid conflicts
        temp_mappings = {}
        
        # Handle standard images first
        for code, filename in standard_images:
            if self.stop_requested:
                break
                
            original_path = os.path.join(folder_path, filename)
            temp_filename = f"TEMP_STD_{code}.JPG"
            temp_path = os.path.join(folder_path, temp_filename)
            
            try:
                os.rename(original_path, temp_path)
                temp_mappings[filename] = temp_filename
                self.log(f"Renamed {filename} to {temp_filename}")
            except Exception as e:
                self.log(f"Error renaming {filename} to temporary name: {str(e)}", logging.ERROR)
        
        # Now handle other JPG files
        for i, filename in enumerate(other_images):
            if self.stop_requested:
                break
                
            original_path = os.path.join(folder_path, filename)
            temp_filename = f"TEMP_OTHER_{i}.JPG"
            temp_path = os.path.join(folder_path, temp_filename)
            
            try:
                os.rename(original_path, temp_path)
                temp_mappings[filename] = temp_filename
                self.log(f"Renamed {filename} to {temp_filename}")
            except Exception as e:
                self.log(f"Error renaming {filename} to temporary name: {str(e)}", logging.ERROR)
        
        # Calculate all the dates first, making sure they are strictly ascending
        date_increments = []
        current_date = base_date
        
        for i in range(total_images):
            seconds_to_add = random.randint(30, 60)
            date_increments.append(current_date)
            current_date = current_date + timedelta(seconds=seconds_to_add)
        
        # Now rename all files to the final sequential names
        all_temp_files = []
        
        # First add standard images
        for code, original_filename in standard_images:
            temp_filename = temp_mappings.get(original_filename)
            if temp_filename:
                all_temp_files.append((temp_filename, original_filename))
        
        # Then add other JPG files
        for original_filename in other_images:
            temp_filename = temp_mappings.get(original_filename)
            if temp_filename:
                all_temp_files.append((temp_filename, original_filename))
        
        # Now rename everything to the new sequence
        for i, (temp_filename, original_filename) in enumerate(all_temp_files):
            if self.stop_requested:
                break
                
            temp_path = os.path.join(folder_path, temp_filename)
            new_code = lowest_code + i
            new_filename = f"IMG_{new_code:04d}.JPG"
            new_path = os.path.join(folder_path, new_filename)
            
            # Get the pre-calculated date for this image
            new_date = date_increments[i]
            
            try:
                # Rename the file
                os.rename(temp_path, new_path)
                self.log(f"Renamed {temp_filename} (originally {original_filename}) to {new_filename}")
                
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

    def edit_image(self, image_path, new_name=None, metadata_changes=None):
        """
        Edit an image's filename and/or metadata independently.
        
        Args:
            image_path: Path to the image file
            new_name: New filename (if None, keep the current name)
            metadata_changes: Dictionary with datetime values for specific fields
        """
        if not os.path.isfile(image_path):
            return False, f"File not found: {image_path}"
            
        try:
            directory = os.path.dirname(image_path)
            current_name = os.path.basename(image_path)
            changes_made = []
            new_path = image_path
            
            # Rename the file if requested
            if new_name and new_name != current_name:
                new_path = os.path.join(directory, new_name)
                
                # Check if the new filename already exists
                if os.path.exists(new_path):
                    return False, f"Cannot rename: {new_name} already exists in the directory"
                
                # Rename the file
                os.rename(image_path, new_path)
                self.log(f"Renamed {current_name} to {new_name}")
                changes_made.append(f"renamed to {new_name}")
            
            # Update metadata if requested
            if metadata_changes:
                success, message = self.set_specific_metadata(new_path, metadata_changes)
                if success:
                    metadata_fields = [k for k in metadata_changes.keys() if metadata_changes[k] is not None]
                    if metadata_fields:
                        changes_made.append(f"updated metadata fields: {', '.join(metadata_fields)}")
                else:
                    return False, message
            
            if changes_made:
                return True, f"Successfully {' and '.join(changes_made)}"
            else:
                return False, "No changes were made"
                
        except Exception as e:
            self.log(f"Error editing {image_path}: {str(e)}", logging.ERROR)
            return False, f"Error: {str(e)}"


class ImageProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Processor")
        self.root.geometry("800x600")
        self.root.minsize(600, 500)
        
        self.processor = None
        self.processing_thread = None
        
        # For single image editor
        self.current_image_path = None
        self.image_preview = None
        
        # Create a processor instance
        self.processor = ImageProcessor("", "", self.update_log)
        
        self.create_widgets()
    
    def create_widgets(self):
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Edit All (renamed from "Rename All")
        self.edit_all_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.edit_all_tab, text="Edit All")
        self.setup_edit_all_tab()
        
        # Tab 2: Edit Picture
        self.edit_picture_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.edit_picture_tab, text="Edit Picture")
        self.setup_edit_picture_tab()
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_edit_all_tab(self):
        """Set up the Edit All tab (renamed from Rename All)."""
        main_frame = ttk.Frame(self.edit_all_tab, padding="10")
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
    
    def setup_edit_picture_tab(self):
        """Set up the Edit Picture tab."""
        main_frame = ttk.Frame(self.edit_picture_tab, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Image selection and preview
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5, anchor=tk.N)
        
        # File selection
        file_frame = ttk.LabelFrame(left_panel, text="Select Image", padding="10")
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(file_frame, text="Image Path:").grid(column=0, row=0, sticky=tk.W, padx=5, pady=5)
        self.image_path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.image_path_var, width=40).grid(column=1, row=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Button(file_frame, text="Browse...", command=self.browse_image_path).grid(column=2, row=0, padx=5, pady=5)
        
        # Image preview
        preview_frame = ttk.LabelFrame(left_panel, text="Preview", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.preview_canvas = tk.Canvas(preview_frame, bg="lightgray")
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Right panel - Editing options
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5, pady=5, anchor=tk.N)
        
        # Filename editor
        name_frame = ttk.LabelFrame(right_panel, text="Rename Image", padding="10")
        name_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(name_frame, text="Current Filename:").grid(column=0, row=0, sticky=tk.W, padx=5, pady=5)
        self.current_filename_var = tk.StringVar()
        ttk.Label(name_frame, textvariable=self.current_filename_var).grid(column=1, row=0, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(name_frame, text="New Filename:").grid(column=0, row=1, sticky=tk.W, padx=5, pady=5)
        self.new_filename_var = tk.StringVar()
        ttk.Entry(name_frame, textvariable=self.new_filename_var, width=30).grid(column=1, row=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Datetime editor sections
        self.date_pickers = {}
        self.time_vars = {}
        
        # DateTimeOriginal
        self.create_datetime_editor(right_panel, "Original Date/Time (when photo was taken)", "DateTimeOriginal")
        
        # DateTimeDigitized
        self.create_datetime_editor(right_panel, "Digitized Date/Time (when photo was digitized)", "DateTimeDigitized")
        
        # DateTime
        self.create_datetime_editor(right_panel, "Modified Date/Time (last modification)", "DateTime")
        
        # File Modification Time
        self.create_datetime_editor(right_panel, "File Modification Date/Time", "FileModificationTime")
        
        # Action buttons
        action_frame = ttk.Frame(right_panel)
        action_frame.pack(fill=tk.X, padx=5, pady=15)
        
        # Filename only button
        self.rename_button = ttk.Button(
            action_frame, 
            text="Rename Only", 
            command=lambda: self.apply_image_changes(rename_only=True), 
            state=tk.DISABLED
        )
        self.rename_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Update all metadata button
        self.metadata_button = ttk.Button(
            action_frame, 
            text="Update Metadata Only", 
            command=lambda: self.apply_image_changes(metadata_only=True),
            state=tk.DISABLED
        )
        self.metadata_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Update both
        self.apply_button = ttk.Button(
            action_frame, 
            text="Rename & Update Metadata", 
            command=lambda: self.apply_image_changes(),
            state=tk.DISABLED
        )
        self.apply_button.pack(side=tk.LEFT, padx=5, pady=5)
    
    def create_datetime_editor(self, parent, title, field_name):
        """Create a date/time editor section for a specific metadata field."""
        frame = ttk.LabelFrame(parent, text=title, padding="10")
        frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Current value
        ttk.Label(frame, text="Current:").grid(column=0, row=0, sticky=tk.W, padx=5, pady=2)
        current_var = tk.StringVar(value="Not available")
        ttk.Label(frame, textvariable=current_var).grid(column=1, row=0, sticky=tk.W, padx=5, pady=2)
        
        # Enable checkbox
        enable_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, 
            text="Enable editing", 
            variable=enable_var,
            command=lambda: self.toggle_datetime_editor(field_name)
        ).grid(column=0, row=1, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        # Create date picker and time entry
        date_frame = ttk.Frame(frame)
        date_frame.grid(column=0, row=2, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=2)
        
        ttk.Label(date_frame, text="Date:").pack(side=tk.LEFT, padx=2)
        date_picker = DateEntry(
            date_frame, 
            width=12, 
            background='darkblue', 
            foreground='white', 
            borderwidth=2,
            state=tk.DISABLED
        )
        date_picker.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(date_frame, text="Time:").pack(side=tk.LEFT, padx=(10, 2))
        
        # Time variables
        hour_var = tk.StringVar(value="00")
        minute_var = tk.StringVar(value="00")
        second_var = tk.StringVar(value="00")
        
        # Time spinboxes
        hour_spinbox = ttk.Spinbox(
            date_frame, 
            from_=0, 
            to=23, 
            width=2, 
            textvariable=hour_var,
            state=tk.DISABLED
        )
        hour_spinbox.pack(side=tk.LEFT)
        
        ttk.Label(date_frame, text=":").pack(side=tk.LEFT)
        
        minute_spinbox = ttk.Spinbox(
            date_frame, 
            from_=0, 
            to=59, 
            width=2, 
            textvariable=minute_var,
            state=tk.DISABLED
        )
        minute_spinbox.pack(side=tk.LEFT)
        
        ttk.Label(date_frame, text=":").pack(side=tk.LEFT)
        
        second_spinbox = ttk.Spinbox(
            date_frame, 
            from_=0, 
            to=59, 
            width=2, 
            textvariable=second_var,
            state=tk.DISABLED
        )
        second_spinbox.pack(side=tk.LEFT)
        
        # Save references to all widgets
        self.date_pickers[field_name] = {
            'current_var': current_var,
            'enable_var': enable_var,
            'date_picker': date_picker,
            'hour_var': hour_var,
            'minute_var': minute_var,
            'second_var': second_var,
            'hour_spinbox': hour_spinbox,
            'minute_spinbox': minute_spinbox,
            'second_spinbox': second_spinbox
        }
    
    def toggle_datetime_editor(self, field_name):
        """Enable or disable a datetime editor based on its checkbox."""
        if field_name in self.date_pickers:
            widgets = self.date_pickers[field_name]
            enabled = widgets['enable_var'].get()
            
            # Set state for date picker and time spinboxes
            state = tk.NORMAL if enabled else tk.DISABLED
            widgets['date_picker'].config(state=state)
            widgets['hour_spinbox'].config(state=state)
            widgets['minute_spinbox'].config(state=state)
            widgets['second_spinbox'].config(state=state)
            
            # Ensure at least one button is enabled if we have a valid image
            if self.current_image_path:
                self.update_button_states()
    
    def update_button_states(self):
        """Update the state of action buttons based on current inputs."""
        if self.current_image_path:
            # Enable rename button if filename is different
            current_filename = os.path.basename(self.current_image_path)
            new_filename = self.new_filename_var.get()
            
            if new_filename and new_filename != current_filename:
                self.rename_button.config(state=tk.NORMAL)
            else:
                self.rename_button.config(state=tk.DISABLED)
            
            # Enable metadata button if any datetime editor is enabled
            metadata_enabled = any(self.date_pickers[field]['enable_var'].get() for field in self.date_pickers)
            
            if metadata_enabled:
                self.metadata_button.config(state=tk.NORMAL)
                # Also enable the combined button if filename is different
                if new_filename and new_filename != current_filename:
                    self.apply_button.config(state=tk.NORMAL)
                else:
                    self.apply_button.config(state=tk.DISABLED)
            else:
                self.metadata_button.config(state=tk.DISABLED)
                self.apply_button.config(state=tk.DISABLED)
        else:
            # Disable all buttons if no image is selected
            self.rename_button.config(state=tk.DISABLED)
            self.metadata_button.config(state=tk.DISABLED)
            self.apply_button.config(state=tk.DISABLED)
    
    def browse_root_path(self):
        directory = filedialog.askdirectory()
        if directory:
            self.root_path_var.set(directory)
    
    def browse_image_path(self):
        image_file = filedialog.askopenfilename(
            filetypes=[("JPEG Images", "*.jpg;*.jpeg"), ("All Files", "*.*")]
        )
        if image_file:
            self.image_path_var.set(image_file)
            self.load_image_data(image_file)
    
    def load_image_data(self, image_path):
        """Load image data and display in the Edit Picture tab."""
        try:
            self.current_image_path = image_path
            filename = os.path.basename(image_path)
            self.current_filename_var.set(filename)
            self.new_filename_var.set(filename)
            
            # Get image metadata
            all_metadata = self.processor.get_all_exif_dates(image_path)
            
            # Update all datetime editors with current values
            for field_name, widgets in self.date_pickers.items():
                current_value = all_metadata.get(field_name)
                
                if current_value:
                    widgets['current_var'].set(current_value)
                    
                    # Parse the datetime string and set the values
                    dt = self.processor.parse_datetime_str(current_value)
                    if dt:
                        widgets['date_picker'].set_date(dt.date())
                        widgets['hour_var'].set(f"{dt.hour:02d}")
                        widgets['minute_var'].set(f"{dt.minute:02d}")
                        widgets['second_var'].set(f"{dt.second:02d}")
                else:
                    widgets['current_var'].set("Not available")
                    
                    # Set default values
                    now = datetime.now()
                    widgets['date_picker'].set_date(now.date())
                    widgets['hour_var'].set(f"{now.hour:02d}")
                    widgets['minute_var'].set(f"{now.minute:02d}")
                    widgets['second_var'].set(f"{now.second:02d}")
                
                # Reset the enable checkbox
                widgets['enable_var'].set(False)
                self.toggle_datetime_editor(field_name)
            
            # Load and display image preview
            self.load_image_preview(image_path)
            
            # Update button states
            self.update_button_states()

            self.new_filename_var.trace_add("write", lambda *args: self.update_button_states())
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading image data: {str(e)}")
    
    def load_image_preview(self, image_path):
        """Load and display image preview."""
        try:
            # Clear previous image
            self.preview_canvas.delete("all")
            
            # Open image and resize for preview
            original_image = PIL.Image.open(image_path)
            
            # Calculate resize dimensions while maintaining aspect ratio
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()
            
            # If canvas hasn't been realized yet, use default sizes
            if canvas_width <= 1:
                canvas_width = 300
            if canvas_height <= 1:
                canvas_height = 300
            
            # Calculate resize dimensions
            img_width, img_height = original_image.size
            ratio = min(canvas_width/img_width, canvas_height/img_height)
            new_width = int(img_width * ratio)
            new_height = int(img_height * ratio)
            
            # Resize image
            resized_image = original_image.resize((new_width, new_height), PIL.Image.LANCZOS)
            
            # Convert to PhotoImage
            self.image_preview = PIL.ImageTk.PhotoImage(resized_image)
            
            # Display on canvas
            self.preview_canvas.create_image(
                canvas_width//2, canvas_height//2,
                image=self.image_preview,
                anchor=tk.CENTER
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading image preview: {str(e)}")
    
    def get_enabled_metadata_changes(self):
        """Get a dictionary of enabled metadata changes."""
        metadata_changes = {}
        
        for field_name, widgets in self.date_pickers.items():
            if widgets['enable_var'].get():
                try:
                    # Get date from picker
                    selected_date = widgets['date_picker'].get_date()
                    
                    # Get time components
                    hour = int(widgets['hour_var'].get())
                    minute = int(widgets['minute_var'].get())
                    second = int(widgets['second_var'].get())
                    
                    # Create datetime object
                    dt = datetime.combine(
                        selected_date,
                        datetime.min.time().replace(hour=hour, minute=minute, second=second)
                    )
                    
                    metadata_changes[field_name] = dt
                except ValueError as e:
                    messagebox.showerror("Error", f"Invalid date/time for {field_name}: {str(e)}")
                    return None
        
        return metadata_changes
    
    def apply_image_changes(self, rename_only=False, metadata_only=False):
        """Apply the changes to the selected image."""
        if not self.current_image_path:
            messagebox.showerror("Error", "No image selected")
            return
        
        try:
            new_filename = None
            metadata_changes = None
            
            # Determine what changes to make
            if not metadata_only:
                # Get the new filename
                new_name = self.new_filename_var.get()
                if not new_name:
                    messagebox.showerror("Error", "Please enter a new filename")
                    return
                
                # Check if the filename has a valid extension
                if not self.is_valid_image_filename(new_name):
                    messagebox.showerror("Error", "Invalid filename. Please ensure it has a .jpg or .jpeg extension")
                    return
                
                # Set the new filename if it's different from current
                current_name = os.path.basename(self.current_image_path)
                if new_name != current_name:
                    new_filename = new_name
            
            if not rename_only:
                # Get metadata changes
                metadata_changes = self.get_enabled_metadata_changes()
                if metadata_changes is None:  # Error occurred
                    return
            
            # Check if we actually have changes to make
            if not new_filename and not metadata_changes:
                messagebox.showinfo("No Changes", "No changes specified to apply")
                return
            
            # Apply changes
            success, message = self.processor.edit_image(
                self.current_image_path,
                new_filename,
                metadata_changes
            )
            
            if success:
                messagebox.showinfo("Success", message)
                # Update the current image path if renamed
                if new_filename:
                    self.current_image_path = os.path.join(os.path.dirname(self.current_image_path), new_filename)
                    self.image_path_var.set(self.current_image_path)
                
                # Reload the image data to reflect changes
                self.load_image_data(self.current_image_path)
            else:
                messagebox.showerror("Error", message)
                
        except Exception as e:
            messagebox.showerror("Error", f"Error applying changes: {str(e)}")
    
    def is_valid_image_filename(self, filename):
        """Check if the filename has a valid image extension."""
        return filename.lower().endswith(('.jpg', '.jpeg'))
    
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
            messagebox.showerror("Error", "Please provide both root path and target folder name")
            return
        
        if not os.path.isdir(root_path):
            messagebox.showerror("Error", f"The root path '{root_path}' is not a valid directory")
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
                messagebox.showinfo("Processing Complete", f"Successfully processed {folders_processed} folders.")
            
            self.root.after(0, on_complete)
        except Exception as e:
            def on_error():
                self.start_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)
                self.status_var.set("Error occurred")
                self.update_log(f"ERROR: {str(e)}")
                messagebox.showerror("Error", f"An error occurred: {str(e)}")
            
            self.root.after(0, on_error)
    
    def stop_processing(self):
        if self.processor:
            self.processor.stop()
            self.status_var.set("Stopping...")
            self.stop_button.config(state=tk.DISABLED)


def main():
    root = tk.Tk()
    app = ImageProcessorGUI(root)
    
    # Configure canvas update when window is resized
    def on_resize(event):
        if hasattr(app, 'current_image_path') and app.current_image_path and app.notebook.index(app.notebook.select()) == 1:
            # Only reload preview if we're on the Edit Picture tab
            app.load_image_preview(app.current_image_path)
    
    # Bind the resize event to update the image preview
    root.bind('<Configure>', on_resize)
    
    root.mainloop()

if __name__ == "__main__":
    main()