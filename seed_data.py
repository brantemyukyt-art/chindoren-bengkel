#!/usr/bin/env python3
"""Database seeder for Chindoren Bengkel.
Loads environment variables, enters the Flask app context, then seeds
default Layanan entries if the table is empty.
"""

from dotenv import load_dotenv
load_dotenv()

from app import app
from models import db, Layanan


def main():
    with app.app_context():
        # Ensure tables exist
        db.create_all()

        existing = Layanan.query.count()
        if existing:
            print(f"Layanan table already has {existing} entries. No seeding performed.")
            return

        services = [
            Layanan(nama_layanan="Servis Ringan", estimasi_durasi_menit=30, estimasi_harga=60000),
            Layanan(nama_layanan="Ganti Oli Mesin", estimasi_durasi_menit=40, estimasi_harga=90000),
            Layanan(nama_layanan="Servis CVT", estimasi_durasi_menit=60, estimasi_harga=150000),
            Layanan(nama_layanan="Ganti Kampas Rem", estimasi_durasi_menit=45, estimasi_harga=120000),
            Layanan(nama_layanan="Overhaul Mesin", estimasi_durasi_menit=240, estimasi_harga=2500000),
        ]

        try:
            # Use bulk_save_objects for efficiency
            db.session.bulk_save_objects(services)
            db.session.commit()
            print(f"Successfully inserted {len(services)} layanan into the database.")
        except Exception as e:
            db.session.rollback()
            print("Failed to seed layanan:", e)


if __name__ == '__main__':
    main()
