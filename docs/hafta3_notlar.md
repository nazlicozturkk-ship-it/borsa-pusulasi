# Hafta 3 Notları – Veri Kalitesi ve Dönemsel Getiri Hesapları

## Bu hafta ne yaptık?

1. **Veri kalitesi kontrolü:** Her hissenin fiyat verisi eksik gün, aşırı fiyat hareketi,
   hacimsiz gün ve mantıksız fiyat satırları (OHLC hatası) açısından kontrol edildi.
2. **Getiri hesapları:** Her hisse için 1 ay, 3 ay, 6 ay, yılbaşından bu yana, 1 yıl,
   5 yıl ve 10 yıllık getiriler hesaplandı.
3. **Risk ölçüleri:** Volatilite, maksimum düşüş ve beta hesaplandı.
4. **Endeks karşılaştırması:** Her dönem için hissenin BIST 100'e göre farkı hesaplandı.
5. **Otomatik günlük güncelleme:** Hafta içi her akşam fiyatların indirilip analizlerin
   yenilenmesi için Windows Görev Zamanlayıcısı'na görev eklendi.

Sonuçlar veritabanında `veri_kalitesi` ve `getiriler` tablolarında, ayrıca Excel'de
açılabilen `data/getiriler.csv` ve `data/veri_kalitesi.csv` dosyalarında.

## Yeni dosyalar

| Dosya | Görevi |
|---|---|
| `src/analiz/veri_kalitesi.py` | Kalite kontrolleri |
| `src/analiz/getiri.py` | Getiri ve risk formülleri |
| `src/analiz/analiz.py` | İkisini çalıştırır, sonuçları kaydeder ve özet yazar |
| `3_analiz.bat` | Analizi elle çalıştırır |
| `4_gunluk_guncelleme.bat` | Fiyat güncellemesi + analiz (otomatik görev bunu çalıştırır) |
| `5_otomatik_guncelleme_ac.bat` / `_kapat.bat` | Otomatik görevi açar / kapatır |

## Formüller

| Ölçü | Formül | Ne anlatır? |
|---|---|---|
| Dönem getirisi | son fiyat / dönem başı fiyat − 1 | O dönemde yüzde kaç kazandırdı |
| Yıllık (bileşik) getiri | (1 + getiri)^(1/yıl) − 1 | Uzun dönem getiriyi yıllık ortalamaya çevirir |
| Volatilite | std(günlük getiri) × √252 | Fiyatın ne kadar oynak olduğu (risk) |
| Maksimum düşüş | min(fiyat / o ana kadarki zirve − 1) | Zirveden yaşanan en büyük kayıp |
| Beta | kov(hisse, endeks) / var(endeks) | Endekse duyarlılık: 1,5 ise endeks %1 oynadığında hisse ~%1,5 oynar |
| Endekse göre fark | hisse getirisi − BIST 100 getirisi | Pozitifse hisse endeksi geçmiş |

**Neden √252?** Borsada bir yılda yaklaşık 252 işlem günü vardır. Günlük oynaklığı yıllığa
çevirmek için √252 ile çarpılır (bağımsız günlük değişimlerin varyansları toplanır).

**Dönem başı fiyat nasıl bulunuyor?** Örneğin 1 yıllık getiri için tam 1 yıl önceki tarihin
kapanışı alınır. O gün tatil ya da hafta sonuysa ondan önceki son işlem günü kullanılır.

## Doğrulama

Hesaplar elle kontrol edildi. Örnek olarak THY (THYAO) 3 Kasım 2026 itibarıyla:
- 1 yıl önceki kapanış 294,00 TL, son kapanış 265,00 TL
- Elle hesap: 265 / 294 − 1 = **−%9,86**, sistemin hesabı: **−%9,86**
- 10 yıllık getiri yıllıklandırması da elle hesapla aynı çıktı (%47,8)

## Bulgular (3 Kasım 2026 verisiyle)

- 634 kodun 617'sinin verisi sorunsuz, 17'si işaretlendi (çoğu işlem görmeyen veya
  çok eski bölünmesi olan hisseler).
- Son 1 yılda BIST 100 yatay (−%0,3), BIST 30 ise +%14,5. Buna karşın **medyan hisse
  yaklaşık −%44**. Sadece 92 hisse BIST 100'ü geçebildi.
- Bunun sebebi BIST 100'ün **piyasa değeriyle ağırlıklı** olması: büyük şirketler endeksi
  taşırken küçük hisseler, özellikle Eylül–Ekim 2026'daki sert düşüşte, çok daha fazla
  değer kaybetti. Bu, veri hatası olmadığı tek tek hisseler incelenerek doğrulandı.

## Olası hoca soruları

**Getiriler enflasyondan arındırılmış mı?**
Hayır, getiriler nominal TL getirisidir. Örneğin THY'nin 10 yıllık getirisi yaklaşık
+%4.860 görünür; bunun büyük kısmı TL'nin değer kaybından kaynaklanır. İleride dolar bazlı
veya enflasyona göre düzeltilmiş getiri eklenebilir (9. haftadaki makro veriler ile).

**Temettüler dahil mi?**
Hayır. Fiyatlar sadece bölünmelere (bedelsiz sermaye artırımlarına) göre düzeltilmiştir;
temettüler dahil edilmemiştir. Bu yüzden yüksek temettü veren hisselerin toplam getirisi
gösterilenden biraz daha yüksektir.

**Neden kalite sorunu olan veriyi silmediniz?**
Aşırı bir hareket gerçek bir olay da olabilir (örneğin uzun bir işlem yasağından sonra
açılış). Veriyi otomatik silmek doğru bilgiyi de silebilir. Bu yüzden veri işaretlenir ve
modeller kurulurken (6. hafta) işaretli hisseler ayrıca ele alınır.

**İşlem görmeyen hisseler ne oldu?**
Son 30 günde işlem görmeyen hisseler getiri tablosuna alınmadı, çünkü "son fiyat" güncel
değil ve getirileri yanıltıcı olurdu.

## Gelecek hafta (Hafta 4)

Web uygulamasının iskeleti: FastAPI ile ana sayfa, şirket arama ve her şirket için
fiyat grafiği ile bu hafta hesaplanan getirilerin gösterildiği detay sayfası.
