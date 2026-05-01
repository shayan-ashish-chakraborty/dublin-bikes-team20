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


# RDS CONNECTION DETAILS
# Update these to match your RDS instance before running
import os
from dotenv import load_dotenv

if os.path.exists("var.env"):
    load_dotenv(dotenv_path="var.env")

RDS_USER = os.getenv("DB_USER")
RDS_PASSWORD = os.getenv("DB_PASSWORD")
RDS_PORT = int(os.getenv("DB_PORT"))
DB_NAME = os.getenv("DB_NAME_AUTH")
RDS_HOST = os.getenv("DB_HOST")
 


# Database config
try:
    auth_db_cfg = DbConfig(
        host=RDS_HOST,
        port=RDS_PORT,
        user=RDS_USER,
        password=RDS_PASSWORD,
        db_name=DB_NAME
    )
    auth_engine = create_engine_for(auth_db_cfg)
    AuthSession = sessionmaker(bind=auth_engine)
except Exception:
    auth_engine = None
    AuthSession = None



# LOGIN ROUTE
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Render the login page and handle login form submission.

    GET: Redirects to home if already logged in, otherwise renders ``login.html``.

    POST: Validates the email and 6-digit PIN, checks credentials against the
    ``users`` table, and sets ``session["user_id"]`` and ``session["user_name"]``
    on success.

    Args:
        email: Registered user email address (from POST form).
        password: 6-digit numeric PIN (from POST form).

    Returns:
        A Flask response — either a redirect or a rendered ``login.html`` template.
    """
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



# REGISTER ROUTE
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Render the registration page and handle new account creation.

    GET: Redirects to home if already logged in, otherwise renders ``register.html``.

    POST: Validates all fields, enforces a 6-digit numeric PIN, checks for
    duplicate email, hashes the password, and inserts the new user.

    Args:
        full_name: User's full name (from POST form).
        email: Email address, must be unique (from POST form).
        password: 6-digit numeric PIN (from POST form).
        confirm_password: Must match ``password`` (from POST form).

    Returns:
        A Flask response — either a redirect or a rendered ``register.html`` template.
    """
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


# LOGOUT ROUTE
@auth_bp.route('/logout')
def logout():
    """Clear the user session and redirect to the home page.

    Returns:
        A redirect response to the home page.
    """
    session.clear()                         
    flash("You've been signed out.", "success")
    return redirect(url_for('frontend.home'))  # back to home — header shows Log In / Sign Upa