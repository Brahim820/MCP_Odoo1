@echo off
echo ================================================
echo     INSTALASI MCP ODOO SERVER
echo ================================================
echo.

:: Tetapkan lokasi instalasi (di folder yang sama dengan installer)
set "CURRENT_DIR=%~dp0"
set "INSTALL_DIR=%CURRENT_DIR%"
set "VENV_DIR=%INSTALL_DIR%venv"
set "SERVER_FILE=%INSTALL_DIR%odoo_mcp_server.py"
set "CLAUDE_CONFIG_DIR=%APPDATA%\Claude"
set "CONFIG_FILE=%CLAUDE_CONFIG_DIR%\claude_desktop_config.json"

echo Lokasi instalasi: %INSTALL_DIR%
echo.

:: Cek apakah Claude Desktop sudah terinstal
if not exist "%CLAUDE_CONFIG_DIR%" (
    echo [ERROR] Folder Claude tidak ditemukan di %CLAUDE_CONFIG_DIR%
    echo         Pastikan Claude Desktop sudah terinstal terlebih dahulu.
    echo         Download Claude Desktop dari: https://claude.ai/download
    pause
    exit /b 1
)

:: Cek apakah Python tersedia
echo [INFO] Memeriksa instalasi Python...
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python tidak ditemukan. Silakan install Python 3.9 atau lebih baru.
    echo         Download Python dari: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Cek versi Python (minimal 3.9)
for /f "tokens=2" %%a in ('python --version 2^>^&1') do set PYTHON_VERSION=%%a
echo [INFO] Python versi %PYTHON_VERSION% terdeteksi.

:: Validasi versi Python minimal 3.9
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set PYTHON_MAJOR=%%a
    set PYTHON_MINOR=%%b
)

if %PYTHON_MAJOR% LSS 3 (
    echo [ERROR] Python versi 3.9 atau lebih tinggi diperlukan.
    echo         Versi terdeteksi: %PYTHON_VERSION%
    pause
    exit /b 1
) else if %PYTHON_MAJOR%==3 (
    if %PYTHON_MINOR% LSS 9 (
        echo [ERROR] Python versi 3.9 atau lebih tinggi diperlukan.
        echo         Versi terdeteksi: %PYTHON_VERSION%
        pause
        exit /b 1
    )
)

:: Buat direktori instalasi jika belum ada
echo [INFO] Memeriksa direktori instalasi...

:: Salin file MCP server jika belum ada di lokasi instalasi
echo [INFO] Memastikan file odoo_mcp_server.py ada di tempat yang benar...
if not exist "%SERVER_FILE%" (
    echo [INFO] Menyalin odoo_mcp_server.py...
    copy "%CURRENT_DIR%odoo_mcp_server.py" "%SERVER_FILE%" /Y
)

:: Buat virtual environment
echo.
echo [INFO] Membuat virtual environment...
if exist "%VENV_DIR%" (
    echo [INFO] Virtual environment sudah ada, menggunakan yang sudah ada...
) else (
    python -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo [ERROR] Gagal membuat virtual environment.
        pause
        exit /b 1
    )
)

:: Aktifkan virtual environment dan install dependencies
echo.
echo [INFO] Mengupdate pip dan setuptools...
call "%VENV_DIR%\Scripts\activate"
python -m pip install --upgrade pip setuptools wheel
if %errorlevel% neq 0 (
    echo [WARNING] Gagal mengupdate pip, mencoba melanjutkan instalasi...
)

echo.
echo [INFO] Instalasi paket MCP...
pip install "mcp[cli]"
if %errorlevel% neq 0 (
    echo [ERROR] Gagal menginstall paket MCP.
    pause
    exit /b 1
)

:: Dapatkan path Python dalam venv untuk konfigurasi
for /f "tokens=*" %%a in ('where python') do (
    set "PYTHON_PATH=%%a"
)

:: Sesuaikan path Python ke virtual environment
set "PYTHON_VENV_PATH=%VENV_DIR%\Scripts\python.exe"

:: Buat file konfigurasi Claude Desktop
echo.
echo [INFO] Membuat konfigurasi Claude Desktop...
if exist "%CONFIG_FILE%" (
    echo [INFO] Membuat backup konfigurasi yang sudah ada...
    copy "%CONFIG_FILE%" "%CLAUDE_CONFIG_DIR%\claude_desktop_config.bak" /Y
)

:: Metode alternatif yang lebih sederhana untuk membuat file JSON dengan double backslash
set "PYTHON_PATH_ESCAPED=%PYTHON_VENV_PATH:\=\\%"
set "SERVER_FILE_ESCAPED=%SERVER_FILE:\=\\%"
set "PYTHONPATH_ESCAPED=%VENV_DIR%\Lib\site-packages"
set "PYTHONPATH_ESCAPED=%PYTHONPATH_ESCAPED:\=\\%"

echo [INFO] Menulis file konfigurasi baru...
echo {> "%CONFIG_FILE%"
echo   "mcpServers": {>> "%CONFIG_FILE%"
echo     "odoo-perusahaan": {>> "%CONFIG_FILE%"
echo       "command": "%PYTHON_PATH_ESCAPED%",>> "%CONFIG_FILE%"
echo       "args": [>> "%CONFIG_FILE%"
echo         "%SERVER_FILE_ESCAPED%">> "%CONFIG_FILE%"
echo       ],>> "%CONFIG_FILE%"
echo       "env": {>> "%CONFIG_FILE%"
echo         "PYTHONPATH": "%PYTHONPATH_ESCAPED%",>> "%CONFIG_FILE%"
echo         "ODOO_URL": "https://api-odoo.visiniaga.com",>> "%CONFIG_FILE%"
echo         "ODOO_DB": "OdooDev",>> "%CONFIG_FILE%"
echo         "ODOO_USER": "od@visiniaga.com",>> "%CONFIG_FILE%"
echo         "ODOO_PASSWORD": "P">> "%CONFIG_FILE%"
echo       }>> "%CONFIG_FILE%"
echo     }>> "%CONFIG_FILE%"
echo   }>> "%CONFIG_FILE%"
echo }>> "%CONFIG_FILE%"

:: Deaktifkan virtual environment
call "%VENV_DIR%\Scripts\deactivate"

echo.
echo ================================================
echo      INSTALASI SELESAI
echo ================================================
echo.
echo MCP Odoo Server berhasil diinstall.
echo.
echo Berikut informasi instalasi:
echo - MCP Server: %SERVER_FILE%
echo - Python    : %PYTHON_PATH%
echo - Konfigurasi: %CONFIG_FILE%
echo.
echo LANGKAH SELANJUTNYA:
echo 1. Edit file konfigurasi Claude Desktop untuk mengubah
echo    kredensial ODOO (URL, DB, USER, PASSWORD) jika diperlukan.
echo 2. Restart Claude Desktop untuk memuat konfigurasi baru.
echo.
pause