# cScan - User Space Cleanup Assistant

> A comprehensive Windows disk cleanup utility that helps you reclaim disk space by finding and removing large files, cleaning temporary files, and emptying the recycle bin.

---

## Table of Contents

- [What This Tool Does](#what-this-tool-does)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start Guide](#quick-start-guide)
- [Detailed Usage Instructions](#detailed-usage-instructions)
- [Understanding Results](#understanding-results)
- [Configuration & Settings](#configuration--settings)
- [Safety Features](#safety-features)
- [Troubleshooting](#troubleshooting)
- [Performance & Examples](#performance--examples)
- [Advanced Usage](#advanced-usage)
- [Support & FAQ](#support--faq)

---

## What This Tool Does

cScan helps you **free up disk space** on your Windows computer by:

| Feature | Description |
|---------|-------------|
| **Large File Detection** | Finds files taking up significant space |
| **Temporary File Cleanup** | Removes accumulated temporary files |
| **Recycle Bin Management** | Safely empties your recycle bin |
| **Smart Suggestions** | Provides manual cleanup recommendations |

### Key Benefits

```
✓ Safe Operation    - Only works with your personal files
✓ User Control      - Always asks before deleting anything  
✓ Detailed Logging  - Shows exactly what was done
✓ No Admin Required - Runs with regular user privileges
```

---

## Prerequisites

### System Requirements

| Component | Requirement |
|-----------|-------------|
| **Operating System** | Windows 10 or Windows 11 (any edition) |
| **Python Version** | Python 3.6 or higher |
| **Disk Space** | Less than 1 MB for program files |
| **User Account** | Regular user account (no admin needed) |

### Checking if Python is Installed

1. **Open Command Prompt:**
   - Press `Windows Key + R`
   - Type `cmd` and press Enter

2. **Check Python Version:**
   ```cmd
   python --version
   ```

3. **Expected Results:**
   - ✅ **Success:** Shows "Python 3.x.x"
   - ❌ **Need to Install:** Shows error message

### Installing Python (If Needed)

> **Step-by-Step Python Installation**

1. **Download Python:**
   - Visit: https://python.org/downloads
   - Click the large "Download Python" button

2. **Install Python:**
   - Run the downloaded file
   - **CRITICAL:** Check "Add Python to PATH"
   - Click "Install Now"
   - Wait for completion

3. **Verify Installation:**
   - Restart your computer
   - Test with `python --version` command

---

## Installation

### Method 1: GitHub Download (Recommended)

```
Step 1: Download
┌─────────────────────────────────────┐
│ Go to GitHub repository page       │
│ Click green "Code" button          │
│ Select "Download ZIP"              │
│ Save to Downloads folder           │
└─────────────────────────────────────┘

Step 2: Extract
┌─────────────────────────────────────┐
│ Right-click downloaded ZIP file     │
│ Select "Extract All..."            │
│ Choose destination folder          │
│ Recommended: C:\Scripts\cScan      │
└─────────────────────────────────────┘

Step 3: Verify
┌─────────────────────────────────────┐
│ Open extracted folder              │
│ Confirm these files exist:         │
│  • cScan.py                       │
│  • cScan_config.ini               │
│  • README.md                      │
└─────────────────────────────────────┘
```

### Method 2: Manual Setup

```
1. Create folder: C:\Scripts\cScan
2. Copy files to folder:
   • cScan.py
   • cScan_config.ini
3. Verify files are present
```

---

## Quick Start Guide

### Getting Started in 3 Steps

```
┌─ STEP 1: Open Command Window ─────────────────────┐
│                                                   │
│ 1. Navigate to cScan folder                      │
│ 2. Hold Shift + Right-click in empty space       │
│ 3. Select "Open PowerShell window here"          │
│                                                   │
└───────────────────────────────────────────────────┘

┌─ STEP 2: Run Program ─────────────────────────────┐
│                                                   │
│ Type: python cScan.py                            │
│ Press: Enter                                      │
│                                                   │
└───────────────────────────────────────────────────┘

┌─ STEP 3: Choose Interface ───────────────────────┐
│                                                   │
│ Option 1: Command Line (text-based)              │
│ Option 2: Graphical Interface (window-based)     │
│ Option 3: Settings (customize program)           │
│                                                   │
└───────────────────────────────────────────────────┘
```

---

## Detailed Usage Instructions

### Graphical Interface (Easiest for Beginners)

```
┌─ LAUNCH ─────────────────────────────────────────┐
│ 1. Run: python cScan.py                         │
│ 2. Choose: Option 2 (GUI)                       │
│ 3. Window opens with buttons and text area      │
└──────────────────────────────────────────────────┘

┌─ SCAN ───────────────────────────────────────────┐
│ 1. Click: "Start Scan" button                   │
│ 2. Wait: Progress bar shows status              │
│ 3. Review: Results appear in text area          │
└──────────────────────────────────────────────────┘

┌─ ACTIONS ────────────────────────────────────────┐
│ • "Clean Temp Files" - Remove temporary files   │
│ • "Empty Recycle Bin" - Clear recycle bin       │
│ • "Settings" - Customize program behavior       │
│ • "Exit" - Close program                        │
└──────────────────────────────────────────────────┘
```

### Command Line Interface (For Advanced Users)

```
┌─ LAUNCH ─────────────────────────────────────────┐
│ 1. Run: python cScan.py                         │
│ 2. Choose: Option 1 (CLI)                       │
│ 3. Follow text prompts in window                │
└──────────────────────────────────────────────────┘

┌─ INTERACTION ────────────────────────────────────┐
│ • Type 'y' for Yes                              │
│ • Type 'n' for No                               │
│ • Type 'q' to Quit deletion process             │
│ • Type 'DELETE ALL' to delete all files         │
└──────────────────────────────────────────────────┘
```

---

## Understanding Results

### Large Files Report Format

```
Example Output:
┌────────────────────────────────────────────────────────────┐
│ Found 5 large files:                                      │
│    250.00 MB - C:\Users\YourName\Downloads\movie.mp4      │
│    180.50 MB - C:\Users\YourName\Documents\presentation.  │
│    120.25 MB - C:\Users\YourName\Downloads\software.exe   │
│                                                            │
│ Total size of large files: 550.75 MB                      │
└────────────────────────────────────────────────────────────┘
```

### File Types Explanation

| File Type | Extension | Description | Safe to Delete? |
|-----------|-----------|-------------|-----------------|
| **Software Installers** | `.exe`, `.msi` | Programs you've installed | Usually Yes (if already installed) |
| **Video Files** | `.mp4`, `.avi`, `.mkv` | Movies, recordings | Your choice |
| **Backup Files** | `.bak`, `.old`, `.backup` | Old file copies | Usually Yes |
| **Documents** | `.pdf`, `.docx`, `.pptx` | Your documents | Your choice |
| **Archives** | `.zip`, `.rar`, `.7z` | Compressed files | Check contents first |

### Size Reference Guide

```
Size Units:
┌─────────────┬──────────────┬─────────────────────┐
│ Unit        │ Equivalent   │ Example             │
├─────────────┼──────────────┼─────────────────────┤
│ KB (Kilobyte) │ 1,024 bytes  │ Small text file     │
│ MB (Megabyte) │ 1,024 KB     │ Photo, song         │
│ GB (Gigabyte) │ 1,024 MB     │ Movie, large app    │
│ TB (Terabyte) │ 1,024 GB     │ Entire hard drive   │
└─────────────┴──────────────┴─────────────────────┘
```

---

## Configuration & Settings

### Accessing Settings

| Method | Command | When to Use |
|--------|---------|-------------|
| **From Main Menu** | Choose Option 3 | When starting program |
| **From GUI** | Click "Settings" button | While using graphical interface |
| **Direct Access** | `python cScan.py --config` | Quick settings access |

### Key Settings Explained

#### File Size Threshold
```
┌─ FILE SIZE THRESHOLD ────────────────────────────┐
│                                                  │
│ Default: 100 MB                                  │
│                                                  │
│ Lower values (50 MB):                            │
│   • Finds more files                             │
│   • More detailed cleanup                        │
│                                                  │
│ Higher values (500 MB):                          │
│   • Finds fewer files                            │
│   • Only very large files                        │
│                                                  │
└──────────────────────────────────────────────────┘
```

#### Scan Locations
```
┌─ RECOMMENDED SETTINGS ───────────────────────────┐
│                                                  │
│ ✓ User Profile      - Your entire user folder   │
│ ✓ Downloads         - Downloads folder          │
│ ✓ Documents         - Documents folder          │
│ ✓ Desktop           - Desktop files             │
│ ✓ Pictures          - Pictures folder           │
│ ✓ Videos           - Videos folder              │
│ ✓ Music            - Music folder               │
│ ✓ Temp Folders     - Temporary file locations   │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## Safety Features

### What cScan WILL NOT Do

```
🛡️ SAFETY GUARANTEES
┌────────────────────────────────────────────────────┐
│                                                    │
│ ✗ Delete system files                             │
│ ✗ Delete files without asking                     │
│ ✗ Break your computer                             │
│ ✗ Delete important programs                       │
│ ✗ Access files you can't access                   │
│ ✗ Run without your permission                     │
│                                                    │
└────────────────────────────────────────────────────┘
```

### What cScan WILL Do

```
✅ SAFETY FEATURES
┌────────────────────────────────────────────────────┐
│                                                    │
│ ✓ Show exactly what will be deleted               │
│ ✓ Allow individual file review                    │
│ ✓ Let you skip files you want to keep             │
│ ✓ Provide detailed operation logs                 │
│ ✓ Only work in your user folders                  │
│ ✓ Respect Windows file permissions                │
│                                                    │
└────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### Common Issues & Solutions

#### Python Not Found
```
❌ PROBLEM: "Python is not recognized"

✅ SOLUTION:
1. Reinstall Python from python.org
2. ✓ Check "Add Python to PATH" during install
3. Restart computer
4. Test: python --version
```

#### Permission Errors
```
❌ PROBLEM: "Permission denied" errors

✅ EXPLANATION:
• This is normal and safe
• Windows protects certain files
• Program skips inaccessible files
• Your system remains secure
```

#### Program Won't Start
```
❌ PROBLEM: Error when running cScan.py

✅ SOLUTIONS:
1. Verify you're in correct folder
2. Check both files exist:
   • cScan.py
   • cScan_config.ini
3. Open new command window
4. Restart computer if needed
```

#### GUI Won't Open
```
❌ PROBLEM: Graphical interface fails

✅ SOLUTION:
• Use command line interface (Option 1)
• Works identically to GUI
• Just as safe and effective
```

### Quick Diagnostic Commands

```bash
# Check Python installation
python --version

# Check current directory
dir

# List Python packages
python -m pip list

# Test cScan directly
python cScan.py --config
```

---

## Performance & Examples

### Typical Performance

| Computer Type | Files Scanned | Time Required |
|---------------|---------------|---------------|
| **Light Usage** | 10,000-50,000 | 1-2 minutes |
| **Average Usage** | 50,000-150,000 | 3-5 minutes |
| **Heavy Usage** | 150,000+ | 5-15 minutes |

### Example Results

#### Example 1: Student Computer
```
┌─ SCAN RESULTS ───────────────────────────────────┐
│                                                  │
│ Files Scanned: 45,000                           │
│ Large Files Found: 8                            │
│ Total Size: 1.5 GB                              │
│                                                  │
│ Breakdown:                                       │
│ • 3 old movie downloads (800 MB)                │
│ • 2 software installers (400 MB)                │
│ • 1 large document (200 MB)                     │
│ • 2 backup files (100 MB)                       │
│                                                  │
│ Space Freed: 1.2 GB                             │
│                                                  │
└──────────────────────────────────────────────────┘
```

#### Example 2: Professional Computer
```
┌─ SCAN RESULTS ───────────────────────────────────┐
│                                                  │
│ Files Scanned: 180,000                          │
│ Large Files Found: 25                           │
│ Total Size: 5.2 GB                              │
│                                                  │
│ Breakdown:                                       │
│ • Video projects (2.8 GB)                       │
│ • Development files (1.1 GB)                    │
│ • System backups (800 MB)                       │
│ • Downloaded content (500 MB)                   │
│                                                  │
│ Space Freed: 2.1 GB                             │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## Advanced Usage

### Command Line Options

```bash
# Interactive mode (choose interface)
python cScan.py

# Open settings directly
python cScan.py --config
```

### Configuration File

```ini
# Location: cScan_config.ini
# Safe to edit with Notepad

[Settings]
large_file_threshold_mb = 100    # Size threshold
default_interface = ask          # Interface preference
clean_temp_by_default = true     # Auto-suggest temp cleanup

[Paths]
include_downloads = true         # Scan Downloads folder
include_documents = true         # Scan Documents folder
custom_scan_paths =             # Additional folders (comma-separated)
```

### Automation Tips

```
For Regular Users:
┌──────────────────────────────────────────────────┐
│ Set default_interface = gui                      │
│ Keep file threshold at 100 MB                    │
│ Enable all standard scan paths                   │
└──────────────────────────────────────────────────┘

For Power Users:
┌──────────────────────────────────────────────────┐
│ Set default_interface = cli                      │
│ Lower threshold to 50 MB for detailed cleanup    │
│ Add custom paths for project folders             │
└──────────────────────────────────────────────────┘
```

---

## Support & FAQ

### Frequently Asked Questions

<details>
<summary><strong>Is this safe to use?</strong></summary>

Yes, cScan is designed with safety as the top priority:
- Only works with your personal files
- Always asks before deleting anything
- Cannot access system files
- Shows exactly what will be deleted

</details>

<details>
<summary><strong>Will this speed up my computer?</strong></summary>

cScan frees up disk space, which can help if your disk was getting full. However:
- It won't directly speed up processing
- It will prevent slowdowns from full disks
- It makes more space for new files

</details>

<details>
<summary><strong>Can I recover deleted files?</strong></summary>

**Important:** Files deleted by cScan are permanently removed, not sent to recycle bin.
- Only delete files you're sure you don't need
- Consider backing up important files first
- Review each file carefully before deletion

</details>

<details>
<summary><strong>How often should I run this?</strong></summary>

Recommended frequency:
- **Monthly** for regular maintenance
- **When disk space is low** (urgent cleanup)
- **Before major installations** (make space)
- **After large downloads** (cleanup afterward)

</details>

### Getting Help

#### Before Requesting Support

```
✓ Check this README for your issue
✓ Try both interfaces (GUI and CLI)
✓ Verify settings are appropriate
✓ Restart program and try again
```

#### Information to Include

When reporting issues, please provide:

```
System Information:
• Windows version (Windows 10/11)
• Python version (python --version)
• Exact error message (copy/paste)
• What you were doing when error occurred
```

---

## Technical Specifications

```
┌─ SYSTEM REQUIREMENTS ────────────────────────────┐
│                                                  │
│ Platform:        Windows 10/11                  │
│ Python:          3.6 or higher                  │
│ Dependencies:    None (built-in libraries only) │
│ Memory Usage:    < 100 MB                       │
│ Disk Space:      < 1 MB                         │
│ Network:         No internet required           │
│ Permissions:     Regular user account           │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## File Structure

```
cScan/
├── cScan.py                 # Main program file
├── cScan_config.ini         # Configuration settings
└── README.md               # This documentation

Required Files:
✓ cScan.py                  # DO NOT EDIT
✓ cScan_config.ini          # Safe to edit
✓ README.md                 # Documentation
```

---

## Version Information

| Attribute | Value |
|-----------|-------|
| **Version** | 1.0 |
| **Release Date** | January 2025 |
| **Compatibility** | Windows 10/11 + Python 3.6+ |
| **License** | Free for personal and educational use |
| **Support** | Community-based |

---

> **Need additional help?** Refer to the [Troubleshooting](#troubleshooting) section or check the [FAQ](#support--faq) for common questions and solutions. 