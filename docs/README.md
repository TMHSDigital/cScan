# cScan - Cross-Platform Cleanup Assistant

> A comprehensive disk cleanup utility for **Windows**, **macOS**, and **Linux** that helps you reclaim disk space by finding and removing large files, cleaning temporary files, and managing trash/recycle bin with advanced safety features.

[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue.svg)](https://github.com/yourusername/cScan)
[![Python](https://img.shields.io/badge/python-3.6%2B-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

---

## Table of Contents

- [Features](#features)
- [Platform Support](#platform-support)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start Guide](#quick-start-guide)
- [Enhanced Features](#enhanced-features)
- [Safety Features](#safety-features)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

---

## Features

### 🚀 Core Features

| Feature | Description |
|---------|-------------|
| **Smart File Analysis** | AI-like categorization and safety assessment |
| **Cross-Platform** | Works on Windows, macOS, and Linux |
| **Safe Deletion** | Recycle Bin/Trash integration with recovery options |
| **Smart Suggestions** | Intelligent cleanup recommendations |
| **Multiple Interfaces** | CLI and GUI options |
| **Comprehensive Logging** | Complete audit trail of all operations |

### 🎯 Smart Cleanup Categories

```
✓ Cache Files        - Browser, app, and system caches
✓ Temporary Files    - Old temp files (7+ days)
✓ Large Downloads    - Files >500MB in Downloads
✓ Old Installers     - Setup files >30 days old
✓ Crash Dumps        - Debug and crash report files
✓ Media Files        - Large videos and audio files
✓ Backup Files       - Old backup files >30 days
```

---

## Platform Support

### Automatic Platform Detection

```
--- User Space Cleanup Assistant (Windows) ---
--- User Space Cleanup Assistant (macOS) ---  
--- User Space Cleanup Assistant (Linux) ---
```

### Platform-Specific Features

| Platform | Trash System | Temp Locations | Admin Check |
|----------|--------------|----------------|-------------|
| **Windows** | Recycle Bin | `%TEMP%`, `%LOCALAPPDATA%\Temp` | UAC |
| **macOS** | Trash | `/tmp`, `~/Library/Caches` | sudo |
| **Linux** | Trash/gio | `/tmp`, `~/.cache` | root |

---

## Prerequisites

### System Requirements

| Component | Windows | macOS | Linux |
|-----------|---------|-------|-------|
| **OS Version** | Windows 10+ | macOS 10.12+ | Ubuntu 18.04+ |
| **Python** | 3.6+ | 3.6+ | 3.6+ |
| **Dependencies** | psutil | psutil | psutil |
| **Storage** | <10MB | <10MB | <10MB |

### Installing Python

#### Windows
```powershell
# Check if Python is installed
python --version

# If not installed, download from python.org
# IMPORTANT: Check "Add Python to PATH" during installation
```

#### macOS
```bash
# Python 3 usually comes pre-installed
python3 --version

# If needed, install via Homebrew
brew install python3
```

#### Linux
```bash
# Check Python version
python3 --version

# If needed, install via package manager
sudo apt-get update
sudo apt-get install python3 python3-pip
```

---

## Installation

### 1. Download cScan

```bash
# Clone repository (all platforms)
git clone https://github.com/yourusername/cScan.git
cd cScan

# Or download ZIP and extract
```

### 2. Install Dependencies

```bash
# Windows
pip install psutil

# macOS/Linux
pip3 install psutil
```

### 3. Verify Installation

```bash
# Windows
python cScan.py --help

# macOS/Linux  
python3 cScan.py --help
```

---

## Quick Start Guide

### Basic Usage

```bash
# Windows
python cScan.py

# macOS/Linux
python3 cScan.py
```

### Interface Options

```
Choose interface:
1. Command Line Interface (CLI)    ← Text-based, powerful
2. Graphical User Interface (GUI)  ← Visual, user-friendly  
3. Edit Configuration             ← Customize settings
```

### First Scan

```
┌─ CLI Quick Start ─────────────────────────────────┐
│                                                   │
│ 1. Choose option 1 (CLI)                         │
│ 2. Review detected platform and scan paths       │
│ 3. Wait for scan to complete                     │
│ 4. Choose from smart suggestions                 │
│ 5. Confirm deletions when prompted               │
│                                                   │
└───────────────────────────────────────────────────┘
```

---

## Enhanced Features

### 🧠 Smart File Analysis

Files are automatically categorized and assessed for safety:

```
File Display Format:
SIZE SAFETY [CATEGORY] - PATH

Examples:
4.36 GB ✓ [cache] - ~/Library/Caches/app.cache
1.22 GB ? [media] - ~/Downloads/movie.mp4  
523 MB  ! [unknown] - ~/Documents/data.bin
102 MB  ✗ [system] - /usr/lib/system.so
```

**Safety Indicators:**
- ✓ = Safe to delete
- ? = User confirmation needed
- ! = Unknown (review carefully)
- ✗ = Critical (protected)

### 📊 Smart Suggestions

The system provides intelligent cleanup recommendations:

```
SMART CLEANUP SUGGESTIONS
════════════════════════════════════════════════════

1. Cache files (can be regenerated)
   Files: 61 | Size: 27.93 GB | Safety: safe

2. Old temporary files (7+ days old)
   Files: 23 | Size: 3.35 GB | Safety: safe

3. Large media files (>1GB each)
   Files: 4 | Size: 5.18 GB | Safety: user
```

### 🔄 Multiple Review Modes

1. **Smart Suggestions** - AI-guided cleanup
2. **Manual Review** - File-by-file control
3. **Category View** - Browse by file type
4. **Quick Actions** - Batch operations

### 📝 Comprehensive Logging

All operations are logged:
- **Windows**: `%TEMP%\cScan_backups\deleted_files.json`
- **macOS/Linux**: `/tmp/cScan_backups/deleted_files.json`

---

## Safety Features

### 🛡️ Multi-Layer Protection

```
Protection Levels:
┌────────────────────────────────────────────────┐
│ 1. Platform-aware system file protection       │
│ 2. Running process detection                   │
│ 3. File-in-use checking                       │
│ 4. Trash/Recycle Bin integration             │
│ 5. Optional backup before deletion            │
│ 6. Comprehensive deletion logging             │
│ 7. Dry-run mode for testing                  │
└────────────────────────────────────────────────┘
```

### Protected Paths

| Platform | Protected Directories |
|----------|---------------------|
| **Windows** | `C:\Windows`, `C:\Program Files`, System32 |
| **macOS** | `/System`, `/Library`, `/Applications` |
| **Linux** | `/bin`, `/usr`, `/lib`, `/etc`, `/boot` |

---

## Configuration

### Configuration File

Location: `cScan_config.ini` (same directory as script)

### Key Settings

```ini
[Settings]
# File size threshold (MB)
large_file_threshold_mb = 100

# Use Trash/Recycle Bin (cross-platform)
use_recycle_bin = true

# Safety features
show_safety_warnings = true
dry_run_mode = false
backup_before_delete = false

# Interface preference
default_interface = ask  # ask, cli, or gui

[Paths]
# Standard folders to scan
include_downloads = true
include_documents = true
include_temp_folders = true

# Platform-specific custom paths
# Windows: custom_scan_paths = D:\Downloads, E:\Temp
# macOS/Linux: custom_scan_paths = /Users/Shared, /opt/temp
custom_scan_paths = 
```

### Editing Configuration

```bash
# Direct configuration access
python cScan.py --config  # Windows
python3 cScan.py --config # macOS/Linux

# Or choose option 3 from main menu
```

---

## Usage Examples

### Example 1: Smart Cleanup (Recommended)

```bash
$ python3 cScan.py

--- User Space Cleanup Assistant (macOS) ---

Choose interface: 1

============================================================
SMART FILE ANALYSIS RESULTS
============================================================

File Categories Found:
  Cache         64 files    28.32 GB
  Media        374 files    87.28 GB
  Downloads      3 files   520.61 MB
  Temp          12 files     1.24 GB

Safety Analysis:
  ✓ Safe         52 files
  ? User        388 files
  ! Unknown      69 files

============================================================
SMART CLEANUP SUGGESTIONS
============================================================

1. Cache files (can be regenerated)
   Files: 61 | Size: 27.93 GB | Safety: safe
   
Delete these files? (Y/n): y
✓ Deleted 61 files

Total space freed: 27.93 GB
```

### Example 2: Manual Review

```bash
Manual Review Mode
Commands: y=delete, n=skip, i=info, q=quit

[1/25] 1.5 GB - ~/Downloads/old_installer.dmg
Category: installers | Safety: user
Action? (y/n/i/q): i

────────────────────────────────
File: old_installer.dmg
Path: /Users/username/Downloads/old_installer.dmg
Size: 1.5 GB
Category: installers
Safety: user
Modified: 2024-11-15 10:30:00
MIME Type: application/x-apple-diskimage
────────────────────────────────

Action? (y/n/i/q): y
✓ Deleted
```

---

## Troubleshooting

### Platform-Specific Issues

#### Windows
```
❌ PowerShell execution policy error
✅ Run: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

❌ Python not found
✅ Reinstall Python with "Add to PATH" checked
```

#### macOS
```
❌ Permission denied errors
✅ Grant Terminal full disk access in System Preferences

❌ Trash won't empty
✅ Run: sudo rm -rf ~/.Trash/* (careful!)
```

#### Linux
```
❌ gio command not found
✅ Install: sudo apt install glib2.0-bin

❌ Permission errors on temp files
✅ Script only deletes files you own
```

### Common Solutions

| Issue | Solution |
|-------|----------|
| **ModuleNotFoundError: psutil** | Install: `pip install psutil` |
| **GUI won't open** | Use CLI mode (option 1) |
| **Scan is slow** | Exclude large media folders |
| **Files won't delete** | Check if files are in use |

---

## FAQ

<details>
<summary><strong>Is this safe to use?</strong></summary>

Yes! cScan includes multiple safety layers:
- System files are protected
- Files go to Trash/Recycle Bin by default
- All deletions require confirmation
- Complete logging for recovery
- Dry-run mode for testing

</details>

<details>
<summary><strong>Can I recover deleted files?</strong></summary>

Yes, if `use_recycle_bin = true` (default):
- **Windows**: Check Recycle Bin
- **macOS**: Check Trash
- **Linux**: Check ~/.local/share/Trash

Additionally, check the deletion log for file information.

</details>

<details>
<summary><strong>How often should I run this?</strong></summary>

Recommended frequency:
- **Weekly**: For heavy computer users
- **Monthly**: For regular maintenance
- **When needed**: When disk space is low

</details>

<details>
<summary><strong>Does it work on servers?</strong></summary>

Yes, but:
- Use CLI mode only
- Enable dry_run_mode first
- Review all suggestions carefully
- Consider using read-only mode

</details>

<details>
<summary><strong>Can I automate this?</strong></summary>

Yes! Set in config:
```ini
default_interface = cli
dry_run_mode = false  # Only after testing!
```

Then script with appropriate responses.

</details>

---

## Advanced Usage

### Command Line Arguments

```bash
# Show help
python cScan.py --help

# Direct configuration access
python cScan.py --config

# Future: Dry run mode
python cScan.py --dry-run

# Future: Specific path scan
python cScan.py --path /specific/directory
```

### Performance Tips

1. **Close unnecessary applications** - Frees up locked files
2. **Exclude media libraries** - If not cleaning media
3. **Run during low usage** - Better performance
4. **Use SSD** - Significantly faster scanning

### Integration Ideas

- **Scheduled Tasks** (Windows) / **Cron** (Unix)
- **System maintenance scripts**
- **Pre-backup cleanup routines**
- **Disk space monitoring alerts**

---

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

### Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/cScan.git
cd cScan

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Unix
venv\Scripts\activate     # Windows

# Install development dependencies
pip install -r requirements.txt
pip install pytest black flake8
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- Built with Python's powerful standard library
- Cross-platform support via psutil
- Community feedback and contributions

---

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/cScan/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/cScan/discussions)
- **Email**: support@example.com

---

> **Remember**: Always backup important data before running cleanup operations! 