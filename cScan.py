import os
import shutil
import tempfile
import sys
import subprocess
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import configparser
from pathlib import Path
import hashlib
import mimetypes
import json
from datetime import datetime, timedelta
import psutil
import errno
import platform
from collections import defaultdict

# Platform detection
IS_WINDOWS = platform.system() == 'Windows'
IS_MAC = platform.system() == 'Darwin'
IS_LINUX = platform.system() == 'Linux'

# Platform-specific imports
if IS_WINDOWS:
    import ctypes
    import winreg

# Initialize configuration globally
config = None

# === File Safety and Analysis ===
class FileAnalyzer:
    """Analyze files for safety and categorization"""
    
    def __init__(self):
        self.critical_paths = self._get_critical_paths()
        self.running_processes = self._get_running_processes()
        self.file_categories = {
            'system': ['.dll', '.sys', '.ocx', '.lib'],
            'media': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.mp3', '.wav', '.flac', '.m4a', '.aac'],
            'documents': ['.pdf', '.doc', '.docx', '.txt', '.xlsx', '.ppt', '.pptx', '.odt'],
            'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg'],
            'archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'],
            'temp': ['.tmp', '.temp', '.cache', '.log', '.etl'],
            'backups': ['.bak', '.old', '.backup', '.~'],
            'installers': ['.msi', '.dmg', '.pkg', '.deb', '.rpm'],
            'virtual': ['.vhd', '.vhdx', '.vmdk', '.vdi', '.qcow2'],
            'models': ['.bin', '.gguf', '.model', '.safetensors', '.weights'],
            'crashdumps': ['.dmp', '.mdmp', '.hdmp'],
            'cache_patterns': ['cache', 'Cache', 'temp', 'Temp', 'tmp']
        }
        
    def _get_critical_paths(self):
        """Get paths that should never be deleted"""
        critical = set()
        
        if IS_WINDOWS:
            # Windows system paths
            windows_dir = os.environ.get('WINDIR', 'C:\\Windows')
            program_files = os.environ.get('PROGRAMFILES', 'C:\\Program Files')
            program_files_x86 = os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)')
            
            critical.update([
                windows_dir.lower(),
                program_files.lower(),
                program_files_x86.lower(),
                os.path.join(windows_dir, 'System32').lower(),
                os.path.join(windows_dir, 'SysWOW64').lower(),
            ])
            
            # Only protect critical Microsoft directories
            critical.add(os.path.join(program_files, 'Microsoft').lower())
            critical.add(os.path.join(program_files_x86, 'Microsoft').lower())
            
            system_dirs = {windows_dir.lower(), program_files.lower(), program_files_x86.lower()}
            
        elif IS_MAC:
            # macOS system paths
            critical.update([
                '/system',
                '/library',
                '/applications',
                '/usr/bin',
                '/usr/sbin',
                '/usr/lib',
                '/usr/share',
                '/bin',
                '/sbin',
                '/private/var',
                '/private/etc',
            ])
            
            system_dirs = {'/system', '/library', '/applications', '/usr', '/bin', '/sbin'}
            
        elif IS_LINUX:
            # Linux system paths
            critical.update([
                '/bin',
                '/sbin',
                '/usr/bin',
                '/usr/sbin',
                '/usr/lib',
                '/usr/share',
                '/lib',
                '/lib64',
                '/etc',
                '/boot',
                '/opt',
            ])
            
            system_dirs = {'/bin', '/sbin', '/usr', '/lib', '/etc', '/opt'}
        
        # Protect running process directories in system locations
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                if proc.info['exe']:
                    exe_dir = os.path.dirname(proc.info['exe']).lower()
                    # Only add if it's in a system directory
                    if any(exe_dir.startswith(sys_dir.lower()) for sys_dir in system_dirs):
                        critical.add(exe_dir)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        return critical
        
    def _get_running_processes(self):
        """Get list of currently running process names"""
        processes = set()
        for proc in psutil.process_iter(['name']):
            try:
                processes.add(proc.info['name'].lower())
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return processes
        
    def categorize_file(self, filepath):
        """Categorize a file based on its path and extension"""
        path_lower = filepath.lower()
        ext = os.path.splitext(filepath)[1].lower()
        filename = os.path.basename(filepath).lower()
        
        # Check for specific path patterns first
        if any(pattern in path_lower for pattern in self.file_categories['cache_patterns']):
            return 'cache'
            
        # Platform-specific path patterns
        if IS_WINDOWS:
            if '\\temp\\' in path_lower or '\\tmp\\' in path_lower:
                return 'temp'
            elif 'recycle' in path_lower:
                return 'recycle'
            elif 'download' in path_lower:
                return 'downloads'
        else:
            # macOS/Linux
            if '/temp/' in path_lower or '/tmp/' in path_lower or '/.tmp' in path_lower:
                return 'temp'
            elif 'trash' in path_lower or '.trash' in path_lower:
                return 'recycle'
            elif 'download' in path_lower:
                return 'downloads'
                
        if 'backup' in path_lower:
            return 'backups'
        elif 'crashdump' in path_lower or 'crash dump' in path_lower:
            return 'crashdumps'
            
        # Special handling for executables
        if ext == '.exe':
            # Check if it's an installer by name patterns
            installer_patterns = ['setup', 'install', 'update', 'patch']
            if any(pattern in filename for pattern in installer_patterns):
                return 'installers'
            # Check if it's in a known app directory
            elif any(app in path_lower for app in ['ollama', 'cursor', 'chrome', 'firefox', 'microsoft']):
                return 'system'
            else:
                return 'executables'
                
        # Check by file extension
        for category, extensions in self.file_categories.items():
            if category != 'cache_patterns' and ext in extensions:
                return category
                
        # Additional categorization for files without clear extensions
        if 'model' in filename or 'weights' in filename:
            return 'models'
        elif any(ext in filename for ext in ['.dll', '.so', '.dylib']):
            return 'system'
            
        return 'other'
        
    def assess_safety(self, filepath):
        """Assess the safety of deleting a file"""
        path_lower = filepath.lower()
        filename = os.path.basename(filepath).lower()
        
        # Critical - check if file is actually INSIDE a critical directory
        for critical_path in self.critical_paths:
            if path_lower.startswith(critical_path):
                return 'critical'
                
        # Check if file is currently in use
        if self._is_file_in_use(filepath):
            return 'in_use'
            
        # System files
        if any(sys_ext in filename for sys_ext in ['.dll', '.sys', '.ocx']):
            return 'system'
            
        # Running executables
        if filename.endswith('.exe') and filename.replace('.exe', '') in self.running_processes:
            return 'running'
            
        # Safe to delete - platform-specific patterns
        if IS_WINDOWS:
            safe_patterns = [
                '\\temp\\', '\\tmp\\', '\\cache\\', '\\caches\\',
                '\\temporary internet files\\', '\\thumbnails\\',
                'crashdumps', 'crash reports', '\\logs\\'
            ]
            safe_locations = [
                'pip\\cache', 'npm-cache', 'nuget\\packages',
                'crashdumps', 'server-cache', 'dxcache',
                'shader_cache', 'gputemp', 'fontcache'
            ]
            user_patterns = ['\\downloads\\', '\\documents\\', '\\desktop\\', '\\videos\\', '\\music\\']
        else:
            # macOS/Linux patterns
            safe_patterns = [
                '/temp/', '/tmp/', '/cache/', '/caches/',
                '/.cache/', '/thumbnails/', '/logs/',
                'crashdumps', 'crash reports'
            ]
            safe_locations = [
                'pip/cache', 'npm-cache', '.npm/', '.cache/',
                'crashdumps', 'server-cache', 'Cache/',
                'shader_cache', 'gputemp', 'fontcache',
                '.Trash/', 'Trash/'
            ]
            user_patterns = ['/downloads/', '/documents/', '/desktop/', '/movies/', '/music/', '/pictures/']
            
        if any(pattern in path_lower for pattern in safe_patterns):
            return 'safe'
            
        if any(location in path_lower for location in safe_locations):
            return 'safe'
            
        # User files (generally safe but need confirmation)
        if any(user_pattern in path_lower for user_pattern in user_patterns):
            return 'user'
            
        # Game/app data that might be safe to delete
        if any(pattern in path_lower for pattern in ['fivem', 'minecraft', 'steam']):
            return 'user'
            
        return 'unknown'
        
    def _is_file_in_use(self, filepath):
        """Check if file is currently in use"""
        if not os.path.exists(filepath):
            return False  # Can't be in use if it doesn't exist
            
        try:
            # Try to open the file with write access
            with open(filepath, 'r+b') as f:
                # If we can open it, it's not locked
                return False
        except (OSError, IOError) as e:
            # On Windows, errno 13 = permission denied, 32 = sharing violation
            if hasattr(e, 'errno') and e.errno in (errno.EACCES, errno.EBUSY, 32):
                return True
            # For other errors, assume file is accessible
            return False
            
    def get_file_info(self, filepath):
        """Get comprehensive file information"""
        try:
            stat = os.stat(filepath)
            return {
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'created': datetime.fromtimestamp(stat.st_ctime),
                'accessed': datetime.fromtimestamp(stat.st_atime),
                'category': self.categorize_file(filepath),
                'safety': self.assess_safety(filepath),
                'mime_type': mimetypes.guess_type(filepath)[0] or 'unknown'
            }
        except (OSError, PermissionError):
            return None

class SafeDeleteManager:
    """Manage safe file deletion with backups and recovery"""
    
    def __init__(self, config):
        self.config = config
        self.backup_dir = os.path.join(tempfile.gettempdir(), 'cScan_backups')
        self.deleted_files_log = os.path.join(self.backup_dir, 'deleted_files.json')
        self.ensure_backup_dir()
        
    def ensure_backup_dir(self):
        """Ensure backup directory exists"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            
    def safe_delete(self, filepath, file_info):
        """Safely delete a file with backup option"""
        if not os.path.exists(filepath):
            return False, "File not found"
            
        # Check if we're in dry run mode
        if self.config.getboolean('Settings', 'dry_run_mode', False):
            return True, f"[DRY RUN] Would delete: {filepath}"
            
        # Check safety level
        if file_info['safety'] in ['critical', 'system', 'running', 'in_use']:
            # Check if user wants to override safety
            if self.config.getboolean('Settings', 'override_safety', False):
                print(f"WARNING: Overriding safety for {file_info['safety']} file: {os.path.basename(filepath)}")
            else:
                return False, f"File is {file_info['safety']} - deletion blocked for safety"
            
        # Create backup if enabled
        if self.config.getboolean('Settings', 'backup_before_delete', False):
            backup_path = self._create_backup(filepath)
            if not backup_path:
                return False, "Failed to create backup"
                
        try:
            # Move to recycle bin instead of permanent deletion
            if self.config.getboolean('Settings', 'use_recycle_bin', True):
                self._move_to_recycle_bin(filepath)
            else:
                os.remove(filepath)
                
            # Log deletion
            self._log_deletion(filepath, file_info)
            return True, "File deleted successfully"
            
        except Exception as e:
            return False, f"Error deleting file: {str(e)}"
            
    def _create_backup(self, filepath):
        """Create a backup of the file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{os.path.basename(filepath)}_{timestamp}"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            shutil.copy2(filepath, backup_path)
            return backup_path
        except Exception:
            return None
            
    def _move_to_recycle_bin(self, filepath):
        """Move file to recycle bin/trash"""
        try:
            if IS_WINDOWS:
                # Windows: Use PowerShell to move to recycle bin
                subprocess.run([
                    "powershell.exe", "-Command",
                    f"Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile('{filepath}', 'OnlyErrorDialogs', 'SendToRecycleBin')"
                ], check=True, capture_output=True)
            elif IS_MAC:
                # macOS: Use osascript to move to trash
                subprocess.run([
                    "osascript", "-e",
                    f'tell application "Finder" to move POSIX file "{filepath}" to trash'
                ], check=True, capture_output=True)
            else:
                # Linux: Try to use gio trash if available
                try:
                    subprocess.run(["gio", "trash", filepath], check=True, capture_output=True)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # Fallback: move to user's trash directory
                    trash_dir = os.path.expanduser("~/.local/share/Trash/files")
                    if os.path.exists(trash_dir):
                        trash_name = os.path.basename(filepath)
                        # Add timestamp if file exists in trash
                        if os.path.exists(os.path.join(trash_dir, trash_name)):
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            trash_name = f"{trash_name}_{timestamp}"
                        shutil.move(filepath, os.path.join(trash_dir, trash_name))
                    else:
                        # Last resort: permanent deletion
                        os.remove(filepath)
        except (subprocess.CalledProcessError, Exception):
            # Fallback to permanent deletion
            os.remove(filepath)
            
    def _log_deletion(self, filepath, file_info):
        """Log deleted file information"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'filepath': filepath,
                'size': file_info['size'],
                'category': file_info['category'],
                'safety': file_info['safety']
            }
            
            # Load existing log
            if os.path.exists(self.deleted_files_log):
                with open(self.deleted_files_log, 'r') as f:
                    log_data = json.load(f)
            else:
                log_data = {'deletions': []}
                
            log_data['deletions'].append(log_entry)
            
            # Save updated log
            with open(self.deleted_files_log, 'w') as f:
                json.dump(log_data, f, indent=2)
                
        except Exception:
            pass  # Don't fail deletion if logging fails

class SmartFileScanner:
    """Enhanced file scanner with categorization and smart suggestions"""
    
    def __init__(self, config):
        self.config = config
        self.analyzer = FileAnalyzer()
        self.file_cache = {}
        
    def scan_files(self, scan_paths, min_size_mb=100, callback=None):
        """Scan files with enhanced analysis"""
        large_files = []
        file_data = defaultdict(list)
        total_files = 0
        
        # Count files first
        if callback:
            callback("Counting files...")
            
        for path in scan_paths:
            for root, _, files in os.walk(path):
                total_files += len(files)
                
        processed = 0
        min_size_bytes = min_size_mb * 1024 * 1024
        
        for path in scan_paths:
            for root, _, files in os.walk(path):
                for file in files:
                    if callback:
                        callback(f"Scanning files: {(processed/total_files)*100:.1f}%")
                    
                    filepath = os.path.join(root, file)
                    processed += 1
                    
                    try:
                        file_size = os.path.getsize(filepath)
                        if file_size >= min_size_bytes:
                            file_info = self.analyzer.get_file_info(filepath)
                            if file_info:
                                file_info['path'] = filepath
                                large_files.append(file_info)
                                file_data[file_info['category']].append(file_info)
                    except (OSError, PermissionError):
                        continue
                        
        return large_files, file_data
        
    def get_smart_suggestions(self, file_data):
        """Generate smart cleanup suggestions"""
        suggestions = []
        
        # Cache files (highest priority - usually safe)
        if 'cache' in file_data:
            cache_files = [f for f in file_data['cache'] if f['safety'] in ['safe', 'unknown']]
            if cache_files:
                total_size = sum(f['size'] for f in cache_files)
                suggestions.append({
                    'category': 'cache',
                    'description': 'Cache files (can be regenerated)',
                    'files': cache_files,
                    'total_size': total_size,
                    'safety': 'safe'
                })
                
        # Temp files
        if 'temp' in file_data:
            temp_files = [f for f in file_data['temp'] if f['safety'] in ['safe', 'unknown']]
            if temp_files:
                # Split into old and recent
                old_temp = [f for f in temp_files if f['modified'] < datetime.now() - timedelta(days=7)]
                recent_temp = [f for f in temp_files if f['modified'] >= datetime.now() - timedelta(days=7)]
                
                if old_temp:
                    total_size = sum(f['size'] for f in old_temp)
                    suggestions.append({
                        'category': 'temp',
                        'description': 'Old temporary files (7+ days old)',
                        'files': old_temp,
                        'total_size': total_size,
                        'safety': 'safe'
                    })
                    
                if recent_temp and sum(f['size'] for f in recent_temp) > 100 * 1024 * 1024:  # >100MB
                    total_size = sum(f['size'] for f in recent_temp)
                    suggestions.append({
                        'category': 'temp',
                        'description': 'Recent temporary files (< 7 days)',
                        'files': recent_temp,
                        'total_size': total_size,
                        'safety': 'user'
                    })
                    
        # Crash dumps
        if 'crashdumps' in file_data:
            crash_files = file_data['crashdumps']
            if crash_files:
                total_size = sum(f['size'] for f in crash_files)
                suggestions.append({
                    'category': 'crashdumps',
                    'description': 'Crash dump files (debug information)',
                    'files': crash_files,
                    'total_size': total_size,
                    'safety': 'safe'
                })
                
        # Old installers
        if 'installers' in file_data:
            old_installers = [f for f in file_data['installers'] 
                            if f['modified'] < datetime.now() - timedelta(days=30)]
            if old_installers:
                total_size = sum(f['size'] for f in old_installers)
                suggestions.append({
                    'category': 'installers',
                    'description': 'Old installer files (30+ days old)',
                    'files': old_installers,
                    'total_size': total_size,
                    'safety': 'user'
                })
                
        # Old backup files
        if 'backups' in file_data:
            old_backups = [f for f in file_data['backups'] 
                          if f['modified'] < datetime.now() - timedelta(days=30)]
            if old_backups:
                total_size = sum(f['size'] for f in old_backups)
                suggestions.append({
                    'category': 'backups',
                    'description': 'Old backup files (30+ days old)',
                    'files': old_backups,
                    'total_size': total_size,
                    'safety': 'user'
                })
                
        # Large media files
        if 'media' in file_data:
            large_media = [f for f in file_data['media'] 
                          if f['size'] > 1024 * 1024 * 1024]  # >1GB
            if large_media:
                total_size = sum(f['size'] for f in large_media)
                suggestions.append({
                    'category': 'media',
                    'description': 'Large media files (>1GB each)',
                    'files': large_media,
                    'total_size': total_size,
                    'safety': 'user'
                })
                
        # Large downloads
        if 'downloads' in file_data:
            large_downloads = [f for f in file_data['downloads'] 
                              if f['size'] > 500 * 1024 * 1024]  # 500MB+
            if large_downloads:
                total_size = sum(f['size'] for f in large_downloads)
                suggestions.append({
                    'category': 'downloads',
                    'description': 'Large files in Downloads folder',
                    'files': large_downloads,
                    'total_size': total_size,
                    'safety': 'user'
                })
                
        # Sort suggestions by safety (safe first) and then by size
        suggestions.sort(key=lambda x: (0 if x['safety'] == 'safe' else 1, -x['total_size']))
        
        return suggestions

def delete_large_files_interactive_enhanced(large_files, file_data):
    """Enhanced interactive file deletion with safety checks"""
    if not large_files:
        return 0
        
    config = ConfigManager()
    safe_delete = SafeDeleteManager(config)
    
    print(f"\n{'='*60}")
    print("SMART FILE ANALYSIS RESULTS")
    print(f"{'='*60}")
    
    # Show categorized summary
    print("\nFile Categories Found:")
    for category, files in file_data.items():
        if files:
            total_size = sum(f['size'] for f in files)
            print(f"  {category.title():12} {len(files):3} files  {get_size_readable(total_size):>10}")
    
    # Show safety analysis
    safety_counts = defaultdict(int)
    for file_info in large_files:
        safety_counts[file_info['safety']] += 1
        
    print(f"\nSafety Analysis:")
    for safety, count in safety_counts.items():
        color = {'safe': '✓', 'user': '?', 'unknown': '!', 'critical': '✗'}.get(safety, '?')
        print(f"  {color} {safety.title():12} {count:3} files")
    
    # Get smart suggestions
    scanner = SmartFileScanner(config)
    suggestions = scanner.get_smart_suggestions(file_data)
    
    if suggestions:
        print(f"\n{'='*60}")
        print("SMART CLEANUP SUGGESTIONS")
        print(f"{'='*60}")
        
        for i, suggestion in enumerate(suggestions, 1):
            print(f"\n{i}. {suggestion['description']}")
            print(f"   Files: {len(suggestion['files'])} | Size: {get_size_readable(suggestion['total_size'])}")
            print(f"   Safety: {suggestion['safety']}")
            
        print(f"\nCleanup Options:")
        print("1. Review smart suggestions")
        print("2. Manual file review (original method)")
        print("3. View all files by category")
        print("4. Skip deletion")
        
        while True:
            choice = input("\nEnter your choice (1/2/3/4): ").strip()
            if choice in ['1', '2', '3', '4']:
                break
            print("Please enter 1, 2, 3, or 4")
            
        if choice == '1':
            return _handle_smart_suggestions(suggestions, safe_delete)
        elif choice == '2':
            return _handle_manual_review(large_files, safe_delete)
        elif choice == '3':
            return _handle_category_view(file_data, safe_delete)
        else:
            print("Deletion cancelled.")
            return 0
    else:
        print("\nNo smart suggestions available. Falling back to manual review.")
        return _handle_manual_review(large_files, safe_delete)

def _handle_smart_suggestions(suggestions, safe_delete):
    """Handle smart suggestion-based cleanup"""
    total_deleted = 0
    
    for i, suggestion in enumerate(suggestions, 1):
        print(f"\n{'-'*50}")
        print(f"Suggestion {i}: {suggestion['description']}")
        print(f"Files: {len(suggestion['files'])} | Size: {get_size_readable(suggestion['total_size'])}")
        print(f"Safety Level: {suggestion['safety']}")
        
        if suggestion['safety'] == 'safe':
            default = 'Y'
            prompt = f"Delete these files? (Y/n): "
        else:
            default = 'N'
            prompt = f"Delete these files? (y/N): "
            
        response = input(prompt).strip().lower()
        
        if (response == 'y') or (response == '' and default == 'Y'):
            print(f"Deleting {len(suggestion['files'])} files...")
            
            for file_info in suggestion['files']:
                success, message = safe_delete.safe_delete(file_info['path'], file_info)
                if success:
                    total_deleted += file_info['size']
                else:
                    print(f"Failed: {os.path.basename(file_info['path'])} - {message}")
                    
            print(f"✓ Deleted {len(suggestion['files'])} files")
        else:
            print("Skipped.")
            
    return total_deleted

def _handle_manual_review(large_files, safe_delete):
    """Handle manual file-by-file review"""
    print(f"\nManual Review Mode")
    print("Commands: y=delete, n=skip, i=info, q=quit, a=delete all remaining")
    
    total_deleted = 0
    
    for i, file_info in enumerate(large_files, 1):
        print(f"\n[{i}/{len(large_files)}] {get_size_readable(file_info['size'])} - {file_info['path']}")
        print(f"Category: {file_info['category']} | Safety: {file_info['safety']}")
        
        while True:
            response = input("Action? (y/n/i/q/a): ").lower().strip()
            if response in ['y', 'n', 'i', 'q', 'a']:
                break
            print("Please enter y, n, i, q, or a")
            
        if response == 'i':
            _show_file_info(file_info)
            continue
        elif response == 'y':
            success, message = safe_delete.safe_delete(file_info['path'], file_info)
            if success:
                total_deleted += file_info['size']
                print("✓ Deleted")
            else:
                print(f"✗ Failed: {message}")
        elif response == 'q':
            break
        elif response == 'a':
            # Delete all remaining files
            for remaining_file in large_files[i-1:]:
                success, message = safe_delete.safe_delete(remaining_file['path'], remaining_file)
                if success:
                    total_deleted += remaining_file['size']
            print(f"✓ Deleted all remaining files")
            break
            
    return total_deleted

def _handle_category_view(file_data, safe_delete):
    """Handle category-based file viewing and deletion"""
    print(f"\nCategory View")
    
    categories = list(file_data.keys())
    for i, category in enumerate(categories, 1):
        files = file_data[category]
        total_size = sum(f['size'] for f in files)
        print(f"{i}. {category.title()} - {len(files)} files ({get_size_readable(total_size)})")
        
    while True:
        choice = input(f"\nSelect category (1-{len(categories)}) or 'q' to quit: ").strip()
        if choice == 'q':
            return 0
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(categories):
                category = categories[idx]
                return _review_category_files(file_data[category], safe_delete)
        except ValueError:
            pass
        print("Invalid choice")

def _review_category_files(files, safe_delete):
    """Review files in a specific category"""
    print(f"\nReviewing {len(files)} files:")
    
    for i, file_info in enumerate(files, 1):
        print(f"{i:3}. {get_size_readable(file_info['size']):>10} - {os.path.basename(file_info['path'])}")
        
    response = input(f"\nDelete all files in this category? (y/N): ").lower().strip()
    if response == 'y':
        total_deleted = 0
        for file_info in files:
            success, message = safe_delete.safe_delete(file_info['path'], file_info)
            if success:
                total_deleted += file_info['size']
        return total_deleted
    else:
        return 0

def _show_file_info(file_info):
    """Show detailed file information"""
    print(f"\n{'-'*40}")
    print(f"File: {os.path.basename(file_info['path'])}")
    print(f"Path: {file_info['path']}")
    print(f"Size: {get_size_readable(file_info['size'])}")
    print(f"Category: {file_info['category']}")
    print(f"Safety: {file_info['safety']}")
    print(f"Modified: {file_info['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"MIME Type: {file_info['mime_type']}")
    print(f"{'-'*40}")

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
                'scan_hidden_folders': 'false',
                'use_recycle_bin': 'true',
                'show_safety_warnings': 'true',
                'dry_run_mode': 'false',
                'override_safety': 'false'
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
        
        if IS_WINDOWS:
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
        else:
            # macOS/Linux
            home = os.path.expanduser("~")
            
            if self.getboolean('Paths', 'include_user_profile'):
                paths.append(home)
            
            if self.getboolean('Paths', 'include_downloads'):
                paths.append(os.path.join(home, "Downloads"))
            
            if self.getboolean('Paths', 'include_documents'):
                paths.append(os.path.join(home, "Documents"))
            
            if self.getboolean('Paths', 'include_desktop'):
                paths.append(os.path.join(home, "Desktop"))
            
            if self.getboolean('Paths', 'include_pictures'):
                if IS_MAC:
                    paths.append(os.path.join(home, "Pictures"))
                else:
                    paths.append(os.path.join(home, "Pictures"))
            
            if self.getboolean('Paths', 'include_videos'):
                if IS_MAC:
                    paths.append(os.path.join(home, "Movies"))
                else:
                    paths.append(os.path.join(home, "Videos"))
            
            if self.getboolean('Paths', 'include_music'):
                paths.append(os.path.join(home, "Music"))
            
            if self.getboolean('Paths', 'include_temp_folders'):
                temp_paths = [
                    "/tmp",
                    "/var/tmp",
                    os.path.join(home, ".cache"),
                ]
                if IS_MAC:
                    temp_paths.extend([
                        os.path.join(home, "Library", "Caches"),
                        os.environ.get("TMPDIR", "/tmp"),
                    ])
                paths.extend(temp_paths)
        
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
        
        # New settings for safety
        use_recycle_bin_var = tk.BooleanVar(value=self.getboolean('Settings', 'use_recycle_bin'))
        ttk.Checkbutton(settings_frame, text="Use Windows Recycle Bin for deletion", 
                       variable=use_recycle_bin_var).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
        
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
            self.set('Settings', 'use_recycle_bin', use_recycle_bin_var.get())
            
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
        print("5. Use Recycle Bin for deletion:", self.getboolean('Settings', 'use_recycle_bin'))
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
    """Check if running with admin/root privileges"""
    if IS_WINDOWS:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    else:
        # macOS/Linux - check if running as root
        return os.geteuid() == 0

# === Function to convert bytes to readable format ===
def get_size_readable(num):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024:
            return f"{num:.2f} {unit}"
        num /= 1024

# === Step 1: Find Large Files ===
def find_large_files(scan_paths, min_size_mb):
    """Find files larger than specified size in MB - Enhanced version"""
    config = ConfigManager()
    scanner = SmartFileScanner(config)
    
    print(f"Scanning for large files (>{min_size_mb}MB) with enhanced analysis...")
    
    # Use the enhanced scanner
    large_files_info, file_data = scanner.scan_files(scan_paths, min_size_mb)
    
    if large_files_info:
        # Convert to original format for compatibility
        large_files = [(info['path'], info['size']) for info in large_files_info]
        
        print(f"\nFound {len(large_files)} large files:")
        for info in sorted(large_files_info, key=lambda x: -x['size'])[:10]:
            safety_icon = {'safe': '✓', 'user': '?', 'unknown': '!', 'critical': '✗'}.get(info['safety'], '?')
            print(f"  {get_size_readable(info['size']):>10} {safety_icon} [{info['category']}] - {info['path']}")
        
        if len(large_files) > 10:
            print(f"  ... and {len(large_files) - 10} more files")
            
        return large_files
    else:
        print("No large files found.")
        return []

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
    """Clean user-accessible temp directories on all platforms"""
    temp_dirs = []
    
    if IS_WINDOWS:
        user_profile = os.environ.get("USERPROFILE", "")
        temp_dirs = [
            tempfile.gettempdir(),  # Usually user temp
            os.environ.get("TEMP", ""),
            os.environ.get("TMP", ""),
            os.path.join(user_profile, "AppData", "Local", "Temp"),
        ]
    else:
        # macOS/Linux
        home = os.path.expanduser("~")
        temp_dirs = [
            tempfile.gettempdir(),
            "/tmp",
            "/var/tmp",
            os.path.join(home, ".cache"),
        ]
        if IS_MAC:
            # Add macOS-specific cache directories
            temp_dirs.extend([
                os.path.join(home, "Library", "Caches"),
                os.environ.get("TMPDIR", "/tmp"),
            ])
    
    # Remove duplicates and non-existent paths
    temp_dirs = list(set([d for d in temp_dirs if d and os.path.exists(d)]))
    
    if not temp_dirs:
        print("No accessible temp directories found.")
        return 0
    
    # Count total files first
    print("Counting temp files...")
    total_files = 0
    for temp_dir in temp_dirs:
        try:
            for root, dirs, files in os.walk(temp_dir):
                # Skip system directories on macOS/Linux
                if not IS_WINDOWS and ('/private/var' in root or '/System' in root):
                    continue
                total_files += len(files)
        except (OSError, PermissionError):
            continue
    
    if total_files == 0:
        print("No temp files found.")
        return 0
    
    print(f"Cleaning {total_files:,} temp files...")
    progress = ProgressBar(total_files, desc="Cleaning temp files")
    
    total_freed = 0
    for temp_dir in temp_dirs:
        print(f"\nCleaning: {temp_dir}")
        dir_freed = 0
        
        try:
            for root, dirs, files in os.walk(temp_dir, topdown=False):
                # Skip system directories on macOS/Linux
                if not IS_WINDOWS and ('/private/var' in root or '/System' in root):
                    continue
                    
                for name in files:
                    progress.update(1)
                    try:
                        file_path = os.path.join(root, name)
                        # Skip files that might be in use
                        if not IS_WINDOWS:
                            # On Unix systems, check if we own the file
                            stat = os.stat(file_path)
                            if stat.st_uid != os.getuid():
                                continue
                        
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        dir_freed += file_size
                    except (OSError, PermissionError):
                        continue
                        
                for name in dirs:
                    try:
                        dir_path = os.path.join(root, name)
                        # Only remove directories we own
                        if not IS_WINDOWS:
                            stat = os.stat(dir_path)
                            if stat.st_uid != os.getuid():
                                continue
                        shutil.rmtree(dir_path, ignore_errors=True)
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            continue
        
        if dir_freed > 0:
            print(f"\n  Freed from {temp_dir}: {get_size_readable(dir_freed)}")
            total_freed += dir_freed
    
    progress.finish()
    return total_freed

# === Step 3: Empty Recycle Bin/Trash ===
def empty_recycle_bin():
    """Empty Recycle Bin/Trash on all platforms"""
    if IS_WINDOWS:
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
            
    elif IS_MAC:
        print("\nChecking Trash...")
        try:
            # Check trash size
            home = os.path.expanduser("~")
            trash_path = os.path.join(home, ".Trash")
            
            if os.path.exists(trash_path):
                # Count items in trash
                items = os.listdir(trash_path)
                if not items:
                    print("Trash appears to be empty.")
                    return 0
                    
                # Calculate size
                total_size = 0
                for item in items:
                    item_path = os.path.join(trash_path, item)
                    try:
                        if os.path.isfile(item_path):
                            total_size += os.path.getsize(item_path)
                        elif os.path.isdir(item_path):
                            for root, dirs, files in os.walk(item_path):
                                for f in files:
                                    total_size += os.path.getsize(os.path.join(root, f))
                    except (OSError, PermissionError):
                        continue
                        
                print(f"Found {len(items)} items in Trash ({get_size_readable(total_size)})")
                
                response = input("Empty Trash? (y/N): ").lower()
                if response == 'y':
                    try:
                        # Use osascript to empty trash
                        subprocess.run([
                            "osascript", "-e",
                            'tell application "Finder" to empty trash'
                        ], check=True, capture_output=True)
                        print("Trash emptied.")
                        return total_size
                    except subprocess.CalledProcessError:
                        # Fallback: manual deletion
                        try:
                            shutil.rmtree(trash_path)
                            os.makedirs(trash_path)  # Recreate empty trash
                            print("Trash emptied (manual method).")
                            return total_size
                        except Exception as e:
                            print(f"Failed to empty Trash: {e}")
                            return 0
                else:
                    print("Trash not emptied.")
                    return 0
            else:
                print("Trash folder not found.")
                return 0
                
        except Exception as e:
            print(f"Error accessing Trash: {e}")
            return 0
            
    else:
        # Linux
        print("\nChecking Trash...")
        try:
            home = os.path.expanduser("~")
            trash_dirs = [
                os.path.join(home, ".local/share/Trash/files"),
                os.path.join(home, ".local/share/Trash/info"),
            ]
            
            total_size = 0
            total_items = 0
            
            for trash_dir in trash_dirs:
                if os.path.exists(trash_dir):
                    items = os.listdir(trash_dir)
                    total_items += len(items)
                    
                    for item in items:
                        item_path = os.path.join(trash_dir, item)
                        try:
                            if os.path.isfile(item_path):
                                total_size += os.path.getsize(item_path)
                        except (OSError, PermissionError):
                            continue
                            
            if total_items == 0:
                print("Trash appears to be empty.")
                return 0
                
            print(f"Found {total_items} items in Trash")
            
            response = input("Empty Trash? (y/N): ").lower()
            if response == 'y':
                try:
                    # Try using gio trash --empty
                    subprocess.run(["gio", "trash", "--empty"], check=True, capture_output=True)
                    print("Trash emptied.")
                    return total_size
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # Fallback: manual deletion
                    for trash_dir in trash_dirs:
                        if os.path.exists(trash_dir):
                            shutil.rmtree(trash_dir, ignore_errors=True)
                            os.makedirs(trash_dir)
                    print("Trash emptied (manual method).")
                    return total_size
            else:
                print("Trash not emptied.")
                return 0
                
        except Exception as e:
            print(f"Error accessing Trash: {e}")
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
        
        # Platform-specific button text
        trash_button_text = "Empty Recycle Bin" if IS_WINDOWS else "Empty Trash"
        self.empty_recycle_btn = ttk.Button(buttons_frame, text=trash_button_text, 
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
            
            # Get configuration
            global config
            if not config:
                config = ConfigManager()
            
            # Get scan paths from config
            scan_paths = config.get_scan_paths()
            large_file_size_mb = config.getint('Settings', 'large_file_threshold_mb', 100)
            
            # Show scan areas
            accessible_paths = [path for path in scan_paths if path and os.path.exists(path)]
            self.log_output("\nWill scan these areas:")
            for path in accessible_paths:
                self.log_output(f"  • {path}")
            
            # Find large files with progress updates
            self.large_files = self.find_large_files_gui(scan_paths, large_file_size_mb)
            
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
    # Initialize configuration
    config = ConfigManager()
    
    # Display header with platform info
    platform_name = "Windows" if IS_WINDOWS else "macOS" if IS_MAC else "Linux"
    print(f"\n--- User Space Cleanup Assistant ({platform_name}) ---\n")
    
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
        
        # Use enhanced scanner
        scanner = SmartFileScanner(config)
        large_files_info, file_data = scanner.scan_files(accessible_paths, large_file_threshold)
        
        if large_files_info:
            # Convert to original format for compatibility
            large_files = [(info['path'], info['size']) for info in large_files_info]
            
            max_display = config.getint('Settings', 'max_files_to_display', 50)
            print(f"\nFound {len(large_files)} large files:")
            for info in sorted(large_files_info, key=lambda x: -x['size'])[:max_display]:
                safety_icon = {'safe': '✓', 'user': '?', 'unknown': '!', 'critical': '✗'}.get(info['safety'], '?')
                print(f"  {get_size_readable(info['size']):>10} {safety_icon} [{info['category']}] - {info['path']}")
            
            if len(large_files) > max_display:
                print(f"  ... and {len(large_files) - max_display} more files")
            
            # Show total size of large files
            total_large = sum(size for _, size in large_files)
            print(f"\nTotal size of large files: {get_size_readable(total_large)}")
            
            # Ask if user wants to delete files
            delete_response = input("\nWould you like to delete some of these large files? (y/N): ").lower()
            if delete_response == 'y':
                # Use the enhanced interactive deletion function
                total_deleted_size = delete_large_files_interactive_enhanced(large_files_info, file_data)
                total_freed += total_deleted_size
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
            
            if IS_WINDOWS:
                print("  • Remove old Windows.old folders (if any in user space)")
                print("  • Clean %LOCALAPPDATA%\\Microsoft\\Windows\\Explorer\\thumbcache_*.db")
                print("  • Use Disk Cleanup tool (cleanmgr.exe) for system files")
            elif IS_MAC:
                print("  • Clear ~/Library/Caches/ subdirectories")
                print("  • Remove old iOS device backups (~/Library/Application Support/MobileSync/Backup/)")
                print("  • Clean Xcode derived data (~/Library/Developer/Xcode/DerivedData/)")
                print("  • Use Storage Management (Apple Menu > About This Mac > Storage > Manage)")
            else:
                print("  • Clear ~/.cache/ subdirectories")
                print("  • Remove old package manager caches (apt, yum, dnf)")
                print("  • Clean ~/.local/share/Trash/ manually")
                print("  • Use system cleanup tools (bleachbit, etc.)")

        print(f"\nTotal space freed: {get_size_readable(total_freed)}")
        print("Cleanup complete.")
        print(f"\nTip: Run 'python {sys.argv[0]} --config' to customize settings\n")
