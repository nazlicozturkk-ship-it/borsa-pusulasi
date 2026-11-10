"""
Hafta 3 - Veri kalitesi kontrolleri.

Tahmin modelleri ancak beslendikleri veri kadar iyidir. Bu modül her hissenin fiyat
verisini dört açıdan kontrol eder ve sonucu "veri_kalitesi" tablosuna yazar.
Veriyi DEĞİŞTİRMEZ, sadece sorunlu olabilecek yerleri işaretler.

Kontroller:
  1. Eksik gün    : Borsanın açık olduğu (BIST 100 endeksinin işlem gördüğü) bir günde
                    hissenin verisi yoksa eksik sayılır. Hisse o gün işlem görmemiş de
                    olabilir (işlem durdurma, tedbir), bu yüzden az sayıda eksik gün normaldir.
  2. Aşırı hareket: Günlük %25'ten fazla değişim. BIST'te günlük fiyat sınırı çoğu hisse
                    için %10'dur; bundan çok büyük sıçramalar düzeltilmemiş bir bölünmeye,
                    uzun bir işlem durdurmasına veya veri hatasına işaret edebilir.
  3. Sıfır hacim  : Hiç işlem olmayan günler. Çok fazlaysa hisse sığ (likit değil) demektir.
  4. OHLC hatası  : En düşük fiyatın açılış/kapanıştan büyük olması gibi mantıksız satırlar.
"""

import numpy as np
import pandas as pd

ASIRI_HAREKET_ESIK = 0.25   # günlük %25
EKSIK_GUN_ESIK = 0.05       # işlem günlerinin %5'inden fazlası eksikse işaretle
SIFIR_HACIM_ESIK = 0.20     # günlerin %20'sinden fazlası hacimsizse işaretle
TAKVIM_KODU = "XU100"       # borsanın açık olduğu günleri bu endeksten öğreniyoruz


def kalite_kontrol(fiyatlar: pd.DataFrame) -> pd.DataFrame:
    """
    Tüm kodlar için kalite özetini döndürür.
    fiyatlar: tum_fiyatlari_oku() çıktısı (kod, tarih, acilis, yuksek, dusuk, kapanis, hacim)
    """
    takvim = np.sort(fiyatlar.loc[fiyatlar["kod"] == TAKVIM_KODU, "tarih"].unique())
    takvim_kumesi = set(takvim)

    sonuclar = []
    for kod, g in fiyatlar.groupby("kod", sort=True):
        g = g.sort_values("tarih")
        ilk, son = g["tarih"].iloc[0], g["tarih"].iloc[-1]

        # 1) Eksik günler: [ilk, son] aralığında borsanın açık olduğu gün sayısı - hissenin gün sayısı
        acik_gun = np.searchsorted(takvim, son, side="right") - np.searchsorted(takvim, ilk, side="left")
        bulunan = g["tarih"].isin(takvim_kumesi).sum()
        eksik = max(int(acik_gun - bulunan), 0)

        # 2) Aşırı hareketler
        degisim = g["kapanis"].pct_change()
        asiri = g.loc[degisim.abs() > ASIRI_HAREKET_ESIK, "tarih"]

        # 3) Sıfır hacim
        sifir_hacim = int((g["hacim"].fillna(0) <= 0).sum())

        # 4) OHLC tutarlılığı (küçük yuvarlama farklarına tolerans tanınır)
        tol = 1e-6
        ust = g[["acilis", "kapanis"]].max(axis=1)
        alt = g[["acilis", "kapanis"]].min(axis=1)
        ohlc_hatali = int(
            ((g["yuksek"] < ust * (1 - tol)) | (g["dusuk"] > alt * (1 + tol)) | (g["dusuk"] > g["yuksek"])).sum()
        )

        notlar = []
        if acik_gun and eksik / acik_gun > EKSIK_GUN_ESIK:
            notlar.append(f"eksik gün %{100 * eksik / acik_gun:.0f}")
        if len(asiri):
            notlar.append(f"{len(asiri)} aşırı hareket")
        if len(g) and sifir_hacim / len(g) > SIFIR_HACIM_ESIK:
            notlar.append(f"hacimsiz gün %{100 * sifir_hacim / len(g):.0f}")
        if ohlc_hatali:
            notlar.append(f"{ohlc_hatali} OHLC hatası")

        sonuclar.append({
            "kod": kod,
            "ilk_tarih": ilk.date(),
            "son_tarih": son.date(),
            "gun_sayisi": len(g),
            "eksik_gun": eksik,
            "eksik_oran": round(eksik / acik_gun, 4) if acik_gun else 0.0,
            "asiri_hareket": len(asiri),
            "asiri_hareket_tarihleri": ", ".join(d.strftime("%Y-%m-%d") for d in asiri.head(5)),
            "sifir_hacim_gun": sifir_hacim,
            "ohlc_hatali": ohlc_hatali,
            "kalite": "kontrol_et" if notlar else "iyi",
            "notlar": "; ".join(notlar),
        })

    return pd.DataFrame(sonuclar)
