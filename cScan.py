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
            'dev_temp': ['.pdb', '.obj', '.ilk', '.pch', '.suo', '.user'],  # Safe dev temp files
            'packages': ['.nupkg', '.vsix', '.tgz', '.whl', '.gem'],         # Package files
            'thumbnails': ['.db'],  # Thumbnail cache files
            'cache_patterns': ['cache', 'Cache', 'temp', 'Temp', 'tmp', '_cacache', 'node_modules', 'thumbcache']
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
            
        # Enhanced development file detection
        if 'node_modules' in path_lower:
            return 'dev_dependencies'
        elif any(pattern in path_lower for pattern in ['\\bin\\debug', '\\bin\\release', '\\obj\\']):
            return 'build_output'
        elif '_cacache' in path_lower or 'pip/cache' in path_lower or 'nuget/v3-cache' in path_lower:
            return 'dev_cache'
            
        # Thumbnail cache files
        if 'thumbcache' in filename or ('iconcache' in filename and ext == '.db'):
            return 'thumbnails'
            
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
                'include_dev_caches': 'false',  # Conservative default
                'include_browser_caches': 'false',  # Conservative default
                'include_app_caches': 'false',  # Conservative default
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
            
            # Safe development cache directories (disabled by default for safety)
            if self.getboolean('Paths', 'include_dev_caches', False):
                dev_cache_paths = [
                    os.path.join(user_profile, ".npm", "_cacache"),      # NPM cache only
                    os.path.join(user_profile, "AppData", "Local", "pip", "cache"),  # Python pip cache
                    os.path.join(user_profile, "AppData", "Local", "NuGet", "v3-cache"),  # NuGet cache
                    os.path.join(user_profile, ".gradle", "caches"),    # Gradle cache
                ]
                # Only add paths that exist
                paths.extend([p for p in dev_cache_paths if os.path.exists(p)])
            
            # Browser cache directories (disabled by default for safety)
            if self.getboolean('Paths', 'include_browser_caches', False):
                browser_cache_paths = [
                    # Chrome caches (cache only, not user data)
                    os.path.join(user_profile, "AppData", "Local", "Google", "Chrome", "User Data", "Default", "Cache"),
                    os.path.join(user_profile, "AppData", "Local", "Google", "Chrome", "User Data", "Default", "Code Cache"),
                    
                    # Firefox cache
                    os.path.join(user_profile, "AppData", "Local", "Mozilla", "Firefox", "Profiles", "*", "cache2"),
                    
                    # Edge cache
                    os.path.join(user_profile, "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "Cache"),
                    os.path.join(user_profile, "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "Code Cache"),
                ]
                # Handle wildcard paths for Firefox
                import glob
                expanded_paths = []
                for path in browser_cache_paths:
                    if '*' in path:
                        expanded_paths.extend(glob.glob(path))
                    elif os.path.exists(path):
                        expanded_paths.append(path)
                paths.extend(expanded_paths)
            
            # Application cache directories (disabled by default for safety)  
            if self.getboolean('Paths', 'include_app_caches', False):
                app_cache_paths = [
                    # Microsoft Teams cache
                    os.path.join(user_profile, "AppData", "Roaming", "Microsoft", "Teams", "Cache"),
                    os.path.join(user_profile, "AppData", "Roaming", "Microsoft", "Teams", "blob_storage"),
                    
                    # Discord cache
                    os.path.join(user_profile, "AppData", "Roaming", "discord", "Cache"),
                    os.path.join(user_profile, "AppData", "Roaming", "discord", "Code Cache"),
                    
                    # Slack cache
                    os.path.join(user_profile, "AppData", "Roaming", "Slack", "Cache"),
                    os.path.join(user_profile, "AppData", "Roaming", "Slack", "Code Cache"),
                    
                    # Spotify cache
                    os.path.join(user_profile, "AppData", "Local", "Spotify", "Data"),
                ]
                # Only add paths that exist
                paths.extend([p for p in app_cache_paths if os.path.exists(p)])
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
            
            # Safe development cache directories (disabled by default for safety)
            if self.getboolean('Paths', 'include_dev_caches', False):
                dev_cache_paths = [
                    os.path.join(home, ".npm", "_cacache"),      # NPM cache
                    os.path.join(home, ".cache", "pip"),         # Python pip cache
                    os.path.join(home, ".gradle", "caches"),     # Gradle cache
                ]
                if IS_MAC:
                    dev_cache_paths.extend([
                        os.path.join(home, "Library", "Caches", "pip"),  # macOS pip cache
                        os.path.join(home, "Library", "Caches", "Homebrew"),  # Homebrew cache
                    ])
                # Only add paths that exist
                paths.extend([p for p in dev_cache_paths if os.path.exists(p)])
            
            # Browser cache directories (disabled by default for safety)
            if self.getboolean('Paths', 'include_browser_caches', False):
                browser_cache_paths = []
                if IS_MAC:
                    browser_cache_paths = [
                        # Chrome cache
                        os.path.join(home, "Library", "Caches", "Google", "Chrome", "Default"),
                        # Firefox cache
                        os.path.join(home, "Library", "Caches", "Firefox", "Profiles", "*", "cache2"),
                        # Safari cache
                        os.path.join(home, "Library", "Caches", "com.apple.Safari"),
                    ]
                else:  # Linux
                    browser_cache_paths = [
                        # Chrome cache
                        os.path.join(home, ".cache", "google-chrome", "Default"),
                        # Firefox cache
                        os.path.join(home, ".cache", "mozilla", "firefox", "*", "cache2"),
                    ]
                
                # Handle wildcard paths and existing paths
                import glob
                expanded_paths = []
                for path in browser_cache_paths:
                    if '*' in path:
                        expanded_paths.extend(glob.glob(path))
                    elif os.path.exists(path):
                        expanded_paths.append(path)
                paths.extend(expanded_paths)
            
            # Application cache directories (disabled by default for safety)
            if self.getboolean('Paths', 'include_app_caches', False):
                app_cache_paths = []
                if IS_MAC:
                    app_cache_paths = [
                        # Teams cache
                        os.path.join(home, "Library", "Caches", "com.microsoft.teams2"),
                        # Discord cache  
                        os.path.join(home, "Library", "Caches", "com.hnc.Discord"),
                        # Slack cache
                        os.path.join(home, "Library", "Caches", "com.tinyspeck.slackmacgap"),
                        # Spotify cache
                        os.path.join(home, "Library", "Caches", "com.spotify.client"),
                    ]
                else:  # Linux
                    app_cache_paths = [
                        # Discord cache
                        os.path.join(home, ".config", "discord", "Cache"),
                        # Slack cache
                        os.path.join(home, ".config", "Slack", "Cache"),
                    ]
                # Only add paths that exist
                paths.extend([p for p in app_cache_paths if os.path.exists(p)])
        
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
            ('include_temp_folders', 'Temp Folders'),
            ('include_dev_caches', 'Development Caches (NPM, pip, etc.)'),
            ('include_browser_caches', 'Browser Caches (Chrome, Firefox, Edge)'),
            ('include_app_caches', 'Application Caches (Teams, Discord, Slack)')
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
        self.root.title("cScan - Storage Cleanup Assistant")
        self.root.geometry("1000x750")
        self.root.resizable(True, True)
        self.root.configure(bg='#f0f0f0')
        
        # Modern color scheme
        self.colors = {
            'primary': '#2196F3',      # Blue
            'primary_dark': '#1976D2', # Darker blue
            'success': '#4CAF50',      # Green
            'warning': '#FF9800',      # Orange
            'danger': '#F44336',       # Red
            'background': '#f0f0f0',   # Light gray
            'surface': '#ffffff',      # White
            'text': '#212121',         # Dark gray
            'text_secondary': '#757575' # Medium gray
        }
        
        # Configure modern style
        self.setup_styles()
        
        # Variables
        self.large_files = []
        self.total_freed = 0
        
        self.create_widgets()
    
    def setup_styles(self):
        """Configure modern ttk styles"""
        style = ttk.Style()
        
        # Configure modern button style
        style.configure('Modern.TButton',
                       font=('Segoe UI', 10),
                       padding=(15, 8))
        
        # Primary button style
        style.configure('Primary.TButton',
                       font=('Segoe UI', 10, 'bold'),
                       padding=(15, 10))
        
        # Large button style  
        style.configure('Large.TButton',
                       font=('Segoe UI', 11),
                       padding=(20, 12))
        
        # Modern label styles
        style.configure('Title.TLabel',
                       font=('Segoe UI', 18, 'bold'),
                       foreground=self.colors['text'])
        
        style.configure('Subtitle.TLabel',
                       font=('Segoe UI', 12),
                       foreground=self.colors['text_secondary'])
        
        style.configure('Status.TLabel',
                       font=('Segoe UI', 10),
                       foreground=self.colors['primary'])
        
        # Modern frame style
        style.configure('Card.TFrame',
                       relief='solid',
                       borderwidth=1)
        
        # Modern progressbar
        style.configure('Modern.Horizontal.TProgressbar',
                       troughcolor='#e0e0e0',
                       borderwidth=0,
                       lightcolor=self.colors['primary'],
                       darkcolor=self.colors['primary'])
        
    def create_widgets(self):
        # Main container with modern styling
        main_frame = ttk.Frame(self.root, style='Card.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Header section
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Modern title with icon
        title_frame = ttk.Frame(header_frame)
        title_frame.pack(fill=tk.X)
        
        title_label = ttk.Label(title_frame, text="🧹 cScan", style='Title.TLabel')
        title_label.pack(side=tk.LEFT)
        
        subtitle_label = ttk.Label(title_frame, text="Storage Cleanup Assistant", style='Subtitle.TLabel')
        subtitle_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Stats display (modern card-like display)
        stats_frame = ttk.LabelFrame(main_frame, text="Storage Analysis", padding=10)
        stats_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Status and progress section
        status_frame = ttk.Frame(stats_frame)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text="Ready to scan...", style='Status.TLabel')
        self.status_label.pack(side=tk.LEFT)
        
        # Modern progress bar
        self.progress = ttk.Progressbar(stats_frame, style='Modern.Horizontal.TProgressbar', 
                                      length=500, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(10, 0))
        
        # Output section with improved styling
        output_frame = ttk.LabelFrame(main_frame, text="Scan Results", padding=10)
        output_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Enhanced text output with modern styling
        self.output_text = scrolledtext.ScrolledText(
            output_frame, 
            height=18, 
            font=('Consolas', 9),
            wrap=tk.WORD,
            bg=self.colors['surface'],
            fg=self.colors['text'],
            selectbackground=self.colors['primary'],
            selectforeground='white',
            relief='flat',
            borderwidth=0
        )
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        # Modern button section
        action_frame = ttk.LabelFrame(main_frame, text="Actions", padding=15)
        action_frame.pack(fill=tk.X)
        
        # Primary actions row
        primary_row = ttk.Frame(action_frame)
        primary_row.pack(fill=tk.X, pady=(0, 10))
        
        self.scan_btn = ttk.Button(primary_row, text="🔍 Start Scan", 
                                  style='Primary.TButton', command=self.start_scan)
        self.scan_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        # Cleanup actions row
        cleanup_row = ttk.Frame(action_frame)
        cleanup_row.pack(fill=tk.X, pady=(0, 10))
        
        self.clean_temp_btn = ttk.Button(cleanup_row, text="🗑️ Clean Temp Files", 
                                        style='Modern.TButton',
                                        command=self.clean_temp_files, state='disabled')
        self.clean_temp_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Platform-specific button text with icons
        if IS_WINDOWS:
            trash_text = "♻️ Empty Recycle Bin"
        else:
            trash_text = "🗑️ Empty Trash"
            
        self.empty_recycle_btn = ttk.Button(cleanup_row, text=trash_text,
                                           style='Modern.TButton',
                                           command=self.empty_recycle_bin, state='disabled')
        self.empty_recycle_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Secondary actions row
        secondary_row = ttk.Frame(action_frame)
        secondary_row.pack(fill=tk.X)
        
        self.config_btn = ttk.Button(secondary_row, text="⚙️ Settings", 
                                    style='Modern.TButton', command=self.show_config)
        self.config_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Exit button on the right
        self.exit_btn = ttk.Button(secondary_row, text="❌ Exit", 
                                  style='Modern.TButton', command=self.root.quit)
        self.exit_btn.pack(side=tk.RIGHT)
        
    def log_output(self, message, level="info"):
        """Add message to both GUI and terminal with color coding"""
        print(message)  # Print to terminal
        
        # Configure text tags for different message types
        if not hasattr(self, '_tags_configured'):
            self.output_text.tag_configure("info", foreground=self.colors['text'])
            self.output_text.tag_configure("success", foreground=self.colors['success'], font=('Consolas', 9, 'bold'))
            self.output_text.tag_configure("warning", foreground=self.colors['warning'], font=('Consolas', 9, 'bold'))
            self.output_text.tag_configure("error", foreground=self.colors['danger'], font=('Consolas', 9, 'bold'))
            self.output_text.tag_configure("header", foreground=self.colors['primary'], font=('Consolas', 10, 'bold'))
            self._tags_configured = True
        
        # Add timestamp for better tracking
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        # Insert with appropriate styling
        self.output_text.insert(tk.END, formatted_message, level)
        self.output_text.see(tk.END)
        self.root.update_idletasks()
        
    def update_status(self, status):
        """Update status label with modern styling"""
        self.status_label.config(text=f"📊 {status}")
        self.log_output(f"Status: {status}", "info")
        
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
            self.log_output("\n📂 Scanning these locations:", "header")
            for path in accessible_paths:
                self.log_output(f"  📁 {path}")
            
            # Find large files with progress updates
            self.large_files = self.find_large_files_gui(scan_paths, large_file_size_mb)
            
            if self.large_files:
                self.log_output(f"\n🎯 Found {len(self.large_files)} large files:", "header")
                for path, size in sorted(self.large_files, key=lambda x: -x[1])[:50]:
                    self.log_output(f"  {get_size_readable(size):>10} - {path}")
                
                total_large = sum(size for _, size in self.large_files)
                self.log_output(f"\n📏 Total size of large files: {get_size_readable(total_large)}", "success")
                
                # Create file selection window
                self.root.after(0, self.show_file_selection)
            else:
                self.log_output("✅ No large files found.", "success")
                self.root.after(0, self.enable_cleanup_buttons)
                
        except Exception as e:
            self.log_output(f"❌ Error during scan: {e}", "error")
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
        """Show enhanced file selection window with safety features"""
        selection_window = tk.Toplevel(self.root)
        selection_window.title("🗂️ File Cleanup Manager")
        selection_window.geometry("1200x800")
        selection_window.configure(bg=self.colors['background'])
        
        # Main container
        main_container = ttk.Frame(selection_window)
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Header with safety notice
        header_frame = ttk.LabelFrame(main_container, text="⚠️ Safety First", padding=10)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        safety_text = tk.Text(header_frame, height=3, bg=self.colors['surface'], 
                             font=('Segoe UI', 9), wrap=tk.WORD, relief='flat')
        safety_text.pack(fill=tk.X)
        safety_text.insert(tk.END, 
            "🛡️ Files are safely moved to Recycle Bin/Trash by default\n"
            "🔍 Click any file to see details and preview\n"
            "📁 Use filters to focus on specific file types or locations")
        safety_text.configure(state='disabled')
        
        # Create paned window for side-by-side layout
        paned = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Left panel - File list
        left_panel = ttk.Frame(paned)
        paned.add(left_panel, weight=2)
        
        # File list header with controls
        list_header = ttk.Frame(left_panel)
        list_header.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(list_header, text="📋 Files Found:", style='Subtitle.TLabel').pack(side=tk.LEFT)
        
        # Filters frame
        filters_frame = ttk.Frame(list_header)
        filters_frame.pack(side=tk.RIGHT)
        
        ttk.Label(filters_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.filter_var = tk.StringVar(value="All")
        filter_combo = ttk.Combobox(filters_frame, textvariable=self.filter_var, 
                                   values=["All", "Safe to Delete", "User Files", "Large (>1GB)", "Recent (<7 days)"],
                                   state="readonly", width=15)
        filter_combo.pack(side=tk.LEFT)
        filter_combo.bind('<<ComboboxSelected>>', self.apply_file_filter)
        
        # File list with enhanced display
        list_container = ttk.Frame(left_panel)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview for better file display
        columns = ('Select', 'Size', 'Type', 'Safety', 'Name', 'Location')
        self.file_tree = ttk.Treeview(list_container, columns=columns, show='headings', height=20)
        
        # Configure columns
        self.file_tree.heading('Select', text='☐')
        self.file_tree.heading('Size', text='Size')
        self.file_tree.heading('Type', text='Type') 
        self.file_tree.heading('Safety', text='Safety')
        self.file_tree.heading('Name', text='Filename')
        self.file_tree.heading('Location', text='Location')
        
        self.file_tree.column('Select', width=50, anchor='center')
        self.file_tree.column('Size', width=80, anchor='e')
        self.file_tree.column('Type', width=80)
        self.file_tree.column('Safety', width=80)
        self.file_tree.column('Name', width=200)
        self.file_tree.column('Location', width=300)
        
        # Scrollbars for treeview
        v_scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.file_tree.yview)
        h_scrollbar = ttk.Scrollbar(list_container, orient="horizontal", command=self.file_tree.xview)
        self.file_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.file_tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        list_container.grid_rowconfigure(0, weight=1)
        list_container.grid_columnconfigure(0, weight=1)
        
        # Bind events for file selection and details
        self.file_tree.bind('<ButtonRelease-1>', self.on_file_click)
        self.file_tree.bind('<Double-1>', self.show_file_details)
        
        # Right panel - File details and actions
        right_panel = ttk.Frame(paned)
        paned.add(right_panel, weight=1)
        
        # File details section
        details_frame = ttk.LabelFrame(right_panel, text="📄 File Details", padding=10)
        details_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.details_text = tk.Text(details_frame, height=15, width=40, 
                                   bg=self.colors['surface'], font=('Segoe UI', 9),
                                   wrap=tk.WORD, relief='flat')
        self.details_text.pack(fill=tk.BOTH, expand=True)
        
        # Selection summary
        summary_frame = ttk.LabelFrame(right_panel, text="📊 Selection Summary", padding=10)
        summary_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.summary_text = tk.Text(summary_frame, height=4, bg=self.colors['surface'], 
                                   font=('Segoe UI', 9), wrap=tk.WORD, relief='flat')
        self.summary_text.pack(fill=tk.X)
        
        # Populate the file tree
        self.populate_file_tree()
        
        # Action buttons at bottom
        action_frame = ttk.LabelFrame(main_container, text="🎯 Actions", padding=10)
        action_frame.pack(fill=tk.X)
        
        # Selection controls row
        selection_row = ttk.Frame(action_frame)
        selection_row.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(selection_row, text="☑️ Select All Safe", 
                  command=self.select_safe_files, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(selection_row, text="☐ Clear All", 
                  command=self.clear_all_selections, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(selection_row, text="🔍 Select by Type", 
                  command=self.show_type_selector, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 10))
        
        # Main action row
        main_action_row = ttk.Frame(action_frame)
        main_action_row.pack(fill=tk.X)
        
        ttk.Button(main_action_row, text="♻️ Move to Recycle Bin", 
                  command=lambda: self.handle_file_deletion(selection_window, 'recycle'),
                  style='Primary.TButton').pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Button(main_action_row, text="💾 Backup & Delete", 
                  command=lambda: self.handle_file_deletion(selection_window, 'backup'),
                  style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(main_action_row, text="📂 Open Location", 
                  command=self.open_file_location, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(main_action_row, text="❌ Cancel", 
                  command=selection_window.destroy, style='Modern.TButton').pack(side=tk.RIGHT)
        
        # Update summary initially
        self.update_selection_summary()
    
    def populate_file_tree(self):
        """Populate the file tree with enhanced file information"""
        # Clear existing items
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        # Initialize file data with safety analysis
        self.file_data = []
        from cScan import FileAnalyzer
        analyzer = FileAnalyzer()
        
        for filepath, size in self.large_files:
            file_info = analyzer.get_file_info(filepath)
            if file_info:
                # Add to our data structure
                file_entry = {
                    'path': filepath,
                    'size': size,
                    'name': os.path.basename(filepath),
                    'location': os.path.dirname(filepath),
                    'category': file_info['category'],
                    'safety': file_info['safety'],
                    'modified': file_info['modified'],
                    'selected': False,
                    'safety_icon': {'safe': '✅', 'user': '⚠️', 'unknown': '❓', 'critical': '❌'}.get(file_info['safety'], '❓')
                }
                self.file_data.append(file_entry)
        
        # Sort by size (largest first)
        self.file_data.sort(key=lambda x: -x['size'])
        
        # Populate tree
        self.refresh_file_tree()
    
    def refresh_file_tree(self):
        """Refresh the file tree display based on current filter"""
        # Clear tree
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        # Apply current filter
        filtered_files = self.apply_filter(self.file_data)
        
        # Add filtered files to tree
        for i, file_entry in enumerate(filtered_files):
            select_icon = "☑️" if file_entry['selected'] else "☐"
            
            values = (
                select_icon,
                get_size_readable(file_entry['size']),
                file_entry['category'].title(),
                f"{file_entry['safety_icon']} {file_entry['safety'].title()}",
                file_entry['name'],
                file_entry['location']
            )
            
            # Insert with tags for styling
            item = self.file_tree.insert('', tk.END, values=values, tags=(file_entry['safety'],))
            
        # Configure tags for safety coloring
        self.file_tree.tag_configure('safe', foreground=self.colors['success'])
        self.file_tree.tag_configure('user', foreground=self.colors['warning'])
        self.file_tree.tag_configure('unknown', foreground=self.colors['text'])
        self.file_tree.tag_configure('critical', foreground=self.colors['danger'])
    
    def apply_filter(self, files):
        """Apply the current filter to file list"""
        filter_value = self.filter_var.get()
        
        if filter_value == "All":
            return files
        elif filter_value == "Safe to Delete":
            return [f for f in files if f['safety'] in ['safe', 'cache', 'temp']]
        elif filter_value == "User Files":
            return [f for f in files if f['safety'] == 'user']
        elif filter_value == "Large (>1GB)":
            return [f for f in files if f['size'] > 1024*1024*1024]
        elif filter_value == "Recent (<7 days)":
            from datetime import datetime, timedelta
            week_ago = datetime.now() - timedelta(days=7)
            return [f for f in files if f['modified'] > week_ago]
        
        return files
    
    def apply_file_filter(self, event=None):
        """Apply filter when selection changes"""
        self.refresh_file_tree()
        self.update_selection_summary()
    
    def on_file_click(self, event):
        """Handle file click for selection toggle and details display"""
        item = self.file_tree.selection()[0] if self.file_tree.selection() else None
        if not item:
            return
        
        # Get the row index
        row_index = self.file_tree.index(item)
        filtered_files = self.apply_filter(self.file_data)
        
        if row_index < len(filtered_files):
            file_entry = filtered_files[row_index]
            
            # Check if click was on the select column
            region = self.file_tree.identify_region(event.x, event.y)
            if region == "cell":
                column = self.file_tree.identify_column(event.x, event.y)
                if column == '#1':  # Select column
                    # Toggle selection
                    original_file = next(f for f in self.file_data if f['path'] == file_entry['path'])
                    original_file['selected'] = not original_file['selected']
                    self.refresh_file_tree()
                    self.update_selection_summary()
                    return
            
            # Show file details
            self.show_file_info(file_entry)
    
    def show_file_info(self, file_entry):
        """Display detailed file information"""
        self.details_text.configure(state='normal')
        self.details_text.delete(1.0, tk.END)
        
        # Format file details
        details = f"""📄 {file_entry['name']}

📁 Location:
{file_entry['location']}

📏 Size: {get_size_readable(file_entry['size'])}

🏷️ Category: {file_entry['category'].title()}

🛡️ Safety Level: {file_entry['safety_icon']} {file_entry['safety'].title()}

📅 Last Modified: {file_entry['modified'].strftime('%Y-%m-%d %H:%M:%S')}

💡 Safety Notes:"""
        
        if file_entry['safety'] == 'safe':
            details += "\n✅ This file is safe to delete. It's likely cache or temporary data that can be regenerated."
        elif file_entry['safety'] == 'user':
            details += "\n⚠️ This is a user file. Review carefully before deletion."
        elif file_entry['safety'] == 'unknown':
            details += "\n❓ Safety level unknown. Proceed with caution."
        elif file_entry['safety'] == 'critical':
            details += "\n❌ This file may be critical to system operation. Deletion not recommended."
        
        self.details_text.insert(tk.END, details)
        self.details_text.configure(state='disabled')
    
    def update_selection_summary(self):
        """Update the selection summary display"""
        selected_files = [f for f in self.file_data if f['selected']]
        total_size = sum(f['size'] for f in selected_files)
        
        # Count by safety level
        safety_counts = {}
        for f in selected_files:
            safety_counts[f['safety']] = safety_counts.get(f['safety'], 0) + 1
        
        self.summary_text.configure(state='normal')
        self.summary_text.delete(1.0, tk.END)
        
        summary = f"""📊 Selection Summary

📋 Files Selected: {len(selected_files)}
💾 Total Size: {get_size_readable(total_size)}

🛡️ Safety Breakdown:"""
        
        for safety, count in safety_counts.items():
            icon = {'safe': '✅', 'user': '⚠️', 'unknown': '❓', 'critical': '❌'}.get(safety, '❓')
            summary += f"\n{icon} {safety.title()}: {count} files"
        
        self.summary_text.insert(tk.END, summary)
        self.summary_text.configure(state='disabled')
    
    def select_safe_files(self):
        """Select all files that are safe to delete"""
        for file_entry in self.file_data:
            if file_entry['safety'] in ['safe', 'cache', 'temp']:
                file_entry['selected'] = True
        self.refresh_file_tree()
        self.update_selection_summary()
    
    def clear_all_selections(self):
        """Clear all file selections"""
        for file_entry in self.file_data:
            file_entry['selected'] = False
        self.refresh_file_tree()
        self.update_selection_summary()
    
    def show_type_selector(self):
        """Show dialog to select files by type/category"""
        type_window = tk.Toplevel(self.root)
        type_window.title("🔍 Select by Type")
        type_window.geometry("400x300")
        type_window.configure(bg=self.colors['background'])
        
        frame = ttk.Frame(type_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Select file categories to include:", style='Subtitle.TLabel').pack(pady=(0, 15))
        
        # Get unique categories
        categories = set(f['category'] for f in self.file_data)
        self.category_vars = {}
        
        for category in sorted(categories):
            var = tk.BooleanVar()
            self.category_vars[category] = var
            ttk.Checkbutton(frame, text=f"{category.title()} ({len([f for f in self.file_data if f['category'] == category])} files)", 
                           variable=var).pack(anchor='w', pady=2)
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=(20, 0))
        
        ttk.Button(button_frame, text="✅ Apply Selection", 
                  command=lambda: self.apply_type_selection(type_window)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="❌ Cancel", 
                  command=type_window.destroy).pack(side=tk.LEFT)
    
    def apply_type_selection(self, type_window):
        """Apply the type-based selection"""
        selected_categories = [cat for cat, var in self.category_vars.items() if var.get()]
        
        for file_entry in self.file_data:
            if file_entry['category'] in selected_categories:
                file_entry['selected'] = True
        
        type_window.destroy()
        self.refresh_file_tree()
        self.update_selection_summary()
    
    def show_file_details(self, event):
        """Show detailed file information in a popup"""
        item = self.file_tree.selection()[0] if self.file_tree.selection() else None
        if not item:
            return
        
        row_index = self.file_tree.index(item)
        filtered_files = self.apply_filter(self.file_data)
        
        if row_index < len(filtered_files):
            file_entry = filtered_files[row_index]
            
            # Create detailed info window
            detail_window = tk.Toplevel(self.root)
            detail_window.title(f"📄 {file_entry['name']}")
            detail_window.geometry("600x400")
            
            text_widget = scrolledtext.ScrolledText(detail_window, wrap=tk.WORD, 
                                                   font=('Segoe UI', 10), padding=20)
            text_widget.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            # Extended file information
            try:
                file_stats = os.stat(file_entry['path'])
                
                extended_info = f"""📄 DETAILED FILE INFORMATION

🏷️ Filename: {file_entry['name']}

📁 Full Path: 
{file_entry['path']}

📏 Size: {get_size_readable(file_entry['size'])} ({file_entry['size']:,} bytes)

🏷️ Category: {file_entry['category'].title()}
🛡️ Safety Level: {file_entry['safety_icon']} {file_entry['safety'].title()}

📅 Created: {datetime.fromtimestamp(file_stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S')}
📅 Modified: {file_entry['modified'].strftime('%Y-%m-%d %H:%M:%S')}
📅 Accessed: {datetime.fromtimestamp(file_stats.st_atime).strftime('%Y-%m-%d %H:%M:%S')}

💡 SAFETY ASSESSMENT:
"""
                
                if file_entry['safety'] == 'safe':
                    extended_info += "✅ SAFE TO DELETE\nThis file appears to be cache, temporary data, or other regenerable content."
                elif file_entry['safety'] == 'user':
                    extended_info += "⚠️ USER FILE\nThis file contains user data. Review carefully before deletion."
                elif file_entry['safety'] == 'unknown':
                    extended_info += "❓ UNKNOWN SAFETY LEVEL\nCannot determine if this file is safe to delete. Proceed with caution."
                elif file_entry['safety'] == 'critical':
                    extended_info += "❌ CRITICAL FILE\nThis file may be essential for system operation. Deletion not recommended."
                
                text_widget.insert(tk.END, extended_info)
                text_widget.configure(state='disabled')
                
            except Exception as e:
                text_widget.insert(tk.END, f"Error getting file details: {e}")
    
    def open_file_location(self):
        """Open the location of selected file in file explorer"""
        selected_files = [f for f in self.file_data if f['selected']]
        if not selected_files:
            messagebox.showwarning("No Selection", "Please select a file first.")
            return
        
        file_path = selected_files[0]['path']
        directory = os.path.dirname(file_path)
        
        try:
            if IS_WINDOWS:
                subprocess.run(['explorer', '/select,', file_path])
            elif IS_MAC:
                subprocess.run(['open', '-R', file_path])
            else:  # Linux
                subprocess.run(['xdg-open', directory])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file location: {e}")
    
    def handle_file_deletion(self, selection_window, deletion_mode):
        """Handle file deletion with different safety modes"""
        selected_files = [f for f in self.file_data if f['selected']]
        
        if not selected_files:
            messagebox.showwarning("No Selection", "Please select files to delete first.")
            return
        
        # Safety confirmation based on selection
        critical_files = [f for f in selected_files if f['safety'] == 'critical']
        if critical_files:
            result = messagebox.askyesno(
                "⚠️ Critical Files Selected", 
                f"You have selected {len(critical_files)} critical files that may be essential for system operation.\n\n"
                "Are you absolutely sure you want to proceed?"
            )
            if not result:
                return
        
        # Show confirmation dialog
        total_size = sum(f['size'] for f in selected_files)
        safety_summary = {}
        for f in selected_files:
            safety_summary[f['safety']] = safety_summary.get(f['safety'], 0) + 1
        
        safety_text = "\n".join([f"• {safety.title()}: {count} files" for safety, count in safety_summary.items()])
        
        if deletion_mode == 'recycle':
            action_text = "move to Recycle Bin/Trash"
            icon = "♻️"
        else:  # backup mode
            action_text = "backup and delete"
            icon = "💾"
        
        confirmation = messagebox.askyesno(
            f"{icon} Confirm Deletion",
            f"Ready to {action_text}:\n\n"
            f"📋 Files: {len(selected_files)}\n"
            f"💾 Total Size: {get_size_readable(total_size)}\n\n"
            f"Safety Breakdown:\n{safety_text}\n\n"
            f"This action can be undone from the Recycle Bin/Trash."
        )
        
        if confirmation:
            selection_window.destroy()
            self.perform_safe_deletion(selected_files, deletion_mode)
    
    def perform_safe_deletion(self, selected_files, deletion_mode):
        """Perform the actual file deletion with safety measures"""
        self.log_output(f"\n🎯 Starting {deletion_mode} deletion for {len(selected_files)} files:", "header")
        
        # Initialize the safe delete manager
        from cScan import SafeDeleteManager, ConfigManager
        config = ConfigManager()
        
        # Configure deletion mode
        if deletion_mode == 'recycle':
            config.set('Settings', 'use_recycle_bin', 'true')
            config.set('Settings', 'backup_before_delete', 'false')
        else:  # backup mode
            config.set('Settings', 'use_recycle_bin', 'false')
            config.set('Settings', 'backup_before_delete', 'true')
        
        safe_delete = SafeDeleteManager(config)
        
        # Progress tracking
        self.progress.config(maximum=len(selected_files), value=0)
        self.update_status(f"Safely deleting files...")
        
        success_count = 0
        total_freed = 0
        failed_files = []
        
        # Create deletion log for this session
        session_log = {
            'timestamp': datetime.now().isoformat(),
            'mode': deletion_mode,
            'files': [],
            'success_count': 0,
            'total_size': 0
        }
        
        for i, file_entry in enumerate(selected_files):
            filepath = file_entry['path']
            size = file_entry['size']
            
            # Convert to format expected by safe_delete
            file_info = {
                'size': size,
                'category': file_entry['category'],
                'safety': file_entry['safety'],
                'modified': file_entry['modified']
            }
            
            try:
                success, message = safe_delete.safe_delete(filepath, file_info)
                
                if success:
                    success_count += 1
                    total_freed += size
                    filename = os.path.basename(filepath)
                    self.log_output(f"✅ {deletion_mode.title()}: {get_size_readable(size)} - {filename}", "success")
                    
                    # Add to session log
                    session_log['files'].append({
                        'path': filepath,
                        'size': size,
                        'category': file_entry['category'],
                        'safety': file_entry['safety'],
                        'status': 'success'
                    })
                else:
                    failed_files.append((filepath, message))
                    filename = os.path.basename(filepath)
                    self.log_output(f"❌ Failed: {filename} - {message}", "error")
                    
                    session_log['files'].append({
                        'path': filepath,
                        'size': size,
                        'category': file_entry['category'],
                        'safety': file_entry['safety'],
                        'status': f'failed: {message}'
                    })
                    
            except Exception as e:
                failed_files.append((filepath, str(e)))
                filename = os.path.basename(filepath)
                self.log_output(f"❌ Error: {filename} - {e}", "error")
            
            # Update progress
            self.progress.config(value=i + 1)
            self.root.update_idletasks()
        
        # Update session log totals
        session_log['success_count'] = success_count
        session_log['total_size'] = total_freed
        
        # Save session log
        self.save_deletion_session(session_log)
        
        # Final summary
        if success_count > 0:
            self.log_output(f"\n🎉 Successfully processed {success_count} files, freed {get_size_readable(total_freed)}", "success")
            
            if deletion_mode == 'recycle':
                self.log_output("💡 Files moved to Recycle Bin/Trash - can be restored if needed", "info")
            else:
                self.log_output("💡 Files backed up before deletion - check backup directory", "info")
        
        if failed_files:
            self.log_output(f"\n⚠️ Failed to delete {len(failed_files)} files:", "warning")
            for filepath, error_msg in failed_files[:5]:  # Show first 5 failures
                filename = os.path.basename(filepath)
                self.log_output(f"  • {filename}: {error_msg}", "warning")
            
            if len(failed_files) > 5:
                self.log_output(f"  ... and {len(failed_files) - 5} more failures", "warning")
        
        # Update total freed counter
        self.total_freed += total_freed
        
        # Show undo information
        if success_count > 0:
            self.show_undo_info(deletion_mode, success_count, total_freed)
        
        # Re-enable buttons
        self.enable_cleanup_buttons()
    
    def save_deletion_session(self, session_log):
        """Save deletion session for potential undo operations"""
        try:
            # Create sessions directory if it doesn't exist
            sessions_dir = os.path.join(tempfile.gettempdir(), 'cScan_sessions')
            if not os.path.exists(sessions_dir):
                os.makedirs(sessions_dir)
            
            # Save session file
            session_filename = f"deletion_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            session_path = os.path.join(sessions_dir, session_filename)
            
            with open(session_path, 'w') as f:
                json.dump(session_log, f, indent=2)
                
            self.log_output(f"💾 Session saved: {session_filename}", "info")
            
        except Exception as e:
            self.log_output(f"⚠️ Could not save session log: {e}", "warning")
    
    def show_undo_info(self, deletion_mode, file_count, total_size):
        """Show information about undo options"""
        undo_window = tk.Toplevel(self.root)
        undo_window.title("✅ Deletion Complete")
        undo_window.geometry("500x350")
        undo_window.configure(bg=self.colors['background'])
        
        frame = ttk.Frame(undo_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Success message
        success_label = ttk.Label(frame, text="✅ Files Successfully Processed!", style='Title.TLabel')
        success_label.pack(pady=(0, 20))
        
        # Stats
        stats_text = f"""📊 Summary:
• Files processed: {file_count}
• Space freed: {get_size_readable(total_size)}
• Method: {deletion_mode.title()}"""
        
        stats_label = ttk.Label(frame, text=stats_text, font=('Segoe UI', 10))
        stats_label.pack(pady=(0, 20))
        
        # Undo information
        if deletion_mode == 'recycle':
            undo_text = """♻️ Recovery Options:

Files have been moved to your Recycle Bin/Trash.

To restore files:
• Windows: Open Recycle Bin, select files, click 'Restore'
• macOS: Open Trash, drag files back to original location
• Linux: Use 'gio trash --restore' command

Files will remain in trash until manually emptied."""
        else:
            backup_dir = os.path.join(tempfile.gettempdir(), 'cScan_backups')
            undo_text = f"""💾 Recovery Options:

Files have been backed up before deletion.

Backup location:
{backup_dir}

To restore files:
• Browse to backup directory
• Copy desired files back to original locations
• Files are timestamped for easy identification"""
        
        undo_info = tk.Text(frame, height=10, wrap=tk.WORD, font=('Segoe UI', 9),
                           bg=self.colors['surface'], relief='flat')
        undo_info.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        undo_info.insert(tk.END, undo_text)
        undo_info.configure(state='disabled')
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack()
        
        if deletion_mode == 'recycle':
            ttk.Button(button_frame, text="🗑️ Open Recycle Bin", 
                      command=self.open_recycle_bin, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 10))
        else:
            ttk.Button(button_frame, text="📂 Open Backup Folder", 
                      command=lambda: self.open_backup_folder(), style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="✅ OK", 
                  command=undo_window.destroy, style='Primary.TButton').pack(side=tk.LEFT)
    
    def open_recycle_bin(self):
        """Open the recycle bin/trash"""
        try:
            if IS_WINDOWS:
                subprocess.run(['explorer', 'shell:RecycleBinFolder'])
            elif IS_MAC:
                subprocess.run(['open', os.path.expanduser('~/.Trash')])
            else:  # Linux
                trash_dir = os.path.expanduser('~/.local/share/Trash/files')
                if os.path.exists(trash_dir):
                    subprocess.run(['xdg-open', trash_dir])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open recycle bin: {e}")
    
    def open_backup_folder(self):
        """Open the backup folder"""
        backup_dir = os.path.join(tempfile.gettempdir(), 'cScan_backups')
        try:
            if IS_WINDOWS:
                subprocess.run(['explorer', backup_dir])
            elif IS_MAC:
                subprocess.run(['open', backup_dir])
            else:  # Linux
                subprocess.run(['xdg-open', backup_dir])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open backup folder: {e}")

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
                filename = filepath.split('/')[-1].split('\\')[-1]
                self.log_output(f"✅ Deleted: {get_size_readable(size)} - {filename}", "success")
            except Exception as e:
                filename = filepath.split('/')[-1].split('\\')[-1]
                self.log_output(f"❌ Failed to delete: {filename} - {e}", "error")
            
            self.progress.config(value=i + 1)
            self.root.update_idletasks()
        
        self.total_freed += deleted_size
        self.log_output(f"\n🎉 Successfully deleted {deleted_count} files, freed {get_size_readable(deleted_size)}", "success")
        
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
        self.log_output(f"\n💾 Total space freed this session: {get_size_readable(self.total_freed)}", "success")
    
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
