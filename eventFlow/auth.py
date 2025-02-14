from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from . import db
from .models import User
from .forms import LoginForm, SignupForm

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password. Please try again', 'error')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember.data)
        
        # Get the next page from the request args
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('main.home')
        
        flash(f'Welcome, {user.first_name}!', 'success')
        return redirect(next_page)
    
    return render_template('auth/login.html', form=form)

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = SignupForm()
    if form.validate_on_submit():
        # Check if user with this email already exists
        if User.query.filter_by(email=form.email.data).first():
            flash('An account with this email already exists. Please log in instead.', 'error')
            return redirect(url_for('auth.login'))
        
        # Generate username from first and last name
        username = User.generate_username(
            form.first_name.data.strip(),
            form.last_name.data.strip()
        )
        
        user = User(
            username=username,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        
        try:
            db.session.add(user)
            db.session.commit()
            
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Please try again.', 'error')
            return redirect(url_for('auth.signup'))
    
    return render_template('auth/signup.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('main.home'))

@auth.route('/forgot-password')
def forgot_password():
    return render_template('auth/forgotPassword.html')

@auth.route('/check-email', methods=['POST'])
def check_email():
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({'available': False, 'error': 'No email provided'}), 400
    
    user = User.query.filter_by(email=email).first()
    return jsonify({'available': user is None})
