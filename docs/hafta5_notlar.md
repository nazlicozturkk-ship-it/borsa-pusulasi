# Hafta 5 Notları – Analiz Ekranları

## Bu hafta ne yaptık?

4. haftada ana sayfaya en çok kazandıran/kaybettiren listeleri, sektör özeti ve BIST 100
karşılaştırması zaten eklenmişti. Bu hafta analiz derinleştirildi:

| Yeni özellik | Adres | Ne gösterir? |
|---|---|---|
| Sektörler | `/sektorler` | 23 sektörün 1 aydan 10 yıla medyan getirisi (ısı tablosu), oynaklık, beta |
| Sektör sayfası | `/sektor/Finans` | Eşit ağırlıklı sektör endeksi grafiği (BIST 100 ve tüm hisselerle), sektördeki hisseler |
| Karşılaştır | `/karsilastir?k=THYAO,PGSUS` | 5 hisseye kadar aynı grafikte; getiri, risk ve korelasyon tablosu |
| Risk haritası | `/harita` | Tüm hisseler tek grafikte: yatay eksen oynaklık, dikey eksen getiri |
| Benzer hisseler | Şirket sayfasının altında | Son 1 yılda en benzer hareket eden 5 hisse |

## Yeni analizler (src/analiz)

### Sektör endeksleri (`sektor.py`)
Her sektör için **eşit ağırlıklı** endeks: her gün sektördeki hisselerin günlük getirilerinin
ortalaması alınır, bu ortalamalar bileşik olarak 100'den başlayan bir seriye çevrilir.

    endeks(t) = endeks(t−1) × (1 + ortalama günlük getiri(t))

- Günlük %50'den büyük değişimler (veri hatası olabilir) ortalamaya katılmaz.
- O gün en az 3 hisse işlem görmüyorsa sektör endeksi hesaplanmaz.
- Aynı yöntemle bütün hisseler için de bir endeks hesaplanır ("Tüm hisseler").

**Bulgu:** Son 1 yılda "Tüm hisseler" endeksi **−%38**, BIST 100 ise **−%0,3**. BIST 100
piyasa değeriyle ağırlıklı olduğu için birkaç büyük şirket endeksi ayakta tutarken,
borsadaki tipik hisse ciddi değer kaybetmiş. 3. haftadaki "medyan hisse −%44" bulgusu bu
yöntemle de doğrulanmış oldu.

### Korelasyon ve benzer hisseler (`korelasyon.py`)
Korelasyon, iki hissenin günlük getirilerinin ne kadar birlikte hareket ettiğini −1 ile +1
arasında ölçer. Son 1 yılda en az 150 ortak işlem günü olan hisse çiftleri için hesaplanır
ve her hisse için en yüksek 5 değer saklanır.

**Sonuçların mantıklı olduğunu gösteren örnekler:**

| Hisse | En benzer hisseler (korelasyon) |
|---|---|
| GARAN (Garanti) | YKBNK 0,90 · AKBNK 0,89 · ISCTR 0,85 (hepsi banka) |
| THYAO (THY) | PGSUS 0,83 (Pegasus) · TAVHL 0,66 (TAV Havalimanları) |
| ASELS (Aselsan) | ALTNY 0,51 · SDTTR 0,44 (ikisi de savunma şirketi) |
| TUPRS (Tüpraş) | AYGAZ 0,67 · PETKM 0,50 (enerji/petrokimya) |

Program sektör bilgisini hiç kullanmadan, sadece fiyat hareketlerinden aynı sektördeki
şirketleri bulabiliyor.

## Yeni veritabanı tabloları

| Tablo | İçerik |
|---|---|
| `sektor_endeksleri` | sektor, tarih, deger, hisse_sayisi (~55 bin satır) |
| `sektor_ozeti` | Her sektörün dönem bazında medyan getirisi, oynaklığı, betası |
| `benzer_hisseler` | kod, benzer_kod, korelasyon, sira |

Bu tablolar `3_analiz.bat` (veya günlük otomatik güncelleme) çalıştığında yenilenir.

## Olası hoca soruları

**Sektör endeksinde neden eşit ağırlık, neden piyasa değeri ağırlığı değil?**
Piyasa değeri verisi (hisse sayısı × fiyat) ücretsiz kaynaklarda güvenilir ve geçmişe dönük
olarak bulunmuyor. Ayrıca eşit ağırlık "sektördeki tipik hisse" sorusuna daha iyi cevap
veriyor ve BIST 100 ile karşılaştırıldığında büyük–küçük şirket farkını ortaya çıkarıyor.

**Korelasyon neden fiyatlarla değil getirilerle hesaplandı?**
Fiyatlar zamanla yükselme eğiliminde olduğu için (özellikle enflasyonlu ortamda) neredeyse
bütün hisselerin fiyatları birbiriyle yüksek korelasyonlu çıkar. Bu yanıltıcıdır ("sahte
korelasyon"). Günlük getiriler ise bu trendden arındırılmış olduğu için gerçek birlikte
hareketi ölçer.

**Risk haritası ne işe yarar?**
Bir hissenin getirisini tek başına değerlendirmek eksiktir; aynı getiriyi daha az oynaklıkla
sağlayan hisse daha iyidir. Haritanın sol üst bölgesi (endeksten az risk, endeksten fazla
getiri) en verimli hisseleri gösterir.

**Korelasyon tahminlerde kullanılacak mı?**
Olabilir: 9. haftadaki özellik mühendisliğinde benzer hisselerin ve sektör endeksinin bir
gün önceki hareketi modele ek bilgi olarak verilebilir.

## Gelecek hafta (Hafta 6)

İlk tahmin modelleri: hareketli ortalama, ARIMA ve doğrusal regresyon; modellerin geçmiş
veri üzerinde test edilmesi ve hata ölçüleri (MAE, RMSE).

## Tasarım güncellemesi: "Borsa Pusulası"

Uygulamaya kendine özgü bir kimlik verildi:
- **Ad:** Borsa Pusulası. Logo, kuzeyi mor (yükseliş), güneyi turuncu bir pusula iğnesi.
- **Tema:** "Alacakaranlık". Açık ve ferah zemin; ana sayfa girişinde çivit mavisinden mora ve
  mercana geçen bir gün batımı. Mor birincil vurgu, yükselişler zümrüt, düşüşler mercan rengi.
  Bütün renkler CSS değişkenleriyle tek bir yerde tanımlıdır; grafikler de renklerini aynı
  değişkenlerden alır.
- **İmza öğesi:** Ana sayfadaki BIST 100 kartının altında kubbe, minare ve kuleden oluşan
  soluk bir İstanbul silueti (projeye özel çizilmiş SVG).
- **Yazı tipleri:** Başlıklarda Sora, metin ve rakamlarda Manrope (sabit genişlikli rakamlar
  sayesinde tablolardaki sayılar alt alta hizalanır).
- Stil dosyası yenilenirken tarayıcının eski sürümü göstermemesi için stil ve betik
  dosyalarının adresine sürüm numarası eklendi (`style.css?v=...`).
