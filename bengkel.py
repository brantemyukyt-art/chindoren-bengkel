# bengkel.py
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, Response
from flask_login import login_required, current_user
from sqlalchemy import func, case
from datetime import date, timedelta, datetime
from io import StringIO
import csv

from models import db, Antrean, User, Layanan, Kendaraan, RiwayatServis, Merk, TipeKendaraan, Estimator
from decorators import admin_required
from wa_helper import kirim_whatsapp
from forms import AdminPelangganForm, AdminKendaraanForm, EntriServisForm

bengkel_bp = Blueprint('bengkel', __name__)

class QueueReporter:
    def __init__(self, queue_records):
        self._queue_records = queue_records

    def _format_row(self, antrean):
        nama = antrean.nama_guest or getattr(antrean, 'user', None) and antrean.user.nama or ''
        layanan = antrean.layanan.nama_layanan if antrean.layanan else ''
        tanggal = antrean.tanggal.strftime('%Y-%m-%d') if antrean.tanggal else ''
        return [
            antrean.nomor_antrean,
            nama,
            antrean.plat_nomor,
            layanan,
            antrean.status,
            tanggal,
        ]

    def _format_csv_line(self, row):
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(row)
        return buffer.getvalue()

    def generate_csv_data(self):
        headers = ['No Antrean', 'Nama', 'Plat', 'Layanan', 'Status', 'Tanggal']
        yield self._format_csv_line(headers)
        for antrean in self._queue_records:
            yield self._format_csv_line(self._format_row(antrean))

# ==========================================
# RUTE PUBLIK & PELANGGAN
# ==========================================

@bengkel_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('bengkel.admin_dashboard'))
    return render_template('dashboard.html', user=current_user)


@bengkel_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        current_user.receive_whatsapp_notifications = 'receive_whatsapp_notifications' in request.form
        try:
            db.session.commit()
            flash('Preferensi notifikasi WhatsApp berhasil diperbarui.', 'success')
        except Exception:
            db.session.rollback()
            flash('Gagal memperbarui preferensi notifikasi. Silakan coba lagi.', 'danger')
        return redirect(url_for('bengkel.settings'))

    return render_template('settings.html', user=current_user)


@bengkel_bp.route('/buku-servis')
@login_required
def buku_servis():
    kendaraan_list = Kendaraan.query.filter_by(user_id=current_user.id).order_by(Kendaraan.plat_nomor).all()
    for kendaraan in kendaraan_list:
        kendaraan.riwayat_servis = sorted(kendaraan.riwayat_servis, key=lambda item: item.tanggal_servis, reverse=True)
    return render_template('buku_servis.html', kendaraan_list=kendaraan_list)


@bengkel_bp.route('/booking', methods=['GET', 'POST'])
def booking():
    layanan = Layanan.query.order_by(Layanan.nama_layanan).all()
    kendaraan_list = []
    default_name = ''
    default_phone = ''
    default_vehicle = ''

    if current_user.is_authenticated:
        default_name = current_user.nama
        default_phone = current_user.no_hp
        kendaraan_list = Kendaraan.query.filter_by(user_id=current_user.id).order_by(Kendaraan.plat_nomor).all()
        if kendaraan_list:
            default_vehicle = kendaraan_list[0].plat_nomor

    if request.method == 'POST':
        nama = request.form.get('nama', '').strip()
        no_hp = request.form.get('no_hp', '').strip()
        plat_nomor = request.form.get('plat_nomor', '').strip()
        layanan_id = request.form.get('layanan_id')
        tanggal_booking = request.form.get('tanggal_booking')
        jam_booking = request.form.get('jam_booking')

        display_name = nama or (current_user.nama if current_user.is_authenticated else '')
        display_phone = no_hp or (current_user.no_hp if current_user.is_authenticated else '')

        if not display_name or not plat_nomor or not layanan_id:
            flash('Lengkapi semua data booking terlebih dahulu.', 'danger')
            return render_template('booking.html', layanan=layanan, kendaraan_list=kendaraan_list, default_name=default_name, default_phone=default_phone, default_vehicle=default_vehicle)

        if not current_user.is_authenticated and not display_phone:
            flash('Sebagai Guest, nomor HP wajib diisi agar kami bisa menghubungi Anda', 'danger')
            return redirect(url_for('bengkel.booking'))

        layanan_valid = Layanan.query.get(layanan_id)
        if not layanan_valid:
            flash('Layanan tidak valid atau tidak ditemukan.', 'danger')
            return redirect(url_for('bengkel.booking'))

        if not tanggal_booking or not jam_booking:
            flash('Tanggal dan waktu servis wajib dipilih!', 'danger')
            return redirect(url_for('bengkel.booking'))

        booking_date = date.fromisoformat(tanggal_booking)
        existing_bookings_count = Antrean.query.filter_by(tanggal=booking_date, jam=jam_booking).count()
        if existing_bookings_count >= 3:
            flash('Maaf, slot waktu pada jam tersebut sudah penuh. Silakan pilih jam lain', 'danger')
            return redirect(url_for('bengkel.booking'))

        hari_ini = date.today()
        jumlah_antrean_hari_ini = Antrean.query.filter_by(tanggal=hari_ini).count()
        nomor_baru = f"B-{jumlah_antrean_hari_ini + 1:03d}"

        try:
            antrean_baru = Antrean(
                nama_guest=display_name,
                plat_nomor=plat_nomor,
                layanan_id=layanan_id,
                nomor_antrean=nomor_baru,
                user_id=current_user.id if current_user.is_authenticated else None,
                tanggal=booking_date,
                jam=jam_booking,
            )
            db.session.add(antrean_baru)
            db.session.commit()
            flash(f'Booking berhasil dibuat untuk {display_name}. Jadwal Anda: {tanggal_booking} {jam_booking}.', 'success')
            return redirect(url_for('bengkel.live_tracking', id=antrean_baru.id))
        except Exception:
            db.session.rollback()
            flash('Terjadi kesalahan server saat menyimpan data. Silakan coba lagi.', 'danger')
            return redirect(url_for('bengkel.booking'))

    return render_template('booking.html', layanan=layanan, kendaraan_list=kendaraan_list, default_name=default_name, default_phone=default_phone, default_vehicle=default_vehicle)

@bengkel_bp.route('/tracking/<int:id>')
def live_tracking(id):
    antrean_user = Antrean.query.get_or_404(id)
    hari_ini = date.today()
    
    antrean_saat_ini = Antrean.query.filter_by(tanggal=hari_ini, status='Sedang Dikerjakan').first()
    nomor_saat_ini = antrean_saat_ini.nomor_antrean if antrean_saat_ini else "Belum Ada"

    # Logika Waktu Tunggu (Smart Queue)
    waktu_tunggu_menit = db.session.query(func.sum(Layanan.estimasi_durasi_menit))\
        .join(Antrean)\
        .filter(
            Antrean.tanggal == hari_ini,
            Antrean.status.in_(['Menunggu', 'Sedang Dikerjakan']),
            Antrean.id < antrean_user.id
        ).scalar() or 0

    eta_minutes = max(0, waktu_tunggu_menit + antrean_user.layanan.estimasi_durasi_menit)
    eta_text = f'{eta_minutes} menit'
    if eta_minutes >= 60:
        hours = eta_minutes // 60
        minutes = eta_minutes % 60
        eta_text = f'{hours} jam' + (f' {minutes} menit' if minutes else '')

    return render_template('tracking.html', 
                           antrean=antrean_user, 
                           antrean_saat_ini=nomor_saat_ini, 
                           waktu_tunggu=waktu_tunggu_menit,
                           eta_minutes=eta_minutes,
                           eta_text=eta_text)

@bengkel_bp.route('/api/estimasi', methods=['GET'])
def get_estimasi():
    merk = request.args.get('merk')
    tipe = request.args.get('tipe')
    keluhan = request.args.get('keluhan')

    q = Estimator.query.join(Merk).join(TipeKendaraan)
    q = q.filter(Merk.nama == merk, TipeKendaraan.nama == tipe, Estimator.keluhan == keluhan).first()
    if q:
        return jsonify({'rentang_harga': f"Rp {q.harga_min:,} - Rp {q.harga_max:,}"})
    return jsonify({'rentang_harga': 'Data belum tersedia, silakan hubungi admin.'})


# Estimator API endpoints for dependent dropdowns
@bengkel_bp.route('/api/estimator/merks')
def api_merks():
    merks = Merk.query.order_by(Merk.nama).all()
    return jsonify([{'id': m.id, 'nama': m.nama} for m in merks])


@bengkel_bp.route('/api/estimator/tipes')
def api_tipes():
    merk_id = request.args.get('merk_id')
    if not merk_id:
        return jsonify([])
    tipes = TipeKendaraan.query.filter_by(merk_id=merk_id).order_by(TipeKendaraan.nama).all()
    return jsonify([{'id': t.id, 'nama': t.nama} for t in tipes])


@bengkel_bp.route('/api/estimator/keluhan')
def api_keluhan():
    merk_id = request.args.get('merk_id', type=int)
    tipe_id = request.args.get('tipe_id', type=int)
    query = db.session.query(Estimator.keluhan).distinct()
    if merk_id is not None:
        query = query.filter(Estimator.merk_id == merk_id)
    if tipe_id is not None:
        query = query.filter(Estimator.tipe_id == tipe_id)
    keluhans = query.order_by(Estimator.keluhan).all()
    return jsonify([k[0] for k in keluhans])


@bengkel_bp.route('/api/estimator/services')
def api_estimator_services():
    services = Layanan.query.order_by(Layanan.nama_layanan).all()
    return jsonify([
        {
            'id': service.id,
            'nama_layanan': service.nama_layanan,
            'estimasi_harga': service.estimasi_harga,
            'estimasi_durasi_menit': service.estimasi_durasi_menit,
        }
        for service in services
    ])


@bengkel_bp.route('/api/estimator/price')
def api_price():
    merk_id = request.args.get('merk_id', type=int)
    tipe_id = request.args.get('tipe_id', type=int)
    keluhan = request.args.get('keluhan')
    if not merk_id or not tipe_id or not keluhan:
        return jsonify({'error': 'Parameter kurang'}), 400
    est = Estimator.query.filter(
        Estimator.merk_id == merk_id,
        Estimator.tipe_id == tipe_id,
        func.lower(Estimator.keluhan) == func.lower(keluhan.strip())
    ).first()
    if not est:
        return jsonify({'error': 'Data tidak ditemukan'}), 404
    return jsonify({'harga_min': est.harga_min, 'harga_max': est.harga_max})
    merk_id = request.args.get('merk_id')
    tipe_id = request.args.get('tipe_id')
    keluhan = request.args.get('keluhan')
    if not merk_id or not tipe_id or not keluhan:
        return jsonify({'error': 'Parameter kurang'}), 400
    est = Estimator.query.filter_by(merk_id=merk_id, tipe_id=tipe_id, keluhan=keluhan).first()
    if not est:
        return jsonify({'error': 'Data tidak ditemukan'}), 404
    return jsonify({'harga_min': est.harga_min, 'harga_max': est.harga_max})


@bengkel_bp.route('/estimasi')
def estimasi_page():
    return render_template('estimator.html')


@bengkel_bp.route('/layanan')
def layanan_page():
    layanan = Layanan.query.order_by(Layanan.nama_layanan).all()
    return render_template('layanan.html', layanan=layanan)


@bengkel_bp.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    hari_ini = date.today()
    antrean_list = Antrean.query.filter_by(tanggal=hari_ini).all()
    pelanggan_count = User.query.filter(User.role == 'pelanggan').count()
    admin_count = User.query.filter(User.role == 'admin').count()
    kendaraan_count = Kendaraan.query.count()
    menunggu_count = Antrean.query.filter_by(tanggal=hari_ini, status='Menunggu').count()
    sedang_count = Antrean.query.filter_by(tanggal=hari_ini, status='Sedang Dikerjakan').count()
    selesai_count = Antrean.query.filter_by(tanggal=hari_ini, status='Selesai').count()
    return render_template(
        'admin_dashboard.html',
        antrean_list=antrean_list,
        hari_ini=hari_ini,
        pelanggan_count=pelanggan_count,
        admin_count=admin_count,
        kendaraan_count=kendaraan_count,
        menunggu_count=menunggu_count,
        sedang_count=sedang_count,
        selesai_count=selesai_count,
    )


@bengkel_bp.route('/admin/antrean')
@admin_required
def admin_antrean():
    hari_ini = date.today()
    antrean_list = Antrean.query.filter_by(tanggal=hari_ini).order_by(
        case(
            (Antrean.status == 'Menunggu', 1),
            (Antrean.status == 'Sedang Dikerjakan', 2),
            else_=3
        ),
        Antrean.id
    ).all()
    antrean_saat_ini = Antrean.query.filter_by(tanggal=hari_ini, status='Sedang Dikerjakan').first()
    nomor_saat_ini = antrean_saat_ini.nomor_antrean if antrean_saat_ini else "Belum Ada"
    return render_template('admin_antrean.html', antrean_list=antrean_list, antrean_saat_ini=nomor_saat_ini)


@bengkel_bp.route('/admin/export/csv')
@admin_required
def export_antrean_csv():
    hari_ini = date.today()
    antrean_list = Antrean.query.filter_by(tanggal=hari_ini).order_by(Antrean.id).all()
    reporter = QueueReporter(antrean_list)
    csv_data = reporter.generate_csv_data()

    return Response(
        csv_data,
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=laporan_antrean.csv'
        }
    )


@bengkel_bp.route('/admin/quick-add', methods=['GET', 'POST'])
@admin_required
def quick_add_walkin():
    layanan = Layanan.query.order_by(Layanan.nama_layanan).all()
    if request.method == 'POST':
        nama = request.form.get('nama', '').strip()
        no_hp = request.form.get('no_hp', '').strip()
        plat_nomor = request.form.get('plat_nomor', '').strip()
        layanan_id = request.form.get('layanan_id', '').strip()

        if not nama or not no_hp or not plat_nomor or not layanan_id:
            flash('Semua field wajib diisi.', 'danger')
            return render_template('admin_quick_add.html', layanan=layanan)

        layanan_item = Layanan.query.get(layanan_id)
        if not layanan_item:
            flash('Layanan tidak valid.', 'danger')
            return render_template('admin_quick_add.html', layanan=layanan)

        try:
            hari_ini = date.today()
            jumlah_antrean_hari_ini = Antrean.query.filter_by(tanggal=hari_ini).count()
            nomor_baru = f"B-{jumlah_antrean_hari_ini + 1:03d}"
            antrean_baru = Antrean(
                nama_guest=nama,
                plat_nomor=plat_nomor,
                layanan_id=layanan_item.id,
                nomor_antrean=nomor_baru,
                user_id=None,
                tanggal=hari_ini,
                jam=datetime.now().strftime('%H:%M'),
                status='Menunggu'
            )
            db.session.add(antrean_baru)
            db.session.commit()
            flash('Walk-in berhasil ditambahkan ke antrean.', 'success')
            return redirect(url_for('bengkel.admin_antrean'))
        except Exception:
            db.session.rollback()
            flash('Gagal menambahkan walk-in.', 'danger')
            return render_template('admin_quick_add.html', layanan=layanan)

    return render_template('admin_quick_add.html', layanan=layanan)


@bengkel_bp.route('/admin/riwayat-servis')
@admin_required
def admin_riwayat_servis():
    riwayat_list = RiwayatServis.query.order_by(RiwayatServis.tanggal_servis.desc()).all()
    return render_template('admin_riwayat_servis.html', riwayat_list=riwayat_list)


# ==========================================
# RUTE KHUSUS ADMIN & MEKANIK (DILINDUNGI RBAC)
# ==========================================

@bengkel_bp.route('/admin/pelanggan')
@admin_required
def admin_pelanggan():
    pelanggan = User.query.filter_by(role='pelanggan').all()
    form = AdminPelangganForm()
    return render_template('admin_pelanggan.html', pelanggan=pelanggan, form=form)


@bengkel_bp.route('/admin/pelanggan/tambah', methods=['POST'])
@admin_required
def tambah_pelanggan():
    form = AdminPelangganForm()
    if form.validate_on_submit():
        user = User(
            nama=form.nama.data,
            email=form.email.data,
            no_hp=form.no_hp.data,
            role=form.role.data
        )
        if form.password.data:
            user.set_password(form.password.data)
        else:
            user.set_password('password123')
        try:
            db.session.add(user)
            db.session.commit()
            flash('Pelanggan berhasil ditambahkan.', 'success')
            return redirect(url_for('bengkel.admin_pelanggan'))
        except Exception:
            db.session.rollback()
            flash('Gagal menambahkan pelanggan. Silakan coba lagi.', 'danger')
    pelanggan = User.query.filter_by(role='pelanggan').all()
    return render_template('admin_pelanggan.html', pelanggan=pelanggan, form=form)


@bengkel_bp.route('/admin/pelanggan/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_pelanggan(id):
    user = User.query.get_or_404(id)
    form = AdminPelangganForm(obj=user)
    if form.validate_on_submit():
        user.nama = form.nama.data
        user.email = form.email.data
        user.no_hp = form.no_hp.data
        user.role = form.role.data
        if form.password.data:
            user.set_password(form.password.data)
        try:
            db.session.commit()
            flash('Pelanggan berhasil diperbarui.', 'success')
            return redirect(url_for('bengkel.admin_pelanggan'))
        except Exception:
            db.session.rollback()
            flash('Gagal memperbarui pelanggan. Silakan coba lagi.', 'danger')
            return render_template('admin_pelanggan_form.html', form=form, judul='Edit Pelanggan')
    return render_template('admin_pelanggan_form.html', form=form, judul='Edit Pelanggan')


@bengkel_bp.route('/admin/pelanggan/<int:id>/hapus', methods=['POST'])
@admin_required
def hapus_pelanggan(id):
    user = User.query.get_or_404(id)
    try:
        db.session.delete(user)
        db.session.commit()
        flash('Pelanggan berhasil dihapus.', 'success')
    except Exception:
        db.session.rollback()
        flash('Gagal menghapus pelanggan. Silakan coba lagi.', 'danger')
    return redirect(url_for('bengkel.admin_pelanggan'))


@bengkel_bp.route('/admin/kendaraan')
@admin_required
def admin_kendaraan():
    kendaraan = Kendaraan.query.all()
    return render_template('admin_kendaraan.html', kendaraan=kendaraan)


@bengkel_bp.route('/admin/kendaraan/tambah', methods=['GET', 'POST'])
@admin_required
def tambah_kendaraan():
    form = AdminKendaraanForm()
    form.user_id.choices = [(u.id, u.nama) for u in User.query.filter_by(role='pelanggan').all()]
    if form.validate_on_submit():
        kendaraan = Kendaraan(
            user_id=form.user_id.data,
            plat_nomor=form.plat_nomor.data,
            merk=form.merk.data,
            tipe=form.tipe.data,
            tahun=form.tahun.data
        )
        try:
            db.session.add(kendaraan)
            db.session.commit()
            flash('Kendaraan berhasil ditambahkan.', 'success')
            return redirect(url_for('bengkel.admin_kendaraan'))
        except Exception:
            db.session.rollback()
            flash('Gagal menambahkan kendaraan. Silakan coba lagi.', 'danger')
            return render_template('admin_kendaraan_form.html', form=form, judul='Tambah Kendaraan')
    return render_template('admin_kendaraan_form.html', form=form, judul='Tambah Kendaraan')


@bengkel_bp.route('/admin/kendaraan/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_kendaraan(id):
    kendaraan = Kendaraan.query.get_or_404(id)
    form = AdminKendaraanForm(obj=kendaraan)
    form.user_id.choices = [(u.id, u.nama) for u in User.query.filter_by(role='pelanggan').all()]
    if form.validate_on_submit():
        kendaraan.user_id = form.user_id.data
        kendaraan.plat_nomor = form.plat_nomor.data
        kendaraan.merk = form.merk.data
        kendaraan.tipe = form.tipe.data
        kendaraan.tahun = form.tahun.data
        try:
            db.session.commit()
            flash('Kendaraan berhasil diperbarui.', 'success')
            return redirect(url_for('bengkel.admin_kendaraan'))
        except Exception:
            db.session.rollback()
            flash('Gagal memperbarui kendaraan. Silakan coba lagi.', 'danger')
            return render_template('admin_kendaraan_form.html', form=form, judul='Edit Kendaraan')
    return render_template('admin_kendaraan_form.html', form=form, judul='Edit Kendaraan')


@bengkel_bp.route('/admin/kendaraan/<int:id>/hapus', methods=['POST'])
@admin_required
def hapus_kendaraan(id):
    kendaraan = Kendaraan.query.get_or_404(id)
    try:
        db.session.delete(kendaraan)
        db.session.commit()
        flash('Kendaraan berhasil dihapus.', 'success')
    except Exception:
        db.session.rollback()
        flash('Gagal menghapus kendaraan. Silakan coba lagi.', 'danger')
    return redirect(url_for('bengkel.admin_kendaraan'))


@bengkel_bp.route('/admin/entri-servis', methods=['GET', 'POST'])
@admin_required
def entri_servis():
    form = EntriServisForm()
    form.kendaraan_id.choices = [(k.id, f"{k.plat_nomor} - {k.merk} {k.tipe}") for k in Kendaraan.query.all()]
    if form.validate_on_submit():
        servis = RiwayatServis(
            kendaraan_id=form.kendaraan_id.data,
            mekanik=form.mekanik.data,
            kilometer=form.kilometer.data,
            tindakan=form.tindakan.data,
            sparepart=form.sparepart.data,
            replaced_parts=form.replaced_parts.data,
            cost_breakdown=form.cost_breakdown.data,
            next_service_recommendation=form.next_service_recommendation.data,
            total_biaya=form.total_biaya.data,
            jadwal_servis_berikutnya=date.today() + timedelta(days=60)
        )
        try:
            db.session.add(servis)
            db.session.commit()
            flash('Entri servis berhasil disimpan.', 'success')
            return redirect(url_for('bengkel.entri_servis'))
        except Exception:
            db.session.rollback()
            flash('Gagal menyimpan entri servis. Silakan coba lagi.', 'danger')
            return render_template('admin_entri.html', form=form)
    return render_template('admin_entri.html', form=form)


@bengkel_bp.route('/admin/antrean/<int:id>/status', methods=['POST'])
@admin_required
def update_status(id):
    antrean = Antrean.query.get_or_404(id)
    data = request.get_json(silent=True) or {}
    status_baru = data.get('status')

    if status_baru not in ['Menunggu', 'Sedang Dikerjakan', 'Selesai', 'Batal']:
        return jsonify({'error': 'Status tidak valid'}), 400

    antrean.status = status_baru
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Gagal memperbarui status antrean.'}), 500

    if status_baru == 'Selesai':
        nomor_hp = None
        nama_pelanggan = antrean.nama_guest or "Pelanggan"

        if antrean.user_id:
            user = User.query.get(antrean.user_id)
            if user:
                nomor_hp = user.no_hp
                nama_pelanggan = user.nama

        if nomor_hp:
            pesan_wa = (
                f"Halo {nama_pelanggan} 👋\n\n"
                f"Servis kendaraan Anda dengan plat *{antrean.plat_nomor}* (No. Antrean: {antrean.nomor_antrean}) "
                f"telah *SELESAI* dikerjakan.\n\n"
                f"Silakan menuju kasir untuk penyelesaian pembayaran. Terima kasih! 🛠️"
            )
            kirim_whatsapp(nomor_hp, pesan_wa)

    return jsonify({'pesan': 'Status berhasil diperbarui!', 'status_baru': antrean.status})


@bengkel_bp.route('/admin/antrean/<int:id>/selesai', methods=['POST'])
@admin_required
def selesaikan_antrean(id):
    antrean = Antrean.query.get_or_404(id)
    mekanik = request.form.get('mekanik', '').strip()
    kilometer = request.form.get('kilometer', '').strip()
    parts = request.form.get('parts', '').strip()
    cost = request.form.get('cost', '').strip()

    if not mekanik or not kilometer or not cost:
        return jsonify({'error': 'Mekanik, KM, dan biaya wajib diisi.'}), 400

    kendaraan = Kendaraan.query.filter_by(plat_nomor=antrean.plat_nomor).first()
    if not kendaraan:
        return jsonify({'error': 'Kendaraan tidak ditemukan untuk antrean ini.'}), 400

    try:
        total_biaya = int(cost)
        kilometer_value = int(kilometer)
    except ValueError:
        return jsonify({'error': 'KM dan biaya harus berupa angka.'}), 400

    riwayat = RiwayatServis(
        kendaraan_id=kendaraan.id,
        mekanik=mekanik,
        kilometer=kilometer_value,
        tindakan=f"Servis selesai dari antrean {antrean.nomor_antrean}",
        sparepart=parts or None,
        replaced_parts=parts or None,
        cost_breakdown=f"Biaya servis: Rp {total_biaya:,}",
        next_service_recommendation=None,
        total_biaya=total_biaya,
        jadwal_servis_berikutnya=date.today() + timedelta(days=60)
    )
    try:
        db.session.add(riwayat)
        antrean.status = 'Selesai'
        db.session.commit()
        return jsonify({'pesan': 'Antrean selesai dan riwayat servis tersimpan.'})
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Gagal menyimpan riwayat servis. Silakan coba lagi.'}), 500