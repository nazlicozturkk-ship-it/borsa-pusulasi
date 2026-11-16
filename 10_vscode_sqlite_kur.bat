@echo off
REM ============================================================
REM  VS Code'a SQLite Viewer eklentisini kurar ve veritabanini acar.
REM  Sonra data\bist.db dosyasina tiklayinca tablolar gorunur.
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"
title BIST Projesi - VS Code SQLite Eklentisi

where code >nul 2>&1
if errorlevel 1 (
    echo HATA: VS Code komutu bulunamadi.
    echo VS Code'u kapatip acin ya da bilgisayari yeniden baslatip tekrar deneyin.
    pause
    exit /b 1
)

echo SQLite Viewer eklentisi kuruluyor...
call code --install-extension qwtel.sqlite-viewer
echo.
echo VS Code proje klasoru ve veritabani ile aciliyor...
call code "%~dp0." "%~dp0data\bist.db"
echo.
echo Bitti. VS Code'da bist.db sekmesinde tablolar gorunecek.
pause
