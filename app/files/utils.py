import os
import shutil
import mimetypes
import re
import subprocess
from datetime import datetime
from flask import current_app
import uuid
from app.auth.models import SharedLink
from app import db
from PIL import Image
from io import BytesIO

# Try to import optional dependencies
try:
    import magic
except ImportError:
    magic = None

try:
    import humanize
except ImportError:
    humanize = None
# No duplicate imports needed

def get_file_info(path, relative_path):
    """Get file information"""
    try:
        stat = os.stat(path)
        file_size = stat.st_size
        modified_time = datetime.fromtimestamp(stat.st_mtime)

        # Get file type
        if magic:
            try:
                mime = magic.Magic(mime=True)
                file_type = mime.from_file(path)
            except:
                file_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        else:
            file_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'

        # Get file icon based on type
        is_dir = os.path.isdir(path)
        if is_dir:
            icon = 'bi-folder'
        else:
            icon = get_file_icon(file_type, path)

        # Format human-readable size
        if humanize:
            size_human = humanize.naturalsize(file_size)
            modified_human = humanize.naturaltime(modified_time)
        else:
            # Simple fallback if humanize is not available
            size_human = format_size(file_size)
            modified_human = modified_time.strftime('%Y-%m-%d %H:%M:%S')

        return {
            'name': os.path.basename(path),
            'path': relative_path,
            'size': file_size,
            'size_human': size_human,
            'modified': modified_time,
            'modified_human': modified_human,
            'type': file_type,
            'icon': icon,
            'is_dir': is_dir
        }
    except (PermissionError, FileNotFoundError) as e:
        # Handle inaccessible files
        current_app.logger.warning(f"Cannot access file {path}: {e}")

        # Create a basic entry with limited information
        is_dir = False
        try:
            is_dir = os.path.isdir(path)
        except:
            pass

        return {
            'name': os.path.basename(path),
            'path': relative_path,
            'size': 0,
            'size_human': '-',
            'modified': datetime.now(),
            'modified_human': 'Unknown',
            'type': 'directory' if is_dir else 'unknown',
            'icon': 'bi-folder' if is_dir else 'bi-file-lock',
            'is_dir': is_dir,
            'inaccessible': True
        }

def format_size(size_bytes):
    """Format bytes to human-readable size (fallback for when humanize is not available)"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.1f} MB"
    else:
        return f"{size_bytes/(1024*1024*1024):.1f} GB"

def get_file_icon(file_type, path):
    """Get appropriate icon for file type"""
    if os.path.isdir(path):
        return 'bi-folder'

    if file_type:
        if file_type.startswith('image/'):
            return 'bi-file-image'
        elif file_type.startswith('video/'):
            return 'bi-file-play'
        elif file_type.startswith('audio/'):
            return 'bi-file-music'
        elif file_type.startswith('text/'):
            return 'bi-file-text'
        elif 'pdf' in file_type:
            return 'bi-file-pdf'
        elif 'zip' in file_type or 'compressed' in file_type or 'archive' in file_type:
            return 'bi-file-zip'
        elif 'word' in file_type or 'document' in file_type:
            return 'bi-file-word'
        elif 'excel' in file_type or 'spreadsheet' in file_type:
            return 'bi-file-excel'
        elif 'powerpoint' in file_type or 'presentation' in file_type:
            return 'bi-file-ppt'

    return 'bi-file'

def get_directory_size(path):
    """Get the size of a directory and its contents"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)
    return total_size

def get_storage_info():
    """Get storage usage information"""
    storage_path = current_app.config['STORAGE_PATH']
    total_size = get_directory_size(storage_path)

    # Get disk usage
    free = 0
    total = 0
    used = total_size

    # Try to get actual disk usage on Linux/Unix/MacOS
    if os.name == 'posix':
        try:
            stat = os.statvfs(storage_path)
            free = stat.f_bavail * stat.f_frsize
            total = stat.f_blocks * stat.f_frsize
            used = (stat.f_blocks - stat.f_bfree) * stat.f_frsize
        except (AttributeError, OSError):
            # statvfs not available or path not accessible
            pass

    # Format sizes
    if humanize:
        total_size_human = humanize.naturalsize(total_size)
        disk_free_human = humanize.naturalsize(free) if free > 0 else 'Unknown'
        disk_total_human = humanize.naturalsize(total) if total > 0 else 'Unknown'
        disk_used_human = humanize.naturalsize(used) if used > 0 else 'Unknown'
    else:
        total_size_human = format_size(total_size)
        disk_free_human = format_size(free) if free > 0 else 'Unknown'
        disk_total_human = format_size(total) if total > 0 else 'Unknown'
        disk_used_human = format_size(used) if used > 0 else 'Unknown'

    # Calculate usage percentage safely
    disk_usage_percent = 0
    if total > 0:
        disk_usage_percent = min((used / total * 100), 100)  # Cap at 100%

    return {
        'total_size': total_size,
        'total_size_human': total_size_human,
        'disk_free': free,
        'disk_free_human': disk_free_human,
        'disk_total': total,
        'disk_total_human': disk_total_human,
        'disk_used': used,
        'disk_used_human': disk_used_human,
        'disk_usage_percent': disk_usage_percent
    }

def create_thumbnail(file_path, max_size=(200, 200)):
    """Create a thumbnail for an image file"""
    try:
        img = Image.open(file_path)
        img.thumbnail(max_size)

        # Save thumbnail to BytesIO object
        thumb_io = BytesIO()
        img.save(thumb_io, format=img.format)
        thumb_io.seek(0)

        return thumb_io
    except Exception as e:
        current_app.logger.error(f"Error creating thumbnail: {e}")
        return None

def get_system_info():
    """Get system information (CPU, RAM usage)"""
    import subprocess
    import re

    # Initialize default values
    cpu_percent = 0
    memory_percent = 0
    memory_used = "0 MB"
    memory_total = "0 MB"

    try:
        # Try multiple methods to get CPU usage and use the most reasonable value
        cpu_values = []

        # Method 1: Use htop
        try:
            cpu_cmd = "htop -C -n1 | grep CPU | awk '{print $3}' | sed 's/[^0-9.]//g'"
            cpu_output = subprocess.check_output(cpu_cmd, shell=True, text=True).strip()
            try:
                value = float(cpu_output)
                if 0 <= value <= 100:
                    cpu_values.append(value)
            except ValueError:
                pass
        except:
            pass

        # Method 2: Alternative htop parsing
        try:
            cpu_cmd = "htop -C -n1 | head -n 3 | tail -n 1 | awk '{print $2}' | sed 's/[^0-9.]//g'"
            cpu_output = subprocess.check_output(cpu_cmd, shell=True, text=True).strip()
            try:
                value = float(cpu_output)
                if 0 <= value <= 100:
                    cpu_values.append(value)
            except ValueError:
                pass
        except:
            pass

        # Method 3: Use ps command
        try:
            cpu_cmd = "ps -o %cpu= -e | awk '{s+=$1} END {print s}'"
            cpu_output = subprocess.check_output(cpu_cmd, shell=True, text=True).strip()
            if cpu_output:
                value = float(cpu_output)
                if 0 <= value <= 400:  # Allow for multi-core systems
                    cpu_values.append(min(value, 100))  # Cap at 100%
        except:
            pass

        # Method 4: Parse /proc/stat
        try:
            with open('/proc/stat', 'r') as f:
                cpu_line = f.readline().strip()
                cpu_values_raw = cpu_line.split()[1:5]
                cpu_total = sum(float(x) for x in cpu_values_raw)
                cpu_idle = float(cpu_values_raw[3])
                value = 100 * (1 - (cpu_idle / cpu_total))
                if 0 <= value <= 100:
                    cpu_values.append(value)
        except:
            pass

        # Choose the most reasonable CPU value
        if cpu_values:
            # Filter out unreasonable values
            reasonable_values = [v for v in cpu_values if 0 <= v <= 100]
            if reasonable_values:
                cpu_percent = round(sum(reasonable_values) / len(reasonable_values), 1)
            else:
                cpu_percent = 0
        else:
            cpu_percent = 0

        # Try to get memory info using free command
        try:
            mem_cmd = "free -m | grep 'Mem:'"
            mem_output = subprocess.check_output(mem_cmd, shell=True, text=True).strip()
            mem_parts = mem_output.split()

            if len(mem_parts) >= 3:
                mem_total = int(mem_parts[1])
                mem_used = int(mem_parts[2])
                memory_percent = (mem_used / mem_total) * 100 if mem_total > 0 else 0
                memory_total = f"{mem_total} MB"
                memory_used = f"{mem_used} MB"
        except:
            # Fallback to /proc/meminfo
            try:
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                    total_match = re.search(r'MemTotal:\s+(\d+)', meminfo)
                    free_match = re.search(r'MemFree:\s+(\d+)', meminfo)
                    buffers_match = re.search(r'Buffers:\s+(\d+)', meminfo)
                    cached_match = re.search(r'Cached:\s+(\d+)', meminfo)

                    if total_match and free_match and buffers_match and cached_match:
                        total = int(total_match.group(1))
                        free = int(free_match.group(1))
                        buffers = int(buffers_match.group(1))
                        cached = int(cached_match.group(1))

                        used = total - free - buffers - cached
                        mem_total = total // 1024  # Convert to MB
                        mem_used = used // 1024    # Convert to MB

                        memory_percent = (mem_used / mem_total) * 100 if mem_total > 0 else 0
                        memory_total = f"{mem_total} MB"
                        memory_used = f"{mem_used} MB"
            except:
                pass
    except Exception as e:
        # If commands fail, return default values
        current_app.logger.error(f"Error getting system info: {e}")

    # Get storage info directly without calling get_storage_info to avoid recursion
    storage_path = current_app.config['STORAGE_PATH']
    storage_used = "0 MB"
    storage_free = "0 MB"
    storage_total = "0 MB"
    storage_percent = 0

    try:
        # Get directory size for NAS files
        total_size = get_directory_size(storage_path)
        storage_used = format_size(total_size)

        # Try to get disk usage using df command (most reliable in Termux)
        try:
            df_cmd = f"df -h {storage_path} | tail -1"
            df_output = subprocess.check_output(df_cmd, shell=True, text=True).strip()
            df_parts = df_output.split()

            if len(df_parts) >= 5:
                storage_total = df_parts[1]
                disk_used = df_parts[2]  # This is total disk usage, not just NAS files
                storage_free = df_parts[3]
                storage_percent = float(df_parts[4].replace('%', ''))
        except:
            # Fallback to statvfs if df fails
            try:
                stat = os.statvfs(storage_path)
                free = stat.f_bavail * stat.f_frsize
                total = stat.f_blocks * stat.f_frsize

                storage_free = format_size(free)
                storage_total = format_size(total)

                # Calculate percentage based on total disk usage
                if total > 0:
                    storage_percent = min(((total - free) / total * 100), 100)
            except:
                # Last resort - just use some default values
                storage_free = "Unknown"
                storage_total = "Unknown"
    except Exception as e:
        current_app.logger.error(f"Error getting storage info: {e}")

    return {
        'cpu_percent': cpu_percent,
        'memory_percent': memory_percent,
        'memory_used': memory_used,
        'memory_total': memory_total,
        'storage_used': storage_used,
        'storage_free': storage_free,
        'storage_total': storage_total,
        'storage_percent': storage_percent
    }

def create_share_link(user_id, file_path, expiry_days=7):
    """Create a share link for a file"""
    token = str(uuid.uuid4())

    # Calculate expiry date
    if expiry_days > 0:
        try:
            # Use timezone-aware datetime if available (Python 3.9+)
            from datetime import timezone
            expires_at = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)
        except (ImportError, AttributeError):
            # Fallback to utcnow for older Python versions
            expires_at = datetime.utcnow().replace(hour=23, minute=59, second=59)

        # Add days to expiry using timedelta
        from datetime import timedelta
        expires_at = expires_at + timedelta(days=expiry_days)
    else:
        expires_at = None

    # Create share link
    share_link = SharedLink(
        user_id=user_id,
        file_path=file_path,
        token=token,
        expires_at=expires_at
    )

    db.session.add(share_link)
    db.session.commit()

    return token

def search_files(query, path):
    """Search for files matching the query"""
    results = []
    query = query.lower()

    try:
        # Try using find command for faster search
        # -iname: case-insensitive name matching
        # -type f: only files
        # -o: logical OR
        # -type d: only directories
        # Use print0 and xargs to handle filenames with spaces
        cmd = f"find '{path}' -type f -iname '*{query}*' -o -type d -iname '*{query}*' | sort"
        output = subprocess.check_output(cmd, shell=True, text=True).strip()

        if not output:
            return []

        # Split by newlines
        file_list = output.split('\n')

        # Process the results
        for item_path in file_list:
            if not item_path or item_path == path:  # Skip empty lines and the root path
                continue

            # Skip hidden files and directories
            basename = os.path.basename(item_path)
            if basename.startswith('.'):
                continue

            # Get relative path
            rel_path = os.path.relpath(item_path, path)

            # Get file info
            try:
                # Try to get detailed file info
                results.append(get_file_info(item_path, rel_path))
            except Exception as file_info_error:
                current_app.logger.error(f"Error getting file info: {file_info_error}")

                # If we can't get file info, create a basic entry
                try:
                    is_dir = os.path.isdir(item_path)
                    size = 0
                    if not is_dir:
                        try:
                            size = os.path.getsize(item_path)
                        except:
                            pass

                    results.append({
                        'name': basename,
                        'path': rel_path,
                        'size': size,
                        'size_human': format_size(size) if size > 0 else '-',
                        'modified': datetime.now(),
                        'modified_human': 'Unknown',
                        'type': 'directory' if is_dir else 'unknown',
                        'icon': 'bi-folder' if is_dir else get_file_icon_by_name(basename),
                        'is_dir': is_dir
                    })
                except Exception as basic_info_error:
                    current_app.logger.error(f"Error creating basic file info: {basic_info_error}")
                    continue

        return results
    except Exception as e:
        current_app.logger.error(f"Error using find command: {e}")

        # Fallback to os.walk if find command fails
        results = []
        try:
            for root, dirs, files in os.walk(path):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]

                # Check directories
                for dir_name in dirs:
                    if query in dir_name.lower():
                        full_path = os.path.join(root, dir_name)
                        rel_path = os.path.relpath(full_path, path)
                        try:
                            results.append(get_file_info(full_path, rel_path))
                        except Exception as dir_error:
                            current_app.logger.error(f"Error getting directory info: {dir_error}")

                # Check files
                for file_name in files:
                    if query in file_name.lower():
                        full_path = os.path.join(root, file_name)
                        rel_path = os.path.relpath(full_path, path)
                        try:
                            results.append(get_file_info(full_path, rel_path))
                        except Exception as file_error:
                            current_app.logger.error(f"Error getting file info: {file_error}")
        except Exception as walk_error:
            current_app.logger.error(f"Error walking directory: {walk_error}")

        return results

def sanitize_path(path):
    """Sanitize and validate a path to prevent directory traversal attacks"""
    # Remove any path traversal attempts
    path = re.sub(r'\.\./', '', path)
    path = re.sub(r'\.\.\\', '', path)
    path = path.lstrip('/')
    path = path.lstrip('\\')

    return path

def is_potentially_dangerous_file(filename):
    """
    Check if a file might be flagged as dangerous by browsers.

    Args:
        filename (str): Name of the file to check

    Returns:
        bool: True if the file might be flagged as dangerous
    """
    dangerous_extensions = (
        # Executable files
        '.exe', '.msi', '.dll', '.bat', '.cmd', '.ps1', '.vbs', '.js', '.jar', '.com',
        # Archive files that might contain executables
        '.zip', '.rar', '.7z', '.tar', '.gz', '.tgz',
        # Other potentially dangerous files
        '.apk', '.app', '.dmg', '.iso', '.bin', '.sh'
    )

    return filename.lower().endswith(dangerous_extensions)

def get_directory_contents_with_ls(path):
    """
    Get directory contents using the 'ls' command for better performance with large directories.

    Args:
        path (str): Path to the directory

    Returns:
        list: List of dictionaries with file information
    """
    try:
        # Use ls -la with a null separator to handle filenames with spaces
        # We'll use two commands:
        # 1. First to get all files and their basic info
        # 2. Second to get file types (for icons)

        # Command 1: Get file listing with details
        # Format: permissions links owner group size date time name
        cmd = f"ls -la --time-style=long-iso '{path}'"
        output = subprocess.check_output(cmd, shell=True, text=True).strip().split('\n')

        # Skip the first line (total) and parse the rest
        items = []
        for line in output[1:]:  # Skip the "total" line
            if not line.strip():
                continue

            # The first 7 fields are fixed format, the rest is the filename
            # We'll split by position rather than by spaces to handle filenames with spaces
            try:
                # Parse permissions field (first 10 characters)
                permissions = line[0:10].strip()
                is_dir = permissions.startswith('d')

                # Find the position where the filename starts
                # This is tricky with spaces, so we'll use a heuristic
                # The format is typically: "permissions links owner group size date time filename"
                parts = line.split(None, 7)  # Split into 8 parts max

                if len(parts) < 7:
                    continue  # Not enough parts

                # Get the size, date, and time
                try:
                    size = int(parts[4])
                except ValueError:
                    size = 0

                date_str = parts[5]
                time_str = parts[6]

                # Get the filename (last part, or everything after the 7th space-delimited field)
                if len(parts) >= 8:
                    name = parts[7]
                else:
                    # If we couldn't split properly, try another approach
                    name = line.split()[-1]

                # Skip . and .. entries
                if name == '.' or name == '..':
                    continue

                # Create a basic file info object
                file_info = {
                    'name': name,
                    'is_dir': is_dir,
                    'size': size,
                    'size_human': format_size(size),
                    'modified': datetime.now(),  # Placeholder
                    'modified_human': f"{date_str} {time_str}",
                    'type': 'directory' if is_dir else mimetypes.guess_type(name)[0] or 'application/octet-stream',
                    'icon': 'bi-folder' if is_dir else get_file_icon_by_name(name)
                }

                items.append(file_info)
            except Exception as e:
                current_app.logger.error(f"Error parsing ls output line: {e}")
                continue

        return items
    except Exception as e:
        current_app.logger.error(f"Error using ls command: {e}")
        # Fallback to os.listdir if ls command fails
        return None

def get_file_icon_by_name(filename):
    """Get file icon based on filename extension"""
    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    if ext in ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'):
        return 'bi-file-image'
    elif ext in ('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'):
        return 'bi-file-play'
    elif ext in ('.mp3', '.wav', '.ogg', '.flac', '.aac'):
        return 'bi-file-music'
    elif ext in ('.txt', '.log', '.md', '.csv'):
        return 'bi-file-text'
    elif ext == '.pdf':
        return 'bi-file-pdf'
    elif ext in ('.zip', '.rar', '.7z', '.tar', '.gz', '.tgz'):
        return 'bi-file-zip'
    elif ext in ('.doc', '.docx', '.rtf'):
        return 'bi-file-word'
    elif ext in ('.xls', '.xlsx'):
        return 'bi-file-excel'
    elif ext in ('.ppt', '.pptx'):
        return 'bi-file-ppt'
    else:
        return 'bi-file'

def read_file_in_chunks(file_path, chunk_size=1024*1024, start_pos=0, end_pos=None):
    """
    Read a file in chunks with optimized buffering for better performance.

    Args:
        file_path (str): Path to the file
        chunk_size (int): Size of each chunk in bytes
        start_pos (int): Starting position for reading
        end_pos (int): Ending position for reading (None for end of file)

    Yields:
        bytes: Chunks of file data
    """
    # Calculate total bytes to read
    file_size = os.path.getsize(file_path)

    if end_pos is None:
        end_pos = file_size - 1

    # Ensure positions are valid
    start_pos = max(0, min(start_pos, file_size - 1))
    end_pos = max(start_pos, min(end_pos, file_size - 1))

    # Calculate total bytes to read
    bytes_to_read = end_pos - start_pos + 1

    # Open file with a larger buffer size for better performance
    with open(file_path, 'rb', buffering=chunk_size*2) as f:
        f.seek(start_pos)
        bytes_read = 0

        while bytes_read < bytes_to_read:
            # Adjust chunk size for the last chunk
            current_chunk_size = min(chunk_size, bytes_to_read - bytes_read)
            chunk = f.read(current_chunk_size)

            if not chunk:
                break

            bytes_read += len(chunk)
            yield chunk
