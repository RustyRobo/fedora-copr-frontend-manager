<div align="center">

# 🪐 COPR Manager

**A personal, vibe-coded GUI for managing Fedora COPR repositories.**  
Available in two flavors: **GTK4 / Libadwaita** (native GNOME) and **PyQt6** (cross-desktop).

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Platform: Fedora](https://img.shields.io/badge/Platform-Fedora%2043%2B-blue?logo=fedora)](https://getfedora.org/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-yellow?logo=python)](https://python.org)
[![Vibe Coded](https://img.shields.io/badge/Vibe-Coded-ff69b4)](https://github.com)

</div>

---

## What is this?

COPR Manager is a graphical front-end for **Fedora's COPR** (Cool Other Package Repositories) build system. COPR lets community developers publish packages for Fedora that aren't in the official repositories — think bleeding-edge apps, custom kernels, niche tools, or software that hasn't landed in Fedora yet.

The official way to manage COPR repos is through the terminal (`dnf copr enable owner/project`). This project wraps that workflow in a clean, searchable, clickable GUI so you can discover and manage community repositories the same way you'd use GNOME Software or Discover.

---

## Why does this exist?

This is a **vibe-coding project** — built for personal use, out of curiosity and necessity, not to ship a polished product. I wanted a GUI for COPR that:

- Didn't require me to memorize `dnf copr` subcommand syntax
- Let me browse and search repositories visually
- Showed me exactly what packages a repo provides before enabling it
- Was something I could hack on freely

If it's useful to you too — great. **Fork it, break it, fix it, ship it.** That's what GPL is for.

---

## What does it do?

| Feature | Description |
|---|---|
| 🔍 **Search** | Search the COPR registry by keyword via the official `python3-copr` library |
| 🏷️ **Badges** | Auto-detects repo language/desktop tags (Python, Rust, GTK, GNOME, KDE…) |
| ℹ️ **Details** | View description, instructions, homepage, contact, supported Fedora versions, and storage usage |
| ✅ **Enable** | Enable a repo system-wide via `pkexec dnf copr enable` (polkit auth dialog) |
| 🚫 **Disable** | Disable without removing the `.repo` file |
| 🗑️ **Remove** | Fully delete the repo configuration |
| 📦 **Packages** | Browse all packages in an enabled repo with install/remove per-package |
| 🖥️ **Live Terminal** | All DNF operations stream output live into an embedded terminal-style dialog |
| 🔄 **Installed tab** | Lists all COPR repos currently configured on your system (enabled + disabled) |

---

## Two Versions

This repo contains two fully independent implementations that share the same backend:

```
gnome-copr-manager_dist/
│
├── backend/               ← Shared: COPR API, DNF, validation, preview
│   ├── copr.py            ← python3-copr search wrapper
│   ├── dnf_manager.py     ← DNF + pkexec operations
│   ├── preview.py         ← dnf --assumeno dry-run parser
│   ├── validation.py      ← Input sanitization (allowlist regex)
│   └── system.py          ← Fedora version detection
│
├── ui/                    ← PyQt6 frontend
│   ├── main_window.py
│   ├── repo_details.py
│   ├── packages_window.py
│   ├── terminal_dialog.py
│   └── styles.py
│
├── main.py                ← PyQt6 entry point
│
└── GTKVersion/
    └── gnome-copr-manager_dist-gtk/
        ├── backend/       ← Mirror of shared backend
        ├── window.py      ← GTK4 + Libadwaita frontend (single file)
        └── main.py        ← GTK entry point
```

### Qt Version (PyQt6)
- Runs on any desktop (GNOME, KDE, XFCE, Hyprland…)
- Standard Qt window chrome
- Runs: `python3 main.py` from the project root

### GTK Version (GTK4 + Libadwaita)
- Native GNOME look and feel
- `AdwActionRow`, `AdwViewSwitcher`, `AdwPreferencesGroup`, `Adw.MessageDialog`
- Runs: `python3 main.py` from `GTKVersion/gnome-copr-manager_dist-gtk/`

---

## Security Model

> This application runs `pkexec` (polkit) to invoke DNF with elevated privileges. Calling system package managers with user-supplied input is inherently sensitive — here's exactly how the attack surface is handled.

### Allowlist Input Validation (`backend/validation.py`)

Every external string — from COPR API results, from `dnf copr list` output, from the user search box — passes through a strict allowlist regex **before it touches any subprocess call**.

| Input type | Pattern | Example blocked input |
|---|---|---|
| Owner name | `^@?[a-zA-Z0-9][a-zA-Z0-9._-]{0,98}$` | `--enablerepo=evil`, `../../etc` |
| Project name | `^[a-zA-Z0-9][a-zA-Z0-9._+-]{0,98}$` | `evil; rm -rf /` |
| Package name | `^[a-zA-Z0-9][a-zA-Z0-9._+-]{0,254}$` | `--assumeyes --security` |
| Hostname | DNS-safe only | `evil.com/../../` |
| Search query | Printable, max 200 chars | Control characters, null bytes |

Validation errors cause the operation to **fail safely** with a user-visible error dialog — never silently pass through.

### No Shell Injection (`shell=False`)

All `subprocess` calls use list form (never string + `shell=True`):

```python
# Safe — each token is a separate argument, no shell parsing
cmd = ["pkexec", "dnf", "copr", "enable", "-y", repo_slug]
subprocess.run(cmd, ...)

# Never this
subprocess.run(f"pkexec dnf copr enable -y {repo_slug}", shell=True)  # ❌
```

### Privilege Scope

- `pkexec` is used only for the four DNF operations that require root: `copr enable`, `copr disable`, `copr remove`, `install`, `remove`
- Read-only operations (`repoquery`, `repolist`, `rpm -q`) run as the current user — no unnecessary elevation
- The application itself **never runs as root**

### UI Escaping

- **Qt version**: All COPR API strings rendered in `QLabel` are passed through `html.escape()`. Description and instructions fields are set to `Qt.TextFormat.PlainText` to prevent Qt's HTML renderer from interpreting them at all.
- **GTK version**: Repo data displayed in `Adw.ActionRow` subtitles is wrapped in `GLib.markup_escape_text()`.

---

## Requirements

### System packages (install via `dnf`)

```bash
# Qt version
sudo dnf install python3-pyqt6 python3-copr

# GTK version
sudo dnf install python3-gobject gtk4 libadwaita python3-copr
```

### Python packages

```bash
pip install PyQt6   # if not using the system package
```

`python3-copr` is best installed via `dnf` since it's a system-integrated package.

---

## Running

```bash
# Qt version
cd gnome-copr-manager_dist/
python3 main.py

# GTK version
cd gnome-copr-manager_dist/GTKVersion/gnome-copr-manager_dist-gtk/
python3 main.py
```

## Installing system-wide (Qt version)

```bash
sudo ./install.sh
# Installs to /opt, creates launcher + .desktop entry
```

```bash
sudo ./uninstall.sh
# Removes everything install.sh placed
```

---

## Fork It. Please.

This is a personal vibe-coding project, not a maintained product. The code is yours under GPLv3. That means:

- ✅ Use it for anything
- ✅ Modify it however you want
- ✅ Distribute your version
- ✅ Build something better from it
- ⚠️ Keep the license and credit the original if you redistribute

Ideas to take it further:

- [ ] Flatpak packaging
- [ ] `copr-cli` integration for authenticated operations (enable for specific chroots)
- [ ] Copr project creation from the UI
- [ ] Notifications when packages in enabled repos update
- [ ] Per-repo package changelogs
- [ ] Dark/light mode toggle
- [ ] Search history / favorites

---

## License

**GNU General Public License v3.0 or later**

```
Copyright (C) 2026  elyssa

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
```

See [LICENSE](LICENSE) for the full license text.
