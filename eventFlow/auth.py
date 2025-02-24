from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from . import db
from .models import User
from .forms import LoginForm, SignupForm
import traceback

# Create a Blueprint for authentication routes
auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    # Check if user is already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = LoginForm()
    
    # Get the 'next' URL from either form data (POST) or query parameters (GET)
    next_url = request.form.get('next') or request.args.get('next')
    
    # Handle form submission
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        # Validate user credentials
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password. Please try again', 'error')
            return redirect(url_for('auth.login', next=next_url))
        
        login_user(user, remember=form.remember.data)
        
        # Handle redirect after successful login
        if next_url:
            # Ensure the next_url starts with a slash for security
            if not next_url.startswith('/'):
                next_url = '/' + next_url
            
            # Prevent protocol-relative URL redirects for security
            if not next_url.startswith('//'):
                flash(f'Welcome back, {user.first_name}!', 'success')
                return redirect(next_url)
        
        # If no next URL, redirect to home page
        flash(f'Welcome back, {user.first_name}!', 'success')
        return redirect(url_for('main.home'))
    
    return render_template('auth/login.html', form=form, next=next_url)

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
        
    form = SignupForm()
    if form.validate_on_submit():
        try:
            existing_user = User.query.filter_by(email=form.email.data.lower()).first()
            if existing_user:
                flash('An account with this email already exists. Please log in instead.', 'error')
                return render_template('auth/signup.html', form=form)
            
            username = User.generate_username(
                form.first_name.data.strip(),
                form.last_name.data.strip()
            )

            # Create new user
            user = User(
                username=username,
                email=form.email.data.lower(),
                first_name=form.first_name.data,
                last_name=form.last_name.data
            )
            user.set_password(form.password.data)
            
            db.session.add(user)
            db.session.commit()
                        
            flash('Account created successfully! Please log in to continue.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            traceback.print_exc()  # Add detailed error logging
            flash('An error occurred while creating your account. Please try again.', 'error')
            return render_template('auth/signup.html', form=form)
    
    # If form validation failed, show errors
    if form.errors:
        print("Form validation errors:", form.errors)
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{error}", 'error')
    
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
    try:
        data = request.get_json()
        email = data.get('email', '').lower()
        print(f"Checking email availability: {email}")
        
        if not email:
            return jsonify({'available': False, 'error': 'Email is required'})
            
        existing_user = User.query.filter_by(email=email).first()
        is_available = existing_user is None
        print(f"Email {email} is {'available' if is_available else 'not available'}")
        
        return jsonify({'available': is_available})
    except Exception as e:
        print(f"Error checking email: {str(e)}")
        return jsonify({'available': False, 'error': str(e)})
