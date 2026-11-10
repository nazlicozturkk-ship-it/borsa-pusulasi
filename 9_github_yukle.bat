@echo off
REM ============================================================
REM  Projeyi GitHub'a yukler (ilk seferde depo adresini sorar).
REM  Sonraki seferlerde sadece degisiklikleri gonderir.
REM  Vercel, GitHub'a her yuklemeden sonra siteyi kendiliginden yeniler.
REM  Kayit: logs\github.log
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"
title BIST Projesi - GitHub'a Yukle
if not exist logs mkdir logs

where git >nul 2>&1
if errorlevel 1 (
    echo HATA: Git bulunamadi. Git kurulu olmali.
    echo HATA: git bulunamadi > logs\github.log
    pause
    exit /b 1
)

if not exist .git git init -b main

git config user.name >nul 2>&1
if not errorlevel 1 goto eposta
set /p GADI=GitHub'da gorunecek adin (ornek: Nazli Ozturk): 
git config user.name "%GADI%"

:eposta
git config user.email >nul 2>&1
if not errorlevel 1 goto uzak
set /p GEPOSTA=GitHub hesabindaki e-posta adresin: 
git config user.email "%GEPOSTA%"

:uzak
git remote get-url origin >nul 2>&1
if not errorlevel 1 goto yukle
echo.
echo GitHub'da actigin bos deponun adresini yapistir
echo (ornek: https://github.com/kullanici-adin/borsa-pusulasi.git)
set /p DEPO=Adres: 
git remote add origin "%DEPO%"

:yukle
echo.
echo Dosyalar hazirlaniyor...
REM Otomatik guncelleme ayari GitHub Actions klasorune kopyalanir
if not exist .github\workflows mkdir .github\workflows
copy /y github_actions\guncelle.yml .github\workflows\guncelle.yml >nul
git add -A
git commit -q -m "Borsa Pusulasi guncelleme %date% %time:~0,5%" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
echo GitHub'a gonderiliyor (ilk seferde tarayicida GitHub girisi istenebilir)...
git push -u origin main
if errorlevel 1 (
    echo.
    echo Gonderilemedi. Ayrinti logs\github.log dosyasinda.
)

echo ==== %date% %time% ==== > logs\github.log
git remote -v >> logs\github.log 2>&1
git status -sb >> logs\github.log 2>&1
git log --oneline -3 >> logs\github.log 2>&1
git push --dry-run origin main >> logs\github.log 2>&1
echo.
echo Bitti.
pause
