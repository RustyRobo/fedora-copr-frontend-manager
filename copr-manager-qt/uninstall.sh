#!/bin/bash
set -e

# Check for root
if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root (sudo ./uninstall.sh)"
  exit 1
fi

echo "Removing application files..."
rm -rf /opt/copr-manager-qt

echo "Removing launcher..."
rm -f /usr/local/bin/copr-manager-qt

echo "Removing desktop entry..."
rm -f /usr/share/applications/com.github.elyssa.copr-manager-qt.desktop

echo "Updating desktop database..."
update-desktop-database /usr/share/applications/

echo "Uninstallation complete."
