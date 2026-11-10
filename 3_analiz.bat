@echo off
REM ============================================================
REM  Hafta 3 - Veri kalitesi kontrolu ve getiri/risk hesaplari
REM  Sonuc: data\getiriler.csv, data\veri_kalitesi.csv (Excel ile acilir)
REM  Kayit: logs\analiz.log
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"
title BIST Projesi - Analiz
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if not exist logs mkdir logs

if not exist "venv\Scripts\python.exe" (
    echo HATA: Sanal ortam bulunamadi. Once kurulum.bat dosyasini calistirin.
    pause
    exit /b 1
)

echo Getiri ve risk hesaplari yapiliyor...
echo.
"venv\Scripts\python.exe" -m src.analiz.analiz 2> logs\analiz_hata.log
if errorlevel 1 (
    echo.
    echo Bir hata olustu. Ayrintilar logs klasorune kaydedildi.
    type logs\analiz_hata.log
)

echo.
pause
