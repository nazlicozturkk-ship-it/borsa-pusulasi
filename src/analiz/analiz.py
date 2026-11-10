"""
Hafta 3 - Analizleri çalıştırır.

Sırasıyla:
  1. Veri kalitesi kontrolü   -> "veri_kalitesi" tablosu + data/veri_kalitesi.csv
  2. Getiri ve risk hesapları -> "getiriler" tablosu     + data/getiriler.csv
  3. Sektör endeksleri        -> "sektor_endeksleri" ve "sektor_ozeti" tabloları (Hafta 5)
  4. Benzer hisseler          -> "benzer_hisseler" tablosu (Hafta 5)
  5. Ekrana ve logs/analiz.log dosyasına özet (en çok kazandıran/kaybettirenler, sektörler)

CSV dosyalarında oranlar yüzde olarak yazılır (0,25 yerine 25,00) ve Excel'de doğru açılır.

Çalıştırmak için: 3_analiz.bat dosyasına çift tıklayın.
"""

import pandas as pd

from config import ENDEKSLER, VERI_KLASORU
from src.analiz.getiri import getirileri_hesapla
from src.analiz.korelasyon import benzer_hisseler
from src.analiz.sektor import TUM_HISSELER, sektor_endeksleri, sektor_ozeti
from src.analiz.veri_kalitesi import kalite_kontrol
from src.log_ayari import logger_olustur
from src.veritabani import durumlari_oku, sirketleri_oku, tablo_yaz, tum_fiyatlari_oku

log = logger_olustur("analiz")

ORAN_SUTUNLARI_ONEKI = ("getiri_", "yillik_", "fark_", "volatilite_", "max_dusus_")


def yuzde(x: float) -> str:
    return "   -   " if pd.isna(x) else f"{x * 100:+7.1f}%"


def csv_kaydet(df: pd.DataFrame, dosya_adi: str) -> None:
    """Oranları yüzdeye çevirip Excel uyumlu CSV olarak kaydeder."""
    df = df.copy()
    for s in df.columns:
        if s.startswith(ORAN_SUTUNLARI_ONEKI):
            df[s] = (df[s] * 100).round(2)
    df.to_csv(VERI_KLASORU / dosya_adi, index=False, sep=";", decimal=",", encoding="utf-8-sig")


def main() -> None:
    log.info("Analiz başladı.")
    fiyatlar = tum_fiyatlari_oku()
    if fiyatlar.empty:
        log.error("Veritabanında fiyat verisi yok. Önce 2_fiyat_verisi.bat dosyasını çalıştırın.")
        raise SystemExit(1)
    sirketler = sirketleri_oku()
    durumlar = durumlari_oku()
    log.info("%d kodun %d günlük fiyat kaydı okundu.", fiyatlar["kod"].nunique(), len(fiyatlar))

    # 1) Veri kalitesi
    log.info("1/4 Veri kalitesi kontrol ediliyor...")
    kalite = kalite_kontrol(fiyatlar)
    tablo_yaz("veri_kalitesi", kalite)
    csv_kaydet(kalite, "veri_kalitesi.csv")
    sorunlu = kalite[kalite["kalite"] == "kontrol_et"]
    log.info("    %d kodun %d tanesi sorunsuz, %d tanesi kontrol edilmeli.", len(kalite), len(kalite) - len(sorunlu), len(sorunlu))
    for r in sorunlu.head(10).itertuples():
        log.info("      %-7s %s", r.kod, r.notlar)
    if len(sorunlu) > 10:
        log.info("      ... (tam liste: data/veri_kalitesi.csv)")

    # 2) Getiriler (sadece işlem gören hisseler + endeksler)
    log.info("2/4 Getiri ve risk ölçüleri hesaplanıyor...")
    aktif = set(durumlar.loc[durumlar["durum"] == "tamam", "kod"]) | set(ENDEKSLER)
    getiriler = getirileri_hesapla(fiyatlar, aktif)
    getiriler = getiriler.merge(
        sirketler[["kod", "unvan", "sektor", "bist30", "bist100"]], on="kod", how="left"
    ).merge(kalite[["kod", "kalite"]], on="kod", how="left")
    for kod, ad in ENDEKSLER.items():
        getiriler.loc[getiriler["kod"] == kod, ["unvan", "sektor"]] = [ad, "Endeks"]
    tablo_yaz("getiriler", getiriler)
    csv_kaydet(getiriler, "getiriler.csv")
    log.info("    %d kod için hesaplandı. Hesap tarihi: %s", len(getiriler), getiriler["hesap_tarihi"].iloc[0])

    # 3) Sektör endeksleri
    log.info("3/4 Sektör endeksleri hesaplanıyor...")
    hisseler = getiriler[(getiriler["sektor"] != "Endeks") & getiriler["sektor"].notna()]
    endeksler = sektor_endeksleri(fiyatlar, dict(zip(hisseler["kod"], hisseler["sektor"])))
    tablo_yaz("sektor_endeksleri", endeksler)
    tablo_yaz("sektor_ozeti", sektor_ozeti(getiriler))
    log.info("    %d sektör endeksi (+ %s) hesaplandı.", endeksler["sektor"].nunique() - 1, TUM_HISSELER)

    # 4) Benzer hisseler (korelasyon)
    log.info("4/4 Benzer hareket eden hisseler bulunuyor...")
    aktif_hisseler = [k for k in getiriler["kod"] if k not in ENDEKSLER]
    benzerler = benzer_hisseler(fiyatlar, aktif_hisseler)
    tablo_yaz("benzer_hisseler", benzerler)
    log.info("    %d hisse için benzer hisseler kaydedildi.", benzerler["kod"].nunique() if not benzerler.empty else 0)

    ozet_yazdir(getiriler)
    log.info("Sonuçlar: data/getiriler.csv ve data/veri_kalitesi.csv")
    log.info("Tamamlandı.")


def ozet_yazdir(df: pd.DataFrame) -> None:
    hisseler = df[df["sektor"] != "Endeks"]
    log.info("-" * 70)
    log.info("ENDEKS GETİRİLERİ       1 ay     3 ay     6 ay     1 yıl    5 yıl   10 yıl")
    for r in df[df["sektor"] == "Endeks"].itertuples():
        log.info(
            "  %-12s %s %s %s %s %s %s", r.unvan,
            yuzde(r.getiri_1a), yuzde(r.getiri_3a), yuzde(r.getiri_6a),
            yuzde(r.getiri_1y), yuzde(r.getiri_5y), yuzde(r.getiri_10y),
        )

    for baslik, artan in (("SON 1 YILDA EN ÇOK KAZANDIRAN 10 HİSSE", False), ("SON 1 YILDA EN ÇOK KAYBETTİREN 10 HİSSE", True)):
        log.info("-" * 70)
        log.info(baslik)
        for r in hisseler.dropna(subset=["getiri_1y"]).sort_values("getiri_1y", ascending=artan).head(10).itertuples():
            log.info("  %-7s %-32.32s %s  (volatilite %s)", r.kod, r.unvan or "", yuzde(r.getiri_1y), yuzde(r.volatilite_1y))

    log.info("-" * 70)
    log.info("SEKTÖRLERE GÖRE SON 1 YIL (medyan getiri, hisse sayısı)")
    sektor = (
        hisseler.dropna(subset=["getiri_1y", "sektor"])
        .groupby("sektor")["getiri_1y"].agg(["median", "count"])
        .sort_values("median", ascending=False)
    )
    for ad, r in sektor.iterrows():
        log.info("  %-32.32s %s  (%d hisse)", ad, yuzde(r["median"]), r["count"])

    endeks_1y = df.loc[df["kod"] == "XU100", "getiri_1y"].iloc[0]
    gecen = (hisseler["getiri_1y"] > endeks_1y).sum()
    log.info("-" * 70)
    log.info("Son 1 yılda BIST 100'den fazla kazandıran hisse: %d / %d", gecen, hisseler["getiri_1y"].notna().sum())
    log.info("-" * 70)


if __name__ == "__main__":
    main()
