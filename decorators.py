# decorators.py
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Silakan masuk terlebih dahulu untuk mengakses halaman admin.", "warning")
            return redirect(url_for('auth.login'))
        if current_user.role != 'admin':
            flash("Anda tidak memiliki hak akses ke halaman admin!", "danger")
            return redirect(url_for('bengkel.dashboard'))
        return f(*args, **kwargs)
    return decorated_function