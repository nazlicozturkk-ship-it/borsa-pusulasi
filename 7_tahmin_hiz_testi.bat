@echo off
REM  Tanilama: ARIMA'nin bu bilgisayarda ne kadar surdugunu olcer. Kayit: logs\hiz_testi.log
chcp 65001 >nul
cd /d "%~dp0"
title Borsa Pusulasi - Hiz Testi
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if not exist logs mkdir logs
"venv\Scripts\python.exe" -m src.tahmin.hiz_testi 2>> logs\hiz_testi.log
echo.
pause
