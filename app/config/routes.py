from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.files.utils import get_storage_info
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, IntegerField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange
import os
import json

config = Blueprint('config', __name__, url_prefix='/config')

class ConfigForm(FlaskForm):
    auth_required = BooleanField('Authentication Required')
    max_upload_size = IntegerField('Max Upload Size (MB)', validators=[NumberRange(min=1, max=51200)])
    share_link_expiry = IntegerField('Share Link Expiry (days)', validators=[NumberRange(min=0, max=365)])
    default_theme = SelectField('Default Theme', choices=[('light', 'Light'), ('dark', 'Dark')])
    submit = SubmitField('Save Configuration')

@config.route('/', methods=['GET', 'POST'])
@login_required
def index():
    # Only admin can access configuration
    if not current_user.is_admin:
        flash('You do not have permission to access configuration', 'danger')
        return redirect(url_for('files.index'))

    form = ConfigForm()

    if form.validate_on_submit():
        # Update configuration
        config_data = {
            'AUTH_REQUIRED': form.auth_required.data,
            'MAX_UPLOAD_SIZE': form.max_upload_size.data * 1024 * 1024,  # Convert MB to bytes
            'SHARE_LINK_EXPIRY': form.share_link_expiry.data,
            'DEFAULT_THEME': form.default_theme.data
        }

        # Save to .env file
        with open(os.path.join(current_app.root_path, '..', '.env'), 'w') as f:
            for key, value in config_data.items():
                f.write(f"{key}={value}\n")

        flash('Configuration saved successfully', 'success')
        return redirect(url_for('config.index'))

    # Load current configuration
    form.auth_required.data = current_app.config['AUTH_REQUIRED']
    form.max_upload_size.data = current_app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)  # Convert bytes to MB
    form.share_link_expiry.data = current_app.config['SHARE_LINK_EXPIRY']
    form.default_theme.data = current_app.config['DEFAULT_THEME']

    # Get storage info
    storage_info = get_storage_info()

    return render_template('config/settings.html',
                          form=form,
                          storage_info=storage_info)

@config.route('/system')
@login_required
def system():
    # Only admin can access system information
    if not current_user.is_admin:
        flash('You do not have permission to access system information', 'danger')
        return redirect(url_for('files.index'))

    # Get storage info
    storage_info = get_storage_info()

    # Get system information
    system_info = {
        'python_version': os.sys.version,
        'platform': os.sys.platform,
        'hostname': os.uname().nodename if hasattr(os, 'uname') else 'Unknown',
        'app_path': current_app.root_path,
        'storage_path': current_app.config['STORAGE_PATH']
    }

    return render_template('config/system.html',
                          system_info=system_info,
                          storage_info=storage_info)
