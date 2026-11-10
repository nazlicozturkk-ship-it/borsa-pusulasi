"""
Hafta 5 - Korelasyon: hangi hisseler birlikte hareket ediyor?

Korelasyon iki hissenin günlük getirilerinin ne kadar birlikte hareket ettiğini
-1 ile +1 arasında bir sayıyla ölçer:
   +1 : her gün aynı yönde ve orantılı hareket
    0 : aralarında bir ilişki yok
   -1 : biri yükselirken diğeri düşüyor

Her hisse için son 1 yılda en yüksek korelasyona sahip 5 hisse "benzer hisseler"
olarak kaydedilir. Bu bilgi:
  - Portföy çeşitlendirmede (birbirine çok benzeyen hisseler riski azaltmaz),
  - İleride tahmin modellerinde (benzer hisselerin hareketi bir ipucu olabilir)
kullanılabilir.
"""

import numpy as np
import pandas as pd

EN_AZ_ORTAK_GUN = 150   # iki hissenin birlikte işlem gördüğü en az gün sayısı
BENZER_SAYISI = 5


def gunluk_getiriler(fiyatlar: pd.DataFrame, kodlar: list[str], gun: int = 365) -> pd.DataFrame:
    """Verilen kodların son 'gun' takvim günündeki günlük getiri tablosu (satır: tarih, sütun: kod)."""
    secili = fiyatlar[fiyatlar["kod"].isin(kodlar)]
    kapanis = secili.pivot(index="tarih", columns="kod", values="kapanis").sort_index()
    if kapanis.empty:
        return kapanis
    son = kapanis.index.max()
    kapanis = kapanis[kapanis.index > son - pd.Timedelta(days=gun)]
    getiri = kapanis.pct_change(fill_method=None)
    return getiri.mask(getiri.abs() > 0.5).iloc[1:]


def korelasyon_matrisi(getiri: pd.DataFrame) -> pd.DataFrame:
    return getiri.corr(min_periods=EN_AZ_ORTAK_GUN)


def benzer_hisseler(fiyatlar: pd.DataFrame, kodlar: list[str]) -> pd.DataFrame:
    """Her hisse için en benzer 5 hisse: kod, benzer_kod, korelasyon, sira"""
    getiri = gunluk_getiriler(fiyatlar, kodlar)
    getiri = getiri.loc[:, getiri.notna().sum() >= EN_AZ_ORTAK_GUN]
    kor = korelasyon_matrisi(getiri)
    # Hissenin kendisiyle korelasyonu (1) sayılmaz. Yeni pandas sürümleri tabloyu
    # doğrudan değiştirmeye izin vermediği için kopyası üzerinde çalışılır.
    dizi = kor.to_numpy(copy=True)
    np.fill_diagonal(dizi, np.nan)
    kor = pd.DataFrame(dizi, index=kor.index, columns=kor.columns)

    satirlar = []
    for kod in kor.columns:
        en_iyi = kor[kod].dropna().nlargest(BENZER_SAYISI)
        for sira, (benzer, k) in enumerate(en_iyi.items(), start=1):
            satirlar.append({"kod": kod, "benzer_kod": benzer, "korelasyon": round(float(k), 4), "sira": sira})
    return pd.DataFrame(satirlar)
