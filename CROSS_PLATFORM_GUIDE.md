# cScan Cross-Platform Guide

## Overview

cScan now supports **Windows**, **macOS**, and **Linux**! The script automatically detects your operating system and adapts its behavior accordingly.

## Platform Detection

When you run cScan, it will display the detected platform:
```
--- User Space Cleanup Assistant (Windows) ---
--- User Space Cleanup Assistant (macOS) ---
--- User Space Cleanup Assistant (Linux) ---
```

## Platform-Specific Features

### Windows
- **Recycle Bin**: Files are moved to Windows Recycle Bin
- **Temp Paths**: `%TEMP%`, `%LOCALAPPDATA%\Temp`
- **System Protection**: Protects Windows, Program Files directories
- **Admin Check**: Uses Windows UAC to check admin status

### macOS
- **Trash**: Files are moved to macOS Trash
- **Temp Paths**: `/tmp`, `~/Library/Caches`
- **System Protection**: Protects `/System`, `/Library`, `/Applications`
- **Admin Check**: Checks if running as root (sudo)

### Linux
- **Trash**: Uses `gio trash` or moves to `~/.local/share/Trash`
- **Temp Paths**: `/tmp`, `/var/tmp`, `~/.cache`
- **System Protection**: Protects `/bin`, `/usr`, `/lib`, `/etc`
- **Admin Check**: Checks if running as root

## Cross-Platform File Categories

The script intelligently categorizes files based on platform conventions:

### Safe to Delete
- **All Platforms**: Cache files, temp files, crash dumps
- **Windows**: `DXCache`, `server-cache`, `pip\cache`
- **macOS/Linux**: `.cache/`, `.npm/`, `Trash/`

### User Files (Need Confirmation)
- **Windows**: `Downloads\`, `Documents\`, `Videos\`
- **macOS**: `Downloads/`, `Documents/`, `Movies/`
- **Linux**: `Downloads/`, `Documents/`, `Videos/`

## Installation

### Windows
```bash
pip install psutil
python cScan.py
```

### macOS
```bash
pip3 install psutil
python3 cScan.py
```

### Linux
```bash
pip3 install psutil
python3 cScan.py
```

## Usage Examples

### CLI Mode (All Platforms)
```bash
# Run the script
python cScan.py  # Windows
python3 cScan.py # macOS/Linux

# Direct CLI mode
python cScan.py --config  # Edit configuration
```

### GUI Mode
The GUI adapts to your platform:
- Windows: "Empty Recycle Bin" button
- macOS/Linux: "Empty Trash" button

## Platform-Specific Cleanup Suggestions

### Windows
- Clear `%LOCALAPPDATA%\Microsoft\Windows\Explorer\thumbcache_*.db`
- Use Disk Cleanup tool (cleanmgr.exe)
- Remove old Windows.old folders

### macOS
- Clear `~/Library/Caches/` subdirectories
- Remove old iOS device backups
- Clean Xcode derived data
- Use Storage Management (Apple Menu > About This Mac > Storage)

### Linux
- Clear `~/.cache/` subdirectories
- Remove old package manager caches
- Use system cleanup tools (bleachbit)

## Configuration

The configuration file (`cScan_config.ini`) works the same on all platforms:

```ini
[Settings]
large_file_threshold_mb = 100
use_recycle_bin = true  # Uses Trash on macOS/Linux

[Paths]
# Platform-specific paths are automatically handled
include_downloads = true
include_documents = true
include_temp_folders = true
```

## Safety Features

### Cross-Platform Protection
- System files are protected on all platforms
- Running applications are detected and protected
- Files in use cannot be deleted
- Critical system paths are never touched

### Platform-Specific Safety
- **Windows**: Protects Windows directory, Program Files
- **macOS**: Protects /System, /Library, /Applications
- **Linux**: Protects /bin, /usr, /lib, /etc

## Troubleshooting

### macOS Permission Issues
If you get permission errors on macOS:
1. Grant Terminal/iTerm full disk access in System Preferences
2. Run without sudo for user files
3. Use sudo only for system-wide cleanup

### Linux Trash Issues
If trash doesn't work on Linux:
1. Install `gio`: `sudo apt install glib2.0-bin`
2. Or files will be moved to `~/.local/share/Trash/files/`

### Windows PowerShell Issues
If PowerShell commands fail:
1. Run PowerShell as administrator once
2. Execute: `Set-ExecutionPolicy RemoteSigned`

## Advanced Features

### Custom Scan Paths
Add platform-specific paths in the config:
```ini
[Paths]
# Windows
custom_scan_paths = D:\Downloads, E:\Temp

# macOS/Linux
custom_scan_paths = /Users/Shared/Downloads, /opt/temp
```

### Dry Run Mode
Test what would be deleted without actually deleting:
```ini
[Settings]
dry_run_mode = true
```

## Performance Tips

### All Platforms
- Close unnecessary applications before scanning
- Exclude large media folders if not needed
- Run regular cleanups to prevent buildup

### Platform-Specific
- **Windows**: Disable Windows Defender scanning temporarily
- **macOS**: Quit Time Machine during cleanup
- **Linux**: Stop package managers before cleaning caches

This cross-platform version ensures consistent behavior across all operating systems while respecting platform-specific conventions and safety requirements. 