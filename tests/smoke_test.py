import os
import sys
import time
from datetime import date, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app as application
from models import db, User, Layanan, Antrean

def find_available_booking_slot(booking_date):
    for hour in range(8, 18):
        for minute in (0, 15, 30, 45):
            slot = f"{hour:02d}:{minute:02d}"
            if Antrean.query.filter_by(tanggal=booking_date, jam=slot).count() < 3:
                return slot
    return None

application.config['WTF_CSRF_ENABLED'] = False
application.config['TESTING'] = True


def main():
    with application.app_context():
        db.create_all()

        layanan = Layanan.query.filter_by(nama_layanan='Servis Rutin').first()
        if not layanan:
            layanan = Layanan(nama_layanan='Servis Rutin', estimasi_durasi_menit=30, estimasi_harga=120000)
            db.session.add(layanan)
            db.session.commit()

        timestamp = int(time.time())
        user_email = f'smoke_user_{timestamp}@example.com'
        user_password = 'SmokePass123!'
        admin_email = f'smoke_admin_{timestamp}@example.com'
        admin_password = 'SmokeAdmin123!'
        booking_plat = f'S{timestamp % 1000000:06d}'
        quick_add_plat = f'Q{(timestamp + 1) % 1000000:06d}'
        booking_date = date.today().isoformat()
        booking_time = find_available_booking_slot(date.today())
        if not booking_time:
            raise RuntimeError('No available booking slot found for today')

        print('Creating admin user for smoke test...')
        admin_user = User.query.filter_by(email=admin_email).first()
        if not admin_user:
            admin_user = User(nama='Smoke Test Admin', email=admin_email, no_hp='081234567900', role='admin')
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            db.session.commit()

        client = application.test_client()

        print('POST /register')
        r = client.post(
            '/register',
            data={
                'nama': 'Smoke Test User',
                'email': user_email,
                'no_hp': '081234567891',
                'password': user_password,
                'konfirmasi_password': user_password,
            },
            follow_redirects=False,
        )
        print('  status:', r.status_code, 'location:', r.headers.get('Location'))
        assert r.status_code == 302
        assert '/login' in r.headers.get('Location', '')

        user = User.query.filter_by(email=user_email).first()
        assert user is not None, 'Registered user must exist in the database'

        print('POST /login for regular user')
        r = client.post(
            '/login',
            data={'email': user_email, 'password': user_password},
            follow_redirects=False,
        )
        print('  status:', r.status_code, 'location:', r.headers.get('Location'))
        assert r.status_code == 302
        assert '/dashboard' in r.headers.get('Location', '')

        print('POST /booking for authenticated user')
        r = client.post(
            '/booking',
            data={
                'nama': 'Smoke Booking User',
                'plat_nomor': booking_plat,
                'layanan_id': str(layanan.id),
                'tanggal_booking': booking_date,
                'jam_booking': booking_time,
            },
            follow_redirects=False,
        )
        print('  status:', r.status_code, 'location:', r.headers.get('Location'))
        assert r.status_code == 302
        assert '/tracking/' in r.headers.get('Location', '')

        booking_row = Antrean.query.filter_by(plat_nomor=booking_plat, layanan_id=layanan.id).first()
        assert booking_row is not None, 'Booking record must be written to the database'
        assert booking_row.nomor_antrean.startswith('B-')

        admin_client = application.test_client()
        session_cookie_name = application.config.get('SESSION_COOKIE_NAME', 'session')
        try:
            admin_client.delete_cookie('localhost', session_cookie_name)
        except Exception:
            pass

        print('POST /login for admin user')
        r = admin_client.post(
            '/login',
            data={'email': admin_email, 'password': admin_password},
            follow_redirects=False,
        )
        print('  status:', r.status_code, 'location:', r.headers.get('Location'))
        assert r.status_code == 302
        assert '/admin/dashboard' in r.headers.get('Location', '')

        print('POST /admin/quick-add to create a walk-in antrean')
        r = admin_client.post(
            '/admin/quick-add',
            data={
                'nama': 'Smoke Walkin',
                'no_hp': '081234567902',
                'plat_nomor': quick_add_plat,
                'layanan_id': str(layanan.id),
            },
            follow_redirects=False,
        )
        print('  status:', r.status_code, 'location:', r.headers.get('Location'))
        assert r.status_code == 302
        assert '/admin/antrean' in r.headers.get('Location', '')

        quick_antrean = Antrean.query.filter_by(plat_nomor=quick_add_plat).first()
        assert quick_antrean is not None, 'Admin quick-add must persist a new antrean row'
        assert quick_antrean.status == 'Menunggu'

        print('POST admin status update to Sedang Dikerjakan')
        r = admin_client.post(
            f'/admin/antrean/{quick_antrean.id}/status',
            json={'status': 'Sedang Dikerjakan'},
        )
        print('  status:', r.status_code, 'json:', r.get_json())
        assert r.status_code == 200
        assert r.get_json().get('status_baru') == 'Sedang Dikerjakan'

        db.session.refresh(quick_antrean)
        assert quick_antrean.status == 'Sedang Dikerjakan'

        print('\nSMOKE TEST PASSED: registration, login, booking, admin quick-add, and status update all succeeded.')


if __name__ == '__main__':
    main()
