from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort, jsonify, Response
from flask_login import login_required, current_user
from app import db
from app.files.utils import (
    get_file_info, get_storage_info, create_thumbnail, create_share_link,
    search_files, sanitize_path, get_system_info, read_file_in_chunks,
    is_potentially_dangerous_file, get_directory_contents_with_ls
)
from app.auth.models import SharedLink
from werkzeug.utils import secure_filename
import os
from app.auth.models import get_utc_now
import mimetypes
# Try to import magic, but provide fallback if not available
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
import shutil

files = Blueprint('files', __name__)

@files.route('/')
@files.route('/browse')
@files.route('/browse/<path:subpath>')
@login_required
def index(subpath=''):
    # Sanitize the path to prevent directory traversal
    subpath = sanitize_path(subpath)

    # Get the full path
    storage_path = current_app.config['STORAGE_PATH']
    current_path = os.path.join(storage_path, subpath)

    # Check if path exists and is a directory
    if not os.path.exists(current_path):
        flash('Directory not found', 'danger')
        return redirect(url_for('files.index'))

    if not os.path.isdir(current_path):
        # If it's a file, redirect to preview
        return redirect(url_for('files.preview', subpath=subpath))

    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)  # Default 50 items per page

    # Limit per_page to reasonable values
    per_page = max(10, min(per_page, 100))  # Between 10 and 100

    # Try to get directory contents using ls command first (faster for large directories)
    all_items = get_directory_contents_with_ls(current_path)

    # Fallback to os.listdir if ls command fails
    if all_items is None:
        all_items = []
        try:
            for item in os.listdir(current_path):
                # Skip hidden files
                if item.startswith('.'):
                    continue

                item_path = os.path.join(current_path, item)
                relative_path = os.path.join(subpath, item) if subpath else item
                all_items.append(get_file_info(item_path, relative_path))
        except Exception as e:
            current_app.logger.error(f"Error listing directory: {e}")
            flash(f"Error listing directory: {str(e)}", 'danger')
            return redirect(url_for('files.index'))
    else:
        # Add relative path to each item from ls command
        for item in all_items:
            item['path'] = os.path.join(subpath, item['name']) if subpath else item['name']

    # Sort items: directories first, then by name
    all_items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))

    # Calculate pagination
    total_items = len(all_items)
    total_pages = (total_items + per_page - 1) // per_page  # Ceiling division

    # Ensure page is within valid range
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1

    # Get the items for the current page
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_items)
    items = all_items[start_idx:end_idx]

    # Get storage info
    storage_info = get_storage_info()

    # Breadcrumb navigation
    breadcrumbs = []
    if subpath:
        parts = subpath.split('/')
        path_so_far = ''
        breadcrumbs.append({'name': 'Home', 'path': ''})
        for i, part in enumerate(parts):
            path_so_far = os.path.join(path_so_far, part)
            breadcrumbs.append({'name': part, 'path': path_so_far})
    else:
        breadcrumbs.append({'name': 'Home', 'path': ''})

    # Pagination info
    pagination = {
        'page': page,
        'per_page': per_page,
        'total_items': total_items,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'showing_start': start_idx + 1 if total_items > 0 else 0,
        'showing_end': end_idx,
    }

    return render_template('files/browser.html',
                          items=items,
                          current_path=subpath,
                          breadcrumbs=breadcrumbs,
                          storage_info=storage_info,
                          pagination=pagination,
                          total_items=total_items)

@files.route('/preview/<path:subpath>')
@login_required
def preview(subpath):
    # Sanitize the path to prevent directory traversal
    subpath = sanitize_path(subpath)

    # Get the full path
    storage_path = current_app.config['STORAGE_PATH']
    file_path = os.path.join(storage_path, subpath)

    # Check if file exists
    if not os.path.exists(file_path) or os.path.isdir(file_path):
        flash('File not found', 'danger')
        return redirect(url_for('files.index'))

    # Get file info
    file_info = get_file_info(file_path, subpath)

    # Breadcrumb navigation
    breadcrumbs = []
    parts = subpath.split('/')
    path_so_far = ''
    breadcrumbs.append({'name': 'Home', 'path': ''})
    for i, part in enumerate(parts[:-1]):
        path_so_far = os.path.join(path_so_far, part)
        breadcrumbs.append({'name': part, 'path': path_so_far})
    breadcrumbs.append({'name': parts[-1], 'path': subpath})

    # Check if there's an existing share link
    share_link = SharedLink.query.filter_by(file_path=subpath, user_id=current_user.id).first()

    return render_template('files/preview.html',
                          file=file_info,
                          breadcrumbs=breadcrumbs,
                          share_link=share_link)

@files.route('/download/<path:subpath>')
@login_required
def download(subpath):
    # Sanitize the path to prevent directory traversal
    subpath = sanitize_path(subpath)

    # Get the full path
    storage_path = current_app.config['STORAGE_PATH']
    file_path = os.path.join(storage_path, subpath)

    # Check if file exists
    if not os.path.exists(file_path) or os.path.isdir(file_path):
        flash('File not found', 'danger')
        return redirect(url_for('files.index'))

    # Get file size and name
    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)

    # Get file type
    if MAGIC_AVAILABLE:
        try:
            mime = magic.Magic(mime=True)
            file_type = mime.from_file(file_path)
        except:
            file_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
    else:
        # Fallback to mimetypes if magic is not available
        file_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'

    # Check for Range header to support resumable downloads
    range_header = request.headers.get('Range', None)

    # Default chunk size (1MB - optimized for mobile networks)
    chunk_size = 1024 * 1024

    # If no range header, send entire file with optimized streaming
    if not range_header:
        # Use our optimized file reading function
        def generate():
            yield from read_file_in_chunks(file_path, chunk_size=chunk_size)

        response = Response(generate(), mimetype=file_type)
        response.headers['Content-Disposition'] = f'attachment; filename="{file_name}"'
        response.headers['Content-Length'] = str(file_size)
        response.headers['Accept-Ranges'] = 'bytes'

        # Add security headers to prevent Chrome warnings
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = "default-src 'self'"

        # For potentially dangerous files, set the correct content type
        if is_potentially_dangerous_file(file_name):
            response.headers['Content-Type'] = 'application/octet-stream'
            # Add header to indicate this is a safe download
            response.headers['X-Download-Options'] = 'noopen'

        return response

    # Parse range header
    ranges = range_header.replace('bytes=', '').split(',')
    range_tuple = ranges[0].split('-')

    # Get start and end positions
    range_start = int(range_tuple[0]) if range_tuple[0] else 0
    range_end = int(range_tuple[1]) if len(range_tuple) > 1 and range_tuple[1] else file_size - 1

    # Ensure range is valid
    if range_start >= file_size:
        # Return 416 Range Not Satisfiable
        return Response(status=416)

    # Adjust end if it's beyond file size
    if range_end >= file_size:
        range_end = file_size - 1

    # Calculate content length
    content_length = range_end - range_start + 1

    # Create partial response using our optimized file reading function
    def generate_partial():
        yield from read_file_in_chunks(file_path, chunk_size=chunk_size, start_pos=range_start, end_pos=range_end)

    response = Response(generate_partial(), mimetype=file_type, status=206)
    response.headers['Content-Disposition'] = f'attachment; filename="{file_name}"'
    response.headers['Content-Length'] = str(content_length)
    response.headers['Content-Range'] = f'bytes {range_start}-{range_end}/{file_size}'
    response.headers['Accept-Ranges'] = 'bytes'

    # Add security headers to prevent Chrome warnings
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "default-src 'self'"

    # For potentially dangerous files, set the correct content type
    if is_potentially_dangerous_file(file_name):
        response.headers['Content-Type'] = 'application/octet-stream'
        # Add header to indicate this is a safe download
        response.headers['X-Download-Options'] = 'noopen'

    return response

@files.route('/thumbnail/<path:subpath>')
@login_required
def thumbnail(subpath):
    # Sanitize the path to prevent directory traversal
    subpath = sanitize_path(subpath)

    # Get the full path
    storage_path = current_app.config['STORAGE_PATH']
    file_path = os.path.join(storage_path, subpath)

    # Check if file exists
    if not os.path.exists(file_path) or os.path.isdir(file_path):
        abort(404)

    # Get file type
    if MAGIC_AVAILABLE:
        try:
            mime = magic.Magic(mime=True)
            file_type = mime.from_file(file_path)
        except:
            file_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
    else:
        # Fallback to mimetypes if magic is not available
        file_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'

    # Only create thumbnails for images
    if not file_type.startswith('image/'):
        abort(400)

    # Create thumbnail
    thumb_io = create_thumbnail(file_path)
    if not thumb_io:
        abort(500)

    response = Response(thumb_io.getvalue(), mimetype=file_type)

    # Add security headers to prevent Chrome warnings
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "default-src 'self'"

    return response

@files.route('/upload', methods=['POST'])
@login_required
def upload():
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    # If user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Get the target directory
    target_dir = request.form.get('path', '')
    target_dir = sanitize_path(target_dir)

    # Get the full path
    storage_path = current_app.config['STORAGE_PATH']
    upload_path = os.path.join(storage_path, target_dir)

    # Check if directory exists
    if not os.path.exists(upload_path) or not os.path.isdir(upload_path):
        return jsonify({'error': 'Directory not found'}), 400

    # Save the file
    filename = secure_filename(file.filename)
    file_path = os.path.join(upload_path, filename)
    file.save(file_path)

    # Get file info
    relative_path = os.path.join(target_dir, filename) if target_dir else filename
    file_info = get_file_info(file_path, relative_path)

    return jsonify({'success': True, 'file': file_info})

@files.route('/create_folder', methods=['POST'])
@login_required
def create_folder():
    # Get folder name and path
    folder_name = request.form.get('folder_name', '')
    target_dir = request.form.get('path', '')

    # Validate folder name
    if not folder_name or '/' in folder_name or '\\' in folder_name:
        flash('Invalid folder name', 'danger')
        return redirect(url_for('files.index', subpath=target_dir))

    # Sanitize the path to prevent directory traversal
    target_dir = sanitize_path(target_dir)

    # Get the full path
    storage_path = current_app.config['STORAGE_PATH']
    parent_path = os.path.join(storage_path, target_dir)
    new_folder_path = os.path.join(parent_path, folder_name)

    # Check if directory exists
    if not os.path.exists(parent_path) or not os.path.isdir(parent_path):
        flash('Parent directory not found', 'danger')
        return redirect(url_for('files.index'))

    # Check if folder already exists
    if os.path.exists(new_folder_path):
        flash('Folder already exists', 'danger')
        return redirect(url_for('files.index', subpath=target_dir))

    # Create the folder
    os.makedirs(new_folder_path)
    flash('Folder created successfully', 'success')

    if target_dir:
        return redirect(url_for('files.index', subpath=target_dir))
    else:
        return redirect(url_for('files.index'))

@files.route('/delete/<path:subpath>', methods=['POST'])
@login_required
def delete(subpath):
    # Sanitize the path to prevent directory traversal
    subpath = sanitize_path(subpath)

    # Get the full path
    storage_path = current_app.config['STORAGE_PATH']
    path = os.path.join(storage_path, subpath)

    # Check if path exists
    if not os.path.exists(path):
        flash('Path not found', 'danger')
        return redirect(url_for('files.index'))

    # Get parent directory
    parent_dir = os.path.dirname(subpath)

    # Delete the file or directory
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
            flash('Directory deleted successfully', 'success')
        else:
            os.remove(path)
            flash('File deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting: {str(e)}', 'danger')

    if parent_dir:
        return redirect(url_for('files.index', subpath=parent_dir))
    else:
        return redirect(url_for('files.index'))

@files.route('/rename/<path:subpath>', methods=['POST'])
@login_required
def rename(subpath):
    # Sanitize the path to prevent directory traversal
    subpath = sanitize_path(subpath)

    # Get the new name
    new_name = request.form.get('new_name', '')

    # Validate new name
    if not new_name or '/' in new_name or '\\' in new_name:
        flash('Invalid name', 'danger')
        return redirect(url_for('files.index', subpath=os.path.dirname(subpath)))

    # Get the full path
    storage_path = current_app.config['STORAGE_PATH']
    old_path = os.path.join(storage_path, subpath)

    # Check if path exists
    if not os.path.exists(old_path):
        flash('Path not found', 'danger')
        return redirect(url_for('files.index'))

    # Get parent directory
    parent_dir = os.path.dirname(subpath)
    parent_path = os.path.join(storage_path, parent_dir)

    # Create new path
    new_path = os.path.join(parent_path, new_name)

    # Check if new path already exists
    if os.path.exists(new_path):
        flash('A file or folder with that name already exists', 'danger')
        return redirect(url_for('files.index', subpath=parent_dir))

    # Rename the file or directory
    try:
        os.rename(old_path, new_path)
        flash('Renamed successfully', 'success')
    except Exception as e:
        flash(f'Error renaming: {str(e)}', 'danger')

    if parent_dir:
        return redirect(url_for('files.index', subpath=parent_dir))
    else:
        return redirect(url_for('files.index'))

@files.route('/share/<path:subpath>', methods=['POST'])
@login_required
def share(subpath):
    # Sanitize the path to prevent directory traversal
    subpath = sanitize_path(subpath)

    # Get the full path
    storage_path = current_app.config['STORAGE_PATH']
    file_path = os.path.join(storage_path, subpath)

    # Check if file exists
    if not os.path.exists(file_path) or os.path.isdir(file_path):
        flash('File not found', 'danger')
        return redirect(url_for('files.index'))

    # Check if there's an existing share link
    share_link = SharedLink.query.filter_by(file_path=subpath, user_id=current_user.id).first()

    if share_link:
        # Update existing share link
        share_link.created_at = get_utc_now()
        expiry_days = current_app.config['SHARE_LINK_EXPIRY']
        if expiry_days > 0:
            # Get current time
            now = get_utc_now()
            # Set to end of day
            expires_at = now.replace(hour=23, minute=59, second=59)
            # Add days using timedelta
            from datetime import timedelta
            expires_at = expires_at + timedelta(days=expiry_days)
            share_link.expires_at = expires_at
        db.session.commit()
        flash('Share link refreshed', 'success')
    else:
        # Create new share link
        create_share_link(current_user.id, subpath)
        flash('Share link created', 'success')

    return redirect(url_for('files.preview', subpath=subpath))

@files.route('/shared/<token>')
def shared_file(token):
    # Find the share link
    share_link = SharedLink.query.filter_by(token=token).first_or_404()

    # Check if the link has expired
    if share_link.expires_at and share_link.expires_at < get_utc_now():
        abort(410)  # Gone

    # Get the file path
    storage_path = current_app.config['STORAGE_PATH']
    file_path = os.path.join(storage_path, share_link.file_path)

    # Check if file exists
    if not os.path.exists(file_path) or os.path.isdir(file_path):
        abort(404)

    # Increment access count
    share_link.access_count += 1
    db.session.commit()

    # Get file info
    file_info = get_file_info(file_path, share_link.file_path)

    return render_template('files/shared.html', file=file_info, share_link=share_link)

@files.route('/shared/<token>/download')
def download_shared(token):
    # Find the share link
    share_link = SharedLink.query.filter_by(token=token).first_or_404()

    # Check if the link has expired
    if share_link.expires_at and share_link.expires_at < get_utc_now():
        abort(410)  # Gone

    # Get the file path
    storage_path = current_app.config['STORAGE_PATH']
    file_path = os.path.join(storage_path, share_link.file_path)

    # Check if file exists
    if not os.path.exists(file_path) or os.path.isdir(file_path):
        abort(404)

    # Increment access count
    share_link.access_count += 1
    db.session.commit()

    # Get file size and name
    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)

    # Get file type
    if MAGIC_AVAILABLE:
        try:
            mime = magic.Magic(mime=True)
            file_type = mime.from_file(file_path)
        except:
            file_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
    else:
        # Fallback to mimetypes if magic is not available
        file_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'

    # Check for Range header to support resumable downloads
    range_header = request.headers.get('Range', None)

    # Default chunk size (1MB - optimized for mobile networks)
    chunk_size = 1024 * 1024

    # If no range header, send entire file with optimized streaming
    if not range_header:
        # Use our optimized file reading function
        def generate():
            yield from read_file_in_chunks(file_path, chunk_size=chunk_size)

        response = Response(generate(), mimetype=file_type)
        response.headers['Content-Disposition'] = f'attachment; filename="{file_name}"'
        response.headers['Content-Length'] = str(file_size)
        response.headers['Accept-Ranges'] = 'bytes'

        # Add security headers to prevent Chrome warnings
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = "default-src 'self'"

        # For potentially dangerous files, set the correct content type
        if is_potentially_dangerous_file(file_name):
            response.headers['Content-Type'] = 'application/octet-stream'
            # Add header to indicate this is a safe download
            response.headers['X-Download-Options'] = 'noopen'

        return response

    # Parse range header
    ranges = range_header.replace('bytes=', '').split(',')
    range_tuple = ranges[0].split('-')

    # Get start and end positions
    range_start = int(range_tuple[0]) if range_tuple[0] else 0
    range_end = int(range_tuple[1]) if len(range_tuple) > 1 and range_tuple[1] else file_size - 1

    # Ensure range is valid
    if range_start >= file_size:
        # Return 416 Range Not Satisfiable
        return Response(status=416)

    # Adjust end if it's beyond file size
    if range_end >= file_size:
        range_end = file_size - 1

    # Calculate content length
    content_length = range_end - range_start + 1

    # Create partial response using our optimized file reading function
    def generate_partial():
        yield from read_file_in_chunks(file_path, chunk_size=chunk_size, start_pos=range_start, end_pos=range_end)

    response = Response(generate_partial(), mimetype=file_type, status=206)
    response.headers['Content-Disposition'] = f'attachment; filename="{file_name}"'
    response.headers['Content-Length'] = str(content_length)
    response.headers['Content-Range'] = f'bytes {range_start}-{range_end}/{file_size}'
    response.headers['Accept-Ranges'] = 'bytes'

    # Add security headers to prevent Chrome warnings
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "default-src 'self'"

    # For potentially dangerous files, set the correct content type
    if is_potentially_dangerous_file(file_name):
        response.headers['Content-Type'] = 'application/octet-stream'
        # Add header to indicate this is a safe download
        response.headers['X-Download-Options'] = 'noopen'

    return response

@files.route('/search')
@login_required
def search():
    query = request.args.get('q', '')

    if not query:
        return redirect(url_for('files.index'))

    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)  # Default 50 items per page

    # Limit per_page to reasonable values
    per_page = max(10, min(per_page, 100))  # Between 10 and 100

    # Search for files
    storage_path = current_app.config['STORAGE_PATH']
    all_results = search_files(query, storage_path)

    # Calculate pagination
    total_items = len(all_results)
    total_pages = (total_items + per_page - 1) // per_page  # Ceiling division

    # Ensure page is within valid range
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1

    # Get the items for the current page
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_items)
    results = all_results[start_idx:end_idx]

    # Pagination info
    pagination = {
        'page': page,
        'per_page': per_page,
        'total_items': total_items,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'showing_start': start_idx + 1 if total_items > 0 else 0,
        'showing_end': end_idx,
    }

    return render_template('files/search.html',
                          query=query,
                          results=results,
                          pagination=pagination,
                          total_items=total_items)

@files.route('/system_info')
@login_required
def system_info():
    """Get system information (CPU, RAM usage)"""
    try:
        # Get system info
        sys_info = get_system_info()
        return jsonify(sys_info)
    except Exception as e:
        current_app.logger.error(f"Error getting system info: {e}")
        return jsonify({
            'cpu_percent': 0,
            'memory_percent': 0,
            'memory_used': 'N/A',
            'memory_total': 'N/A',
            'error': str(e)
        }), 500
