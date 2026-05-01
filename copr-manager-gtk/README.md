# GNOME COPR Manager

A native GNOME application for managing Fedora COPR repositories.

## Installation

### Prerequisites
Reference `install.sh` for exact packages, but generally requires:
- Fedora Linux (Optimized for Fedora 43+)
- python3-gobject
- gtk4
- libadwaita
- python3-copr

### Easy Install
Run the included installer script with root privileges:

```bash
sudo ./install.sh
```

This will:
1. Install necessary system dependencies.
2. Install the application to `/opt/gnome-copr-manager`.
3. Create a launcher `gnome-copr-manager`.
4. Add a desktop entry so it appears in your app grid.

### Uninstall
To remove the application:

```bash
sudo ./uninstall.sh
```

## Manual Usage
You can also run the application without installing:

```bash
python3 main.py
```

## Features
- **Search**: Find COPR repositories easily.
- **Manage**: Enable/Disable repositories with a click.
- **Install**: Browse and install packages from repositories.
- **Inspect**: View detailed metadata, supported versions, and badges.

## License
MIT / GPLv3 (See source headers)
