# Borsa Pusulası — Claude için proje notları

## Kullanıcı
- Nazlı, bitirme projesi (16 hafta; 8. hafta vize, 16. hafta final). Türkçe konuşur, kısa ve adım adım yönlendirme ister.
- Windows kullanıyor. Proje klasörü: `C:\Users\nazli\Desktop\BitirmeOdevi1`
- Komutları tek tek yazdırmak yerine işi sen yap; kullanıcıya sadece sonucu ve yapması gereken tek adımı söyle.

## Proje
Borsa İstanbul'daki tüm şirketlerin 10 yıllık fiyatlarını toplayan, 1A/3A/6A/YB/1Y/5Y/10Y getirilerini
ve risklerini analiz eden, her hisse için 20 işlem günlük fiyat tahmini yapan Python web uygulaması.
README.md'de klasör yapısı ve çalıştırma adımları var; docs/haftaN_notlar.md dosyalarında haftalık notlar.

- Python 3.12, sanal ortam `venv\` → komutlar `venv\Scripts\python.exe -m modul` şeklinde, proje kökünden.
- Veri: borsapy (KAP, TradingView), yedek yfinance. Veritabanı yerelde SQLite `data/bist.db` (SQLAlchemy).
- Web: FastAPI + Jinja2 + Plotly (`src/web/`). Yerelde `6_web_uygulamasi.bat` → http://127.0.0.1:8000
- Tahmin: naif, hareketli ortalama, doğrusal regresyon, ARIMA; geriye dönük test (6 başlangıç, 20 gün ufuk),
  her hisse için en düşük hatalı model seçilir (`src/tahmin/`).
- `.bat` dosyaları ASCII + CRLF satır sonu olmalı (Türkçe karakter yok), `chcp 65001` ve `PYTHONUTF8=1` kullanır.

## İnternetteki kopya (kullanıcı raporda/sunumda bahsedilmesini istemiyor)
- Kullanıcı Vercel, Neon, GitHub Actions gibi yayın ayrıntılarının rapor, sunum, README ve site metinlerinde geçmesini istemiyor.
  Proje sunumda bilgisayardan (`6_web_uygulamasi.bat`) gösterilir.
- Yine de site https://borsa-pusulasi.vercel.app adresinde çalışmaya devam ediyor (kullanıcı kapatılmasını istemedi).
  Gerekli dosyalar `yayin/` klasöründe: `guncelle.yml` (otomatik güncelleme; `9_github_yukle.bat` onu `.github/workflows/` içine kopyalar),
  `aktar.py` (SQLite → internetteki PostgreSQL), `requirements-guncelleme.txt`. Kökte kalması zorunlu olanlar: `index.py`, `requirements.txt`, `public/`.
- GitHub: https://github.com/nazlicozturkk-ship-it/borsa-pusulasi — `9_github_yukle.bat` ile yüklenir.
  Veritabanı bağlantı adresi şifre içerir: asla dosyaya, koda veya commit'e yazma.

## Tasarım kararları (kullanıcı istekleri)
- Tema: "Alacakaranlık" (açık zemin, mor-pembe gün batımı gradyanı, Sora + Manrope yazı tipleri, İstanbul silueti, pusula logosu). Tema değiştirici yok.
- Site bir ödev raporu gibi değil gerçek bir finans sitesi gibi görünmeli: yöntem anlatan uzun paragraflar,
  "naif model", ".bat çalıştırın" gibi geliştirici/akademik ifadeler ziyaretçiye gösterilmez.
  Modeller sayfası kaldırıldı; model tablosu şirket sayfasında kapalı "Model ayrıntıları" içinde.
- Her sayfanın altında sadece "Gösterilen analizler ve tahminler yatırım tavsiyesi değildir." uyarısı kalır.
- Ana sayfadaki dönem sekmeleri sayfa yenilemeden değişir.

## Plan (vize sonrası)
- Hafta 9: teknik göstergeler (RSI, MACD), makro veriler (dolar/TL, faiz)
- Hafta 10: XGBoost, LightGBM, Prophet · Hafta 11: LSTM
- Hafta 12: ayrı doğrulama dönemiyle model seçimi (aşırı uyum kontrolü)
- Hafta 13: arayüz, Excel/PDF indirme · Hafta 14: performans, Docker · Hafta 15: proje raporu · Hafta 16: final
