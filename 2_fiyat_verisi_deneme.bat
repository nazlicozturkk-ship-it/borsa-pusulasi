@echo off
REM ============================================================
REM  Hafta 2 - Hizli deneme: sadece BIST 30 hisselerinin verisini indirir
REM  Kayit: logs\fiyat_verisi.log
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"
title BIST Projesi - Fiyat Verisi
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if not exist logs mkdir logs

if not exist "venv\Scripts\python.exe" (
    echo HATA: Sanal ortam bulunamadi. Once kurulum.bat dosyasini calistirin.
    pause
    exit /b 1
)

echo BIST 30 hisselerinin verisi indiriliyor, 1-2 dakika surer...
echo Pencereyi kapatmayin. Yarida kalirsa tekrar calistirdiginizda kaldigi yerden devam eder.
echo.
"venv\Scripts\python.exe" -m src.veri.fiyat_verisi --sadece bist30 2> logs\fiyat_verisi_hata.log
if errorlevel 1 (
    echo.
    echo Bir hata olustu. Ayrintilar logs klasorune kaydedildi.
    type logs\fiyat_verisi_hata.log
)

echo.
pause
