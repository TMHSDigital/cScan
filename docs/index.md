---
layout: default
title: cScan - Cross-Platform Cleanup Assistant
---

# cScan Documentation

Welcome to the official documentation for **cScan** - a comprehensive disk cleanup utility for Windows, macOS, and Linux.

[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue.svg)](https://github.com/yourusername/cScan)
[![Python](https://img.shields.io/badge/python-3.6%2B-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](https://github.com/yourusername/cScan/blob/main/LICENSE)

## 🚀 Quick Links

### Getting Started
- [**Installation & Quick Start**](README.md) - Complete setup guide
- [**Cross-Platform Guide**](CROSS_PLATFORM_GUIDE.md) - Platform-specific features

### Features & Improvements
- [**Enhanced Features**](IMPROVEMENTS.md) - What's new in cScan
- [**Technical Fixes**](FIXES_APPLIED.md) - Safety improvements explained

### Additional Resources
- [**Documentation Review**](DOCUMENTATION_REVIEW.md) - Documentation overview
- [**GitHub Repository**](https://github.com/yourusername/cScan) - Source code

## 🎯 What is cScan?

cScan helps you reclaim disk space by intelligently finding and removing:
- 🗑️ **Cache Files** - Browser, app, and system caches
- 📁 **Temporary Files** - Old temp files (7+ days)
- 💿 **Large Downloads** - Files >500MB in Downloads
- 🔧 **Old Installers** - Setup files >30 days old
- 💥 **Crash Dumps** - Debug and crash report files

## ✨ Key Features

### Smart File Analysis
- **AI-like categorization** with safety assessment
- **Visual indicators**: ✓ Safe | ? User Review | ! Unknown | ✗ Protected
- **Smart suggestions** for optimal cleanup

### Cross-Platform Support
| Platform | Trash System | Temp Locations |
|----------|--------------|----------------|
| **Windows** | Recycle Bin | `%TEMP%`, `%LOCALAPPDATA%\Temp` |
| **macOS** | Trash | `/tmp`, `~/Library/Caches` |
| **Linux** | gio trash | `/tmp`, `~/.cache` |

### Safety First
- 🛡️ **7 Protection Layers** including system file protection
- 🔄 **Trash/Recycle Bin** integration (files recoverable)
- 📝 **Complete logging** of all operations
- ⚠️ **Dry-run mode** for testing

## 📊 Example Results

```bash
SMART CLEANUP SUGGESTIONS
════════════════════════════════════════════════════

1. Cache files (can be regenerated)
   Files: 61 | Size: 27.93 GB | Safety: safe

2. Old temporary files (7+ days old)
   Files: 23 | Size: 3.35 GB | Safety: safe

Total space freed: 31.28 GB
```

## 🔧 Installation

```bash
# Clone repository
git clone https://github.com/yourusername/cScan.git
cd cScan

# Install dependencies
pip install psutil  # Windows
pip3 install psutil # macOS/Linux

# Run cScan
python cScan.py   # Windows
python3 cScan.py  # macOS/Linux
```

## 📚 Documentation Index

### User Guides
1. [**README**](README.md) - Complete user manual
2. [**Cross-Platform Guide**](CROSS_PLATFORM_GUIDE.md) - OS-specific instructions

### Technical Documentation
1. [**Improvements**](IMPROVEMENTS.md) - Feature enhancements
2. [**Fixes Applied**](FIXES_APPLIED.md) - Safety fixes explained

### Meta Documentation
1. [**Documentation Review**](DOCUMENTATION_REVIEW.md) - Documentation overview

## 💡 Quick Tips

- **Always backup** important data before cleanup
- **Start with smart suggestions** for safest cleanup
- **Review unknown files** carefully before deletion
- **Use dry-run mode** to preview changes

## 🤝 Contributing

We welcome contributions! Please see our [GitHub repository](https://github.com/yourusername/cScan) for:
- Issue reporting
- Feature requests
- Pull requests
- Discussions

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](https://github.com/yourusername/cScan/blob/main/LICENSE) file for details.

---

<p align="center">
  Made with ❤️ by the cScan team<br>
  <a href="https://github.com/yourusername/cScan">GitHub</a> •
  <a href="https://github.com/yourusername/cScan/issues">Issues</a> •
  <a href="https://github.com/yourusername/cScan/discussions">Discussions</a>
</p> 