@echo off
REM ============================================================
REM  BIST Getiri Tahmin Projesi - Kutuphane kurulumu
REM  Cift tiklayarak calistirin. Islem birkac dakika surebilir.
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"
title BIST Projesi - Kurulum
set PYTHONUTF8=1
if not exist logs mkdir logs

if not exist "venv\Scripts\python.exe" (
    echo Sanal ortam bulunamadi, olusturuluyor...
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m venv venv
)
if not exist "venv\Scripts\python.exe" (
    echo HATA: Sanal ortam olusturulamadi. Python kurulumunu kontrol edin.
    echo HATA: venv olusturulamadi > logs\kurulum.log
    pause
    exit /b 1
)

echo.
echo Kutuphaneler kuruluyor, lutfen pencereyi kapatmayin...
echo.
"venv\Scripts\python.exe" -m pip install --upgrade pip
"venv\Scripts\python.exe" -m pip install -r requirements-tam.txt --log logs\kurulum_pip.log

echo.
echo Kurulum kontrol ediliyor...
"venv\Scripts\python.exe" -c "import borsapy, pandas, sqlalchemy, fastapi, plotly, yfinance; print('KURULUM BASARILI - borsapy', borsapy.__version__)" > logs\kurulum.log 2>&1
type logs\kurulum.log

echo.
echo Bitti. Bu pencereyi kapatabilirsiniz.
pause
