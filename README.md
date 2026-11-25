# MANAJEMENKU — Smart Finance System

**MANAJEMENKU** adalah aplikasi web **Smart Finance System** berbasis Python Flask untuk membantu pengelolaan keuangan pribadi dan harian secara praktis, terstruktur, dan transparan—mulai dari pencatatan arus kas, pemantauan saldo aktif, target tabungan, *split bill*, hingga catatan hutang dan piutang.

## Fitur Utama

* **Autentikasi & Keamanan Akun**: Registrasi validasi Gmail, login berbasis *session*, dan *Lupa Password* via kode OTP ke email.
* **Dashboard Keuangan**: Saldo aktif, total pemasukan, total pengeluaran, progres target tabungan, grafik bulanan, dan konverter mata uang.
* **Kalkulator Split Bill**: Mode **Bagi per Menu** dan **Bagi Rata**, lengkap dengan peserta, diskon, pajak, *service charge*, ongkir, dan rekap WhatsApp.
* **Catatan Hutang & Piutang**: Pencatatan hutang dan piutang agar lebih rapi dan tidak mudah terlupa.
* **Akun VIP & Ekspor PDF**: Upgrade akun VIP dan ekspor ringkasan laporan keuangan ke PDF.
* **Halaman Tentang Kami**: Profil aplikasi, latar belakang pengembangan, dan tim pengembang.

## Teknologi yang Digunakan

* **Backend**: Python, Flask
* **Database**: SQLite (`sqlite3`)
* **Frontend**: HTML5, Tailwind CSS, JavaScript
* **PDF Generator**: ReportLab

## Struktur Proyek

* `main.py` — Aplikasi utama Flask & *routing* API
* `requirements.txt` — Daftar dependensi Python
* `static/` — Aset gambar & logo (`Manajemenku.png`, dll.)
* `templates/` — Halaman HTML (`login`, `index`, `split_bill`, dll.)

## Cara Menjalankan di Lokal

1. Clone repository:
   `git clone https://github.com/nazaramru08-cyber/Manajemenku.git`
2. Masuk ke folder proyek:
   `cd Manajemenku`
3. Instal dependensi:
   `pip install -r requirements.txt`
4. Jalankan aplikasi:
   `python main.py`
5. Buka di browser:
   `http://127.0.0.1:5000`

## Tim Pengembang

Dikembangkan oleh mahasiswa **Program Studi Teknologi Informasi, Fakultas Teknik & Informatika, Universitas Bina Sarana Informatika (UBSI) Kampus Kota Tegal** (awal pengembangan untuk mata kuliah *Entrepreneurship*):

* **M. Nazar Habib Amrullah** — *Lead Web Developer*
* **Salsabila Lilanti**
* **Manggala Satrio Wijoyo**
* **M. Iman Nur Ikhfarel Al Hakim**
