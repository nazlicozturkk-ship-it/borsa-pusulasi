@echo off
REM ============================================================
REM  Hafta 6 - Hizli deneme: sadece BIST 30 hisseleri
REM  Kayit: logs\tahmin.log
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"
title Borsa Pusulasi - Tahmin Modelleri
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if not exist logs mkdir logs

if not exist "venv\Scripts\python.exe" (
    echo HATA: Sanal ortam bulunamadi. Once kurulum.bat dosyasini calistirin.
    pause
    exit /b 1
)

echo BIST 30 hisseleri icin tahmin modelleri calisiyor, 1-2 dakika surer...
echo Pencereyi kapatmayin.
echo.
"venv\Scripts\python.exe" -m src.tahmin.calistir --sadece bist30 2> logs\tahmin_hata.log
if errorlevel 1 (
    echo.
    echo Bir hata olustu. Ayrintilar logs klasorune kaydedildi.
    type logs\tahmin_hata.log
)

echo.
pause
