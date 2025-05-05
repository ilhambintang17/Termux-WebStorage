# Termux-WebStorage

A lightweight web-based file server for Termux on Android. Access and manage your Termux files from any device on your local network through a modern, responsive web interface with features like file upload/download, preview, sharing, and user authentication.

## Features

- **File Management**: Browse, upload, download, rename, and delete files and folders
- **File Preview**: Preview images, videos, audio, and text files directly in the browser
- **File Sharing**: Share files with others using temporary links
- **Search**: Quickly find files by name
- **Authentication**: Secure your files with user authentication
- **Responsive UI**: Modern interface that works on mobile and desktop
- **Dark/Light Mode**: Choose your preferred theme
- **Storage Monitoring**: Keep track of your storage usage
- **Performance Optimization**: Special handling for folders with large numbers of files
- **Fallback Mechanisms**: Works even without optional dependencies
- **Configuration**: Customize settings to your needs
- **Termux Home Storage**: Store files in Termux home directory at `/data/data/com.termux/files/home/nasmux`

## Requirements

- Android device with Termux installed
- Internet connection for initial setup
- At least 100MB of free storage space

## Installation

1. Install Termux from [F-Droid](https://f-droid.org/packages/com.termux/) (recommended) or [Google Play Store](https://play.google.com/store/apps/details?id=com.termux)

2. Open Termux and run the following commands:

```bash
# Update package repositories
pkg update -y

# Install Git
pkg install -y git

# Clone the repository
git clone https://github.com/ilhambintang17/Termux-WebStorage.git

# Navigate to the project directory
cd Termux-WebStorage

# Make the installation script executable
chmod +x install.sh

# Run the installation script
./install.sh
```

3. During installation, you will be prompted to:
   - Choose whether to use libmagic (for better file type detection) or fallback mode
   - Grant storage permission to Termux (necessary for accessing your device's storage)

4. The installer will create a directory at `/data/data/com.termux/files/home/nasmux` where all your NAS files will be stored.

5. Follow the on-screen instructions to complete the installation.

## Usage

### Starting the WebStorage Server

```bash
# Using the shortcut (recommended)
termux-webstorage

# Or navigate to the project directory and run
cd Termux-WebStorage
python run.py
```

The server will start and display the URL you can use to access your WebStorage from other devices on the same network.

### Accessing Your WebStorage

1. On any device connected to the same network, open a web browser
2. Enter the URL displayed when starting the server (e.g., http://192.168.1.100:5000)
3. Log in with the default credentials:
   - Username: `admin`
   - Password: `admin`
4. **Important**: Change the default password after logging in

### File Management

- **Upload Files**: Click the "Upload" button and select files or drag and drop
- **Create Folders**: Click "New Folder" to create a new directory
- **Navigate**: Click on folders to browse their contents
- **Download**: Click the download button next to a file
- **Preview**: Click on a file to preview it (if supported)
- **Rename/Delete**: Use the options menu (three dots) next to each file

### Sharing Files

1. Navigate to the file you want to share
2. Click on the file to open the preview
3. Click "Create Share Link"
4. Copy the generated link and share it with others

### Changing Themes

- Click on the "Theme" dropdown in the navigation bar
- Select "Light" or "Dark" mode

## Configuration

You can customize the application by editing the `.env` file in the project directory:

```
SECRET_KEY=your_secret_key
AUTH_REQUIRED=True
MAX_UPLOAD_SIZE=104857600
SHARE_LINK_EXPIRY=7
DEFAULT_THEME=light
STORAGE_PATH=/data/data/com.termux/files/home/nasmux
```

- `SECRET_KEY`: A secret key for session security (automatically generated)
- `AUTH_REQUIRED`: Set to `True` to require login, `False` to allow public access
- `MAX_UPLOAD_SIZE`: Maximum file upload size in bytes (default: 100MB)
- `SHARE_LINK_EXPIRY`: Number of days before share links expire (0 for no expiry)
- `DEFAULT_THEME`: Default theme for new users (`light` or `dark`)
- `STORAGE_PATH`: Path to the directory where files will be stored

## Performance Tips

### Handling Large Directories

For folders with hundreds of files (like video collections):
- The system automatically uses optimized listing methods for better performance
- If you experience slow loading in the web UI, try using the search function to find specific files

## Security Considerations

- Change the default admin password immediately after installation
- If exposing your NAS to the internet, use a secure VPN or reverse proxy with HTTPS
- Regularly update the application and Termux packages
- Be cautious about what files you share and with whom

## Troubleshooting

### Server Won't Start

```bash
# Check if Python and dependencies are installed correctly
pip list

# Verify the storage directory exists and is writable
ls -la $STORAGE_PATH

# Check for error messages in the console output
```

### File Type Detection Issues

If you're having issues with file type detection (incorrect icons or MIME types):

```bash
# Option 1: Install libmagic
./install.sh
# Then select option 1 when prompted

# Option 2: Use fallback mode
./install.sh
# Then select option 2 when prompted
```

### Can't Access from Other Devices

```bash
# Check if your device is on the same network
# Verify the IP address displayed when starting the server
# Ensure no firewall is blocking the connection
# Try accessing the server from the device itself using 127.0.0.1:5000
```

### Upload Issues

```bash
# Check the MAX_UPLOAD_SIZE setting in .env
# Ensure you have enough storage space available
# Check file permissions in the storage directory
```

## Advanced Usage

### Running in the Background

To keep the server running when you close Termux:

```bash
# Start the server in the background
nohup python run.py > /dev/null 2>&1 &
```

### Automatic Startup

You can configure Termux to start the NAS server automatically when it opens:

1. Edit the Termux startup script:

```bash
nano ~/.bashrc
```

2. Add the following line at the end:

```bash
cd ~/Termux-WebStorage && python run.py
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Bootstrap](https://getbootstrap.com/) - UI framework
- [Termux](https://termux.com/) - Android terminal emulator

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
