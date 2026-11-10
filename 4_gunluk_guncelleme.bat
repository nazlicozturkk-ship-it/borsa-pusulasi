@echo off
REM ============================================================
REM  Gunluk guncelleme (bilgisayardaki site icin): yeni fiyatlari indirir, analizleri ve tahminleri yeniler.
REM  Internetteki site GitHub Actions ile kendiliginden guncellenir (.github/workflows/guncelle.yml).
REM  Elle cift tiklanabilir veya zamanlanmis gorevle otomatik calisir.
REM  Otomatik calismada "otomatik" parametresi verilir, pencere beklemez.
REM  Kayit: logs\gunluk_guncelleme.log
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"
title BIST Projesi - Gunluk Guncelleme
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if not exist logs mkdir logs

if not exist "venv\Scripts\python.exe" (
    echo HATA: Sanal ortam bulunamadi. >> logs\gunluk_guncelleme.log
    if /i not "%~1"=="otomatik" pause
    exit /b 1
)

echo ==== %date% %time% guncelleme basladi ==== >> logs\gunluk_guncelleme.log
echo 1/3 Fiyatlar guncelleniyor...
"venv\Scripts\python.exe" -m src.veri.fiyat_verisi 2>> logs\gunluk_guncelleme.log
if errorlevel 1 echo Fiyat guncellemesinde hata >> logs\gunluk_guncelleme.log

echo 2/3 Analizler yenileniyor...
"venv\Scripts\python.exe" -m src.analiz.analiz 2>> logs\gunluk_guncelleme.log
if errorlevel 1 echo Analizde hata >> logs\gunluk_guncelleme.log

echo 3/3 Tahminler yenileniyor...
"venv\Scripts\python.exe" -m src.tahmin.calistir 2>> logs\gunluk_guncelleme.log
if errorlevel 1 echo Tahminde hata >> logs\gunluk_guncelleme.log

echo ==== %date% %time% guncelleme bitti ==== >> logs\gunluk_guncelleme.log
echo.
echo Guncelleme tamamlandi.
if /i not "%~1"=="otomatik" pause
