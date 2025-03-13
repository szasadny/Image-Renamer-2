import os
import re
import time
import random
import datetime
import logging
import threading
import piexif
import exifread
from datetime import datetime, timedelta
import PIL.Image

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