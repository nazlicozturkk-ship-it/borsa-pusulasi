@echo off
REM ============================================================
REM  Hafta 8 - Verileri internetteki veritabanina (Neon PostgreSQL) aktarir.
REM  Vercel'deki site verileri oradan okur.
REM  Ilk sefer: tum fiyatlar gonderilir (birkac dakika).
REM  Sonraki seferler: sadece yeni gunler (birkac saniye).
REM  Kayit: logs\buluta_aktar.log
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"
title BIST Projesi - Buluta Aktar
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if not exist logs mkdir logs

if exist .env goto calistir
> .env echo # Internetteki veritabaninin (Neon) baglanti adresi. Bu dosya GitHub'a yuklenmez.
>> .env echo BULUT_VERITABANI_URL=
echo.
echo  .env dosyasi olusturuldu ve Not Defteri'nde aciliyor.
echo  BULUT_VERITABANI_URL= satirinin sonuna Neon baglanti adresini yapistir,
echo  kaydet (Ctrl+S), Not Defteri'ni kapat ve bu dosyaya tekrar cift tikla.
echo.
notepad .env
pause
exit /b 0

:calistir
"venv\Scripts\python.exe" -m src.bulut.aktar 2> logs\buluta_aktar_hata.log
if errorlevel 1 (
    echo.
    echo Aktarimda sorun oldu. Ayrinti: logs\buluta_aktar.log ve logs\buluta_aktar_hata.log
)
echo.
if /i not "%~1"=="otomatik" pause
