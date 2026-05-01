<div align="center">

# 🪐 copr-manager

**A GUI front-end for managing Fedora COPR repositories.**  
Two independent implementations — pick whichever fits your desktop.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Platform: Fedora](https://img.shields.io/badge/Platform-Fedora%2043%2B-blue?logo=fedora)](https://getfedora.org/)

</div>

---

## Versions

| Folder | Toolkit | Best for |
|---|---|---|
| [`copr-manager-qt/`](copr-manager-qt/) | PyQt6 | Any desktop (KDE, XFCE, Hyprland, GNOME…) |
| [`copr-manager-gtk/`](copr-manager-gtk/) | GTK4 + Libadwaita | GNOME — native look and feel |

Both versions share the same backend (`backend/`) and are functionally identical.  
See each subfolder's `README.md` for full documentation, security details, and install instructions.

## Quick Start

```bash
# Qt version
cd copr-manager-qt/
python3 main.py

# GTK version
cd copr-manager-gtk/
python3 main.py
```

## License

GNU General Public License v3.0 or later — see [LICENSE](LICENSE).
