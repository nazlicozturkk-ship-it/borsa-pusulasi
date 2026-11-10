# Hafta 6 Notları – İlk Tahmin Modelleri

## Bu hafta ne yaptık?

1. Dört tahmin modeli yazıldı: **naif**, **hareketli ortalama**, **doğrusal regresyon**, **ARIMA**.
2. Modeller her hissede **geçmiş veri üzerinde test edildi** (geriye dönük test / backtest).
3. Hata ölçüleri hesaplandı: **MAE, RMSE, MAPE**, **yön doğruluğu** ve **naif modele göre iyileşme**.
4. Her hisse için en iyi model seçildi ve bütün modellerle **gelecek 20 işlem günü** (yaklaşık
   1 ay) %95 güven aralıklarıyla tahmin edildi.

## Dosyalar

| Dosya | Görevi |
|---|---|
| `src/tahmin/modeller.py` | Dört model, ortak `tahmin(gecmis, ufuk)` arayüzüyle |
| `src/tahmin/degerlendirme.py` | Geriye dönük test ve hata ölçüleri |
| `src/tahmin/calistir.py` | Bütün hisselerde paralel çalıştırma, sonuçları kaydetme |
| `7_tahmin_deneme.bat` | Sadece BIST 30 ile hızlı deneme |
| `7_tahmin_modelleri.bat` | Bütün hisseler |

## Modeller

Bütün modeller fiyatın **logaritması** üzerinde çalışır. Hisse fiyatları yüzde olarak hareket
eder; logaritmada eşit yüzde değişimler eşit adımlara dönüşür. Sonuçlar `exp()` ile fiyata çevrilir.

| Model | Mantığı |
|---|---|
| **Naif** | "Gelecekte de bugünkü fiyat olur." Diğer modellerin geçmesi gereken **ölçüt** (baseline). |
| **Hareketli ortalama** | Son 20 günün ortalama fiyatı sabit kalır. Kısa vadeli dalgalanmayı yumuşatır. |
| **Doğrusal regresyon** | Son 120 günün (~6 ay) log fiyatına düz bir trend çizgisi uydurulur ve uzatılır. |
| **ARIMA(p,1,q)** | Günlük fiyat değişimlerini kendi geçmiş değerleri (AR, p) ve geçmiş tahmin hataları (MA, q) ile açıklar; d=1 fiyatın değil değişimin modellendiğini gösterir. Sürüklenme (drift) terimi uzun vadeli ortalama artışı yakalar. |

**ARIMA derecesi nasıl seçildi?** Her hisse için 4 aday — (0,1,0), (1,1,0), (0,1,1), (1,1,1) —
son 2 yılın verisiyle denenir (daha büyük dereceler çok yavaş eğitildiği ve günlük getirilerde
belirgin kazanç sağlamadığı için aday listesine alınmadı); **AIC** değeri en düşük olan seçilir. AIC, modelin veriye
uyumunu ödüllendirirken gereksiz parametreleri cezalandırır (aşırı uyumu önler).

## Geriye dönük test (backtest)

Bir modeli, tahmin ettiği dönemi **görmeden** test etmek gerekir. Bu yüzden geçmişte 6 başlangıç
noktası seçildi (aralarında 20 işlem günü):

    [ eğitim: son 2 yıl ][ test: 20 gün ]
          [ eğitim: son 2 yıl ][ test: 20 gün ]
                ...  (6 kez, en yenisi bugünden 20 gün öncesi)

Her başlangıçta model sadece o güne kadarki veriyle eğitilir; sonraki 20 günün tahmini gerçekleşen
fiyatlarla karşılaştırılır.

## Hata ölçüleri

| Ölçü | Formül | Anlamı |
|---|---|---|
| MAE | ortalama(\|tahmin − gerçek\|) | Ortalama kaç TL şaştı |
| RMSE | √ortalama((tahmin − gerçek)²) | Büyük hataları daha çok cezalandırır; en iyi model buna göre seçilir |
| MAPE | ortalama(\|tahmin − gerçek\| / gerçek) | Yüzde hata; farklı fiyattaki hisseleri karşılaştırmak için |
| Yön doğruluğu | 20 gün sonraki artış/azalış yönünü bilme oranı | %50 yazı-tura demektir |
| Naife göre iyileşme | 1 − RMSE(model) / RMSE(naif) | Pozitifse model naiften iyi |

## Beklenen (ve önemli) bulgu

BIST 30 denemesinde (gerçek ARIMA ile) 30 hissenin **16'sında en iyi tahmini naif model** yaptı;
hareketli ortalama 7, doğrusal regresyon 4, ARIMA 3 hissede en iyiydi. Medyan yüzde hata naif modelde
%6,0, ARIMA'da %6,1 oldu. Modellerin yön doğruluğu %37–56 arasında, yani yazı-turaya yakın kaldı. Bu bir hata değil, finans literatüründe iyi
bilinen bir durumdur:

- **Etkin piyasa hipotezi:** Herkesin bildiği geçmiş fiyat bilgisi zaten fiyata yansımıştır; bu
  yüzden sadece geçmiş fiyatlara bakarak geleceği tahmin etmek çok zordur.
- **Rastgele yürüyüş:** Kısa vadede hisse fiyatlarının değişimi büyük ölçüde rastgeledir. Rastgele
  yürüyüşte en iyi tahmin "bugünkü fiyat"tır, yani naif model.

Bu yüzden projede her model **naif modelle karşılaştırılarak** değerlendirilir. Naifi geçemeyen
bir modelin "%95 doğrulukla tahmin" iddiası yanıltıcı olur. Gerçek sonuçlar bilgisayarda çalıştırıldıktan
sonra `logs/tahmin.log` ve `data/model_performans.csv` dosyalarındadır.

**Sonraki haftalarda modelleri iyileştirmek için:** teknik göstergeler (RSI, MACD), makro veriler
(dolar/TL, faiz), sektör ve benzer hisse hareketleri gibi ek bilgiler (9. hafta) ve makine öğrenmesi
modelleri (XGBoost, LSTM — 10. ve 11. haftalar).

## Olası hoca soruları

**Neden veriyi rastgele eğitim/test diye bölmediniz?**
Zaman serilerinde rastgele bölmek geleceği eğitime sızdırır (model 2026 verisini görüp 2025'i
"tahmin eder"). Doğru yöntem, eğitimin her zaman testten önce bittiği zaman sıralı bölmedir.

**Güven aralığı ne demek?**
%95 güven aralığı, modelin varsayımları doğruysa gerçek fiyatın yaklaşık %95 olasılıkla bu aralıkta
kalacağını söyler. Aralığın zamanla genişlemesi, uzak geleceğin daha belirsiz olduğunu gösterir.

**Tahminler neden 20 işlem günü?**
Yaklaşık bir aylık ufuk hem kullanıcı için anlamlı, hem de modellerin farkını ölçmeye yetecek kadar
uzun. Tatil günleri hesaba katılmadı, sadece hafta sonları atlandı.

**İlk hisseler neden uzun sürüyor?**
Paralel çalışan her işlem başlarken statsmodels, scipy ve scikit-learn kütüphanelerini yeniden yükler.
Windows'ta ilk çalıştırmada bu yaklaşık 2 dakika sürdü (BIST 30 denemesinde ilk 4 hisse 141 saniye),
sonraki her hisse ise yaklaşık 1 saniye. Ayrıca her işlemin tek işlemci çekirdeği kullanması
sağlandı; aksi halde işlemler aynı çekirdekler için yarışıp birbirini yavaşlatıyordu.

**Paralel işleme neden gerekti?**
ARIMA her hisse için 11 kez eğitiliyor (4 derece denemesi + 6 test + 1 son tahmin). 600 hisse için
bu yaklaşık 6.500 model eğitimi demek. Hisseler işlemci çekirdeklerine dağıtılarak süre kısaltıldı.

## Gelecek hafta (Hafta 7)

Tahmin grafiklerinin şirket sayfasına eklenmesi (güven aralığı bandıyla), modellerin karşılaştırma
ekranı, her şirket için otomatik rapor ve vize sunumunun hazırlanması.
