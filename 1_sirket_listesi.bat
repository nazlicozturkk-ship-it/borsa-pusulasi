@echo off
REM ============================================================
REM  Hafta 1 - Tum BIST sirketlerinin listesini olusturur
REM  Sonuc: data\bist.db (veritabani) ve data\sirketler.csv
REM  Kayit: logs\sirket_listesi.log
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"
title BIST Projesi - Sirket Listesi
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if not exist logs mkdir logs

if not exist "venv\Scripts\python.exe" (
    echo HATA: Sanal ortam bulunamadi. Once kurulum.bat dosyasini calistirin.
    pause
    exit /b 1
)

echo BIST sirket listesi hazirlaniyor, bu islem 1-2 dakika surebilir...
echo.
"venv\Scripts\python.exe" -m src.veri.sirket_listesi 2> logs\sirket_listesi_hata.log
if errorlevel 1 (
    echo.
    echo Bir hata olustu. Ayrintilar logs klasorune kaydedildi.
    type logs\sirket_listesi_hata.log
)

echo.
pause
