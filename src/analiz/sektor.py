"""
Hafta 5 - Sektör endeksleri.

Her sektör için "eşit ağırlıklı" bir endeks hesaplanır: her gün, sektördeki hisselerin
o günkü getirilerinin ortalaması alınır ve bu günlük ortalamalar birbirine eklenerek
(bileşik) 100'den başlayan bir seri oluşturulur.

Neden eşit ağırlık?
  BIST 100 piyasa değeriyle ağırlıklıdır: büyük şirketler endeksi taşır. Eşit ağırlıklı
  endeks ise "sektördeki tipik bir hisseye yatırım yapsaydım ne olurdu?" sorusunu cevaplar.
  Ayrıca tüm hisseler için de bir eşit ağırlıklı endeks hesaplanır ("Tüm hisseler").
  BIST 100 ile bu seri arasındaki fark, büyük ve küçük şirketlerin ayrışmasını gösterir.

Veri hatalarına karşı önlem:
  Günlük %50'den büyük değişimler (veri hatası veya uzun işlem yasağı sonrası açılış)
  ortalamaya katılmaz. O gün en az 3 hisse işlem görmüyorsa sektör endeksi hesaplanmaz.
"""

import numpy as np
import pandas as pd

TUM_HISSELER = "Tüm hisseler"
EN_AZ_HISSE = 3
ASIRI_GUNLUK = 0.5


def sektor_endeksleri(fiyatlar: pd.DataFrame, sirket_sektor: dict[str, str]) -> pd.DataFrame:
    """
    fiyatlar      : tum_fiyatlari_oku() çıktısı
    sirket_sektor : {hisse kodu: sektör adı} (sadece analize dahil edilecek hisseler)
    Dönen tablo   : sektor, tarih, deger, hisse_sayisi
    """
    kodlar = list(sirket_sektor)
    kapanis = (
        fiyatlar[fiyatlar["kod"].isin(kodlar)]
        .pivot(index="tarih", columns="kod", values="kapanis")
        .sort_index()
    )
    gunluk = kapanis.pct_change(fill_method=None)
    gunluk = gunluk.mask(gunluk.abs() > ASIRI_GUNLUK)

    gruplar = pd.Series(sirket_sektor).reindex(gunluk.columns)
    sonuc = []
    hedefler = [(TUM_HISSELER, list(gunluk.columns))] + [
        (s, list(g.index)) for s, g in gruplar.groupby(gruplar) if len(g) >= EN_AZ_HISSE
    ]
    for ad, uyeler in hedefler:
        g = gunluk[uyeler]
        sayi = g.notna().sum(axis=1)
        ort = g.mean(axis=1).where(sayi >= EN_AZ_HISSE)
        ilk = ort.first_valid_index()
        if ilk is None:
            continue
        ort = ort.loc[ilk:].fillna(0.0)  # hiç işlem olmayan gün: endeks değişmez
        # İlk geçerli günün değişimi dahil edilmez; seri o günden önceki kapanışta 100 kabul edilir
        deger = 100 * (1 + ort.iloc[1:]).cumprod()
        deger = pd.concat([pd.Series([100.0], index=[ort.index[0]]), deger])
        sonuc.append(pd.DataFrame({
            "sektor": ad,
            "tarih": deger.index.date,
            "deger": deger.round(4).values,
            "hisse_sayisi": sayi.reindex(deger.index).astype(int).values,
        }))
    return pd.concat(sonuc, ignore_index=True) if sonuc else pd.DataFrame()


def sektor_ozeti(getiriler: pd.DataFrame) -> pd.DataFrame:
    """Her sektörün dönem bazında medyan getirisi, medyan volatilitesi ve hisse sayısı."""
    h = getiriler[(getiriler["sektor"].notna()) & (getiriler["sektor"] != "Endeks")]
    donemler = ["1a", "3a", "6a", "ytd", "1y", "5y", "10y"]
    tablo = h.groupby("sektor").agg(
        hisse_sayisi=("kod", "count"),
        **{f"getiri_{d}": (f"getiri_{d}", "median") for d in donemler},
        volatilite_1y=("volatilite_1y", "median"),
        beta_1y=("beta_1y", "median"),
    )
    # 5 ve 10 yıl için yeterli geçmişi olan hisse sayısı az olabilir; bunu da kaydet
    tablo["hisse_sayisi_5y"] = h.groupby("sektor")["getiri_5y"].count()
    return tablo.reset_index().round(6)
