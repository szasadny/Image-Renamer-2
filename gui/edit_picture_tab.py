import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from datetime import datetime
from tkcalendar import DateEntry
import PIL.Image
import PIL.ImageTk

class EditPictureTab(ttk.Frame):
    def __init__(self, parent, processor, app):
        super().__init__(parent, padding="10")
        self.processor = processor
        self.app = app
        
        # For image preview
        self.current_image_path = None
        self.image_preview = None
        
        # Date pickers dict
        self.date_pickers = {}
        
        self.create_widgets()
    
    def create_widgets(self):
        # Left panel - Image selection and preview
        left_panel = ttk.Frame(self)
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
        right_panel = ttk.Frame(self)
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
            self.load_image_preview()
            
            # Update button states
            self.update_button_states()

            # Add trace to update button states when filename changes
            self.new_filename_var.trace_add("write", lambda *args: self.update_button_states())
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading image data: {str(e)}")
    
    def load_image_preview(self):
        """Load and display image preview."""
        try:
            if not self.current_image_path:
                return
                
            # Clear previous image
            self.preview_canvas.delete("all")
            
            # Open image and resize for preview
            original_image = PIL.Image.open(self.current_image_path)
            
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
                
                # Update status
                self.app.set_status(f"Image edited: {os.path.basename(self.current_image_path)}")
            else:
                messagebox.showerror("Error", message)
                
        except Exception as e:
            messagebox.showerror("Error", f"Error applying changes: {str(e)}")
    
    def is_valid_image_filename(self, filename):
        """Check if the filename has a valid image extension."""
        return filename.lower().endswith(('.jpg', '.jpeg'))