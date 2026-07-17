# app.py
from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager as _BaseLoginManager
from flask_mail import Mail
from dotenv import load_dotenv
from sqlalchemy import inspect, text
import os

# Ensure environment variables from .env are loaded as early as possible
load_dotenv()

from models import db, User, Layanan, Merk, TipeKendaraan, Estimator, Testimoni
from auth import auth_bp, oauth
from bengkel import bengkel_bp
from scheduler import start_scheduler


class LoginManager(_BaseLoginManager):
    login_view: str

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback_secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///instance/bengkel.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', '')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@umkmbengkel.local')

# Inisialisasi Ekstensi
db.init_app(app)
csrf = CSRFProtect(app)
mail = Mail(app)

login_manager: LoginManager = LoginManager()
login_manager.init_app(app)
oauth.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Silakan masuk terlebih dahulu untuk mengakses halaman ini.'
login_manager.login_message_category = 'warning'


def initialize_database():
    with app.app_context():
        db.create_all()
        inspector = inspect(db.engine)
        antrean_columns = {column['name'] for column in inspector.get_columns('antrean')}
        if 'priority_adjusted' not in antrean_columns:
            db.session.execute(text('ALTER TABLE antrean ADD COLUMN priority_adjusted BOOLEAN DEFAULT 0'))
            db.session.commit()

        riwayat_columns = {column['name'] for column in inspector.get_columns('riwayat_servis')}
        for column_name, column_type in [
            ('replaced_parts', 'TEXT'),
            ('cost_breakdown', 'TEXT'),
            ('next_service_recommendation', 'TEXT'),
        ]:
            if column_name not in riwayat_columns:
                db.session.execute(text(f'ALTER TABLE riwayat_servis ADD COLUMN {column_name} {column_type}'))
                db.session.commit()


initialize_database()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


app.register_blueprint(auth_bp)
app.register_blueprint(bengkel_bp)


def seed_initial_data():
    if not Layanan.query.first():
        for item in [
            {'nama_layanan': 'Servis Rutin', 'estimasi_durasi_menit': 45, 'estimasi_harga': 120000},
            {'nama_layanan': 'Cuci Premium', 'estimasi_durasi_menit': 30, 'estimasi_harga': 80000},
            {'nama_layanan': 'Turun Mesin', 'estimasi_durasi_menit': 90, 'estimasi_harga': 500000},
        ]:
            db.session.add(Layanan(**item))

    if not Merk.query.first():
        merk_list = [{'nama': 'Honda'}, {'nama': 'Toyota'}, {'nama': 'Yamaha'}]
        merk_map = {}
        for item in merk_list:
            merk = Merk(**item)
            db.session.add(merk)
            db.session.flush()
            merk_map[item['nama']] = merk.id
    else:
        merk_map = {m.nama: m.id for m in Merk.query.all()}

    if not TipeKendaraan.query.first():
        tipe_list = [
            {'merk_id': merk_map['Honda'], 'nama': 'Civic'},
            {'merk_id': merk_map['Honda'], 'nama': 'Beat'},
            {'merk_id': merk_map['Toyota'], 'nama': 'Avanza'},
            {'merk_id': merk_map['Toyota'], 'nama': 'Yaris'},
            {'merk_id': merk_map['Yamaha'], 'nama': 'NMAX'},
            {'merk_id': merk_map['Yamaha'], 'nama': 'R15'},
        ]
        tipe_map = {}
        for item in tipe_list:
            tipe = TipeKendaraan(**item)
            db.session.add(tipe)
            db.session.flush()
            tipe_map[(item['merk_id'], item['nama'])] = tipe.id
    else:
        tipe_map = {(t.merk_id, t.nama): t.id for t in TipeKendaraan.query.all()}

    if not Estimator.query.first():
        estimator_items = [
            {'merk_id': merk_map['Honda'], 'tipe_id': tipe_map[(merk_map['Honda'], 'Civic')], 'keluhan': 'Servis Rutin', 'harga_min': 120000, 'harga_max': 180000},
            {'merk_id': merk_map['Honda'], 'tipe_id': tipe_map[(merk_map['Honda'], 'Beat')], 'keluhan': 'Ganti Kampas Rem', 'harga_min': 140000, 'harga_max': 220000},
            {'merk_id': merk_map['Toyota'], 'tipe_id': tipe_map[(merk_map['Toyota'], 'Avanza')], 'keluhan': 'Service Berkala', 'harga_min': 150000, 'harga_max': 220000},
            {'merk_id': merk_map['Yamaha'], 'tipe_id': tipe_map[(merk_map['Yamaha'], 'NMAX')], 'keluhan': 'Perawatan Mesin', 'harga_min': 180000, 'harga_max': 260000},
        ]
        for item in estimator_items:
            db.session.add(Estimator(**item))

    if not Testimoni.query.first():
        db.session.add(Testimoni(nama='Rina', komentar='Antrean cepat dan mekaniknya profesional.', rating=5))
        db.session.add(Testimoni(nama='Bambang', komentar='Buku servis digital sangat membantu saya memantau perawatan kendaraan.', rating=5))

    if not User.query.first():
        admin = User(nama='Admin Bengkel', email='admin@bengkel.com', no_hp='081234567890', role='admin')
        admin.set_password('password123')
        db.session.add(admin)

    db.session.commit()


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_initial_data()
        start_scheduler(app)
    app.run(debug=True)