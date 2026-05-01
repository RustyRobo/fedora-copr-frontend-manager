#!/bin/bash
set -e

# Check for root
if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root (sudo ./install.sh)"
  exit 1
fi

echo "Installing dependencies..."
dnf install -y python3-gobject gtk4 libadwaita python3-copr dnf-plugins-core polkit

echo "Creating application directory..."
mkdir -p /opt/gnome-copr-manager

echo "Copying files..."
cp -r main.py window.py backend ui /opt/gnome-copr-manager/
# Recursively copy backend and ui, main.py window.py

# Create launcher script
echo "Creating launcher..."
cat <<EOF > /usr/local/bin/gnome-copr-manager
#!/bin/bash
cd /opt/gnome-copr-manager
exec python3 main.py "\$@"
EOF

chmod +x /usr/local/bin/gnome-copr-manager

# Install Desktop File
echo "Installing desktop entry..."
cat <<EOF > /usr/share/applications/com.github.elyssa.gnome-copr-manager.desktop
[Desktop Entry]
Type=Application
Name=COPR Manager
Comment=Manage Fedora COPR Repositories
Exec=/usr/local/bin/gnome-copr-manager
Icon=system-software-install
Terminal=false
Categories=System;Settings;PackageManager;
EOF

# Update desktop database
update-desktop-database /usr/share/applications/

echo "Installation complete! You can run 'gnome-copr-manager' or find it in your applications menu."
