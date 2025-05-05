from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.auth.models import User
from werkzeug.urls import url_parse
from app.auth.models import get_utc_now
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError

auth = Blueprint('auth', __name__, url_prefix='/auth')

# Forms
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

# Routes
@auth.route('/login', methods=['GET', 'POST'])
def login():
    # If authentication is disabled, auto-login as admin
    if not current_app.config['AUTH_REQUIRED']:
        user = User.query.filter_by(username='admin').first()
        if user:
            login_user(user)
            return redirect(url_for('files.index'))

    # If user is already authenticated, redirect to home
    if current_user.is_authenticated:
        return redirect(url_for('files.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('auth.login'))

        # Update last login time
        user.last_login = get_utc_now()
        db.session.commit()

        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('files.index')
        return redirect(next_page)

    return render_template('auth/login.html', title='Sign In', form=form)

@auth.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    # Only admin can register new users
    if not current_user.is_admin:
        flash('You do not have permission to register new users', 'danger')
        return redirect(url_for('files.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('New user has been registered!', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', title='Register', form=form)

@auth.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect', 'danger')
            return redirect(url_for('auth.profile'))

        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Your password has been updated', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('auth/profile.html', title='Profile', form=form)

@auth.route('/theme/<theme>')
@login_required
def set_theme(theme):
    if theme not in ['light', 'dark']:
        flash('Invalid theme selection', 'danger')
        return redirect(request.referrer or url_for('files.index'))

    current_user.theme_preference = theme
    db.session.commit()
    return redirect(request.referrer or url_for('files.index'))
