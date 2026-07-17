# Chindoren Bengkel

Chindoren Bengkel adalah aplikasi manajemen bengkel digital berbasis web yang dibangun dengan Flask. Sistem ini menyatukan alur pelanggan dan admin dalam satu platform terpadu: booking servis, estimasi biaya, tracking antrean, manajemen kendaraan, entri servis, dan laporan CSV.

## Brand

Aplikasi ini beroperasi sebagai **Chindoren Bengkel**, platform bengkel digital yang fokus pada proses servis yang cepat, transparan, dan mudah ditangani.

## Fitur Utama

### Modul Pelanggan
- **Booking Servis Digital**: Reservasi antrean dengan batas kuota waktu pada setiap slot.
- **Estimator Biaya**: Kalkulasi rentang biaya berdasarkan merk, tipe, dan keluhan kendaraan.
- **Tracking Real-Time**: Pantau status antrean dan prediksi waktu servis.
- **Buku Servis Digital**: Riwayat servis kendaraan dipantau dalam satu tampilan.

### Modul Administrator
- **Manajemen Antrean Harian**: Kontrol antrean dengan status Menunggu, Sedang Dikerjakan, Selesai, dan Batal.
- **Walk-in Booking**: Tambah pelanggan langsung dari panel admin tanpa mekanisme booking terpisah.
- **Data Pelanggan & Kendaraan**: Kelola user dan armada kendaraan secara langsung.
- **Entri Servis Terintegrasi**: Catat mekanik, kilometer, sparepart, biaya, dan rekomendasi servis berikutnya.
- **Export CSV OOP**: Ekspor laporan antrean hari ini lewat class `QueueReporter`.

## Struktur Program

- `app.py`: Entry point aplikasi Flask dan konfigurasi blueprint.
- `auth.py`: Otentikasi pengguna, pendaftaran, login, logout, dan reset password.
- `bengkel.py`: Route utama pelanggan dan admin, termasuk export CSV, antrean, estimasi, dan layanan.
- `models.py`: Definisi model SQLAlchemy untuk `Antrean`, `User`, `Layanan`, `Kendaraan`, `RiwayatServis`, `Merk`, `TipeKendaraan`, dan `Estimator`.
- `forms.py`: Form dan validasi data dengan Flask-WTF.
- `wa_helper.py`: Helper WhatsApp untuk notifikasi status servis.
- `templates/`: Template HTML untuk UI pelanggan dan admin.
- `tests/`: Pengujian integrasi dasar dan smoke test.

## Pemenuhan Kriteria

Proyek ini mencakup beberapa aspek penting:
- **Python Dasar**: logika, kondisi, perulangan, dan manipulasi string.
- **Struktur Data**: penggunaan list, dictionary, dan query hasil dari database.
- **Modularitas**: pemisahan logika ke dalam file terpisah (`app.py`, `bengkel.py`, `models.py`, dll.).
- **Exception Handling**: rollback transaksi database saat terjadi error.
- **OOP**: class `QueueReporter` untuk export CSV dengan enkapsulasi helper internal.
- **Web Interface**: Flask + template untuk antarmuka fungsional.
- **Persistensi**: operasi CRUD menggunakan SQLAlchemy dan database MySQL.

## Instalasi

1. Buat virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Instal dependensi:
   ```bash
   pip install -r requirements.txt
   ```
3. Siapkan file `.env` di root untuk konfigurasi database jika diperlukan.

## Konfigurasi Database

Aplikasi mendukung MySQL (XAMPP atau MySQL standalone). Pastikan database dibuat dan environment variable `SQLALCHEMY_DATABASE_URI` dikonfigurasi jika Anda menggunakan `.env`.

## Menjalankan Aplikasi

```bash
python app.py
```

Akses aplikasi di `http://127.0.0.1:5000/`.

## Export CSV

Route admin `/admin/export/csv` menghasilkan file `laporan_antrean.csv` berdasarkan antrean hari ini.

## Pengujian

Untuk memeriksa integrasi dasar jaringan dan route:

```bash
python tests/smoke_test.py
```

## Catatan

- Pastikan database sudah diinisialisasi sebelum menjalankan aplikasi.
- Panel admin menangani pelanggan, kendaraan, antrean, dan entri servis.
- UI dibuat untuk fokus pada fungsi operasional bengkel.

## Kontributor
* **[Farrel Gian]** - *Programmer Backend*
* **[Riky Wijaya]** - *Programmer Frontend & UI/UX*
* **[Micheal Valentino]** - *?*
* **[Francesco Efhraim]** - *?*