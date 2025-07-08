import os
import shutil
import tempfile
import ctypes
import sys
import subprocess
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import configparser
from pathlib import Path

# === Configuration Management ===
class ConfigManager:
    def __init__(self, config_file="cScan_config.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load_config()
    
    def get_default_config(self):
        """Return default configuration values"""
        return {
            'Settings': {
                'large_file_threshold_mb': '100',
                'default_interface': 'ask',  # ask, cli, gui
                'clean_temp_by_default': 'true',
                'clean_recycle_by_default': 'true',
                'max_files_to_display': '50',
                'progress_update_interval': '100',
                'backup_before_delete': 'false',
                'scan_hidden_folders': 'false'
            },
            'Paths': {
                'include_user_profile': 'true',
                'include_downloads': 'true',
                'include_documents': 'true',
                'include_desktop': 'true',
                'include_pictures': 'true',
                'include_videos': 'true',
                'include_music': 'true',
                'include_temp_folders': 'true',
                'custom_scan_paths': ''  # comma-separated additional paths
            },
            'FileTypes': {
                'suggest_installer_cleanup': 'true',
                'suggest_video_cleanup': 'true',
                'suggest_backup_cleanup': 'true',
                'installer_extensions': '.exe,.msi,.dmg',
                'video_extensions': '.mp4,.avi,.mkv,.mov,.wmv',
                'backup_extensions': '.bak,.old,.backup'
            },
            'GUI': {
                'window_width': '900',
                'window_height': '700',
                'font_size': '9',
                'theme': 'default'  # default, dark (future)
            }
        }
    
    def load_config(self):
        """Load configuration from file, create with defaults if doesn't exist"""
        if os.path.exists(self.config_file):
            try:
                self.config.read(self.config_file)
                # Validate config has all required sections/keys
                self._validate_config()
            except Exception as e:
                print(f"Error reading config file: {e}")
                print("Using default configuration...")
                self._create_default_config()
        else:
            print(f"Config file not found. Creating {self.config_file} with default settings...")
            self._create_default_config()
    
    def _validate_config(self):
        """Ensure config has all required sections and keys"""
        defaults = self.get_default_config()
        config_updated = False
        
        for section, keys in defaults.items():
            if not self.config.has_section(section):
                self.config.add_section(section)
                config_updated = True
            
            for key, default_value in keys.items():
                if not self.config.has_option(section, key):
                    self.config.set(section, key, default_value)
                    config_updated = True
        
        if config_updated:
            self.save_config()
            print("Configuration updated with missing default values.")
    
    def _create_default_config(self):
        """Create configuration file with default values"""
        defaults = self.get_default_config()
        
        for section, keys in defaults.items():
            self.config.add_section(section)
            for key, value in keys.items():
                self.config.set(section, key, value)
        
        self.save_config()
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                self.config.write(f)
        except Exception as e:
            print(f"Error saving config file: {e}")
    
    def get(self, section, key, fallback=None):
        """Get configuration value"""
        return self.config.get(section, key, fallback=fallback)
    
    def getint(self, section, key, fallback=0):
        """Get integer configuration value"""
        return self.config.getint(section, key, fallback=fallback)
    
    def getboolean(self, section, key, fallback=False):
        """Get boolean configuration value"""
        return self.config.getboolean(section, key, fallback=fallback)
    
    def set(self, section, key, value):
        """Set configuration value"""
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, str(value))
    
    def get_scan_paths(self):
        """Build scan paths list based on configuration"""
        paths = []
        user_profile = os.environ.get("USERPROFILE", "")
        
        if self.getboolean('Paths', 'include_user_profile'):
            paths.append(user_profile)
        
        if self.getboolean('Paths', 'include_downloads'):
            paths.append(os.path.join(user_profile, "Downloads"))
        
        if self.getboolean('Paths', 'include_documents'):
            paths.append(os.path.join(user_profile, "Documents"))
        
        if self.getboolean('Paths', 'include_desktop'):
            paths.append(os.path.join(user_profile, "Desktop"))
        
        if self.getboolean('Paths', 'include_pictures'):
            paths.append(os.path.join(user_profile, "Pictures"))
        
        if self.getboolean('Paths', 'include_videos'):
            paths.append(os.path.join(user_profile, "Videos"))
        
        if self.getboolean('Paths', 'include_music'):
            paths.append(os.path.join(user_profile, "Music"))
        
        if self.getboolean('Paths', 'include_temp_folders'):
            paths.extend([
                os.environ.get("TEMP", ""),
                os.environ.get("TMP", ""),
                os.path.join(user_profile, "AppData", "Local", "Temp"),
            ])
        
        # Add custom paths
        custom_paths = self.get('Paths', 'custom_scan_paths', '')
        if custom_paths:
            for path in custom_paths.split(','):
                path = path.strip()
                if path:
                    paths.append(path)
        
        # Remove duplicates and non-existent paths
        return list(set([p for p in paths if p and os.path.exists(p)]))
    
    def show_config_editor(self):
        """Show a simple config editor dialog"""
        try:
            self._show_config_gui()
        except Exception as e:
            print(f"GUI config editor failed: {e}")
            self._show_config_cli()
    
    def _show_config_gui(self):
        """GUI configuration editor"""
        config_window = tk.Toplevel()
        config_window.title("Configuration Settings")
        config_window.geometry("600x500")
        
        notebook = ttk.Notebook(config_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Settings tab
        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text="Settings")
        
        # File threshold
        ttk.Label(settings_frame, text="Large file threshold (MB):").grid(row=0, column=0, sticky=tk.W, pady=5)
        threshold_var = tk.StringVar(value=self.get('Settings', 'large_file_threshold_mb'))
        ttk.Entry(settings_frame, textvariable=threshold_var, width=10).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Default interface
        ttk.Label(settings_frame, text="Default interface:").grid(row=1, column=0, sticky=tk.W, pady=5)
        interface_var = tk.StringVar(value=self.get('Settings', 'default_interface'))
        interface_combo = ttk.Combobox(settings_frame, textvariable=interface_var, 
                                     values=['ask', 'cli', 'gui'], width=10)
        interface_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Checkboxes for boolean settings
        backup_var = tk.BooleanVar(value=self.getboolean('Settings', 'backup_before_delete'))
        ttk.Checkbutton(settings_frame, text="Backup files before deletion", 
                       variable=backup_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        hidden_var = tk.BooleanVar(value=self.getboolean('Settings', 'scan_hidden_folders'))
        ttk.Checkbutton(settings_frame, text="Scan hidden folders", 
                       variable=hidden_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Paths tab
        paths_frame = ttk.Frame(notebook)
        notebook.add(paths_frame, text="Scan Paths")
        
        path_vars = {}
        path_options = [
            ('include_user_profile', 'User Profile'),
            ('include_downloads', 'Downloads'),
            ('include_documents', 'Documents'),
            ('include_desktop', 'Desktop'),
            ('include_pictures', 'Pictures'),
            ('include_videos', 'Videos'),
            ('include_music', 'Music'),
            ('include_temp_folders', 'Temp Folders')
        ]
        
        for i, (key, label) in enumerate(path_options):
            var = tk.BooleanVar(value=self.getboolean('Paths', key))
            path_vars[key] = var
            ttk.Checkbutton(paths_frame, text=label, variable=var).grid(row=i, column=0, sticky=tk.W, pady=2)
        
        # Custom paths
        ttk.Label(paths_frame, text="Custom paths (comma-separated):").grid(row=len(path_options), column=0, sticky=tk.W, pady=(10, 5))
        custom_paths_var = tk.StringVar(value=self.get('Paths', 'custom_scan_paths'))
        custom_paths_entry = ttk.Entry(paths_frame, textvariable=custom_paths_var, width=50)
        custom_paths_entry.grid(row=len(path_options)+1, column=0, sticky=tk.W, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(config_window)
        button_frame.pack(pady=10)
        
        def save_config():
            # Save settings
            self.set('Settings', 'large_file_threshold_mb', threshold_var.get())
            self.set('Settings', 'default_interface', interface_var.get())
            self.set('Settings', 'backup_before_delete', backup_var.get())
            self.set('Settings', 'scan_hidden_folders', hidden_var.get())
            
            # Save paths
            for key, var in path_vars.items():
                self.set('Paths', key, var.get())
            self.set('Paths', 'custom_scan_paths', custom_paths_var.get())
            
            self.save_config()
            messagebox.showinfo("Success", "Configuration saved successfully!")
            config_window.destroy()
        
        ttk.Button(button_frame, text="Save", command=save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=config_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def _show_config_cli(self):
        """CLI configuration editor"""
        print("\n=== Configuration Editor ===")
        print("1. Large file threshold (MB):", self.get('Settings', 'large_file_threshold_mb'))
        print("2. Default interface:", self.get('Settings', 'default_interface'))
        print("3. Backup before delete:", self.get('Settings', 'backup_before_delete'))
        print("4. Scan hidden folders:", self.get('Settings', 'scan_hidden_folders'))
        print("\nTo modify, edit the file:", self.config_file)

# Initialize global config
config = ConfigManager()

# === Simple Progress Bar Class ===
class ProgressBar:
    def __init__(self, total, width=50, desc="Progress"):
        self.total = total
        self.width = width
        self.desc = desc
        self.current = 0
        self.start_time = time.time()
    
    def update(self, count=1):
        self.current += count
        percent = (self.current / self.total) * 100 if self.total > 0 else 0
        filled = int(self.width * self.current / self.total) if self.total > 0 else 0
        bar = '█' * filled + '░' * (self.width - filled)
        
        elapsed = time.time() - self.start_time
        if self.current > 0:
            eta = (elapsed / self.current) * (self.total - self.current)
            eta_str = f"ETA: {int(eta)}s" if eta > 0 else "Done"
        else:
            eta_str = "ETA: --"
        
        print(f"\r{self.desc}: [{bar}] {percent:.1f}% ({self.current}/{self.total}) {eta_str}", end='', flush=True)
    
    def finish(self):
        self.update(0)  # Update display
        print()  # New line

# === Configuration ===
# Configuration is now handled by ConfigManager class above
# These are kept for backward compatibility but will be overridden
LARGE_FILE_SIZE_MB = config.getint('Settings', 'large_file_threshold_mb', 100)
CLEAN_TEMP = config.getboolean('Settings', 'clean_temp_by_default', True) 
CLEAN_RECYCLE_BIN = config.getboolean('Settings', 'clean_recycle_by_default', True)
SCAN_PATHS = config.get_scan_paths()

# === Check if running as admin ===
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# === Function to convert bytes to readable format ===
def get_size_readable(num):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024:
            return f"{num:.2f} {unit}"
        num /= 1024

# === Step 1: Find Large Files ===
def find_large_files(scan_paths, min_size_mb):
    large_files = []
    skipped_dirs = []
    seen_files = set()  # Track unique file paths to avoid duplicates
    
    # First pass: count total files for progress bar
    print("Counting files for progress tracking...")
    total_files = 0
    valid_paths = []
    
    for base_path in scan_paths:
        if not base_path or not os.path.exists(base_path):
            continue
        valid_paths.append(base_path)
        
        for root, dirs, files in os.walk(base_path):
            if any(x in root.lower() for x in ['appdata\\local\\microsoft\\windows', 'ntuser', '$recycle']):
                continue
            total_files += len(files)
    
    if total_files == 0:
        print("No files found to scan.")
        return large_files
    
    # Second pass: scan with progress bar
    print(f"Scanning {total_files:,} files for large files (>{min_size_mb}MB)...")
    progress = ProgressBar(total_files, desc="Scanning files")
    
    for base_path in valid_paths:
        for root, dirs, files in os.walk(base_path):
            # Skip system/hidden directories
            if any(x in root.lower() for x in ['appdata\\local\\microsoft\\windows', 'ntuser', '$recycle']):
                continue
                
            for name in files:
                progress.update(1)
                try:
                    filepath = os.path.join(root, name)
                    
                    # Skip if we've already seen this file
                    if filepath in seen_files:
                        continue
                    seen_files.add(filepath)
                    
                    size = os.path.getsize(filepath)
                    if size >= min_size_mb * 1024 * 1024:
                        large_files.append((filepath, size))
                except (OSError, PermissionError) as e:
                    if root not in skipped_dirs:
                        skipped_dirs.append(root)
                    continue
    
    progress.finish()
    
    if skipped_dirs:
        print(f"Note: Skipped {len(skipped_dirs)} directories due to access restrictions")
    
    return large_files

# === Step 1.5: Interactive File Deletion ===
def delete_large_files_interactive(large_files):
    if not large_files:
        return 0
    
    total_size = sum(size for _, size in large_files)
    print(f"\nFound {len(large_files)} large files totaling {get_size_readable(total_size)}")
    print("\nDeletion options:")
    print("  1. Review each file individually (y/n for each)")
    print("  2. Delete ALL large files at once")
    print("  3. Skip deletion")
    
    while True:
        choice = input("\nEnter your choice (1/2/3): ").strip()
        if choice in ['1', '2', '3']:
            break
        print("Please enter 1, 2, or 3")
    
    if choice == '3':
        print("Skipping file deletion.")
        return 0
    
    files_to_delete = []
    total_deleted_size = 0
    
    if choice == '1':
        # Individual file review
        print(f"\nReviewing {len(large_files)} files individually...")
        print("(y=delete, n=skip, q=quit deletion, a=delete all remaining)")
        
        for i, (filepath, size) in enumerate(large_files, 1):
            print(f"\n[{i}/{len(large_files)}] {get_size_readable(size)} - {filepath}")
            
            while True:
                response = input("Delete this file? (y/n/q/a): ").lower().strip()
                if response in ['y', 'n', 'q', 'a']:
                    break
                print("Please enter y, n, q, or a")
            
            if response == 'y':
                files_to_delete.append((filepath, size))
            elif response == 'q':
                print("Stopping file review.")
                break
            elif response == 'a':
                # Add current file and all remaining files
                files_to_delete.extend(large_files[i-1:])
                print(f"Marked all remaining {len(large_files) - i + 1} files for deletion.")
                break
            # 'n' just continues to next file
    
    elif choice == '2':
        # Delete all files
        confirmation = input(f"\nAre you SURE you want to delete ALL {len(large_files)} files ({get_size_readable(total_size)})? Type 'DELETE ALL' to confirm: ")
        if confirmation == "DELETE ALL":
            files_to_delete = large_files[:]
        else:
            print("Deletion cancelled - confirmation text didn't match.")
            return 0
    
    # Actually delete the files
    if files_to_delete:
        print(f"\nDeleting {len(files_to_delete)} files...")
        progress = ProgressBar(len(files_to_delete), desc="Deleting files")
        
        deleted_count = 0
        for filepath, size in files_to_delete:
            progress.update(1)
            try:
                os.remove(filepath)
                total_deleted_size += size
                deleted_count += 1
            except (OSError, PermissionError) as e:
                print(f"\nFailed to delete: {filepath} - {e}")
            except Exception as e:
                print(f"\nError deleting: {filepath} - {e}")
        
        progress.finish()
        print(f"Successfully deleted {deleted_count} files, freed {get_size_readable(total_deleted_size)}")
        
        if deleted_count < len(files_to_delete):
            print(f"Failed to delete {len(files_to_delete) - deleted_count} files (permission/access issues)")
    
    return total_deleted_size

# === Step 2: Clear Temp Files (User-accessible only) ===
def clear_temp_dirs():
    # Only clean user-accessible temp directories
    user_profile = os.environ.get("USERPROFILE", "")
    temp_dirs = [
        tempfile.gettempdir(),  # Usually user temp
        os.environ.get("TEMP", ""),
        os.environ.get("TMP", ""),
        os.path.join(user_profile, "AppData", "Local", "Temp"),
    ]
    
    # Remove duplicates and non-existent paths
    temp_dirs = list(set([d for d in temp_dirs if d and os.path.exists(d)]))
    
    if not temp_dirs:
        print("No accessible temp directories found.")
        return 0
    
    # Count total files first
    print("Counting temp files...")
    total_files = 0
    for temp_dir in temp_dirs:
        for root, dirs, files in os.walk(temp_dir):
            total_files += len(files)
    
    if total_files == 0:
        print("No temp files found.")
        return 0
    
    print(f"Cleaning {total_files:,} temp files...")
    progress = ProgressBar(total_files, desc="Cleaning temp files")
    
    total_freed = 0
    for temp_dir in temp_dirs:
        print(f"\nCleaning: {temp_dir}")
        dir_freed = 0
        
        for root, dirs, files in os.walk(temp_dir, topdown=False):
            for name in files:
                progress.update(1)
                try:
                    file_path = os.path.join(root, name)
                    file_size = os.path.getsize(file_path)
                    os.remove(file_path)
                    dir_freed += file_size
                except (OSError, PermissionError):
                    continue
                    
            for name in dirs:
                try:
                    shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                except (OSError, PermissionError):
                    continue
        
        if dir_freed > 0:
            print(f"\n  Freed from {temp_dir}: {get_size_readable(dir_freed)}")
            total_freed += dir_freed
    
    progress.finish()
    return total_freed

# === Step 3: Empty Recycle Bin ===
def empty_recycle_bin():
    print("\nChecking Recycle Bin...")
    try:
        # First try to check if recycle bin has items
        result = subprocess.run([
            "powershell.exe", "-Command", 
            "(Get-ChildItem -Path '$env:USERPROFILE\\$Recycle.Bin' -Force -Recurse -ErrorAction SilentlyContinue | Measure-Object).Count"
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip().isdigit():
            count = int(result.stdout.strip())
            
            if count == 0:
                print("Recycle Bin appears to be empty.")
                return 0
            else:
                print(f"Found items in Recycle Bin.")
                
                # Ask for confirmation
                response = input("Empty Recycle Bin? (y/N): ").lower()
                if response == 'y':
                    # Try the standard Clear-RecycleBin command first
                    try:
                        subprocess.run(["powershell.exe", "-Command", "Clear-RecycleBin -Force"], 
                                     check=True, capture_output=True)
                        print("Recycle Bin emptied.")
                        return 0
                    except subprocess.CalledProcessError:
                        # Fallback: try alternative method
                        try:
                            subprocess.run([
                                "powershell.exe", "-Command", 
                                "Get-ChildItem -Path '$env:USERPROFILE\\$Recycle.Bin' -Force -Recurse | Remove-Item -Recurse -Force"
                            ], check=True, capture_output=True)
                            print("Recycle Bin emptied (using alternative method).")
                            return 0
                        except subprocess.CalledProcessError as e:
                            print(f"Failed to empty Recycle Bin: {e}")
                            print("You can manually empty it from the desktop Recycle Bin icon.")
                            return 0
                else:
                    print("Recycle Bin not emptied.")
                    return 0
        else:
            # Can't check status, just ask if they want to try
            response = input("Unable to check Recycle Bin status. Try to empty it? (y/N): ").lower()
            if response == 'y':
                try:
                    subprocess.run(["powershell.exe", "-Command", "Clear-RecycleBin -Force"], 
                                 check=True, capture_output=True)
                    print("Recycle Bin empty command executed.")
                except subprocess.CalledProcessError:
                    print("Failed to empty Recycle Bin. Try emptying it manually.")
            return 0
            
    except Exception as e:
        print(f"Error accessing Recycle Bin: {e}")
        return 0

# === GUI Class ===
class CleanupGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("User Space Cleanup Assistant")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # Variables
        self.large_files = []
        self.total_freed = 0
        
        self.create_widgets()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="User Space Cleanup Assistant", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Status display
        self.status_label = ttk.Label(main_frame, text="Ready to scan...")
        self.status_label.grid(row=1, column=0, columnspan=3, pady=(0, 10))
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, length=400, mode='determinate')
        self.progress.grid(row=2, column=0, columnspan=3, pady=(0, 10), sticky=(tk.W, tk.E))
        
        # Text output area (mirrors terminal output)
        self.output_text = scrolledtext.ScrolledText(main_frame, height=20, width=80)
        self.output_text.grid(row=3, column=0, columnspan=3, pady=(0, 10), sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=4, column=0, columnspan=3, pady=(10, 0))
        
        # Buttons
        self.scan_btn = ttk.Button(buttons_frame, text="Start Scan", command=self.start_scan)
        self.scan_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.clean_temp_btn = ttk.Button(buttons_frame, text="Clean Temp Files", 
                                        command=self.clean_temp_files, state='disabled')
        self.clean_temp_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.empty_recycle_btn = ttk.Button(buttons_frame, text="Empty Recycle Bin", 
                                           command=self.empty_recycle_bin, state='disabled')
        self.empty_recycle_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.config_btn = ttk.Button(buttons_frame, text="Settings", command=self.show_config)
        self.config_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.exit_btn = ttk.Button(buttons_frame, text="Exit", command=self.root.quit)
        self.exit_btn.pack(side=tk.RIGHT)
        
    def log_output(self, message):
        """Add message to both GUI and terminal"""
        print(message)  # Print to terminal
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)
        self.root.update_idletasks()
        
    def update_status(self, status):
        """Update status label and log"""
        self.status_label.config(text=status)
        self.log_output(f"Status: {status}")
        
    def start_scan(self):
        """Start the file scanning process"""
        self.scan_btn.config(state='disabled')
        self.clean_temp_btn.config(state='disabled')
        self.empty_recycle_btn.config(state='disabled')
        
        # Clear previous output
        self.output_text.delete(1.0, tk.END)
        
        # Start scan in separate thread
        thread = threading.Thread(target=self.scan_files)
        thread.daemon = True
        thread.start()
        
    def scan_files(self):
        """Scan for large files (runs in separate thread)"""
        try:
            self.update_status("Scanning for large files...")
            
            # Show scan areas
            accessible_paths = [path for path in SCAN_PATHS if path and os.path.exists(path)]
            self.log_output("\nWill scan these areas:")
            for path in accessible_paths:
                self.log_output(f"  • {path}")
            
            # Find large files with progress updates
            self.large_files = self.find_large_files_gui(SCAN_PATHS, LARGE_FILE_SIZE_MB)
            
            if self.large_files:
                self.log_output(f"\nFound {len(self.large_files)} large files:")
                for path, size in sorted(self.large_files, key=lambda x: -x[1])[:50]:
                    self.log_output(f"  {get_size_readable(size):>10} - {path}")
                
                total_large = sum(size for _, size in self.large_files)
                self.log_output(f"\nTotal size of large files: {get_size_readable(total_large)}")
                
                # Create file selection window
                self.root.after(0, self.show_file_selection)
            else:
                self.log_output("No large files found.")
                self.root.after(0, self.enable_cleanup_buttons)
                
        except Exception as e:
            self.log_output(f"Error during scan: {e}")
            self.root.after(0, self.enable_scan_button)
    
    def find_large_files_gui(self, scan_paths, min_size_mb):
        """Find large files with GUI progress updates"""
        large_files = []
        skipped_dirs = []
        seen_files = set()
        
        # Count total files
        self.root.after(0, lambda: self.update_status("Counting files..."))
        total_files = 0
        valid_paths = []
        
        for base_path in scan_paths:
            if not base_path or not os.path.exists(base_path):
                continue
            valid_paths.append(base_path)
            
            for root, dirs, files in os.walk(base_path):
                if any(x in root.lower() for x in ['appdata\\local\\microsoft\\windows', 'ntuser', '$recycle']):
                    continue
                total_files += len(files)
        
        if total_files == 0:
            return large_files
        
        # Scan files with progress
        self.root.after(0, lambda: self.progress.config(maximum=total_files))
        current_file = 0
        
        for base_path in valid_paths:
            for root, dirs, files in os.walk(base_path):
                if any(x in root.lower() for x in ['appdata\\local\\microsoft\\windows', 'ntuser', '$recycle']):
                    continue
                    
                for name in files:
                    current_file += 1
                    if current_file % 100 == 0:  # Update progress every 100 files
                        progress_val = (current_file / total_files) * 100
                        self.root.after(0, lambda p=progress_val: self.progress.config(value=current_file))
                        self.root.after(0, lambda: self.update_status(f"Scanning... {current_file:,}/{total_files:,} files"))
                    
                    try:
                        filepath = os.path.join(root, name)
                        if filepath in seen_files:
                            continue
                        seen_files.add(filepath)
                        
                        size = os.path.getsize(filepath)
                        if size >= min_size_mb * 1024 * 1024:
                            large_files.append((filepath, size))
                    except (OSError, PermissionError):
                        if root not in skipped_dirs:
                            skipped_dirs.append(root)
                        continue
        
        self.root.after(0, lambda: self.progress.config(value=total_files))
        if skipped_dirs:
            self.log_output(f"Note: Skipped {len(skipped_dirs)} directories due to access restrictions")
        
        return large_files
    
    def show_file_selection(self):
        """Show window for selecting files to delete"""
        selection_window = tk.Toplevel(self.root)
        selection_window.title("Select Files to Delete")
        selection_window.geometry("800x600")
        
        # File list with checkboxes
        frame = ttk.Frame(selection_window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Instructions
        ttk.Label(frame, text="Select files to delete:", font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        # Scrollable frame for file list
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # File checkboxes
        self.file_vars = []
        for i, (filepath, size) in enumerate(sorted(self.large_files, key=lambda x: -x[1])):
            var = tk.BooleanVar()
            self.file_vars.append((var, filepath, size))
            
            file_frame = ttk.Frame(scrollable_frame)
            file_frame.pack(fill=tk.X, pady=2)
            
            cb = ttk.Checkbutton(file_frame, variable=var)
            cb.pack(side=tk.LEFT)
            
            size_label = ttk.Label(file_frame, text=f"{get_size_readable(size):>10}", font=('Courier', 9))
            size_label.pack(side=tk.LEFT, padx=(5, 10))
            
            path_label = ttk.Label(file_frame, text=filepath, font=('Arial', 9))
            path_label.pack(side=tk.LEFT)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=(10, 0))
        
        ttk.Button(button_frame, text="Select All", 
                  command=lambda: [var.set(True) for var, _, _ in self.file_vars]).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Select None", 
                  command=lambda: [var.set(False) for var, _, _ in self.file_vars]).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Delete Selected", 
                  command=lambda: self.delete_selected_files(selection_window)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", 
                  command=selection_window.destroy).pack(side=tk.RIGHT)
    
    def delete_selected_files(self, selection_window):
        """Delete the selected files"""
        selected_files = [(filepath, size) for var, filepath, size in self.file_vars if var.get()]
        
        if not selected_files:
            messagebox.showwarning("No Selection", "No files selected for deletion.")
            return
        
        total_size = sum(size for _, size in selected_files)
        result = messagebox.askyesno("Confirm Deletion", 
                                   f"Delete {len(selected_files)} files ({get_size_readable(total_size)})?")
        
        if result:
            selection_window.destroy()
            self.delete_files_with_progress(selected_files)
        
    def delete_files_with_progress(self, files_to_delete):
        """Delete files with progress feedback"""
        self.update_status("Deleting files...")
        self.progress.config(maximum=len(files_to_delete), value=0)
        
        deleted_count = 0
        deleted_size = 0
        
        for i, (filepath, size) in enumerate(files_to_delete):
            try:
                os.remove(filepath)
                deleted_count += 1
                deleted_size += size
                self.log_output(f"Deleted: {get_size_readable(size)} - {filepath}")
            except Exception as e:
                self.log_output(f"Failed to delete: {filepath} - {e}")
            
            self.progress.config(value=i + 1)
            self.root.update_idletasks()
        
        self.total_freed += deleted_size
        self.log_output(f"\nSuccessfully deleted {deleted_count} files, freed {get_size_readable(deleted_size)}")
        
        self.enable_cleanup_buttons()
    
    def clean_temp_files(self):
        """Clean temporary files"""
        self.clean_temp_btn.config(state='disabled')
        self.update_status("Cleaning temporary files...")
        
        # Run in separate thread
        thread = threading.Thread(target=self.clean_temp_thread)
        thread.daemon = True
        thread.start()
    
    def clean_temp_thread(self):
        """Clean temp files in separate thread"""
        try:
            freed = clear_temp_dirs()
            self.total_freed += freed
            self.log_output(f"Temp cleanup complete. Freed: {get_size_readable(freed)}")
            self.root.after(0, lambda: self.clean_temp_btn.config(state='normal'))
        except Exception as e:
            self.log_output(f"Error cleaning temp files: {e}")
            self.root.after(0, lambda: self.clean_temp_btn.config(state='normal'))
    
    def empty_recycle_bin(self):
        """Empty the recycle bin"""
        self.empty_recycle_btn.config(state='disabled')
        self.update_status("Emptying recycle bin...")
        
        # Run in separate thread
        thread = threading.Thread(target=self.empty_recycle_thread)
        thread.daemon = True
        thread.start()
    
    def empty_recycle_thread(self):
        """Empty recycle bin in separate thread"""
        try:
            empty_recycle_bin()
            self.log_output("Recycle bin operation complete.")
            self.root.after(0, lambda: self.empty_recycle_btn.config(state='normal'))
        except Exception as e:
            self.log_output(f"Error with recycle bin: {e}")
            self.root.after(0, lambda: self.empty_recycle_btn.config(state='normal'))
    
    def show_config(self):
        """Show the configuration editor GUI"""
        self.root.withdraw() # Hide main window
        config.show_config_editor()
        self.root.deiconify() # Show main window after config closes
    
    def enable_cleanup_buttons(self):
        """Enable cleanup buttons after scan"""
        self.clean_temp_btn.config(state='normal')
        self.empty_recycle_btn.config(state='normal')
        self.enable_scan_button()
        self.update_status(f"Scan complete. Total freed: {get_size_readable(self.total_freed)}")
    
    def enable_scan_button(self):
        """Re-enable scan button"""
        self.scan_btn.config(state='normal')
    
    def run(self):
        """Start the GUI"""
        self.root.mainloop()

# === Main ===
if __name__ == "__main__":
    print("\n--- User Space Cleanup Assistant ---\n")
    
    # Check if user wants to edit config first
    if len(sys.argv) > 1 and sys.argv[1] == "--config":
        config.show_config_editor()
        sys.exit()
    
    # Determine interface based on config
    default_interface = config.get('Settings', 'default_interface', 'ask')
    
    if default_interface == 'ask':
        # Ask for interface preference
        print("Choose interface:")
        print("1. Command Line Interface (CLI)")
        print("2. Graphical User Interface (GUI)")
        print("3. Edit Configuration")
        
        while True:
            choice = input("\nEnter your choice (1/2/3): ").strip()
            if choice in ['1', '2', '3']:
                break
            print("Please enter 1, 2, or 3")
    elif default_interface == 'gui':
        choice = '2'
        print("Starting GUI mode (configured as default)...")
    elif default_interface == 'cli':
        choice = '1'
        print("Starting CLI mode (configured as default)...")
    else:
        choice = '1'  # Fallback to CLI
    
    if choice == '3':
        config.show_config_editor()
        print("\nConfiguration updated. Please run the script again.")
        sys.exit()
    
    if choice == '2':
        print("Launching GUI mode...")
        print("Note: All operations will also be logged to this terminal window.\n")
        
        try:
            gui = CleanupGUI()
            gui.run()
        except Exception as e:
            print(f"Error launching GUI: {e}")
            print("Falling back to CLI mode...\n")
            choice = '1'
    
    if choice == '1':
        print("Running in CLI mode...\n")
        
        # Check admin privileges and inform user
        if not is_admin():
            print("Running in user mode (no admin privileges)")
            print("Scanning user-accessible folders only.\n")
        else:
            print("Running with admin privileges\n")

        # Show scan areas (now from config)
        accessible_paths = config.get_scan_paths()
        print("Will scan these areas:")
        for path in accessible_paths:
            print(f"  • {path}")
        print()

        # Initialize total freed counter
        total_freed = 0

        # 1. Find large files (using config threshold)
        large_file_threshold = config.getint('Settings', 'large_file_threshold_mb', 100)
        large_files = find_large_files(accessible_paths, large_file_threshold)
        
        if large_files:
            max_display = config.getint('Settings', 'max_files_to_display', 50)
            print(f"\nFound {len(large_files)} large files:")
            for path, size in sorted(large_files, key=lambda x: -x[1])[:max_display]:
                print(f"  {get_size_readable(size):>10} - {path}")
            
            if len(large_files) > max_display:
                print(f"  ... and {len(large_files) - max_display} more files")
            
            # Show total size of large files
            total_large = sum(size for _, size in large_files)
            print(f"\nTotal size of large files: {get_size_readable(total_large)}")
            
            # Ask if user wants to delete files
            delete_response = input("\nWould you like to delete some of these large files? (y/N): ").lower()
            if delete_response == 'y':
                deleted_size = delete_large_files_interactive(large_files)
                total_freed += deleted_size
            else:
                print("Skipping file deletion.")
            
            # Suggest common large file cleanup
            print("\nCommon large files to consider removing:")
            print("  • Old downloads in Downloads folder")
            print("  • Video files (check Videos/Movies folders)")
            print("  • Old installers (.msi, .exe files)")
            print("  • Backup files (.bak, .old)")
            print("  • Virtual machine files (.vmdk, .vdi)")
        else:
            print("No large files found.")

        print("\n" + "="*50)
        
        # 2. Clear temp directories (using config default)
        clean_temp_default = config.getboolean('Settings', 'clean_temp_by_default', True)
        if clean_temp_default:
            response = input("Clean user temporary files? (Y/n): ").lower()
            if response != 'n':
                freed = clear_temp_dirs()
                total_freed += freed
                print(f"User temp cleanup complete. Freed: {get_size_readable(freed)}")

        # 3. Empty Recycle Bin (using config default)
        clean_recycle_default = config.getboolean('Settings', 'clean_recycle_by_default', True)
        if clean_recycle_default:
            freed = empty_recycle_bin()
            total_freed += freed

        # Additional suggestions for non-admin users
        if not is_admin():
            print(f"\nAdditional cleanup suggestions (manual):")
            print("  • Clear browser cache (Chrome: Settings > Privacy > Clear browsing data)")
            print("  • Clean up browser downloads")
            print("  • Remove old Windows.old folders (if any in user space)")
            print("  • Clean %LOCALAPPDATA%\\Microsoft\\Windows\\Explorer\\thumbcache_*.db")
            print("  • Use Disk Cleanup tool (cleanmgr.exe) for system files")

        print(f"\nTotal space freed: {get_size_readable(total_freed)}")
        print("Cleanup complete.")
        print(f"\nTip: Run 'python {sys.argv[0]} --config' to customize settings\n")
