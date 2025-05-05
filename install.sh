#!/bin/bash

# Termux-WebStorage Installation Script

echo "====================================="
echo "Termux-WebStorage Installation"
echo "====================================="
echo

# Check if running in Termux
if [ ! -d "/data/data/com.termux" ]; then
    echo "Error: This script must be run in Termux on Android."
    exit 1
fi

# Function to handle errors
handle_error() {
    echo "Error: $1"
    echo "Installation failed. Please check the error message above."
    exit 1
}

# Update package repositories
echo "[1/8] Updating package repositories..."
pkg update -y || handle_error "Failed to update package repositories"

# Install required packages
echo "[2/8] Installing required packages..."
pkg install -y python python-pip file || handle_error "Failed to install required packages"

# Ask about libmagic installation
echo "[3/8] File type detection setup..."
echo "Termux NAS can use libmagic for better file type detection, but it's optional."
echo "1. Install libmagic (recommended, better file type detection)"
echo "2. Use fallback mode (no libmagic, uses Python's mimetypes module)"
read -p "Choose an option [1/2] (default: 1): " libmagic_choice
libmagic_choice=${libmagic_choice:-1}

if [ "$libmagic_choice" = "1" ]; then
    echo "Installing libmagic..."
    pkg install -y libmagic || echo "Warning: libmagic installation failed, will use fallback mode"

    # Install Python dependencies including python-magic
    echo "[4/8] Installing Python dependencies with libmagic support..."
    pip install -r requirements.txt || handle_error "Failed to install Python dependencies"

    # Create a symlink to help Python find libmagic
    if [ -f "/data/data/com.termux/files/usr/lib/libmagic.so.1" ]; then
        ln -sf /data/data/com.termux/files/usr/lib/libmagic.so.1 /data/data/com.termux/files/usr/lib/libmagic.so
        echo "Symlink created for libmagic."
    else
        echo "Warning: File libmagic.so.1 not found. File type detection may not work correctly."
    fi
elif [ "$libmagic_choice" = "2" ]; then
    echo "Using fallback mode (without libmagic)..."

    # Install Python dependencies except python-magic
    echo "[4/8] Installing Python dependencies without libmagic..."
    pip install -r requirements.txt || handle_error "Failed to install Python dependencies"
    pip uninstall -y python-magic

    echo "Fallback mode activated. Using Python's mimetypes module for file type detection."
else
    echo "Invalid choice. Using default (libmagic)."
    echo "[4/8] Installing Python dependencies..."
    pip install -r requirements.txt || handle_error "Failed to install Python dependencies"
fi

# Request storage permission and set up storage directory
echo "[5/8] Setting up storage directory..."
echo "Requesting storage permission for Termux..."
termux-setup-storage

# Wait for user to grant permission
echo "Please grant storage permission in the Android dialog that appears."
echo "Press Enter after granting permission..."
read -p ""

# Create NAS directory in Termux home
echo "Creating NAS directory in Termux home..."
mkdir -p /data/data/com.termux/files/home/nasmux

# Set storage path
STORAGE_PATH="/data/data/com.termux/files/home/nasmux"

# Check if directory was created successfully
if [ ! -d "$STORAGE_PATH" ]; then
    echo "Warning: Could not create directory in Termux home."
    echo "Creating fallback directory in Termux home..."
    STORAGE_PATH="$HOME/storage/nasmux"
    mkdir -p "$STORAGE_PATH" || handle_error "Failed to create storage directory"
fi

echo "Storage directory created successfully at $STORAGE_PATH"

# Generate a random secret key
echo "[6/8] Generating configuration..."
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(16))")

# Create .env file
cat > .env << EOF
SECRET_KEY=${SECRET_KEY}
AUTH_REQUIRED=True
MAX_UPLOAD_SIZE=104857600
SHARE_LINK_EXPIRY=7
DEFAULT_THEME=light
STORAGE_PATH=${STORAGE_PATH}
EOF

# Set up Termux:API for easier access (optional)
echo "[7/8] Setting up Termux shortcuts..."
mkdir -p ~/bin

# Create shortcut script regardless of Termux:API
cat > ~/bin/termux-webstorage << EOF
#!/bin/bash
cd $(pwd)
python run.py
EOF

chmod +x ~/bin/termux-webstorage

echo "Shortcut created: You can now start the WebStorage by typing 'termux-webstorage'"

# Check if Termux:API is installed and offer additional features
if [ -d "/data/data/com.termux.api" ]; then
    pkg install -y termux-api
    echo "Termux:API installed. Additional features enabled."
else
    echo "Note: For additional features, you can install Termux:API from F-Droid."
fi

# Final instructions
echo "[8/8] Installation completed!"
echo
echo "====================================="
echo "Termux-WebStorage has been installed successfully!"
echo "====================================="
echo
echo "To start the WebStorage server:"
echo "  cd $(pwd)"
echo "  python run.py"
echo
echo "Or simply type:"
echo "  termux-webstorage"
echo
echo "The default login credentials are:"
echo "  Username: admin"
echo "  Password: admin"
echo
echo "IMPORTANT: Please change the default password after logging in."
echo "====================================="
echo "Enjoy your personal NAS on Termux!"
echo "====================================="
