from app import app
from models import db, Merk, TipeKendaraan, Estimator

with app.app_context():
    db.create_all()

    if not Merk.query.first():
        m1 = Merk(nama='Honda')
        m2 = Merk(nama='Yamaha')
        db.session.add_all([m1, m2])
        db.session.commit()

        t1 = TipeKendaraan(merk_id=m1.id, nama='Vario')
        t2 = TipeKendaraan(merk_id=m1.id, nama='Beat')
        t3 = TipeKendaraan(merk_id=m2.id, nama='NMAX')
        db.session.add_all([t1, t2, t3])
        db.session.commit()

        e1 = Estimator(merk_id=m1.id, tipe_id=t1.id, keluhan='servis_rutin', harga_min=120000, harga_max=150000)
        e2 = Estimator(merk_id=m1.id, tipe_id=t2.id, keluhan='ganti_oli', harga_min=60_000, harga_max=80_000)
        e3 = Estimator(merk_id=m2.id, tipe_id=t3.id, keluhan='servis_rutin', harga_min=150_000, harga_max=200_000)
        db.session.add_all([e1, e2, e3])
        db.session.commit()
        print('Seeded estimator data')
    else:
        print('Merk already exists, skipping')
