from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config
import os
from datetime import datetime

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)

    # Ensure storage directory exists
    os.makedirs(app.config['STORAGE_PATH'], exist_ok=True)

    # Register blueprints
    from app.auth.routes import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from app.files.routes import files as files_blueprint
    app.register_blueprint(files_blueprint)

    from app.config.routes import config as config_blueprint
    app.register_blueprint(config_blueprint)

    # Create database tables
    with app.app_context():
        db.create_all()

        # Create default admin user if no users exist
        from app.auth.models import User
        if not User.query.first() and app.config['AUTH_REQUIRED']:
            default_user = User(username='admin', email='admin@example.com')
            default_user.set_password('admin')
            db.session.add(default_user)
            db.session.commit()

    # Add template context processor for current date/time and theme
    @app.context_processor
    def inject_template_vars():
        return {
            'now': datetime.now(),
            'config': app.config
        }

    return app
