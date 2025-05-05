from app import create_app
from config import Config
import os
import socket

app = create_app()

def get_ip_address():
    """Get the local IP address of the device"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

if __name__ == '__main__':
    # Create storage directory if it doesn't exist
    if not os.path.exists(Config.STORAGE_PATH):
        os.makedirs(Config.STORAGE_PATH)
    
    # Get local IP address
    ip_address = get_ip_address()
    
    print(f"Starting Termux NAS server...")
    print(f"Storage path: {Config.STORAGE_PATH}")
    print(f"Access your NAS at: http://{ip_address}:{Config.PORT}")
    print(f"Press Ctrl+C to stop the server")
    
    app.run(host=Config.HOST, port=Config.PORT, debug=True)
