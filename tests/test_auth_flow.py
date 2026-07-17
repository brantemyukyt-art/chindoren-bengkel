import os
import unittest
from datetime import date, timedelta

import app
from app import app as application, db
from models import User, Kendaraan, RiwayatServis


class AuthFlowTests(unittest.TestCase):
    def setUp(self):
        application.config['TESTING'] = True
        application.config['WTF_CSRF_ENABLED'] = False
        self.client = application.test_client()
        with application.app_context():
            db.drop_all()
            db.create_all()
            user = User(nama='Test User', email='test@example.com', no_hp='08123456789', role='pelanggan')
            user.set_password('secret123')
            db.session.add(user)
            db.session.commit()

    def test_login_page_has_social_login_and_forgot_password(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Masuk dengan Google', html)
        self.assertIn('Masuk dengan WhatsApp OTP', html)
        self.assertIn('Lupa password?', html)

    def test_google_oauth_redirect_contains_provider(self):
        os.environ['GOOGLE_CLIENT_ID'] = 'test-client-id'
        os.environ['GOOGLE_CLIENT_SECRET'] = 'test-client-secret'
        response = self.client.get('/login/google')
        self.assertEqual(response.status_code, 302)
        self.assertIn('accounts.google.com', response.headers['Location'])

    def test_booking_page_prefills_user_and_vehicle_data(self):
        with application.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            user_id = user.id
            vehicle = Kendaraan(user_id=user_id, plat_nomor='B1234XYZ', merk='Honda', tipe='Civic', tahun=2023)
            db.session.add(vehicle)
            db.session.commit()

        with self.client.session_transaction() as session:
            session['_user_id'] = str(user_id)
            session['_fresh'] = True

        response = self.client.get('/booking')
        html = response.get_data(as_text=True)
        self.assertIn('B1234XYZ', html)
        self.assertIn('Test User', html)
        self.assertIn('type="date"', html)
        self.assertIn('type="time"', html)

    def test_guest_booking_requires_phone_number(self):
        response = self.client.post('/booking', data={
            'nama': 'Tamu',
            'plat_nomor': 'B9999XYZ',
            'layanan_id': '1',
            'tanggal_booking': '2026-07-20',
            'jam_booking': '09:00',
            'no_hp': '',
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Sebagai Guest, nomor HP wajib diisi agar kami bisa menghubungi Anda', html)

    def test_service_history_page_renders_detailed_history_cards(self):
        with application.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            user_id = user.id
            vehicle = Kendaraan(user_id=user_id, plat_nomor='B9999XYZ', merk='Toyota', tipe='Avanza', tahun=2022)
            db.session.add(vehicle)
            db.session.commit()
            history = RiwayatServis(
                kendaraan_id=vehicle.id,
                mekanik='Budi',
                kilometer=12000,
                tindakan='Service berkala',
                replaced_parts='Oli mesin\nFilter oli',
                cost_breakdown='Jasa servis: 150000\nOli mesin: 90000\nFilter oli: 35000',
                next_service_recommendation='Periksa rem dan cek tekanan ban pada 3000 km berikutnya',
                total_biaya=275000,
                jadwal_servis_berikutnya=date.today() + timedelta(days=60),
            )
            db.session.add(history)
            db.session.commit()

        with self.client.session_transaction() as session:
            session['_user_id'] = str(user_id)
            session['_fresh'] = True

        response = self.client.get('/buku-servis')
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Daftar sparepart', html)
        self.assertIn('Oli mesin', html)
        self.assertIn('Rincian biaya', html)
        self.assertIn('Periksa rem', html)

    def test_dashboard_renders_vehicle_carousel_and_quick_actions(self):
        with application.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            user_id = user.id
            vehicle = Kendaraan(user_id=user_id, plat_nomor='B1234XYZ', merk='Honda', tipe='Civic', tahun=2023)
            db.session.add(vehicle)
            db.session.commit()

        with self.client.session_transaction() as session:
            session['_user_id'] = str(user_id)
            session['_fresh'] = True

        response = self.client.get('/dashboard')
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Kendaraan terdaftar', html)
        self.assertIn('Booking', html)
        self.assertIn('History', html)

    def test_admin_login_redirects_to_admin_dashboard(self):
        with application.app_context():
            admin = User(nama='Admin Test', email='admin-test@example.com', no_hp='081234567890', role='admin')
            admin.set_password('adminpass')
            db.session.add(admin)
            db.session.commit()

        response = self.client.post('/login', data={
            'email': 'admin-test@example.com',
            'password': 'adminpass'
        }, follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/dashboard', response.headers['Location'])

    def test_admin_user_accesses_admin_dashboard_directly(self):
        with application.app_context():
            admin = User.query.filter_by(email='admin-test@example.com').first()
            if not admin:
                admin = User(nama='Admin Test', email='admin-test@example.com', no_hp='081234567890', role='admin')
                admin.set_password('adminpass')
                db.session.add(admin)
                db.session.commit()
            admin_id = admin.id

        with self.client.session_transaction() as session:
            session['_user_id'] = str(admin_id)
            session['_fresh'] = True

        response = self.client.get('/admin/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Dashboard operasional bengkel', response.get_data(as_text=True))

    def test_settings_page_updates_whatsapp_notification_preference(self):
        with application.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            user_id = user.id

        with self.client.session_transaction() as session:
            session['_user_id'] = str(user_id)
            session['_fresh'] = True

        response = self.client.post('/settings', data={'receive_whatsapp_notifications': 'on'})
        self.assertEqual(response.status_code, 302)

        with application.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            self.assertTrue(user.receive_whatsapp_notifications)


if __name__ == '__main__':
    unittest.main()
