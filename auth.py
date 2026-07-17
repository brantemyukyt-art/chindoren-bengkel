# auth.py
import os
import secrets
from urllib.parse import urlparse, urljoin

from authlib.integrations.base_client.errors import OAuthError
from authlib.integrations.flask_client import OAuth
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, PasswordResetToken
from forms import LoginForm, RegisterForm, ForgotPasswordForm, ResetPasswordForm
from wa_helper import kirim_whatsapp

auth_bp = Blueprint('auth', __name__)

oauth = OAuth()


def ensure_google_oauth_registered():
    if 'google' in oauth._clients:
        return True

    google_client_id = os.getenv('GOOGLE_CLIENT_ID')
    google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    if not google_client_id or not google_client_secret:
        return False

    oauth.register(
        name='google',
        client_id=google_client_id,
        client_secret=google_client_secret,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )
    return True


def is_safe_url(target):
    host_url = request.host_url
    redirect_url = urljoin(host_url, target)
    return urlparse(redirect_url).scheme in ('http', 'https') and urlparse(host_url).netloc == urlparse(redirect_url).netloc

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('bengkel.dashboard'))
        
    form = RegisterForm()
    if form.validate_on_submit():
        # Cek apakah email sudah terdaftar sebelumnya
        email_terdaftar = User.query.filter_by(email=form.email.data).first()
        if email_terdaftar:
            flash("Email tersebut sudah terdaftar dalam sistem. Silakan gunakan email lain.", "danger")
            return render_template('register.html', form=form)
            
        # Membuat user baru (secara default role = pelanggan)
        user_baru = User(
            nama=form.nama.data,
            email=form.email.data,
            no_hp=form.no_hp.data,
            role='pelanggan'
        )
        user_baru.set_password(form.password.data) # Proses hashing password
        
        db.session.add(user_baru)
        db.session.commit()
        
        flash("Pendaftaran berhasil! Silakan masuk menggunakan akun Anda.", "success")
        return redirect(url_for('auth.login'))
        
    return render_template('register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        target_dashboard = 'bengkel.admin_dashboard' if current_user.role == 'admin' else 'bengkel.dashboard'
        return redirect(url_for(target_dashboard))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        # Validasi keberadaan user dan kecocokan hash password
        if user and user.check_password(form.password.data):
            login_user(user)
            flash(f"Selamat datang kembali, {user.nama}!", "success")
            print('DEBUG login user role:', repr(user.role))

            user_role = str(user.role or '').strip().lower()
            if user_role == 'admin':
                return redirect(url_for('bengkel.admin_dashboard'))

            next_page = request.args.get('next')
            if next_page and is_safe_url(next_page):
                return redirect(next_page)
            return redirect(url_for('bengkel.dashboard'))
        else:
            flash("Email atau password yang Anda masukkan salah. Silakan coba lagi.", "danger")
            
    return render_template('login.html', form=form)

@auth_bp.route('/login/google')
def login_google():
    google_client_id = os.getenv('GOOGLE_CLIENT_ID')
    google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    if not google_client_id or not google_client_secret:
        flash('Google OAuth belum dikonfigurasi. Silakan atur GOOGLE_CLIENT_ID dan GOOGLE_CLIENT_SECRET.', 'warning')
        return redirect(url_for('auth.login'))

    if not ensure_google_oauth_registered():
        flash('Google OAuth belum dikonfigurasi. Silakan atur GOOGLE_CLIENT_ID dan GOOGLE_CLIENT_SECRET.', 'warning')
        return redirect(url_for('auth.login'))

    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', url_for('auth.google_callback', _external=True))
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/login/google/callback')
def google_callback():
    google_client_id = os.getenv('GOOGLE_CLIENT_ID')
    google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    if not google_client_id or not google_client_secret:
        flash('Google OAuth belum dikonfigurasi.', 'warning')
        return redirect(url_for('auth.login'))

    try:
        token = oauth.google.authorize_access_token()
    except OAuthError as exc:
        flash(f'Gagal login Google: {exc}', 'danger')
        return redirect(url_for('auth.login'))

    userinfo = token.get('userinfo')
    if not userinfo:
        try:
            userinfo = oauth.google.parse_id_token(token)
        except Exception:
            userinfo = None

    if not userinfo:
        flash('Gagal membaca data akun Google.', 'danger')
        return redirect(url_for('auth.login'))

    email = (userinfo.get('email') or '').strip().lower()
    nama = userinfo.get('name') or email.split('@')[0]
    if not email:
        flash('Email Google tidak tersedia.', 'danger')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(nama=nama, email=email, no_hp='000000000000', role='pelanggan')
        user.set_password(secrets.token_urlsafe(16))
        db.session.add(user)
        db.session.commit()

    login_user(user)
    flash(f'Selamat datang, {user.nama}!', 'success')
    target_dashboard = 'bengkel.admin_dashboard' if user.role == 'admin' else 'bengkel.dashboard'
    return redirect(url_for(target_dashboard))


@auth_bp.route('/login/whatsapp-otp', methods=['GET', 'POST'])
def login_whatsapp_otp():
    if request.method == 'POST':
        nomor = request.form.get('no_hp', '').strip()
        if not nomor:
            flash('Nomor WhatsApp wajib diisi.', 'danger')
            return render_template('whatsapp_otp_login.html')

        otp = f'{secrets.randbelow(900000) + 100000}'
        pesan = f'Kode OTP login Chindoren Bengkel Anda adalah {otp}. Kode berlaku 5 menit.'
        kirim_whatsapp(nomor, pesan)
        flash('Kode OTP dikirim melalui WhatsApp. Silakan gunakan kode tersebut untuk masuk.', 'success')
        return render_template('whatsapp_otp_login.html', otp_sent=True, phone_number=nomor)

    return render_template('whatsapp_otp_login.html')


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = PasswordResetToken(user_id=user.id)
            db.session.add(token)
            db.session.commit()
            flash('Link reset password telah dipersiapkan. Silakan cek email Anda.', 'info')
        else:
            flash('Jika email terdaftar, kami akan mengirim instruksi reset password.', 'info')
        return render_template('forgot_password.html', form=form, submitted=True)
    return render_template('forgot_password.html', form=form)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    reset_token = PasswordResetToken.query.filter_by(token=token, used=False).first()
    if not reset_token:
        flash('Token reset password tidak valid atau sudah digunakan.', 'danger')
        return redirect(url_for('auth.login'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = reset_token.user
        user.set_password(form.password.data)
        reset_token.used = True
        db.session.commit()
        flash('Password berhasil direset. Silakan masuk kembali.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', form=form, token=token)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Anda telah berhasil keluar dari sistem.", "info")
    return redirect(url_for('auth.login'))