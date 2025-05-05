from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import sys

# Define a timezone-aware UTC now function
def get_utc_now():
    try:
        # Python 3.9+
        from datetime import timezone
        return datetime.now(timezone.utc)
    except (ImportError, AttributeError):
        # Fallback for older Python versions
        return datetime.utcnow()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    theme_preference = db.Column(db.String(10), default='light')  # 'light' or 'dark'
    created_at = db.Column(db.DateTime, default=get_utc_now)
    last_login = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class SharedLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    file_path = db.Column(db.String(512))
    token = db.Column(db.String(64), unique=True)
    created_at = db.Column(db.DateTime, default=get_utc_now)
    expires_at = db.Column(db.DateTime, nullable=True)
    access_count = db.Column(db.Integer, default=0)

    user = db.relationship('User', backref='shared_links')

    def __repr__(self):
        return f'<SharedLink {self.token}>'
