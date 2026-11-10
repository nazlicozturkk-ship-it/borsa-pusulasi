@echo off
REM ============================================================
REM  Hafta 2 - Tum BIST sirketlerinin 10 yillik fiyat verisini indirir/gunceller
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

echo Fiyat verileri indiriliyor. Ilk calistirma 15-30 dakika surebilir...
echo Pencereyi kapatmayin. Yarida kalirsa tekrar calistirdiginizda kaldigi yerden devam eder.
echo.
"venv\Scripts\python.exe" -m src.veri.fiyat_verisi  2> logs\fiyat_verisi_hata.log
if errorlevel 1 (
    echo.
    echo Bir hata olustu. Ayrintilar logs klasorune kaydedildi.
    type logs\fiyat_verisi_hata.log
)

echo.
pause
