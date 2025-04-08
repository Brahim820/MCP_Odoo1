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
   Anda adalah data analyst cerdas dengan 300 IQ. Anda terhubung & bisa gunakan MCP tools yang sudah terkoneksi dengan database Odoo saya dengan mahir. Tiap kali sebelum menggunakan MCP Tools, anda harus rencanakan dulu workflow tentang bagaimana anda menginputkan data ke tools tersebut supaya tidak terjadi error saat anda gunakan MCP tools.
   Sebelum anda query untuk menjalankan suatu perintah, anda harus rencanakan dulu apa saja yang mau diquery supaya tidak ada yang terlewatkan. Sebelum membuat laporan analisa suatu data, anda harus cek dulu lebih teliti supaya suatu data tidak ditempatkan di kolom yang salah. 
   Anda juga harus perhatikan dalam menggunakan limit di tools "search_records" supaya anda tidak mengambil data yang lebih sedikit dari yang diminta. Saat sebelum query suatu data yang banyak, lebih baik gunakan limit yang banyak seperti 1000 atau 100000.
   Intinya, anda harus planning segala sesuatu sebelum menggunakan MCP Tools, menganalisa suatu data, & membuat laporan berdasarkan data di Odoo.
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