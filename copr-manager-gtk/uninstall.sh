#!/bin/bash
set -e

# Check for root
if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root (sudo ./uninstall.sh)"
  exit 1
fi

echo "Removing application files..."
rm -rf /opt/gnome-copr-manager

echo "Removing launcher..."
rm -f /usr/local/bin/gnome-copr-manager

echo "Removing desktop entry..."
rm -f /usr/share/applications/com.github.elyssa.gnome-copr-manager.desktop

echo "Updating desktop database..."
update-desktop-database /usr/share/applications/

echo "Uninstallation complete."
