@echo off
REM ============================================================
REM  Windows Gorev Zamanlayicisi'na bir gorev ekler:
REM  Hafta ici her gun saat 19:15'te (borsa kapandiktan sonra)
REM  4_gunluk_guncelleme.bat otomatik calisir.
REM  Bilgisayar o saatte kapaliysa o gun atlanir.
REM  Kapatmak icin: 5_otomatik_guncelleme_kapat.bat
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"
schtasks /create /tn "BIST Gunluk Guncelleme" /tr "\"%~dp04_gunluk_guncelleme.bat\" otomatik" /sc weekly /d MON,TUE,WED,THU,FRI /st 19:15 /f
if errorlevel 1 (
    echo.
    echo Gorev olusturulamadi.
) else (
    echo.
    echo Otomatik guncelleme acildi: hafta ici her gun 19:15.
    echo Calisma kaydi: logs\gunluk_guncelleme.log
)
echo.
pause
