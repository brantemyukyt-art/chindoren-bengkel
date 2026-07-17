# forms.py
import re

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, EqualTo, Length, Optional, NumberRange, ValidationError


class CustomEmail(object):
    def __init__(self, message=None):
        self.message = message or 'Format email tidak valid.'

    def __call__(self, form, field):
        if not field.data:
            return
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', field.data):
            raise ValidationError(self.message)


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message="Email wajib diisi."),
        CustomEmail(message="Format email tidak valid.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password wajib diisi.")
    ])
    submit = SubmitField('Masuk ke Akun')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message="Email wajib diisi."),
        CustomEmail(message="Format email tidak valid.")
    ])
    submit = SubmitField('Kirim Link Reset')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password Baru', validators=[
        DataRequired(message="Password wajib diisi."),
        Length(min=6, message="Password minimal 6 karakter.")
    ])
    konfirmasi_password = PasswordField('Konfirmasi Password', validators=[
        DataRequired(message="Konfirmasi password wajib diisi."),
        EqualTo('password', message="Konfirmasi password harus cocok dengan password di atas.")
    ])
    submit = SubmitField('Reset Password')


class RegisterForm(FlaskForm):
    nama = StringField('Nama Lengkap', validators=[
        DataRequired(message="Nama lengkap wajib diisi."),
        Length(min=2, max=100, message="Nama minimal 2 karakter.")
    ])
    email = StringField('Email', validators=[
        DataRequired(message="Email wajib diisi."),
        CustomEmail(message="Format email tidak valid.")
    ])
    no_hp = StringField('Nomor HP', validators=[
        DataRequired(message="Nomor HP wajib diisi."),
        Length(min=10, max=15, message="Nomor HP harus terdiri dari 10-15 digit.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password wajib diisi."),
        Length(min=6, message="Password minimal 6 karakter.")
    ])
    konfirmasi_password = PasswordField('Konfirmasi Password', validators=[
        DataRequired(message="Konfirmasi password wajib diisi."),
        EqualTo('password', message="Konfirmasi password harus cocok dengan password di atas.")
    ])
    submit = SubmitField('Daftar Akun Baru')


class AdminPelangganForm(FlaskForm):
    nama = StringField('Nama Lengkap', validators=[DataRequired(message="Nama lengkap wajib diisi."), Length(min=2, max=100, message="Nama minimal 2 karakter.")])
    email = StringField('Email', validators=[DataRequired(message="Email wajib diisi."), CustomEmail(message="Format email tidak valid.")])
    no_hp = StringField('Nomor HP', validators=[DataRequired(message="Nomor HP wajib diisi."), Length(min=10, max=15, message="Nomor HP harus terdiri dari 10-15 digit.")])
    password = PasswordField('Password', validators=[Optional(), Length(min=6, message="Password minimal 6 karakter.")])
    role = SelectField('Role', choices=[('pelanggan', 'Pelanggan'), ('admin', 'Admin/Mekanik')], validators=[DataRequired(message="Role harus dipilih.")])
    submit = SubmitField('Simpan Pelanggan')


class AdminKendaraanForm(FlaskForm):
    user_id = SelectField('Pelanggan', coerce=int, validators=[DataRequired(message="Pelanggan harus dipilih.")])
    plat_nomor = StringField('Plat Nomor', validators=[DataRequired(message="Plat nomor wajib diisi."), Length(min=3, max=15, message="Plat nomor tidak valid.")])
    merk = StringField('Merk', validators=[DataRequired(message="Merk wajib diisi."), Length(max=50)])
    tipe = StringField('Tipe', validators=[DataRequired(message="Tipe wajib diisi."), Length(max=50)])
    tahun = IntegerField('Tahun', validators=[DataRequired(message="Tahun wajib diisi."), NumberRange(min=1900, max=2100, message="Tahun tidak valid.")])
    submit = SubmitField('Simpan Kendaraan')


class EntriServisForm(FlaskForm):
    kendaraan_id = SelectField('Pilih Kendaraan', coerce=int, validators=[DataRequired(message="Kendaraan harus dipilih.")])
    mekanik = StringField('Mekanik', validators=[DataRequired(message="Nama mekanik wajib diisi."), Length(max=100)])
    kilometer = IntegerField('Kilometer', validators=[DataRequired(message="Kilometer wajib diisi."), NumberRange(min=0, max=999999, message="Kilometer tidak valid.")])
    tindakan = TextAreaField('Tindakan', validators=[DataRequired(message="Tindakan wajib diisi.")])
    sparepart = TextAreaField('Sparepart Lama', validators=[Optional()])
    replaced_parts = TextAreaField('Daftar Sparepart yang Diganti', validators=[Optional()])
    cost_breakdown = TextAreaField('Rincian Biaya', validators=[Optional()])
    next_service_recommendation = TextAreaField('Rekomendasi untuk Servis Berikutnya', validators=[Optional()])
    total_biaya = IntegerField('Total Biaya (Rp)', validators=[DataRequired(message="Total biaya wajib diisi."), NumberRange(min=0, message="Total biaya tidak valid.")])
    submit = SubmitField('Simpan Entri Servis')
