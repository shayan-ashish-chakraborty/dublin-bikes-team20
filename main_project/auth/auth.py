from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..db import create_engine_for, DbConfig
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text
import pathlib

# Paths for templates and static
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
template_path = BASE_DIR / 'main_project' / 'templates'
static_path = BASE_DIR / 'main_project' / 'static'

# Blueprint
auth_bp = Blueprint(
    'auth',
    __name__,
    template_folder=template_path,
    static_folder=static_path,
    static_url_path='/static'
)

# Database config
auth_db_cfg = DbConfig(
    host="localhost",       # replace with your RDS endpoint on EC2
    port=3306,
    user="app_user",            # replace with your RDS username
    password="Strong123!",      # replace with your RDS password
    db_name="dublin_bikes_auth" 
)

auth_engine = create_engine_for(auth_db_cfg)
AuthSession = sessionmaker(bind=auth_engine)


# ==========================
# LOGIN ROUTE
# ==========================
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():

    if session.get('user_id'):
        return redirect(url_for('frontend.home'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Validate password length & digits
        if not password.isdigit() or len(password) != 6:
            flash("Password must be exactly 6 digits.", "error")
            return redirect(url_for('auth.login'))

        db_session = AuthSession()
        try:
            result = db_session.execute(
                text("SELECT * FROM users WHERE email = :email"),
                {"email": email}
            ).fetchone()

            if result is None:
                flash("Email not found.", "error")
                return redirect(url_for('auth.login'))

            if not check_password_hash(result['password_hash'], password):
                flash("Invalid email or password.", "error")
                return redirect(url_for('auth.login'))

            # Successful login
            session['user_id'] = result['id']
            session['user_name'] = result['full_name'] 
            flash(f"Welcome, {result['full_name']}!", "success")
            return redirect(url_for('frontend.home'))  # change to dashboard/home if you have one

        finally:
            db_session.close()

    return render_template('login.html')


# ==========================
# REGISTER ROUTE
# ==========================
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # Already logged in,redirect to home
    if session.get('user_id'):
        return redirect(url_for('frontend.home'))
    
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Check all fields
        if not full_name or not email or not password or not confirm_password:
            flash("Please fill in all fields.", "error")
            return redirect(url_for('auth.register'))

        # Password must be numeric & 6 digits
        if not password.isdigit() or len(password) != 6:
            flash("Password must be exactly 6 digits.", "error")
            return redirect(url_for('auth.register'))

        # Password confirmation
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for('auth.register'))

        db_session = AuthSession()
        try:
            # Check if email already exists
            existing = db_session.execute(
                text("SELECT * FROM users WHERE email = :email"),
                {"email": email}
            ).fetchone()
            if existing:
                flash("Email is already registered.", "error")
                return redirect(url_for('auth.register'))

            # Hash the password and insert user
            password_hash = generate_password_hash(password)
            db_session.execute(
                text("INSERT INTO users (full_name, email, password_hash) VALUES (:full_name, :email, :password_hash)"),
                {"full_name": full_name, "email": email, "password_hash": password_hash}
            )
            db_session.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('auth.login'))

        except Exception as e:
            db_session.rollback()
            flash(f"Error: {e}", "error")
            return redirect(url_for('auth.register'))

        finally:
            db_session.close()

    return render_template('register.html')

# ==========================
# LOGOUT ROUTE
# ==========================
@auth_bp.route('/logout')
def logout():
    session.clear()                         
    flash("You've been signed out.", "success")
    return redirect(url_for('frontend.home'))  # back to home — header shows Log In / Sign Upa