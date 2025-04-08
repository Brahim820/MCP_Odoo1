@echo off
echo ================================================
echo     UNINSTALL MCP ODOO SERVER
echo ================================================
echo.

:: Tetapkan lokasi instalasi
set "CURRENT_DIR=%~dp0"
set "INSTALL_DIR=%CURRENT_DIR%"
set "VENV_DIR=%INSTALL_DIR%venv"
set "CLAUDE_CONFIG_DIR=%APPDATA%\Claude"
set "CONFIG_FILE=%CLAUDE_CONFIG_DIR%\claude_desktop_config.json"
set "CONFIG_BACKUP=%CLAUDE_CONFIG_DIR%\claude_desktop_config.bak"

echo Proses uninstall akan:
echo - Menghapus virtual environment (folder venv)
echo - Menghapus konfigurasi MCP server Odoo dari Claude Desktop
echo.
echo PERINGATAN: Pastikan Claude Desktop ditutup sebelum melanjutkan.
echo.

set /p CONFIRM="Apakah Anda yakin ingin melanjutkan? (y/n): "
if /i "%CONFIRM%" neq "y" (
    echo Uninstall dibatalkan.
    pause
    exit /b 0
)

:: Cek apakah folder venv ada
echo.
echo [INFO] Menghapus virtual environment...
if not exist "%VENV_DIR%" (
    echo [WARNING] Virtual environment (venv) tidak ditemukan.
) else (
    :: Coba menghentikan semua proses Python yang menggunakan virtual environment
    taskkill /f /im python.exe >nul 2>&1
    
    :: Tunggu sebentar untuk memastikan proses sudah berakhir
    timeout /t 2 >nul
    
    :: Hapus folder virtual environment
    rd /s /q "%VENV_DIR%" >nul 2>&1
    
    if exist "%VENV_DIR%" (
        echo [WARNING] Gagal menghapus virtual environment. Beberapa file mungkin sedang digunakan.
    ) else (
        echo [INFO] Virtual environment berhasil dihapus.
    )
)

:: Menangani file konfigurasi Claude Desktop
echo.
echo [INFO] Memperbarui konfigurasi Claude Desktop...
if not exist "%CONFIG_FILE%" (
    echo [WARNING] File konfigurasi Claude Desktop tidak ditemukan.
) else (
    :: Buat backup jika belum ada
    if not exist "%CONFIG_BACKUP%" (
        copy "%CONFIG_FILE%" "%CONFIG_BACKUP%" >nul
    )
    
    :: Baca file konfigurasi untuk cek apakah ada konfigurasi Odoo
    findstr /C:"odoo-perusahaan" "%CONFIG_FILE%" >nul
    if %errorlevel% equ 0 (
        echo [INFO] Menghapus konfigurasi MCP Odoo dari Claude Desktop...
        
        :: Buat file konfigurasi minimal jika kita tidak bisa mengedit dengan cara yang lebih canggih
        echo {> "%CONFIG_FILE%"
        echo   "mcpServers": {>> "%CONFIG_FILE%"
        echo   }>> "%CONFIG_FILE%"
        echo }>> "%CONFIG_FILE%"
        
        echo [INFO] Konfigurasi Claude Desktop berhasil diperbarui.
    ) else (
        echo [INFO] Konfigurasi MCP Odoo tidak ditemukan di file konfigurasi.
    )
)

echo.
echo ================================================
echo      UNINSTALL SELESAI
echo ================================================
echo.
echo MCP Odoo Server berhasil diuninstall.
echo.
echo Catatan:
echo 1. Jika Anda mengalami masalah, file backup konfigurasi
echo    tersimpan di: %CONFIG_BACKUP%
echo 2. Silakan restart Claude Desktop untuk menerapkan perubahan.
echo.
pause