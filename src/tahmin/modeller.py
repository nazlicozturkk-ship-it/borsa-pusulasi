"""
Hafta 6 - İlk tahmin modelleri.

Bütün modeller aynı şekilde kullanılır:

    model.tahmin(gecmis, ufuk)  ->  Tahmin(ortalama, alt, ust)

  gecmis : fiyatların doğal logaritması (eskiden yeniye)
  ufuk   : kaç işlem günü ileriye tahmin yapılacağı
  dönen  : her gün için tahmin edilen log fiyat ve (varsa) %95 güven aralığı

Neden logaritma?
  Hisse fiyatları yüzde olarak hareket eder: 10 TL'lik hissenin 1 TL artması ile
  100 TL'lik hissenin 1 TL artması aynı şey değildir. Logaritmada eşit yüzde değişimler
  eşit adımlara dönüşür; modeller bu ölçekte daha tutarlı çalışır. Sonuç fiyata
  çevrilirken exp() alınır.

Modeller:
  Naif               : "Yarın da bugünkü fiyat olur." Karşılaştırma ölçütü (baseline).
                       Hisse fiyatları rastgeleye yakın hareket ettiği için bu modeli
                       geçmek sanıldığından zordur; diğer modeller ona göre değerlendirilir.
  HareketliOrtalama  : Son N günün ortalaması gelecekte de sabit kalır.
  DogrusalRegresyon  : Son N günün log fiyatına düz bir çizgi (trend) uydurur ve uzatır.
  Arima              : Fiyat değişimlerini kendi geçmişleriyle ve geçmiş hatalarla açıklayan
                       istatistiksel zaman serisi modeli (statsmodels kütüphanesi).
"""

import warnings
from dataclasses import dataclass

import numpy as np

Z_95 = 1.96  # %95 güven aralığı için standart normal dağılım değeri


@dataclass
class Tahmin:
    ortalama: np.ndarray            # tahmin edilen log fiyatlar
    alt: np.ndarray | None = None   # %95 güven aralığı alt sınırı (log)
    ust: np.ndarray | None = None   # %95 güven aralığı üst sınırı (log)


class Naif:
    ad = "naif"
    baslik = "Naif (son fiyat)"

    def tahmin(self, gecmis: np.ndarray, ufuk: int) -> Tahmin:
        son = gecmis[-1]
        # Rastgele yürüyüş varsayımı: belirsizlik zamanla √gün oranında büyür
        sigma = np.std(np.diff(gecmis[-250:]))
        adim = np.arange(1, ufuk + 1)
        ortalama = np.full(ufuk, son)
        return Tahmin(ortalama, ortalama - Z_95 * sigma * np.sqrt(adim), ortalama + Z_95 * sigma * np.sqrt(adim))


class HareketliOrtalama:
    ad = "hareketli_ortalama"
    baslik = "Hareketli ortalama (20 gün)"

    def __init__(self, pencere: int = 20):
        self.pencere = pencere

    def tahmin(self, gecmis: np.ndarray, ufuk: int) -> Tahmin:
        return Tahmin(np.full(ufuk, gecmis[-self.pencere:].mean()))


class DogrusalRegresyon:
    ad = "dogrusal_regresyon"
    baslik = "Doğrusal regresyon (6 ay trend)"

    def __init__(self, pencere: int = 120):
        self.pencere = pencere

    def tahmin(self, gecmis: np.ndarray, ufuk: int) -> Tahmin:
        from sklearn.linear_model import LinearRegression

        y = gecmis[-self.pencere:]
        x = np.arange(len(y)).reshape(-1, 1)
        model = LinearRegression().fit(x, y)
        gelecek = np.arange(len(y), len(y) + ufuk).reshape(-1, 1)
        ortalama = model.predict(gelecek)
        # Basit güven aralığı: trend çizgisinden sapmaların standart sapması
        sigma = np.std(y - model.predict(x))
        return Tahmin(ortalama, ortalama - Z_95 * sigma, ortalama + Z_95 * sigma)


class Arima:
    ad = "arima"
    baslik = "ARIMA"

    # Denenecek (p, d, q) dereceleri. d=1: model fiyatın kendisini değil günlük değişimini modeller.
    # (2,1,2) gibi daha büyük dereceler çok daha yavaş eğitiliyor ve günlük hisse getirilerinde
    # belirgin bir kazanç sağlamıyor; bu yüzden aday listesi küçük tutuldu.
    ADAYLAR = [(0, 1, 0), (1, 1, 0), (0, 1, 1), (1, 1, 1)]

    def __init__(self, derece: tuple[int, int, int] | None = None):
        self.derece = derece  # None ise derece_sec() ile seçilir

    @staticmethod
    def _uydur(gecmis: np.ndarray, derece):
        from statsmodels.tsa.arima.model import ARIMA

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # yakınsama uyarıları vb.
            # trend="t": fiyatların uzun vadeli ortalama artışı (sürüklenme) da modele dahil
            # maxiter: en fazla 50 optimizasyon adımı (yakınsamayan durumlarda süreyi sınırlar)
            return ARIMA(gecmis, order=derece, trend="t").fit(method_kwargs={"maxiter": 50})

    @classmethod
    def derece_sec(cls, gecmis: np.ndarray) -> tuple[int, int, int]:
        """Aday dereceler arasından AIC'si en düşük olanı seçer (AIC: uyum ile sadelik dengesi)."""
        en_iyi, en_iyi_aic = (0, 1, 0), np.inf
        for derece in cls.ADAYLAR:
            try:
                aic = cls._uydur(gecmis, derece).aic
            except Exception:
                continue
            if np.isfinite(aic) and aic < en_iyi_aic:
                en_iyi, en_iyi_aic = derece, aic
        return en_iyi

    def tahmin(self, gecmis: np.ndarray, ufuk: int) -> Tahmin:
        derece = self.derece or self.derece_sec(gecmis)
        sonuc = self._uydur(gecmis, derece).get_forecast(steps=ufuk)
        aralik = np.asarray(sonuc.conf_int(alpha=0.05))
        return Tahmin(np.asarray(sonuc.predicted_mean), aralik[:, 0], aralik[:, 1])


def tum_modeller(arima_derecesi=None) -> list:
    """Karşılaştırılacak modellerin listesi (ilk sıradaki naif model ölçüttür)."""
    return [Naif(), HareketliOrtalama(), DogrusalRegresyon(), Arima(arima_derecesi)]


MODEL_BASLIKLARI = {m.ad: m.baslik for m in tum_modeller()}
