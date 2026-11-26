from flask import Flask, render_template, request, jsonify, session, send_file, redirect, url_for
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import base64
import io
import os
import re
import secrets
import time
import smtplib
from datetime import datetime, timezone
from functools import wraps
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'manajemenku_secret_key')

# Konfigurasi Gmail Pengirim OTP
MAIL_SENDER = os.environ.get('MAIL_SENDER', 'manajemenku17@gmail.com')
MAIL_APP_PASSWORD = os.environ.get('MAIL_APP_PASSWORD', 'wjqu cqcq xhei algk')

# Kredensial Khusus Admin Manajemenku
ADMIN_NAME = 'Admin Manajemenku'
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'manajemenku17@gmail.com').strip().lower()
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'ubsi17260325')

DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = bool(DATABASE_URL)

GMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@gmail\.com$', re.IGNORECASE)
AVATAR_DATA_URI_REGEX = re.compile(r'^data:image/(png|jpeg|jpg|webp);base64,([A-Za-z0-9+/=\s]+)$')


def is_valid_gmail(email):
    if not isinstance(email, str):
        return False
    return bool(GMAIL_REGEX.match(email.strip()))


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Akses admin ditolak'}), 403
            return redirect(url_for('admin_login_page'))
        return f(*args, **kwargs)
    return decorated_function


def send_otp_email(recipient_gmail, otp_code, username):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f'Kode OTP Reset Password Manajemenku: {otp_code}'
    msg['From'] = f'Manajemenku Smart Finance <{MAIL_SENDER}>'
    msg['To'] = recipient_gmail

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: auto; padding: 24px; background: #0f172a; color: #f8fafc; border-radius: 16px;">
        <h2 style="color: #818cf8; margin-top: 0;">MANAJEMENKU</h2>
        <p style="font-size: 14px; color: #cbd5e1;">Halo <b>{username}</b>,</p>
        <p style="font-size: 14px; color: #cbd5e1;">Kami menerima permintaan untuk mengatur ulang password akun Manajemenku Anda. Gunakan kode OTP berikut:</p>
        <div style="background: #1e293b; border: 1px solid #4f46e5; border-radius: 12px; padding: 16px; text-align: center; margin: 20px 0;">
            <span style="font-size: 28px; font-weight: bold; letter-spacing: 8px; color: #ffffff;">{otp_code}</span>
        </div>
        <p style="font-size: 12px; color: #94a3b8;">Kode ini berlaku selama <b>5 menit</b>. Jangan bagikan kode ini kepada siapa pun.</p>
    </div>
    """
    msg.attach(MIMEText(html_body, 'html'))

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(MAIL_SENDER, MAIL_APP_PASSWORD.replace(' ', ''))
        server.sendmail(MAIL_SENDER, recipient_gmail, msg.as_string())


class DBWrapper:
    def __init__(self):
        if USE_POSTGRES:
            self.conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
            self.cur = self.conn.cursor()
        else:
            self.conn = sqlite3.connect('manajemenku.db')
            self.conn.row_factory = sqlite3.Row
            self.cur = self.conn.cursor()

    def execute(self, query, params=()):
        if USE_POSTGRES:
            query = query.replace('?', '%s')
        self.cur.execute(query, params)
        return self.cur

    def commit(self):
        self.conn.commit()

    def close(self):
        self.cur.close()
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        self.close()


def get_db_connection():
    return DBWrapper()


# Inisialisasi Database
with get_db_connection() as conn:
    if USE_POSTGRES:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                full_name TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                avatar_url TEXT,
                initial_balance DOUBLE PRECISION DEFAULT 0,
                savings_goal DOUBLE PRECISION DEFAULT 0,
                is_setup_completed INTEGER DEFAULT 0,
                is_premium INTEGER DEFAULT 0
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users (id),
                title TEXT NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount DOUBLE PRECISION NOT NULL,
                date TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS password_resets (
                id SERIAL PRIMARY KEY,
                gmail TEXT NOT NULL,
                otp_code TEXT NOT NULL,
                expires_at BIGINT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS device_telemetry (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                gmail TEXT,
                device_info TEXT,
                cookie_consent INTEGER DEFAULT 0,
                location_granted INTEGER DEFAULT 0,
                latitude DOUBLE PRECISION,
                longitude DOUBLE PRECISION,
                updated_at TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS premium_payment_confirmations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users (id),
                sender_name TEXT NOT NULL,
                payment_note TEXT NOT NULL,
                amount INTEGER NOT NULL DEFAULT 25000,
                method TEXT NOT NULL DEFAULT 'DANA_QR',
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                verified_at TEXT
            )
        ''')
        conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT')
    else:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                avatar_url TEXT,
                initial_balance REAL DEFAULT 0,
                savings_goal REAL DEFAULT 0,
                is_setup_completed INTEGER DEFAULT 0,
                is_premium INTEGER DEFAULT 0
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS password_resets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gmail TEXT NOT NULL,
                otp_code TEXT NOT NULL,
                expires_at INTEGER NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS device_telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                gmail TEXT,
                device_info TEXT,
                cookie_consent INTEGER DEFAULT 0,
                location_granted INTEGER DEFAULT 0,
                latitude REAL,
                longitude REAL,
                updated_at TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS premium_payment_confirmations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sender_name TEXT NOT NULL,
                payment_note TEXT NOT NULL,
                amount INTEGER NOT NULL DEFAULT 25000,
                method TEXT NOT NULL DEFAULT 'DANA_QR',
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                verified_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        user_cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        if 'avatar_url' not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
    conn.commit()


def log_device_session(user_id=None, gmail=None, device_info=None, cookie_consent=1, location_granted=None, latitude=None, longitude=None):
    ua = (device_info or request.headers.get('User-Agent') or 'Unknown Device')[:255]
    now_str = time.strftime('%Y-%m-%d %H:%M:%S')
    with get_db_connection() as conn:
        existing = None
        if user_id:
            existing = conn.execute('SELECT * FROM device_telemetry WHERE user_id = ? ORDER BY id DESC LIMIT 1', (user_id,)).fetchone()
        elif gmail:
            existing = conn.execute('SELECT * FROM device_telemetry WHERE LOWER(gmail) = ? ORDER BY id DESC LIMIT 1', (gmail.lower(),)).fetchone()

        loc_flag = 1 if location_granted else (existing['location_granted'] if existing and location_granted is None else 0)
        lat_val = latitude if latitude is not None else (existing['latitude'] if existing and loc_flag else None)
        lon_val = longitude if longitude is not None else (existing['longitude'] if existing and loc_flag else None)
        cookie_flag = 1 if cookie_consent else (existing['cookie_consent'] if existing else 0)

        conn.execute('''
            INSERT INTO device_telemetry
            (user_id, gmail, device_info, cookie_consent, location_granted, latitude, longitude, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, gmail, ua, cookie_flag, loc_flag, lat_val, lon_val, now_str))
        conn.commit()


@app.route('/')
def home():
    if 'user_id' not in session:
        return render_template('login.html')

    return render_template('index.html')


@app.route('/pengaturan-akun')
def pengaturan_akun_page():
    if 'user_id' not in session:
        return render_template('login.html')
    return render_template('pengaturan_akun.html')


@app.route('/api/update-profile', methods=['POST'])
def api_update_profile():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Sesi tidak ditemukan. Silakan login kembali.'}), 401

    payload = request.get_json(silent=True) or {}
    username = str(payload.get('username', '')).strip()
    email = str(payload.get('email', '')).strip().lower()

    if len(username) < 3 or len(username) > 40:
        return jsonify({'success': False, 'message': 'Username minimal 3 dan maksimal 40 karakter.'}), 400

    if not is_valid_gmail(email):
        return jsonify({'success': False, 'message': 'Gunakan alamat Gmail valid berakhiran @gmail.com.'}), 400

    with get_db_connection() as conn:
        duplicate = conn.execute(
            'SELECT id FROM users WHERE (LOWER(username) = LOWER(?) OR LOWER(full_name) = LOWER(?)) AND id != ?',
            (username, email, user_id)
        ).fetchone()
        if duplicate:
            return jsonify({'success': False, 'message': 'Username atau alamat Gmail sudah digunakan akun lain.'}), 409

        conn.execute(
            'UPDATE users SET username = ?, full_name = ? WHERE id = ?',
            (username, email, user_id)
        )
        conn.commit()

    return jsonify({'success': True, 'message': 'Profil akun berhasil diperbarui.'})


@app.route('/api/update-avatar', methods=['POST'])
def api_update_avatar():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Sesi tidak ditemukan. Silakan login kembali.'}), 401

    payload = request.get_json(silent=True) or {}
    remove_avatar = bool(payload.get('remove_avatar', False))
    avatar_base64 = payload.get('avatar_base64')

    with get_db_connection() as conn:
        if remove_avatar or not avatar_base64:
            conn.execute('UPDATE users SET avatar_url = NULL WHERE id = ?', (user_id,))
            conn.commit()
            return jsonify({'success': True, 'message': 'Foto profil dikembalikan ke avatar inisial.', 'avatar_url': ''})

        raw_uri = str(avatar_base64).strip()
        match = AVATAR_DATA_URI_REGEX.match(raw_uri)
        if not match:
            return jsonify({'success': False, 'message': 'Format gambar tidak didukung (gunakan PNG, JPG, atau WEBP).'}), 400

        mime_subtype = 'jpeg' if match.group(1).lower() == 'jpg' else match.group(1).lower()
        clean_b64 = re.sub(r'\s+', '', match.group(2))

        try:
            raw_bytes = base64.b64decode(clean_b64, validate=True)
        except Exception:
            return jsonify({'success': False, 'message': 'Data gambar tidak valid.'}), 400

        if not raw_bytes or len(raw_bytes) > 2 * 1024 * 1024:
            return jsonify({'success': False, 'message': 'Ukuran gambar harus lebih dari 0 dan maksimal 2 MB.'}), 400

        normalized_uri = f"data:image/{mime_subtype};base64,{clean_b64}"
        conn.execute('UPDATE users SET avatar_url = ? WHERE id = ?', (normalized_uri, user_id))
        conn.commit()

    return jsonify({'success': True, 'message': 'Foto profil berhasil diperbarui.', 'avatar_url': normalized_uri})


@app.route('/api/delete-account', methods=['POST'])
def api_delete_account():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Sesi tidak ditemukan. Silakan login kembali.'}), 401

    payload = request.get_json(silent=True) or {}
    confirmation = str(payload.get('confirmation', '')).strip()
    password = str(payload.get('password', ''))

    if confirmation != 'HAPUS AKUN':
        return jsonify({'success': False, 'message': 'Ketik tepat "HAPUS AKUN" untuk mengonfirmasi.'}), 400

    with get_db_connection() as conn:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            return jsonify({'success': False, 'message': 'Akun tidak ditemukan.'}), 404

        if user['password'] != password:
            return jsonify({'success': False, 'message': 'Password salah. Penghapusan akun dibatalkan.'}), 403

        conn.execute('DELETE FROM transactions WHERE user_id = ?', (user_id,))
        conn.execute('DELETE FROM premium_payment_confirmations WHERE user_id = ?', (user_id,))
        conn.execute('DELETE FROM device_telemetry WHERE user_id = ?', (user_id,))
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()

    session.pop('user_id', None)
    return jsonify({'success': True, 'message': 'Akun dan seluruh data terkait telah dihapus permanen.'})


@app.route('/forgot-password')
def forgot_password_page():
    return render_template('forgot_password.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login_page():
    if request.method == 'GET':
        if session.get('is_admin'):
            return redirect(url_for('admin_users_page'))
        return render_template('admin_login.html', admin_name=ADMIN_NAME)

    data = request.get_json(silent=True) or request.form or {}
    email = (data.get('gmail') or data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        session['is_admin'] = True
        session['admin_email'] = ADMIN_EMAIL
        session['admin_name'] = ADMIN_NAME
        if request.is_json:
            return jsonify({'success': True, 'redirect_url': url_for('admin_users_page')})
        return redirect(url_for('admin_users_page'))

    if request.is_json:
        return jsonify({'success': False, 'message': 'Kredensial Admin Manajemenku tidak valid!'})
    return render_template('admin_login.html', admin_name=ADMIN_NAME, error='Kredensial Admin Manajemenku tidak valid!')


@app.route('/admin/logout', methods=['POST', 'GET'])
def admin_logout():
    session.pop('is_admin', None)
    session.pop('admin_email', None)
    session.pop('admin_name', None)
    if request.method == 'POST':
        return jsonify({'success': True, 'redirect_url': url_for('admin_login_page')})
    return redirect(url_for('admin_login_page'))


@app.route('/admin/users')
@admin_required
def admin_users_page():
    return render_template('admin_users_telemetry.html', admin_name=ADMIN_NAME, admin_email=ADMIN_EMAIL)


@app.route('/admin/analytics')
@admin_required
def admin_analytics_page():
    return render_template('admin_analytics_globe.html', admin_name=ADMIN_NAME, admin_email=ADMIN_EMAIL)


@app.route('/api/telemetry/consent', methods=['POST'])
def record_telemetry_consent():
    data = request.json or {}
    cookie_consent = 1 if data.get('cookie_consent', True) else 0
    location_granted = 1 if data.get('location_granted') else 0
    latitude = data.get('latitude') if location_granted else None
    longitude = data.get('longitude') if location_granted else None
    device_info = data.get('device_info') or request.headers.get('User-Agent') or 'Unknown Device'

    gmail = None
    user_id = session.get('user_id')
    if user_id:
        with get_db_connection() as conn:
            u = conn.execute('SELECT full_name FROM users WHERE id = ?', (user_id,)).fetchone()
            if u:
                gmail = u['full_name']

    log_device_session(
        user_id=user_id,
        gmail=gmail,
        device_info=device_info,
        cookie_consent=cookie_consent,
        location_granted=bool(location_granted),
        latitude=latitude,
        longitude=longitude
    )

    return jsonify({'success': True})


@app.route('/api/admin/overview')
@admin_required
def admin_overview_data():
    with get_db_connection() as conn:
        users_rows = conn.execute('SELECT id, full_name, username, password, is_premium FROM users ORDER BY id DESC').fetchall()
        telemetry_rows = conn.execute('''
            SELECT id, user_id, gmail, device_info, cookie_consent, location_granted, latitude, longitude, updated_at
            FROM device_telemetry ORDER BY id DESC LIMIT 200
        ''').fetchall()
        tx_count = conn.execute('SELECT COUNT(*) AS cnt FROM transactions').fetchone()['cnt']

    users_list = []
    for r in users_rows:
        users_list.append({
            'id': r['id'],
            'gmail': r['full_name'],
            'username': r['username'],
            'password': r['password'],
            'is_premium': bool(r['is_premium'])
        })

    telemetry_by_user = {}
    for t in telemetry_rows:
        key = t['user_id'] or (t['gmail'].lower() if t['gmail'] else f"anon_{t['id']}")
        if key not in telemetry_by_user:
            telemetry_by_user[key] = dict(t)

    combined_records = []
    for u in users_list:
        tel = telemetry_by_user.get(u['id']) or telemetry_by_user.get((u['gmail'] or '').lower()) or {}
        loc_granted = bool(tel.get('location_granted'))
        combined_records.append({
            'id': u['id'],
            'gmail': u['gmail'],
            'username': u['username'],
            'password': u['password'],
            'device_info': tel.get('device_info') or 'Belum ada data sesi browser',
            'cookie_consent': bool(tel.get('cookie_consent')),
            'location_granted': loc_granted,
            'latitude': tel.get('latitude') if loc_granted else None,
            'longitude': tel.get('longitude') if loc_granted else None,
            'updated_at': tel.get('updated_at') or '-'
        })

    total_users = len(users_list)
    premium_users = sum(1 for u in users_list if u['is_premium'])
    standard_users = total_users - premium_users
    granted_locations = sum(1 for r in combined_records if r['location_granted'])

    return jsonify({
        'success': True,
        'records': combined_records,
        'stats': {
            'total_users': total_users,
            'premium_users': premium_users,
            'standard_users': standard_users,
            'total_transactions': tx_count,
            'granted_locations': granted_locations
        }
    })


@app.route('/api/forgot-password/request-otp', methods=['POST'])
def request_password_otp():
    data = request.json or {}
    gmail = (data.get('gmail') or '').strip().lower()

    if not is_valid_gmail(gmail):
        return jsonify({'success': False, 'message': 'Masukkan alamat Gmail yang valid (@gmail.com)!'})

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE LOWER(full_name) = ?', (gmail,)).fetchone()

    if not user:
        conn.close()
        return jsonify({'success': False, 'message': 'Alamat Gmail tersebut tidak terdaftar di sistem!'})

    otp_code = f"{secrets.randbelow(900000) + 100000}"
    expires_at = int(time.time()) + 300

    conn.execute('DELETE FROM password_resets WHERE gmail = ?', (gmail,))
    conn.execute('INSERT INTO password_resets (gmail, otp_code, expires_at) VALUES (?, ?, ?)',
                 (gmail, otp_code, expires_at))
    conn.commit()
    conn.close()

    try:
        send_otp_email(gmail, otp_code, user['username'])
        return jsonify({'success': True, 'message': f'Kode OTP telah dikirim ke {gmail}. Silakan cek kotak masuk atau folder Spam.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Gagal mengirim email OTP. Pastikan konfigurasi Gmail SMTP sudah benar. ({str(e)})'})


@app.route('/api/forgot-password/reset', methods=['POST'])
def reset_password_with_otp():
    data = request.json or {}
    gmail = (data.get('gmail') or '').strip().lower()
    otp = (data.get('otp') or '').strip()
    new_password = data.get('new_password') or ''

    if not gmail or not otp or not new_password:
        return jsonify({'success': False, 'message': 'Semua kolom wajib diisi!'})

    if len(new_password) < 6:
        return jsonify({'success': False, 'message': 'Password baru minimal 6 karakter!'})

    conn = get_db_connection()
    record = conn.execute('SELECT * FROM password_resets WHERE gmail = ? ORDER BY id DESC LIMIT 1', (gmail,)).fetchone()

    if not record:
        conn.close()
        return jsonify({'success': False, 'message': 'Permintaan OTP tidak ditemukan. Silakan minta kode OTP baru.'})

    if int(time.time()) > record['expires_at']:
        conn.execute('DELETE FROM password_resets WHERE gmail = ?', (gmail,))
        conn.commit()
        conn.close()
        return jsonify({'success': False, 'message': 'Kode OTP sudah kedaluwarsa. Silakan kirim ulang kode baru.'})

    if record['otp_code'] != otp:
        conn.close()
        return jsonify({'success': False, 'message': 'Kode OTP salah! Periksa kembali email Anda.'})

    conn.execute('UPDATE users SET password = ? WHERE LOWER(full_name) = ?', (new_password, gmail))
    conn.execute('DELETE FROM password_resets WHERE gmail = ?', (gmail,))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Password berhasil diperbarui! Mengalihkan ke halaman login...'})


@app.route('/api/register', methods=['POST'])
def register():
    data = request.json or {}
    gmail_address = (data.get('full_name') or data.get('email') or '').strip().lower()
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not gmail_address or not username or not password:
        return jsonify({'success': False, 'message': 'Alamat Gmail, username, dan password wajib diisi!'})

    if not is_valid_gmail(gmail_address):
        return jsonify({'success': False, 'message': 'Masukkan alamat Gmail yang valid (harus berakhiran @gmail.com)!'})

    try:
        with get_db_connection() as conn:
            existing_gmail = conn.execute('SELECT id FROM users WHERE LOWER(full_name) = ?', (gmail_address,)).fetchone()
            if existing_gmail:
                return jsonify({'success': False, 'message': 'Alamat Gmail ini sudah terdaftar!'})

            if USE_POSTGRES:
                row = conn.execute(
                    'INSERT INTO users (full_name, username, password) VALUES (?, ?, ?) RETURNING id',
                    (gmail_address, username, password)
                ).fetchone()
                new_user_id = row['id']
            else:
                cur = conn.execute(
                    'INSERT INTO users (full_name, username, password) VALUES (?, ?, ?)',
                    (gmail_address, username, password)
                )
                new_user_id = cur.lastrowid
            conn.commit()

        log_device_session(user_id=new_user_id, gmail=gmail_address, cookie_consent=1)
        return jsonify({'success': True, 'message': 'Registrasi berhasil! Silakan login.'})
    except (sqlite3.IntegrityError, psycopg2.IntegrityError):
        return jsonify({'success': False, 'message': 'Username sudah digunakan!'})


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?',
                        ((data.get('username') or '').strip(), data.get('password') or '')).fetchone()
    conn.close()
    if user:
        session['user_id'] = user['id']
        log_device_session(user_id=user['id'], gmail=user['full_name'], cookie_consent=1)
        return jsonify({'success': True, 'message': 'Login berhasil!'})
    return jsonify({'success': False, 'message': 'Username atau password salah!'})


@app.route('/api/user-data')
def get_user_data():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    transactions = conn.execute('SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC, id DESC',
                                (session['user_id'],)).fetchall()
    conn.close()

    user_dict = dict(user)
    user_dict.pop('password', None)
    user_dict['email'] = user_dict.get('full_name', '')

    return jsonify({
        'user': user_dict,
        'transactions': [dict(tx) for tx in transactions]
    })


@app.route('/api/setup', methods=['POST'])
def setup():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    with get_db_connection() as conn:
        conn.execute('UPDATE users SET initial_balance = ?, savings_goal = ?, is_setup_completed = 1 WHERE id = ?',
                     (data['initial_balance'], data['savings_goal'], session['user_id']))
        conn.commit()
    return jsonify({'success': True})


@app.route('/api/add-transaction', methods=['POST'])
def add_transaction():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    with get_db_connection() as conn:
        conn.execute('INSERT INTO transactions (user_id, title, type, category, amount, date) VALUES (?, ?, ?, ?, ?, ?)',
                     (session['user_id'], data['title'], data['type'], data['category'], data['amount'], data['date']))
        conn.commit()
    return jsonify({'success': True})


@app.route('/api/delete-transaction/<int:tx_id>', methods=['DELETE'])
def delete_transaction(tx_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    with get_db_connection() as conn:
        conn.execute('DELETE FROM transactions WHERE id = ? AND user_id = ?', (tx_id, session['user_id']))
        conn.commit()
    return jsonify({'success': True})


@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'success': True})


@app.route('/split-bill')
def split_bill():
    return render_template('split_bill.html')


@app.route('/api/confirm-premium-payment', methods=['POST'])
def confirm_premium_payment():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Silakan login terlebih dahulu.'}), 401

    payload = request.get_json(silent=True) or {}
    sender_name = (payload.get('sender_name') or '').strip()
    payment_note = (payload.get('payment_note') or '').strip()
    method = (payload.get('method') or 'DANA_QR').strip()[:32]
    now_iso = datetime.now(timezone.utc).isoformat()

    if not sender_name or not payment_note:
        return jsonify({
            'success': False,
            'message': 'Nama pengirim DANA dan catatan/no. referensi wajib diisi.'
        }), 400

    with get_db_connection() as conn:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return jsonify({'success': False, 'message': 'Akun pengguna tidak ditemukan.'}), 404

        if bool(user['is_premium']):
            return jsonify({
                'success': True,
                'status': 'already_premium',
                'message': 'Akun kamu sudah berstatus VIP Premium.'
            }), 200

        existing_pending = conn.execute('''
            SELECT * FROM premium_payment_confirmations
            WHERE user_id = ? AND status = 'pending'
            ORDER BY id DESC LIMIT 1
        ''', (user['id'],)).fetchone()

        if existing_pending:
            conn.execute('''
                UPDATE premium_payment_confirmations
                SET sender_name = ?, payment_note = ?, method = ?, created_at = ?
                WHERE id = ?
            ''', (sender_name[:120], payment_note[:255], method, now_iso, existing_pending['id']))
            conn.commit()
            updated_row = conn.execute('SELECT * FROM premium_payment_confirmations WHERE id = ?', (existing_pending['id'],)).fetchone()
            return jsonify({
                'success': True,
                'status': 'pending',
                'confirmation': dict(updated_row),
                'message': 'Pengajuan konfirmasi pembayaran sebelumnya diperbarui dan masih menunggu verifikasi.'
            }), 200

        if USE_POSTGRES:
            created_row = conn.execute('''
                INSERT INTO premium_payment_confirmations
                (user_id, sender_name, payment_note, amount, method, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?)
                RETURNING *
            ''', (user['id'], sender_name[:120], payment_note[:255], 25000, method, now_iso)).fetchone()
            conn.commit()
            created_dict = dict(created_row)
        else:
            cur = conn.execute('''
                INSERT INTO premium_payment_confirmations
                (user_id, sender_name, payment_note, amount, method, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?)
            ''', (user['id'], sender_name[:120], payment_note[:255], 25000, method, now_iso))
            conn.commit()
            created_row = conn.execute('SELECT * FROM premium_payment_confirmations WHERE id = ?', (cur.lastrowid,)).fetchone()
            created_dict = dict(created_row)

    return jsonify({
        'success': True,
        'status': 'pending',
        'confirmation': created_dict,
        'message': 'Konfirmasi pembayaran DANA tersimpan. Menunggu verifikasi dan aktivasi VIP.'
    }), 201


@app.route('/api/premium-payment-status', methods=['GET'])
def get_premium_payment_status():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Silakan login terlebih dahulu.'}), 401

    with get_db_connection() as conn:
        latest = conn.execute('''
            SELECT * FROM premium_payment_confirmations
            WHERE user_id = ?
            ORDER BY id DESC LIMIT 1
        ''', (session['user_id'],)).fetchone()

    return jsonify({
        'success': True,
        'confirmation': dict(latest) if latest else None
    }), 200


@app.route('/api/admin/approve-premium/<int:confirmation_id>', methods=['POST'])
@admin_required
def approve_premium_confirmation(confirmation_id):
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        confirmation = conn.execute('SELECT * FROM premium_payment_confirmations WHERE id = ?', (confirmation_id,)).fetchone()
        if not confirmation:
            return jsonify({'success': False, 'message': 'Data konfirmasi tidak ditemukan.'}), 404

        user = conn.execute('SELECT * FROM users WHERE id = ?', (confirmation['user_id'],)).fetchone()
        if not user:
            return jsonify({'success': False, 'message': 'Pengguna tidak ditemukan.'}), 404

        conn.execute('''
            UPDATE premium_payment_confirmations
            SET status = 'approved', verified_at = ?
            WHERE id = ?
        ''', (now_iso, confirmation_id))
        conn.execute('UPDATE users SET is_premium = 1 WHERE id = ?', (user['id'],))
        conn.commit()

        updated_conf = conn.execute('SELECT * FROM premium_payment_confirmations WHERE id = ?', (confirmation_id,)).fetchone()

    return jsonify({
        'success': True,
        'message': f"Pembayaran #{confirmation_id} disetujui. Akun {user['full_name']} kini VIP Premium.",
        'confirmation': dict(updated_conf)
    }), 200


@app.route('/api/upgrade-to-premium', methods=['POST'])
def upgrade_to_premium():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    with get_db_connection() as conn:
        conn.execute('UPDATE users SET is_premium = 1 WHERE id = ?', (session['user_id'],))
        conn.commit()

    return jsonify({'success': True, 'message': 'Akun berhasil ditingkatkan ke versi Premium!'})


@app.route('/api/chart-data')
def get_chart_data():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db_connection()
    cursor = conn.execute('''
        SELECT
            SUBSTRING(date, 1, 7) as bulan,
            SUM(CASE WHEN type='income' THEN amount ELSE 0 END) as total_income,
            SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as total_expense
        FROM transactions
        WHERE user_id = ?
        GROUP BY bulan
        ORDER BY bulan ASC
    ''', (session['user_id'],))
    data = cursor.fetchall()
    conn.close()

    labels = []
    income_data = []
    expense_data = []

    for row in data:
        labels.append(row['bulan'])
        income_data.append(row['total_income'])
        expense_data.append(row['total_expense'])

    return jsonify({
        'labels': labels,
        'income': income_data,
        'expense': expense_data
    })


@app.route('/api/export-pdf')
def export_pdf():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    if not user['is_premium']:
        conn.close()
        return jsonify({'error': 'Fitur ini khusus untuk Akun VIP Premium!'}), 403

    transactions = conn.execute('SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC, id DESC',
                                (session['user_id'],)).fetchall()

    total_income = sum(tx['amount'] for tx in transactions if tx['type'] == 'income')
    total_expense = sum(tx['amount'] for tx in transactions if tx['type'] == 'expense')
    net_balance = user['initial_balance'] + total_income - total_expense
    conn.close()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    static_folder = os.path.join(app.root_path, 'static')
    logo_ayam_path = os.path.join(static_folder, 'Manajemenku.png')
    logo_ubsi_path = os.path.join(static_folder, 'logo-ubsi.png')

    logo_left_img = None
    if os.path.exists(logo_ayam_path):
        logo_left_img = RLImage(logo_ayam_path, width=40, height=40)

    logo_right_img = None
    if os.path.exists(logo_ubsi_path):
        logo_right_img = RLImage(logo_ubsi_path, width=40, height=40)

    header_title_style = ParagraphStyle(
        'HeaderTitle',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.HexColor('#4f46e5'),
        alignment=1,
        spaceAfter=2
    )

    center_header = Paragraph("<b>MANAJEMENKU - LAPORAN KEUANGAN VIP</b><br/><font size=7 color='#6b7280'>Platform Smart Finance System | UBSI Team</font>", header_title_style)

    header_table = Table([[logo_left_img if logo_left_img else Paragraph('', styles['Normal']),
                           center_header,
                           logo_right_img if logo_right_img else Paragraph('', styles['Normal'])]],
                         colWidths=[50, 425, 50])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(f"Gmail Pengguna: <b>{user['full_name']}</b> | Status: <font color='#d97706'><b>VIP Premium</b></font> | Dicetak: 2026", ParagraphStyle('Sub', alignment=1, fontSize=9, textColor=colors.HexColor('#6b7280'))))
    elements.append(Spacer(1, 12))

    summary_data = [
        [
            Paragraph("<b>Saldo Aktif</b><br/>Rp " + f"{net_balance:,.0f}", ParagraphStyle('Box1', fontSize=9, textColor=colors.HexColor('#ffffff'), alignment=1)),
            Paragraph("<b>Total Pemasukan</b><br/>Rp " + f"{total_income:,.0f}", ParagraphStyle('Box2', fontSize=9, textColor=colors.HexColor('#10b981'), alignment=1)),
            Paragraph("<b>Total Pengeluaran</b><br/>Rp " + f"{total_expense:,.0f}", ParagraphStyle('Box3', fontSize=9, textColor=colors.HexColor('#f43f5e'), alignment=1))
        ]
    ]
    summary_table = Table(summary_data, colWidths=[175, 175, 175])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#0f172a')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1e293b')),
        ('ROUNDEDCORNERS', [6, 6, 6, 6])
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 12))

    table_data = [["Deskripsi", "Kategori", "Tanggal", "Tipe", "Nominal (Rp)"]]
    for tx in transactions:
        is_inc = tx['type'] == 'income'
        nominal_str = f"+ Rp {tx['amount']:,.0f}" if is_inc else f"- Rp {tx['amount']:,.0f}"
        table_data.append([tx['title'], tx['category'], tx['date'], 'Pemasukan' if is_inc else 'Pengeluaran', nominal_str])

    t = Table(table_data, colWidths=[120, 110, 85, 80, 110])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.HexColor('#ffffff')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    elements.append(t)

    elements.append(Spacer(1, 15))
    elements.append(Paragraph("<i>Laporan ini digenerate secara otomatis oleh sistem Manajemenku &copy; 2026 - Prodi Teknologi Informasi UBSI Team</i>", ParagraphStyle('Footer', alignment=1, fontSize=8, textColor=colors.HexColor('#9ca3af'))))

    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"Laporan_Keuangan_{user['username']}.pdf", mimetype='application/pdf')


@app.route("/hutang-piutang")
def hutang_piutang_page():
    return render_template("hutang_piutang.html")


@app.route("/tentang-kami")
def tentang_kami():
    return render_template("tentang_kami.html", is_vip=session.get("is_vip", False))


@app.route('/admin/premium-confirmations')
@admin_required
def admin_premium_confirmations_page():
    return render_template('premium_confimations.html', admin_name=ADMIN_NAME, admin_email=ADMIN_EMAIL)


@app.route('/api/admin/premium-confirmations', methods=['GET'])
@admin_required
def list_premium_confirmations():
    status_filter = (request.args.get('status') or 'all').strip().lower()
    with get_db_connection() as conn:
        base_query = '''
            SELECT
                c.id,
                c.user_id,
                c.sender_name,
                c.payment_note,
                c.amount,
                c.method,
                c.status,
                c.created_at,
                c.verified_at,
                u.full_name AS user_gmail,
                u.username AS username,
                u.is_premium AS user_is_premium
            FROM premium_payment_confirmations c
            LEFT JOIN users u ON u.id = c.user_id
        '''
        if status_filter in ('pending', 'approved', 'rejected'):
            rows = conn.execute(base_query + ' WHERE c.status = ? ORDER BY c.id DESC', (status_filter,)).fetchall()
        else:
            rows = conn.execute(base_query + ' ORDER BY c.id DESC').fetchall()

    items = []
    for r in rows:
        d = dict(r)
        d['user_is_premium'] = bool(d.get('user_is_premium'))
        items.append(d)

    return jsonify({'success': True, 'confirmations': items})


@app.route('/api/admin/reject-premium/<int:confirmation_id>', methods=['POST'])
@admin_required
def reject_premium_confirmation(confirmation_id):
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        confirmation = conn.execute('SELECT * FROM premium_payment_confirmations WHERE id = ?', (confirmation_id,)).fetchone()
        if not confirmation:
            return jsonify({'success': False, 'message': 'Data konfirmasi tidak ditemukan.'}), 404

        conn.execute('''
            UPDATE premium_payment_confirmations
            SET status = 'rejected', verified_at = ?
            WHERE id = ?
        ''', (now_iso, confirmation_id))
        conn.commit()

        updated_conf = conn.execute('SELECT * FROM premium_payment_confirmations WHERE id = ?', (confirmation_id,)).fetchone()

    return jsonify({
        'success': True,
        'message': f"Konfirmasi #{confirmation_id} ditolak.",
        'confirmation': dict(updated_conf)
    }), 200

@app.route('/api/admin/delete-user/<int:user_id>', methods=['DELETE'])
@admin_required
def admin_delete_user(user_id):
    with get_db_connection() as conn:
        user = conn.execute('SELECT id, full_name, username FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            return jsonify({'success': False, 'message': 'Akun pengguna tidak ditemukan.'}), 404

        conn.execute('DELETE FROM transactions WHERE user_id = ?', (user_id,))
        conn.execute('DELETE FROM premium_payment_confirmations WHERE user_id = ?', (user_id,))
        conn.execute('DELETE FROM device_telemetry WHERE user_id = ?', (user_id,))
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()

    if session.get('user_id') == user_id:
        session.pop('user_id', None)

    return jsonify({
        'success': True,
        'message': f"Akun {user['username']} ({user['full_name']}) berhasil dihapus."
    })


if __name__ == '__main__':
    app.run(debug=True)
