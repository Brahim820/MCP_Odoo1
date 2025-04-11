# ODOO MCP SERVER - PANDUAN INSTALASI

## Persiapan
1. **Install Claude Desktop**: 
   - Unduh Claude Desktop dari https://claude.ai/download
   - Ikuti instruksi instalasi untuk menyelesaikan proses instalasi
   - Pastikan Claude Desktop sudah berjalan setidaknya sekali untuk membuat folder konfigurasi

2. **Install Python 3.13 atau lebih tinggi**:
   - Jika Python belum terinstal, unduh dari https://www.python.org/downloads/
   - Pastikan untuk **mencentang opsi "Add Python to PATH"** saat instalasi
   - Jika sudah punya python yg terinstall, bisa gunakan command berikut untuk update: "winget install Python.Python.3.13"

## Langkah Instalasi

1. **Jalankan Installer**:
   - Ekstrak semua file ZIP ke sebuah folder baru
   - Double-click pada file `install_mcp_odoo_simple.bat`
   - Tunggu proses instalasi selesai
   - Jangan tutup jendela installer sampai muncul pesan "INSTALASI SELESAI"

2. **Konfigurasi Kredensial Odoo**:
   - Setelah instalasi selesai, Anda perlu mengubah kredensial Odoo jika diperlukan
   - Anda bisa temukan PATH untuk file "claude_desktop_config.json" dengan klik menu "File -> settings" di claude desktop
   - Pilih Tab Developer & klik "Edit Config" 
   - Edit bagian berikut sesuai dengan kredensial Odoo Anda:
     ```json
     "env": {
       "PYTHONPATH": "...",
       "ODOO_URL": "https://api-odoo.visiniaga.com",
       "ODOO_DB": "OdooDev",
       "ODOO_USER": "od@visiniaga.com",
       "ODOO_PASSWORD": "Passwoord"
     }
     ```

3. **Restart Claude Desktop**:
   - Tutup Claude Desktop jika sedang berjalan
   - Buka kembali Claude Desktop untuk memuat konfigurasi baru

4. **Setting AI Agent**:
   - Buka New project
   - isi prompt berikut di bagian Knowledge Base: 
   Anda adalah data analyst cerdas dengan 300 IQ. Anda terhubung & bisa gunakan MCP tools yang sudah terkoneksi ke database Odoo dengan mahir. Tugas anda adalah query data, analisa, & beri insight dari data yang di-query. sebelum pakai MCP Tools, pelajari cara pakai & input ke MCP tools supaya tidak error. Pelajari format yang dibutuhkan untuk isi input JSON nya di MCP tools.

anda harus planning sebelum pakai MCP Tools, analisa data, & membuat laporan dari data Odoo.

Saat anda ingin ambil data berbentuk gabungan dari data lain seperti total penjualan januari atau total komisi, jangan hitung manual totalnya supaya menghindari salah hitung! Anda harus query pakai fitur pencarian seperti "filter" & "group by" supaya mendapatkan nilai total tersebut!

Saat saya tulis prompt instruksi untuk pakai MCP tools, jangan langsung pakai MCP Tools! 
tambah & optimize supaya prompt lebih detail supaya output lebih baik. konfirmasi ke saya dulu sebelum query ke Odoo. 

Tulis setiap analisa di artifacts. bicara dalam bahasa indonesia.

Ingat! sebelum pakai MCP Tools, pelajari cara pakai & input ke MCP tools supaya tidak error! Pelajari format untuk isi input JSON nya di MCP tools.
Ingat, Jangan sampai error!
Selalu baca lagi instruksi di knowledge base ini sebelum eksekusi prompt!


## Penggunaan

Setelah instalasi berhasil, Anda dapat menggunakan Claude untuk:

1. **Menjelajahi Model Odoo**:
   - Minta Claude untuk "Tampilkan daftar model Odoo yang tersedia"
   - Atau "Tunjukkan skema model res.partner"

2. **Mencari Data**:
   - Minta Claude untuk "Cari 10 pelanggan teratas di Odoo"
   - Atau "Tampilkan daftar pesanan penjualan bulan ini"

3. **Membuat Laporan**:
   - Minta Claude untuk "Buat laporan penjualan berdasarkan produk"
   - Atau "Analisis stok berdasarkan lokasi"

## Uninstall Program

Jika Anda ingin menghapus MCP Odoo Server:
1. Jalankan `uninstall_mcp_odoo_simple.bat`
2. Ikuti instruksi yang muncul
3. Restart Claude Desktop setelah uninstall selesai

## Pemecahan Masalah

Jika mengalami masalah:

1. **Claude tidak menampilkan ikon MCP** (ikon palu di kanan bawah):
   - Pastikan file konfigurasi sudah benar
   - Restart Claude Desktop

2. **Error koneksi Odoo**:
   - Periksa kredensial Odoo di file konfigurasi
   - Pastikan URL Odoo dapat diakses dari komputer Anda

3. **Error Python**:
   - Pastikan Python terinstal dengan benar
   - Coba reinstall dengan menjalankan installer lagi

Untuk bantuan lebih lanjut, hubungi tim IT.
