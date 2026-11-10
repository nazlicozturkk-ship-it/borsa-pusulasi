"""
Hafta 3 - Dönemsel getiri ve risk hesapları.

Her hisse için hesaplananlar:

  Getiriler (son kapanışa göre):
    getiri_1a, getiri_3a, getiri_6a  : son 1, 3, 6 ay
    getiri_ytd                       : yılbaşından bu yana
    getiri_1y, getiri_5y, getiri_10y : son 1, 5, 10 yıl
    yillik_5y, yillik_10y            : 5 ve 10 yıllık getirinin yıllık ortalaması (bileşik)
    fark_1a ... fark_10y             : aynı dönemde BIST 100'e göre fark (pozitifse endeksi geçmiş)

  Risk ölçüleri (son 1 yıl):
    volatilite_1y  : günlük getirilerin yıllıklandırılmış standart sapması (oynaklık)
    volatilite_3a  : aynı hesap, son 3 ay
    max_dusus_1y   : son 1 yıldaki en yüksek noktadan en büyük düşüş
    beta_1y        : hissenin BIST 100'e duyarlılığı (1'den büyükse endeksten oynak)

Formüller:
    getiri          = son_fiyat / dönem_başı_fiyat - 1
    yıllık getiri   = (1 + getiri) ^ (1 / yıl_sayısı) - 1
    volatilite      = std(günlük getiri) * √252        (yılda yaklaşık 252 işlem günü var)
    maks. düşüş     = min(fiyat / o güne kadarki en yüksek fiyat - 1)
    beta            = kovaryans(hisse, endeks) / varyans(endeks)

Hisse dönem başında henüz borsada değilse (sonradan halka arz) o dönemin getirisi
boş bırakılır; sıfır ya da yanlış bir değer yazılmaz.
"""

import numpy as np
import pandas as pd

# Dönem adı -> geriye gidilecek süre
DONEMLER = {
    "1a": pd.DateOffset(months=1),
    "3a": pd.DateOffset(months=3),
    "6a": pd.DateOffset(months=6),
    "1y": pd.DateOffset(years=1),
    "5y": pd.DateOffset(years=5),
    "10y": pd.DateOffset(years=10),
}
YILLIK_DONEMLER = {"5y": 5, "10y": 10}
ISLEM_GUNU_YIL = 252
HALKA_ARZ_TOLERANS = pd.Timedelta(days=7)  # dönem başından en fazla 1 hafta sonra başlayan veri kabul edilir
ENDEKS = "XU100"


def _donem_basi_fiyat(seri: pd.Series, hedef: pd.Timestamp) -> float:
    """
    Hedef tarihteki (o gün işlem yoksa ondan önceki son işlem günündeki) kapanış fiyatı.
    Hisse o tarihte henüz işlem görmüyorsa NaN döner.
    """
    if seri.index[0] > hedef:
        # Veri hedef tarihten çok kısa süre sonra başlıyorsa (tatil vb.) ilk fiyatı kullan
        return float(seri.iloc[0]) if seri.index[0] - hedef <= HALKA_ARZ_TOLERANS else np.nan
    return float(seri.asof(hedef))


def _yillik(getiri: float, yil: int) -> float:
    if pd.isna(getiri) or getiri <= -1:
        return np.nan
    return (1 + getiri) ** (1 / yil) - 1


def _risk_olculeri(seri: pd.Series, endeks_getiri: pd.Series, ref: pd.Timestamp) -> dict:
    """Son 1 yıl ve son 3 ay için volatilite, maksimum düşüş ve beta."""
    bir_yil = seri[seri.index > ref - pd.DateOffset(years=1)]
    uc_ay = seri[seri.index > ref - pd.DateOffset(months=3)]
    g1 = bir_yil.pct_change().dropna()
    g3 = uc_ay.pct_change().dropna()

    sonuc = {
        "volatilite_1y": g1.std() * np.sqrt(ISLEM_GUNU_YIL) if len(g1) >= 150 else np.nan,
        "volatilite_3a": g3.std() * np.sqrt(ISLEM_GUNU_YIL) if len(g3) >= 40 else np.nan,
        "max_dusus_1y": (bir_yil / bir_yil.cummax() - 1).min() if len(bir_yil) >= 150 else np.nan,
        "beta_1y": np.nan,
    }
    # Beta: sadece hissenin ve endeksin birlikte işlem gördüğü günler
    ortak = pd.concat([g1, endeks_getiri], axis=1, join="inner").dropna()
    if len(ortak) >= 150 and ortak.iloc[:, 1].var() > 0:
        sonuc["beta_1y"] = ortak.cov().iloc[0, 1] / ortak.iloc[:, 1].var()
    return sonuc


def getirileri_hesapla(fiyatlar: pd.DataFrame, aktif_kodlar: set[str] | None = None) -> pd.DataFrame:
    """
    Tüm kodlar için getiri ve risk tablosunu döndürür.

    fiyatlar     : tum_fiyatlari_oku() çıktısı
    aktif_kodlar : sadece bu kodlar hesaplanır (işlem görmeyenleri dışarıda bırakmak için).
                   None ise hepsi hesaplanır.
    """
    kapanis = fiyatlar.pivot(index="tarih", columns="kod", values="kapanis").sort_index()
    if ENDEKS not in kapanis.columns:
        raise ValueError(f"{ENDEKS} endeks verisi bulunamadı; önce fiyat verisini indirin.")

    # Referans tarih: borsanın son işlem günü (endeksin son günü)
    endeks_seri = kapanis[ENDEKS].dropna()
    ref = endeks_seri.index[-1]
    endeks_gunluk = endeks_seri[endeks_seri.index > ref - pd.DateOffset(years=1)].pct_change().dropna()
    yil_basi = pd.Timestamp(year=ref.year, month=1, day=1) - pd.Timedelta(days=1)

    satirlar = []
    for kod in kapanis.columns:
        if aktif_kodlar is not None and kod not in aktif_kodlar:
            continue
        seri = kapanis[kod].dropna()
        if len(seri) < 2:
            continue
        son_fiyat = float(seri.iloc[-1])

        satir = {
            "kod": kod,
            "hesap_tarihi": ref.date(),
            "son_tarih": seri.index[-1].date(),
            "son_kapanis": son_fiyat,
            "ilk_tarih": seri.index[0].date(),
        }
        for ad, sure in DONEMLER.items():
            bas = _donem_basi_fiyat(seri, ref - sure)
            satir[f"getiri_{ad}"] = son_fiyat / bas - 1 if bas and not pd.isna(bas) else np.nan
        bas = _donem_basi_fiyat(seri, yil_basi)
        satir["getiri_ytd"] = son_fiyat / bas - 1 if bas and not pd.isna(bas) else np.nan
        for ad, yil in YILLIK_DONEMLER.items():
            satir[f"yillik_{ad}"] = _yillik(satir[f"getiri_{ad}"], yil)

        satir.update(_risk_olculeri(seri, endeks_gunluk, ref))
        satirlar.append(satir)

    df = pd.DataFrame(satirlar)

    # BIST 100'e göre fark (hissenin getirisi - endeksin getirisi)
    endeks_satir = df.loc[df["kod"] == ENDEKS].iloc[0]
    for ad in list(DONEMLER) + ["ytd"]:
        df[f"fark_{ad}"] = df[f"getiri_{ad}"] - endeks_satir[f"getiri_{ad}"]

    sayisal = df.select_dtypes("number").columns.drop("son_kapanis")
    df[sayisal] = df[sayisal].round(6)
    return df
