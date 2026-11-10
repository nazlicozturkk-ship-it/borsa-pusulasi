# Hafta 2 Notları – 10 Yıllık Fiyat Verilerinin Toplanması

## Bu hafta ne yaptık?

1. Veritabanına iki yeni tablo eklendi: **fiyatlar** ve **veri_durumu**.
2. Tüm BIST şirketleri ile BIST 30 ve BIST 100 endekslerinin son 10 yıllık **günlük**
   fiyat verisi (açılış, en yüksek, en düşük, kapanış, hacim) indirildi.
3. Borsada işlem görmeyen veya hisse senedi olmayan kodlar otomatik olarak ayıklandı.
4. Veri her gün tekrar çalıştırılabilecek şekilde **artımlı güncelleme** yapısı kuruldu.

## Yeni tablolar

**fiyatlar**: her satır bir kodun bir günlük verisidir.

| Sütun | Açıklama |
|---|---|
| kod | Hisse veya endeks kodu (THYAO, XU100) |
| tarih | İşlem günü |
| acilis, yuksek, dusuk, kapanis | O günün fiyatları (TL) |
| hacim | İşlem gören lot sayısı |

`kod + tarih` birlikte **birincil anahtardır**, yani aynı hissenin aynı günü iki kez kaydedilemez.

**veri_durumu**: her kodun verisinin özeti (ilk ve son tarih, gün sayısı, kaynak, durum).
Durum değerleri:
- `tamam`: veri güncel
- `islem_gormuyor`: son 30 günde işlem yok (borsadan çıkmış veya işlemleri durdurulmuş)
- `veri_yok`: hiçbir kaynakta veri yok (çoğunlukla hisse senedi olmayan kodlar)

## Nasıl çalışıyor?

`src/veri/fiyat_verisi.py` dosyası:

1. Şirket listesini veritabanından okur.
2. Her kod için hangi tarihten itibaren veri gerektiğine karar verir:
   - Daha önce hiç indirilmediyse: **son 10 yıl**
   - Daha önce indirildiyse: **son kaydedilen günden 7 gün öncesinden itibaren**
     (son günlerdeki olası düzeltmeleri de almak için)
3. Veriyi **TradingView**'dan (borsapy ile) çeker. Veri gelmezse **Yahoo Finance**'e
   (yfinance ile) geçer. Geçici bağlantı hatalarına karşı her kaynak 2 kez denenir.
4. Aynı anda **4 hisse paralel** indirilir (`ThreadPoolExecutor`). Tek tek indirmeye
   göre yaklaşık 4 kat hızlıdır. Sunucuyu yormamak için daha fazla artırılmadı.
5. Veritabanına yazma sadece ana iş parçacığında yapılır, çünkü SQLite aynı anda
   birden fazla yazmayı desteklemez.

## Olası hoca soruları

**Fiyatlar neden "düzeltilmiş"?**
Türkiye'de şirketler sık sık bedelsiz sermaye artırımı yapar. Örneğin %100 bedelsizde
hisse fiyatı bir gecede yarıya iner ama yatırımcı para kaybetmez. Düzeltilmemiş veride bu
durum sahte bir %50'lik düşüş gibi görünür ve hem getiri hesaplarını hem de tahmin
modellerini bozar. TradingView verisi bu artırımlara göre düzeltilmiş gelir.

**Neden iki veri kaynağı var?**
Ücretsiz kaynaklar zaman zaman çalışmayabilir ya da bazı hisseleri içermeyebilir. Yedek
kaynak sistemi daha güvenilir yapar. (1. haftada İş Yatırım sitesindeki değişiklik bunun
neden gerekli olduğunu gösterdi.)

**10 yıldan kısa verisi olan şirketler ne olacak?**
Son 10 yılda halka arz olan şirketlerin verisi halka arz tarihinden başlar. Getiri
hesaplarında (3. hafta) bu şirketler için 10 yıllık ve 5 yıllık getiri "hesaplanamaz"
olarak gösterilecek, sıfır veya yanlış bir değer yazılmayacak.

**Program yarıda kesilirse ne olur?**
Her hisse indirildiği anda veritabanına yazılır. Program tekrar çalıştırıldığında
tamamlanan hisseler için sadece son günler indirilir, yani kaldığı yerden devam eder.

**Veritabanı ne kadar büyük?**
Yaklaşık 600 hisse × 2.500 gün ≈ 1,5 milyon satır. SQLite için sorun olmayan bir boyut
(yaklaşık 100–150 MB).

## Gelecek hafta (Hafta 3)

Veri kalitesi kontrolleri (eksik günler, aşırı sıçramalar) ve her hisse için 1 ay,
3 ay, 6 ay, 1 yıl, 5 yıl ve 10 yıllık getiri ile volatilite hesapları.
