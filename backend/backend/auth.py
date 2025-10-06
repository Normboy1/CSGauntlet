from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from .models import User
from . import db
from sqlalchemy.exc import IntegrityError
import jwt
import datetime
import os
from functools import wraps

auth = Blueprint('auth', __name__)

def generate_token(user):
    """Generate JWT token for user"""
    payload = {
        'user_id': user.id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
    }
    return jwt.encode(payload, os.environ.get('SECRET_KEY', 'dev'), algorithm='HS256')

def jwt_required(f):
    """Decorator to require JWT authentication for API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'message': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            # Decode the token
            payload = jwt.decode(token, os.environ.get('SECRET_KEY', 'dev'), algorithms=['HS256'])
            user_id = payload['user_id']
            user = User.query.get(user_id)
            
            if not user:
                return jsonify({'message': 'User not found'}), 401
                
            # Add user to request context
            request.current_user = user
            
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            email_or_username = data.get('email') or data.get('username')
            password = data.get('password')
        else:
            email_or_username = request.form.get('email') or request.form.get('username')
            password = request.form.get('password')

        if not email_or_username or not password:
            if request.is_json:
                return jsonify({'message': 'Please fill in all fields.'}), 400
            flash('Please fill in all fields.', category='error')
            return render_template("login.html", user=current_user)

        # Try to find user by email or username
        user = User.query.filter(
            (User.email == email_or_username) | (User.username == email_or_username)
        ).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            token = generate_token(user)
            
            if request.is_json:
                return jsonify({
                    'token': token,
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'college_name': user.college_name,
                        'avatar_url': user.avatar_url
                    }
                })
            
            flash('Logged in successfully!', category='success')
            return redirect(url_for('main.home'))
        
        if request.is_json:
            return jsonify({'message': 'Invalid email/username or password.'}), 401
        
        flash('Invalid email/username or password.', category='error')
        return render_template("login.html", user=current_user)

    return render_template("login.html", user=current_user)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', category='success')
    return redirect(url_for('auth.login'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            email = data.get('email', '').strip()
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()
            password2 = data.get('password2', '').strip()
            university = data.get('university', '').strip()
        else:
            email = request.form.get('email', '').strip()
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            password2 = request.form.get('password2', '').strip()
            university = request.form.get('university', '').strip()

        # Validate input fields
        errors = []
        if not email:
            errors.append('Email is required.')
        elif not User.is_valid_email(email):
            errors.append('Please enter a valid email address.')
        elif not username:
            errors.append('Username is required.')
        elif not password:
            errors.append('Password is required.')
        elif not password2:
            errors.append('Please confirm your password.')
        elif len(email) < 4:
            errors.append('Email must be greater than 3 characters.')
        elif len(username) < 2:
            errors.append('Username must be greater than 1 character.')
        elif password != password2:
            errors.append('Passwords don\'t match.')
        elif len(password) < 7:
            errors.append('Password must be at least 7 characters.')

        if errors:
            if request.is_json:
                return jsonify({'message': errors[0]}), 400
            for error in errors:
                flash(error, category='error')
            return render_template("register.html", user=current_user)

        try:
            # Check for existing email
            if User.query.filter_by(email=email).first():
                if request.is_json:
                    return jsonify({'message': 'Email already registered.'}), 400
                flash('Email already registered.', category='error')
                return render_template("register.html", user=current_user)

            # Check for existing username
            if User.query.filter_by(username=username).first():
                if request.is_json:
                    return jsonify({'message': 'Username already taken.'}), 400
                flash('Username already taken.', category='error')
                return render_template("register.html", user=current_user)

            # Create new user
            new_user = User(
                email=email,
                username=username,
                university=university
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            # Log in the new user
            login_user(new_user, remember=True)
            token = generate_token(new_user)

            if request.is_json:
                return jsonify({
                    'token': token,
                    'user': {
                        'id': new_user.id,
                        'username': new_user.username,
                        'email': new_user.email,
                        'college_name': new_user.college_name,
                        'avatar_url': new_user.avatar_url
                    }
                }), 201

            flash('Account created successfully!', category='success')
            return redirect(url_for('main.home'))

        except IntegrityError:
            db.session.rollback()
            if request.is_json:
                return jsonify({'message': 'An error occurred. Please try again.'}), 500
            flash('An error occurred. Please try again.', category='error')

    return render_template("register.html", user=current_user)
