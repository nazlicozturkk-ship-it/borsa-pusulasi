# Hafta 4 Notları – Web Uygulamasının İlk Sürümü

## Bu hafta ne yaptık?

FastAPI ile çalışan bir web uygulaması kuruldu. `6_web_uygulamasi.bat` ile başlatılıyor ve
tarayıcıda `http://127.0.0.1:8000` adresinde açılıyor. Üç sayfa var:

| Sayfa | Adres | İçerik |
|---|---|---|
| Ana sayfa | `/` | BIST 100 değeri ve grafiği, endeksin dönem getirileri, son günde yükselen/düşen hisse sayısı, en çok kazandıran ve kaybettiren hisseler (dönem seçilebilir), sektörlerin medyan getirisi |
| Şirketler | `/sirketler` | Tüm hisselerin tablosu: arama, sektör ve endeks filtresi, her sütuna göre sıralama |
| Şirket detayı | `/sirket/THYAO` | Son fiyat, etkileşimli fiyat grafiği (dönem seçimi, mum grafiği, BIST 100 ile karşılaştırma, hacim), dönem getirileri ve BIST 100 farkı, risk ölçüleri |

Üstteki arama kutusu her sayfada çalışır; yazdıkça kod ve şirket adına göre öneri getirir.

## Mimari

```
Tarayıcı  ──istek──▶  FastAPI (src/web/app.py)
                         │  sayfa adresleri  → Jinja2 şablonları (HTML)
                         │  /api/... adresleri → JSON veri
                         ▼
                   Veri katmanı (src/web/veri.py, önbellekli)
                         ▼
                   Veritabanı (data/bist.db)
```

| Dosya | Görevi |
|---|---|
| `src/web/app.py` | Adresler (route) ve sayı biçimlendirme |
| `src/web/veri.py` | Sayfaların ihtiyaç duyduğu sorgular, önbellek |
| `src/web/templates/*.html` | Sayfaların HTML şablonları (Jinja2) |
| `src/web/static/style.css` | Tasarım |
| `src/web/static/app.js` | Arama kutusu, grafikler (Plotly), tablo filtre/sıralama |

**JSON servisleri:** `/api/ara?q=aselsan` arama sonuçlarını, `/api/fiyat/THYAO` grafik için
fiyat geçmişini döndürür. Otomatik oluşturulan API belgesi `/api/belgeler` adresindedir.

## Tasarım kararları

- **Getiri şeridi:** 1 aydan 10 yıla kadar her dönemin getirisi yan yana renkli kutularda
  gösterilir; rengin koyuluğu getirinin büyüklüğünü anlatır. Böylece bir hissenin kısa ve
  uzun vadeli performansı tek bakışta okunur. Şirketler tablosunda her satırda küçük hali var.
- **Türkçe sayı biçimi:** Ondalık için virgül, binlik için nokta (1.234,56), yüzde işareti
  sayının önünde (%12,5).
- **Renkler:** Yükseliş yeşil, düşüş kırmızı; vurgu rengi İstanbul'un İznik çinilerinden
  esinlenen turkuaz.
- **İnternetsiz çalışma:** Grafik kütüphanesi (plotly.js) internetten değil, bilgisayarda kurulu
  Python plotly paketinin içinden sunulur. Sunumda internet olmasa da grafikler çalışır.
  (Yazı tipi internetten yüklenir; internet yoksa sistem yazı tipi kullanılır.)
- **Telefona uyumlu:** Sayfalar dar ekranda tek sütuna geçer, tablolar yatay kaydırılır.

## Olası hoca soruları

**Neden FastAPI?**
Modern, hızlı ve az kodla hem HTML sayfası hem JSON servis sunabilen bir Python çatısıdır.
Otomatik API belgesi üretir. İleride tahmin modelleri de aynı uygulamaya servis olarak eklenecek.

**Önbellek ne işe yarıyor?**
Getiri tablosu her sayfa açılışında veritabanından okunmaz, bellekte tutulur. Veritabanı
dosyası değiştiğinde (günlük güncellemeden sonra) otomatik yeniden okunur. Bu sayede sayfalar
anında açılır ama veriler her zaman güncel kalır.

**Grafik verisi nasıl geliyor?**
Sayfa açıldığında tarayıcı `/api/fiyat/KOD` adresinden 10 yıllık veriyi bir kez alır. Dönem
düğmelerine (1A, 1Y…) basıldığında yeni istek atılmaz, grafik tarayıcıda yeniden çizilir.

**Sektör karşılaştırmasında neden medyan?**
Ortalama birkaç aşırı değere çok duyarlıdır: bir sektörde bir hisse %500 yükseldiyse ortalama
sektörü olduğundan iyi gösterir. Medyan, sektördeki "tipik" hisseyi gösterir.

## Gelecek hafta (Hafta 5)

Analiz ekranlarının zenginleştirilmesi: hisse karşılaştırma, sektör sayfaları, getiri
dağılımı ve korelasyon grafikleri.
