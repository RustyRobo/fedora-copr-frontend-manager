#!/bin/bash
set -e

# Check for root
if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root (sudo ./install.sh)"
  exit 1
fi

echo "Installing dependencies..."
dnf install -y python3-pyqt6 python3-copr dnf-plugins-core polkit

echo "Creating application directory..."
mkdir -p /opt/copr-manager-qt

echo "Copying files..."
cp -r main.py window_old.py backend ui /opt/copr-manager-qt/
chmod -R 755 /opt/copr-manager-qt/
# Recursively copy backend and ui, main.py window_old.py

# Create launcher script
echo "Creating launcher..."
cat <<EOF > /usr/local/bin/copr-manager-qt
#!/bin/bash
cd /opt/copr-manager-qt
exec python3 main.py "\$@"
EOF

chmod +x /usr/local/bin/copr-manager-qt

# Install Desktop File
echo "Installing desktop entry..."
cat <<EOF > /usr/share/applications/com.github.elyssa.copr-manager-qt.desktop
[Desktop Entry]
Type=Application
Name=CoprManagerQT
Comment=Manage Fedora COPR Repositories
Exec=/usr/local/bin/copr-manager-qt
Icon=system-software-install
Terminal=false
Categories=System;Settings;PackageManager;
EOF

# Update desktop database
update-desktop-database /usr/share/applications/

echo "Installation complete! You can run 'copr-manager-qt' or find it in your applications menu."
