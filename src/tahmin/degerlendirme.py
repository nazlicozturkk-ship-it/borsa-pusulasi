"""
Hafta 6 - Modellerin geçmiş veri üzerinde test edilmesi (geriye dönük test / backtest).

Bir modelin ne kadar iyi tahmin yaptığını, tahmin ettiği dönemi "görmeden" ölçmek gerekir.
Bunun için geçmişte birkaç farklı başlangıç noktası seçilir:

    zaman ──────────────────────────────────────────────────────▶
    [ eğitim (son 2 yıl) ][ test 20 gün ]                         başlangıç 1
          [ eğitim (son 2 yıl) ][ test 20 gün ]                   başlangıç 2
                ...
                         [ eğitim (son 2 yıl) ][ test 20 gün ]    başlangıç 6 (en yeni)

Her başlangıçta model sadece o güne kadarki veriyle eğitilir, sonraki 20 işlem günü
(~1 ay) tahmin edilir ve gerçekleşen fiyatlarla karşılaştırılır.

Hata ölçüleri (fiyat ölçeğinde, TL):
  MAE   : ortalama mutlak hata. "Tahmin ortalama kaç TL şaştı?"
  RMSE  : hataların karelerinin ortalamasının karekökü. Büyük hataları daha çok cezalandırır.
  MAPE  : ortalama mutlak yüzde hata. Farklı fiyattaki hisseleri karşılaştırmak için.
  Yön   : 20 gün sonunda fiyatın artacağını/azalacağını doğru bilme oranı.
  Naife göre iyileşme = 1 - RMSE(model) / RMSE(naif).
          Pozitifse model "yarın da bugünkü fiyat olur" tahmininden daha iyi.
"""

import numpy as np

UFUK = 20          # tahmin edilecek işlem günü (~1 ay)
BASLANGIC = 6      # geriye dönük test başlangıç noktası sayısı
ADIM = 20          # başlangıç noktaları arası işlem günü
EGITIM = 500       # her modelin eğitildiği en fazla işlem günü (~2 yıl)
EN_AZ_EGITIM = 250 # bundan kısa geçmişle test yapılmaz (~1 yıl)


def baslangic_noktalari(n: int) -> list[int]:
    """Testlerin başlayacağı indeksler (eskiden yeniye). Veri yetmezse daha az nokta döner."""
    noktalar = [n - UFUK - k * ADIM for k in range(BASLANGIC)]
    return sorted(c for c in noktalar if c >= EN_AZ_EGITIM)


def geriye_donuk_test(log_fiyat: np.ndarray, modeller: list) -> dict[str, dict]:
    """
    Her model için hata ölçülerini döndürür:
    {model_adi: {"mae", "rmse", "mape", "yon", "test_sayisi"}}
    """
    sonuclar: dict[str, dict] = {}
    for model in modeller:
        mutlak, kare, yuzde, yon, sayi = [], [], [], [], 0
        for c in baslangic_noktalari(len(log_fiyat)):
            egitim = log_fiyat[max(0, c - EGITIM):c]
            gercek = np.exp(log_fiyat[c:c + UFUK])
            try:
                tahmin = np.exp(model.tahmin(egitim, UFUK).ortalama)
            except Exception:
                continue  # bu başlangıçta model çalışmadıysa diğerlerine devam
            if not np.all(np.isfinite(tahmin)):
                continue
            hata = tahmin - gercek
            mutlak.extend(np.abs(hata))
            kare.extend(hata ** 2)
            yuzde.extend(np.abs(hata) / gercek)
            sayi += 1
            son_fiyat = np.exp(egitim[-1])
            # Yön: model artış veya azalış öngördüyse doğru bilip bilmediği.
            # Naif model hiçbir yön öngörmez (fiyat aynı kalır), bu yüzden onda ölçülmez.
            tahmini_yon = np.sign(tahmin[-1] - son_fiyat)
            if tahmini_yon != 0:
                yon.append(tahmini_yon == np.sign(gercek[-1] - son_fiyat))
        if mutlak:
            sonuclar[model.ad] = {
                "mae": float(np.mean(mutlak)),
                "rmse": float(np.sqrt(np.mean(kare))),
                "mape": float(np.mean(yuzde)),
                "yon": float(np.mean(yon)) if yon else float("nan"),
                "test_sayisi": sayi,
            }
    return sonuclar
