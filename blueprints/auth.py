"""
Authentication Blueprint
Handles user registration, login, logout with bcrypt password hashing.
"""

import sqlite3
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
import bcrypt

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# ── Helpers ────────────────────────────────────────────────

def get_db():
    """Get database connection from app context."""
    if 'db' not in g:
        from flask import current_app
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def login_required(f):
    """Decorator: require user to be logged in."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('กรุณาเข้าสู่ระบบก่อน', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator: require user to be admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('กรุณาเข้าสู่ระบบก่อน', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


# ── Routes ─────────────────────────────────────────────────

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validation
        if not username or not email or not password:
            flash('กรุณากรอกข้อมูลให้ครบถ้วน', 'danger')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('รหัสผ่านไม่ตรงกัน', 'danger')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร', 'danger')
            return render_template('auth/register.html')

        db = get_db()

        # Check existing user (parameterized query — prevents SQL injection)
        existing = db.execute(
            'SELECT id FROM users WHERE username = ? OR email = ?',
            (username, email)
        ).fetchone()

        if existing:
            flash('ชื่อผู้ใช้หรืออีเมลนี้ถูกใช้แล้ว', 'danger')
            return render_template('auth/register.html')

        # Hash password with bcrypt
        password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        # Insert new user
        db.execute(
            'INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)',
            (username, email, password_hash, 'user')
        )
        db.commit()

        flash('สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบ', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('กรุณากรอกข้อมูลให้ครบถ้วน', 'danger')
            return render_template('auth/login.html')

        db = get_db()

        # Parameterized query — prevents SQL injection
        user = db.execute(
            'SELECT * FROM users WHERE username = ?',
            (username,)
        ).fetchone()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session.permanent = True
            flash(f'ยินดีต้อนรับ, {user["username"]}!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    """User logout."""
    session.clear()
    flash('ออกจากระบบเรียบร้อย', 'info')
    return redirect(url_for('auth.login'))
