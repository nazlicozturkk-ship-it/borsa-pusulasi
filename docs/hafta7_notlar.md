# Hafta 7 Notları – Tahminlerin Siteye Eklenmesi ve Vize Hazırlığı

## Bu hafta ne yaptık?

1. **Şirket sayfasına tahmin bölümü:** Her hisse için önümüzdeki 20 işlem günü.
   - Özet kartları: en iyi model, 20 gün sonraki tahmini fiyat ve değişim, %95 olası aralık,
     geçmiş testteki ortalama hata ve naif modele göre fark.
   - Grafik: son 6 ayın gerçekleşen fiyatı + dört modelin tahmini. En iyi model kalın çizgi ve
     %95 güven aralığı bandıyla, diğerleri kesikli çizgiyle.
   - Tablo: o hissede dört modelin geçmiş test sonuçları (ortalama hata, RMSE, yön doğruluğu,
     naife göre fark) ve 20 gün sonraki tahminleri.
   - En iyi model naif çıkarsa bunu açıklayan bir not.
2. **Modeller sayfası (`/modeller`):** Dört modelin bütün borsadaki karşılaştırması, bulgular
   ("Ne öğrendik?") ve ARIMA'nın en başarılı olduğu 10 hisse.
3. **Şirket raporu (`/rapor/KOD`):** Her şirket için iki sayfalık, yazdırılabilir rapor. "Yazdır / PDF
   olarak kaydet" düğmesiyle tarayıcıdan PDF'e çevrilir. Şirket sayfasındaki "Rapor" düğmesiyle açılır.
4. **Günlük güncelleme:** `4_gunluk_guncelleme.bat` artık fiyatları, analizleri ve tahminleri
   sırasıyla yeniliyor (3 adım).

## Yeni / değişen dosyalar

| Dosya | Görevi |
|---|---|
| `src/web/templates/_tahmin.html` | Tahmin bölümü (şirket sayfası ve raporda ortak) |
| `src/web/templates/modeller.html` | Modeller sayfası |
| `src/web/templates/rapor.html` | Yazdırılabilir şirket raporu |
| `src/web/veri.py` | Tahmin sorguları: `tahmin_bilgisi`, `tahmin_grafigi`, `model_karsilastirmasi` |
| `src/web/app.py` | Yeni adresler: `/modeller`, `/rapor/{kod}`, `/api/tahmin/{kod}` |
| `src/web/static/app.js` | Tahmin grafiği, yazdırma öncesi grafik boyutlandırma |

## Tasarım kararları

- **Tahmin her zaman hatasıyla birlikte gösterilir.** Kullanıcı sadece "65 TL olacak" değil,
  "bu model geçmişte ortalama %4,8 yanıldı" bilgisini de görür. Yanıltıcı kesinlik önlenir.
- **Belirsizlik görselleştirilir.** Güven aralığı bandı zamanla genişler; uzak geleceğin daha
  belirsiz olduğu grafikten görülür.
- **Naif model her yerde ölçüt olarak durur.** Bir modelin "iyi" olup olmadığı, en basit tahminle
  karşılaştırılarak anlaşılır.
- **Rapor PDF için ek kütüphane kullanmaz.** Tarayıcının yazdırma özelliği kullanılır; yazdırmadan
  hemen önce grafikler A4 genişliğine küçültülür.

## Vize sunumu için demo akışı (önerilen, ~5 dakika)

1. **Ana sayfa:** BIST 100 kartı, getiri şeridi, dönem sekmeleri. Bulgu: endeks yatayken tipik hisse −%40.
2. **Arama → THYAO:** fiyat grafiği (1A–10Y, mum, BIST 100 ile karşılaştırma), getiriler, risk.
3. **Tahmin bölümü:** en iyi model, güven bandı, model tablosu.
4. **Benzer hisseler → Karşılaştır:** THYAO, PGSUS, TAVHL; korelasyon tablosu.
5. **Risk haritası:** sektör vurgulama, bir noktaya tıklayıp şirkete geçiş.
6. **Modeller sayfası:** "naif model hisselerin yarısında en iyi" bulgusu ve anlamı.
7. **Rapor:** bir şirketin raporunu açıp PDF olarak kaydetme.

## Olası hoca soruları

**Tahminleriniz ne kadar doğru?**
Ortalama yüzde hata hisselerin yarısında %10'un altında, ama bu oranı naif modelle karşılaştırmak
gerekir: naif model de benzer hatayı yapıyor. ARIMA hisselerin %35'inde naif modelden daha iyi.
Yön tahmininde hiçbir model %50'yi belirgin şekilde geçemedi. Bunu saklamak yerine sitede açıkça
gösteriyoruz.

**Neden en iyi modeli her hisse için ayrı seçtiniz?**
Hisseler farklı davranıyor: bazıları belirgin trendli, bazıları rastgeleye yakın. Tek bir modeli her
yere uygulamak yerine, her hissede geçmiş testte en iyi sonucu veren model kullanılıyor.

**Bu seçim aşırı uyuma (overfitting) yol açmaz mı?**
Risk var, çünkü en iyi model aynı test verisine bakılarak seçiliyor. 12. haftada bunu ayrı bir
doğrulama dönemiyle (seçim için kullanılmayan son dönem) ölçmeyi planlıyoruz.

## Vize sonrası (Hafta 9–15)

Teknik göstergeler ve makro veriler (9), XGBoost/LightGBM ve Prophet (10), LSTM (11), otomatik model
seçimi ve toplu tahmin (12), gelişmiş arayüz ve Excel/PDF indirme (13), performans ve sunucuya
yükleme (14), proje raporu ve final sunumu (15).
