# models.py (Pembaruan)
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import secrets

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False) # Menyimpan hash password
    no_hp = db.Column(db.String(20), nullable=False)
    role = db.Column(db.String(20), default='pelanggan') # 'pelanggan' atau 'admin'
    receive_whatsapp_notifications = db.Column(db.Boolean, default=True)
    
    # Kumpulan Relasi (Sama seperti sebelumnya)
    kendaraan = db.relationship('Kendaraan', backref='pemilik', lazy=True, cascade="all, delete-orphan")
    antrean = db.relationship('Antrean', backref='pelanggan', lazy=True)

    # Helper untuk enkripsi password
    def set_password(self, password):
        self.password = generate_password_hash(password)

    # Helper untuk verifikasi password saat login
    def check_password(self, password):
        return check_password_hash(self.password, password)
        
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class Kendaraan(db.Model):
    __tablename__ = 'kendaraan'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plat_nomor = db.Column(db.String(15), unique=True, nullable=False)
    merk = db.Column(db.String(50), nullable=False)
    tipe = db.Column(db.String(50), nullable=False)
    tahun = db.Column(db.Integer, nullable=False)
    
    # Relationships
    riwayat_servis = db.relationship('RiwayatServis', backref='kendaraan', lazy=True)

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class Layanan(db.Model):
    __tablename__ = 'layanan'
    id = db.Column(db.Integer, primary_key=True)
    nama_layanan = db.Column(db.String(100), nullable=False)
    estimasi_durasi_menit = db.Column(db.Integer, nullable=False) # Untuk Wait Time Logic
    estimasi_harga = db.Column(db.Integer, nullable=False)

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class Merk(db.Model):
    __tablename__ = 'merk'
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False, unique=True)

    tipe = db.relationship('TipeKendaraan', backref='merk', lazy=True, cascade='all, delete-orphan')

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class TipeKendaraan(db.Model):
    __tablename__ = 'tipe_kendaraan'
    id = db.Column(db.Integer, primary_key=True)
    merk_id = db.Column(db.Integer, db.ForeignKey('merk.id'), nullable=False)
    nama = db.Column(db.String(100), nullable=False)

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class Estimator(db.Model):
    __tablename__ = 'estimator'
    id = db.Column(db.Integer, primary_key=True)
    merk_id = db.Column(db.Integer, db.ForeignKey('merk.id'), nullable=False)
    tipe_id = db.Column(db.Integer, db.ForeignKey('tipe_kendaraan.id'), nullable=False)
    keluhan = db.Column(db.String(100), nullable=False)
    harga_min = db.Column(db.Integer, nullable=False)
    harga_max = db.Column(db.Integer, nullable=False)

    merk = db.relationship('Merk', backref='estimasi')
    tipe = db.relationship('TipeKendaraan', backref='estimasi')

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class Testimoni(db.Model):
    __tablename__ = 'testimoni'
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    komentar = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False, default=5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(32))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref='password_reset_tokens')

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class Setting(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), nullable=False, unique=True)
    value = db.Column(db.String(500), nullable=True)

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class Antrean(db.Model):
    __tablename__ = 'antrean'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Bisa null jika publik (guest)
    nama_guest = db.Column(db.String(100), nullable=True)
    plat_nomor = db.Column(db.String(15), nullable=False)
    layanan_id = db.Column(db.Integer, db.ForeignKey('layanan.id'), nullable=False)
    nomor_antrean = db.Column(db.String(10), nullable=False) # Contoh: B-014
    status = db.Column(db.String(30), default='Menunggu') # Menunggu, Sedang Dikerjakan, Selesai
    tanggal = db.Column(db.Date, default=date.today)
    jam = db.Column(db.String(10), nullable=True)
    priority_adjusted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    layanan = db.relationship('Layanan', backref='antrean')

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class RiwayatServis(db.Model):
    __tablename__ = 'riwayat_servis'
    id = db.Column(db.Integer, primary_key=True)
    kendaraan_id = db.Column(db.Integer, db.ForeignKey('kendaraan.id'), nullable=False)
    tanggal_servis = db.Column(db.Date, default=date.today)
    mekanik = db.Column(db.String(100), nullable=False)
    kilometer = db.Column(db.Integer, nullable=False)
    tindakan = db.Column(db.Text, nullable=False)
    sparepart = db.Column(db.Text, nullable=True)
    replaced_parts = db.Column(db.Text, nullable=True)
    cost_breakdown = db.Column(db.Text, nullable=True)
    next_service_recommendation = db.Column(db.Text, nullable=True)
    total_biaya = db.Column(db.Integer, nullable=False)
    jadwal_servis_berikutnya = db.Column(db.Date, nullable=False) # Diisi otomatis +2 bulan

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)