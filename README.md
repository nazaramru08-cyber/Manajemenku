# MANAJEMENKU — Smart Finance System

**MANAJEMENKU** adalah aplikasi web **Smart Finance System** berbasis Python Flask yang dirancang untuk membantu pengelolaan keuangan pribadi dan harian secara terstruktur, praktis, dan transparan—mulai dari pencatatan arus kas, pemantauan saldo aktif, target tabungan, pembagian tagihan bersama (*split bill*), hingga pencatatan hutang dan piutang.

---

## Fitur Utama

* **Autentikasi & Keamanan Akun**: Registrasi dengan validasi Gmail, login berbasis *session*, serta fitur pemulihan sandi (*Lupa Password*) menggunakan kode OTP ke email.
* **Dashboard Keuangan**: Menampilkan saldo aktif, total pemasukan, total pengeluaran, persentase progres target tabungan, grafik bulanan, dan konverter valuta asing.
* **Kalkulator Split Bill**: Mendukung mode **Bagi per Menu** dan **Bagi Rata**, lengkap dengan pengaturan peserta, diskon, pajak, *service charge*, ongkir, serta format rekap siap kirim ke WhatsApp.
* **Catatan Hutang & Piutang**: Pencatatan transaksi hutang dan piutang harian agar lebih rapi dan tidak mudah terlupa.
* **Akun VIP & Ekspor Laporan PDF**: Fitur peningkatan akun ke VIP Premium serta ekspor ringkasan laporan keuangan ke dalam dokumen PDF.
* **Halaman Tentang Kami**: Informasi profil aplikasi, latar belakang pengembangan, dan tim pengembang.

---

## Teknologi yang Digunakan

* **Backend**: Python, Flask
* **Database**: SQLite (`sqlite3`)
* **Frontend**: HTML5, Tailwind CSS, JavaScript
* **PDF Generator**: ReportLab

---

## Struktur Proyek

```text
Manajemenku/
├── main.py              # File utama aplikasi web Flask & routing API
├── requirements.txt     # Daftar dependensi Python
├── static/              # Aset gambar & logo aplikasi (Manajemenku.png, dll.)
└── templates/           # Halaman antarmuka HTML (login, index, split_bill, dll.)

## Cara Menjalankan di Lokal

Clone repository ini:

Bash
git clone [https://github.com/nazaramru08-cyber/Manajemenku.git](https://github.com/nazaramru08-cyber/Manajemenku.git)
cd Manajemenku
Instal dependensi:

Bash
pip install -r requirements.txt
Jalankan aplikasi:

Bash
python main.py
Buka di browser:
Akses http://127.0.0.1:5000

Tim Pengembang
Dikembangkan oleh mahasiswa Program Studi Teknologi Informasi, Fakultas Teknik & Informatika, Universitas Bina Sarana Informatika (UBSI) Kampus Kota Tegal (awal pengembangan untuk mata kuliah Entrepreneurship):

M. Nazar Habib Amrullah — Lead Web Developer

Salsabila Lilanti

Manggala Satrio Wijoyo

M. Iman Nur Ikhfarel Al Hakim
