# scheduler.py (Pembaruan)
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import date, timedelta
from flask_mail import Message
from models import db, RiwayatServis, User, Kendaraan
from wa_helper import kirim_whatsapp


def kirim_reminder_email(app, user, kendaraan, tanggal_format):
    if not app.config.get('MAIL_SERVER'):
        return False

    from app import mail

    pesan = Message(
        subject='Pengingat servis kendaraan Anda',
        recipients=[user.email],
        body=(
            f'Halo {user.nama},\n\n'
            f'Ini adalah pengingat otomatis dari Chindoren Bengkel.\n'
            f'Kendaraan Anda ({kendaraan.merk} {kendaraan.tipe} - {kendaraan.plat_nomor}) '
            f'akan mendekati jadwal servis rutin pada {tanggal_format}.\n\n'
            f'Silakan lakukan booking servis online agar antrean Anda lebih nyaman.\n\n'
            f'Terima kasih.\n'
        ),
        sender=app.config.get('MAIL_DEFAULT_SENDER')
    )
    mail.send(pesan)
    return True


def cek_dan_kirim_reminder_wa(app):
    with app.app_context():
        target_tanggal = date.today() + timedelta(days=3)
        servis_mendatang = db.session.query(RiwayatServis).filter_by(jadwal_servis_berikutnya=target_tanggal).all()

        for servis in servis_mendatang:
            kendaraan = Kendaraan.query.get(servis.kendaraan_id)
            if not kendaraan:
                continue

            user = None
            if kendaraan.user_id:
                user = User.query.get(kendaraan.user_id)

            if user:
                tanggal_format = servis.jadwal_servis_berikutnya.strftime('%d %B %Y')

                if user.email:
                    kirim_reminder_email(app, user, kendaraan, tanggal_format)

                if user.no_hp and getattr(user, 'receive_whatsapp_notifications', True):
                    pesan_wa = (
                        f'Halo {user.nama} 🛵\n\n'
                        f'Ini adalah pengingat otomatis dari *Chindoren Bengkel*.\n\n'
                        f'Kendaraan Anda ({kendaraan.merk} {kendaraan.tipe} - *{kendaraan.plat_nomor}*) '
                        f'telah mendekati jadwal servis rutin pada *{tanggal_format}*.\n\n'
                        f'Untuk menghindari antrean panjang, silakan lakukan *Booking Servis Online* '
                        f'melalui website kami di: https://umkmbengkel.com/booking\n\n'
                        f'Jaga performa mesin Anda agar tetap prima! 🔧'
                    )
                    kirim_whatsapp(user.no_hp, pesan_wa)


def start_scheduler(app):
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(func=lambda: cek_dan_kirim_reminder_wa(app), trigger='cron', hour=9, minute=0)
    scheduler.start()