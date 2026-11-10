@echo off
REM ============================================================
REM  Hafta 4 - Web uygulamasini baslatir ve tarayicida acar.
REM  Adres: http://127.0.0.1:8000 (doluysa 8001, 8002...)
REM  Kayit: logs\web.log
REM  Kapatmak icin bu pencereyi kapatin (veya Ctrl+C).
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"
title BIST Projesi - Web Uygulamasi (kapatmak icin bu pencereyi kapatin)
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if not exist logs mkdir logs

if not exist "venv\Scripts\python.exe" (
    echo HATA: Sanal ortam bulunamadi. Once kurulum.bat dosyasini calistirin.
    pause
    exit /b 1
)

REM Arkada acik kalmis eski sunucu varsa kapat (sadece bu projenin web sunucusu)
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'src\.web' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

echo Web uygulamasi baslatiliyor. Hazir olunca tarayici kendiliginden acilacak.
echo Uygulama calistigi surece bu pencereyi KAPATMAYIN.
echo.
"venv\Scripts\python.exe" -m src.web.calistir
echo.
echo Uygulama durdu. Hata varsa yukarida gorunur.
pause
