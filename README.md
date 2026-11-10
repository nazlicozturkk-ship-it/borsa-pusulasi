# Borsa Pusulası — BIST Getiri Analiz ve Tahmin Sistemi

Borsa İstanbul'da işlem gören tüm şirketlerin geçmiş fiyat verilerini toplayan,
1 ay / 3 ay / 6 ay / 1 yıl / 5 yıl / 10 yıllık getirilerini analiz eden ve her
şirket için tahmin grafikleri ile raporlar üreten Python tabanlı web uygulaması.

> Bu proje eğitim amaçlıdır. Üretilen tahminler yatırım tavsiyesi değildir.

## Kullanılan teknolojiler

| Alan | Araç |
|---|---|
| Dil | Python 3.12 |
| Veri kaynağı | borsapy (KAP, İş Yatırım, TradingView), yfinance |
| Veritabanı | SQLite (bilgisayarda), PostgreSQL – Neon (internetteki site) |
| Yayın | Vercel |
| Veritabanı erişimi | SQLAlchemy |
| Analiz | pandas, numpy, statsmodels, scikit-learn |
| Tahmin modelleri | ARIMA, XGBoost, LightGBM, Prophet, LSTM (TensorFlow) |
| Web uygulaması | FastAPI, Jinja2 |
| Grafikler | Plotly |

## Klasör yapısı

```
BitirmeOdevi1/
├── config.py               Proje ayarları (klasörler, veritabanı adresi)
├── requirements.txt        İnternetteki site (Vercel) için gereken kütüphaneler
├── requirements-tam.txt    Bilgisayardaki tam kurulum için kütüphaneler
├── index.py, vercel.json   Vercel ayarları (internetteki site)
├── .env                    İnternetteki veritabanının adresi (gizli, GitHub'a yüklenmez)
├── kurulum.bat             Kütüphaneleri kurar (çift tıkla)
├── 1_sirket_listesi.bat    Hafta 1: tüm BIST şirketlerini çeker (çift tıkla)
├── 2_fiyat_verisi.bat      Hafta 2: 10 yıllık fiyat verilerini indirir/günceller
├── 2_fiyat_verisi_deneme.bat  Hafta 2: sadece BIST 30 ile hızlı deneme
├── 3_analiz.bat            Hafta 3: veri kalitesi, getiri ve risk hesapları
├── 4_gunluk_guncelleme.bat Fiyatları, analizleri ve tahminleri birlikte günceller
├── 5_otomatik_guncelleme_ac.bat / _kapat.bat  Hafta içi her akşam otomatik güncelleme
├── 6_web_uygulamasi.bat    Hafta 4: web uygulamasını başlatır (http://127.0.0.1:8000)
├── 7_tahmin_deneme.bat     Hafta 6: tahmin modelleri, sadece BIST 30 ile hızlı deneme
├── 7_tahmin_modelleri.bat  Hafta 6: tahmin modelleri, tüm hisseler
├── 8_buluta_aktar.bat      Verileri internetteki veritabanına (Neon) aktarır
├── 9_github_yukle.bat      Projeyi GitHub'a yükler; Vercel siteyi kendiliğinden yeniler
├── public/kutuphane/       Grafik kütüphanesi (plotly.js)
├── src/
│   ├── log_ayari.py        Çalışma kayıtlarını logs/ klasörüne yazar
│   ├── veritabani.py       Veritabanı tabloları ve kayıt fonksiyonları
│   ├── analiz/
│   │   ├── veri_kalitesi.py    Eksik gün, aşırı hareket, hacim, OHLC kontrolleri
│   │   ├── getiri.py           1A-10Y getiri, volatilite, maks. düşüş, beta
│   │   ├── sektor.py           Eşit ağırlıklı sektör endeksleri
│   │   ├── korelasyon.py       Benzer hareket eden hisseler
│   │   └── analiz.py           Analizleri çalıştırır, sonuçları kaydeder
│   ├── tahmin/
│   │   ├── modeller.py         Naif, hareketli ortalama, doğrusal regresyon, ARIMA
│   │   ├── degerlendirme.py    Geriye dönük test, MAE / RMSE / MAPE / yön doğruluğu
│   │   └── calistir.py         Tüm hisselerde paralel çalıştırma, 20 günlük tahmin
│   ├── bulut/
│   │   └── aktar.py            SQLite → PostgreSQL (Neon) aktarımı, sadece değişen veriler
│   ├── web/
│   │   ├── app.py              FastAPI uygulaması: sayfalar ve JSON servisleri
│   │   ├── veri.py             Sayfaların veri sorguları (önbellekli)
│   │   ├── templates/          HTML şablonları
│   │   └── static/             CSS ve JavaScript (grafik, arama, tablo)
│   └── veri/
│       ├── sirket_listesi.py   Şirket listesi, sektör ve endeks bilgisi
│       └── fiyat_verisi.py     10 yıllık günlük fiyat verileri
├── data/                   Veritabanı (bist.db) ve CSV çıktıları
├── logs/                   Çalışma kayıtları
└── docs/                   Haftalık notlar
```

## Nasıl çalıştırılır?

1. `kurulum.bat` dosyasına çift tıkla (sadece ilk seferde).
2. `1_sirket_listesi.bat` dosyasına çift tıkla.
3. `2_fiyat_verisi.bat` dosyasına çift tıkla (ilk sefer 15-30 dk, sonra her gün birkaç dakika).
4. `3_analiz.bat` dosyasına çift tıkla (birkaç saniye).
5. Sonuçlar Excel ile açılabilen `data/sirketler.csv`, `data/getiriler.csv` ve `data/veri_kalitesi.csv` dosyalarında; tüm veriler `data/bist.db` veritabanında.
6. `6_web_uygulamasi.bat` ile web uygulamasını aç.
7. İsteğe bağlı: `5_otomatik_guncelleme_ac.bat` ile verilerin hafta içi her akşam kendiliğinden güncellenmesini aç.

## İnternette yayınlama (Vercel)

```
Bilgisayar (her akşam)                         İnternet
fiyat → analiz → tahmin → SQLite ──aktar──▶ Neon PostgreSQL ◀── Vercel (site)
```

Ağır işler (veri indirme, analiz, tahmin) bilgisayarda çalışır; Vercel uzun süren işleri
çalıştıramaz. Sonuçlar `8_buluta_aktar.bat` ile internetteki veritabanına kopyalanır, site
oradan okur. `.env` dosyası varsa `4_gunluk_guncelleme.bat` bu aktarımı kendisi yapar.
Vercel'de `DATABASE_URL` değişkeni tanımlıdır; bilgisayarda tanımlı olmadığı için yerel site
SQLite ile çalışmaya devam eder.

## Haftalık ilerleme

- [x] Hafta 1 – Proje yapısı, veritabanı, tüm BIST şirket listesi
- [x] Hafta 2 – 10 yıllık fiyat verilerinin toplanması
- [x] Hafta 3 – Veri kalitesi, dönemsel getiri ve risk hesapları, otomatik güncelleme
- [x] Hafta 4 – Web uygulaması: ana sayfa, şirket listesi, şirket detay ve grafikler
- [x] Hafta 5 – Analiz ekranları: sektörler, hisse karşılaştırma, risk haritası, benzer hisseler
- [x] Hafta 6 – İlk tahmin modelleri (naif, hareketli ortalama, doğrusal regresyon, ARIMA) ve geriye dönük test
- [x] Hafta 7 – Tahmin bölümü, modeller sayfası, yazdırılabilir şirket raporu, vize hazırlığı
