@echo off
REM  Otomatik gunluk guncelleme gorevini kaldirir.
chcp 65001 >nul
schtasks /delete /tn "BIST Gunluk Guncelleme" /f
echo.
pause
