"""
Hafta 2 - Tüm BIST şirketlerinin 10 yıllık günlük fiyat verilerini toplar.

Ne yapar?
  1. 1. haftada oluşturulan şirket listesini veritabanından okur.
  2. Her şirket için günlük açılış, en yüksek, en düşük, kapanış ve hacim verisini çeker.
     - Ana kaynak: borsapy (TradingView). Fiyatlar bedelsiz sermaye artırımlarına
       göre düzeltilmiş gelir; böylece grafiklerde yapay düşüşler görünmez.
     - Yedek kaynak: yfinance (Yahoo Finance), ana kaynak veri vermezse kullanılır.
  3. Karşılaştırma için BIST 30 ve BIST 100 endekslerinin verisini de çeker.
  4. Her şeyi veritabanındaki "fiyatlar" tablosuna, her kodun durumunu da
     "veri_durumu" tablosuna kaydeder.

Akıllı güncelleme:
  - Bir kodun verisi daha önce çekildiyse sadece son günler indirilir. Bu sayede
    program her gün çalıştırıldığında saniyeler içinde güncellenir.
  - Program yarıda kesilirse tekrar çalıştırıldığında kaldığı yerden devam eder.
  - Daha önce hiç veri bulunamayan kodlar tekrar denenmez (--yeniden ile denenir).

Kullanım:
  python -m src.veri.fiyat_verisi                 # tüm şirketler
  python -m src.veri.fiyat_verisi --sadece bist30 # sadece BIST 30 (hızlı deneme)
  python -m src.veri.fiyat_verisi --yeniden       # her şeyi 10 yıllık baştan indir

Çalıştırmak için: 2_fiyat_verisi.bat dosyasına çift tıklayın.
"""

import argparse
import logging
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

import pandas as pd

from config import ENDEKSLER
from src.log_ayari import logger_olustur
from src.veritabani import (
    durum_kaydet,
    durumlari_oku,
    fiyatlari_kaydet,
    sirketleri_oku,
    tablolari_olustur,
)

log = logger_olustur("fiyat_verisi")
warnings.filterwarnings("ignore")  # kütüphanelerin zararsız uyarılarını gizle
# yfinance, bulunamayan her kod için "possibly delisted" yazar; bunlar hata değil
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

YIL_SAYISI = 10             # kaç yıllık veri çekilecek
ESZAMANLI_ISTEK = 4         # aynı anda kaç hisse indirilecek
ISLEM_GORMUYOR_GUN = 30     # son işlem bu kadar günden eskiyse "işlem görmüyor" say
GUNCELLEME_PAYI_GUN = 7     # güncellemede son kaç günü yeniden indir (düzeltmeler için)


# ---------------------------------------------------------------------------
# Veri kaynakları
# ---------------------------------------------------------------------------

def _tabloyu_duzenle(df: pd.DataFrame) -> pd.DataFrame:
    """Kaynaktan gelen tabloyu veritabanı biçimine çevirir (Türkçe sütunlar, tarih)."""
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename(columns={
        "Open": "acilis", "High": "yuksek", "Low": "dusuk", "Close": "kapanis", "Volume": "hacim",
    })
    gerekli = ["acilis", "yuksek", "dusuk", "kapanis"]
    if not all(s in df.columns for s in gerekli):
        return pd.DataFrame()
    if "hacim" not in df.columns:
        df["hacim"] = None

    df = df[gerekli + ["hacim"]].copy()
    # Saat ve saat dilimini at, sadece gün kalsın
    tarihler = pd.DatetimeIndex(df.index)
    if tarihler.tz is not None:
        tarihler = tarihler.tz_convert("Europe/Istanbul").tz_localize(None)
    df["tarih"] = tarihler.normalize().date

    df = df.dropna(subset=["kapanis"])
    df = df[df["kapanis"] > 0]
    df = df.drop_duplicates(subset="tarih", keep="last").sort_values("tarih")
    return df.reset_index(drop=True)


def borsapy_ile_cek(kod: str, baslangic: date, endeks: bool = False) -> pd.DataFrame:
    """TradingView verisini borsapy üzerinden çeker."""
    import borsapy as bp

    nesne = bp.Index(kod) if endeks else bp.Ticker(kod)
    return _tabloyu_duzenle(nesne.history(start=baslangic.isoformat(), interval="1d"))


def yfinance_ile_cek(kod: str, baslangic: date, endeks: bool = False) -> pd.DataFrame:
    """Yahoo Finance verisini yfinance üzerinden çeker (yedek kaynak)."""
    import yfinance as yf

    sembol = f"{kod}.IS"
    df = yf.Ticker(sembol).history(start=baslangic.isoformat(), interval="1d", auto_adjust=False)
    return _tabloyu_duzenle(df)


def veri_cek(kod: str, baslangic: date, endeks: bool = False) -> tuple[pd.DataFrame, str | None, str | None]:
    """
    Önce ana kaynağı, olmazsa yedek kaynağı dener.
    Dönen değer: (veri tablosu, kaynak adı, hata mesajı)
    """
    hatalar = []
    for kaynak_adi, fonksiyon in (("tradingview", borsapy_ile_cek), ("yahoo", yfinance_ile_cek)):
        for deneme in range(2):  # geçici bağlantı hatalarına karşı bir kez daha dene
            try:
                df = fonksiyon(kod, baslangic, endeks)
                if not df.empty:
                    return df, kaynak_adi, None
                break  # boş geldiyse tekrar denemenin anlamı yok
            except Exception as hata:
                son_hata = f"{kaynak_adi}: {str(hata)[:80]}"
                if deneme == 1:
                    hatalar.append(son_hata)
                time.sleep(1)
    return pd.DataFrame(), None, "; ".join(hatalar) or "hiçbir kaynakta veri yok"


# ---------------------------------------------------------------------------
# Ana iş akışı
# ---------------------------------------------------------------------------

def islenecek_kodlar(sadece: str | None, yeniden: bool) -> list[tuple[str, date, bool, bool]]:
    """
    Hangi kodların hangi tarihten itibaren indirileceğini belirler.
    Dönen liste: [(kod, başlangıç tarihi, endeks mi?, önceden verisi var mı?), ...]
    """
    sirketler = sirketleri_oku()
    if sirketler.empty:
        raise SystemExit("Şirket listesi boş. Önce 1_sirket_listesi.bat dosyasını çalıştırın.")

    if sadece == "bist30":
        sirketler = sirketler[sirketler["bist30"]]
    elif sadece == "bist100":
        sirketler = sirketler[sirketler["bist100"]]

    on_yil_once = date.today() - timedelta(days=365 * YIL_SAYISI + 3)
    durumlar = {} if yeniden else {r.kod: r for r in durumlari_oku().itertuples()}

    liste = []
    hepsi = [(k, True) for k in ENDEKSLER] + [(k, False) for k in sirketler["kod"]]
    for kod, endeks in hepsi:
        d = durumlar.get(kod)
        if d is None or d.son_tarih is None or pd.isna(d.son_tarih):
            if d is not None and d.durum == "veri_yok":
                continue  # daha önce hiç bulunamadı, boşuna tekrar deneme
            liste.append((kod, on_yil_once, endeks, False))
        else:
            son = pd.Timestamp(d.son_tarih).date()
            liste.append((kod, max(on_yil_once, son - timedelta(days=GUNCELLEME_PAYI_GUN)), endeks, True))
    return liste


def tek_kod_isle(kod: str, baslangic: date, endeks: bool):
    """Bir kodun verisini çeker (paralel çalışan iş parçacıklarında çağrılır)."""
    df, kaynak, hata = veri_cek(kod, baslangic, endeks)
    return kod, df, kaynak, hata


def main() -> None:
    parser = argparse.ArgumentParser(description="BIST fiyat verilerini indirir")
    parser.add_argument("--sadece", choices=["bist30", "bist100"], help="sadece bir endeksin hisseleri")
    parser.add_argument("--yeniden", action="store_true", help="tüm veriyi baştan indir")
    args = parser.parse_args()

    tablolari_olustur()
    liste = islenecek_kodlar(args.sadece, args.yeniden)
    log.info("Fiyat verisi indirme başladı: %d kod işlenecek (aynı anda %d).", len(liste), ESZAMANLI_ISTEK)
    log.info("İlk çalıştırma 15-30 dakika sürebilir; sonraki güncellemeler çok daha hızlıdır.")

    sayac = {"tamam": 0, "islem_gormuyor": 0, "veri_yok": 0, "guncellenemedi": 0}
    toplam_satir = 0
    sinir = date.today() - timedelta(days=ISLEM_GORMUYOR_GUN)
    baslama = time.time()

    with ThreadPoolExecutor(max_workers=ESZAMANLI_ISTEK) as havuz:
        isler = {havuz.submit(tek_kod_isle, kod, bas, endeks): var for kod, bas, endeks, var in liste}
        # Veritabanına yazma işi sadece ana iş parçacığında yapılır (SQLite için güvenli)
        for i, is_ in enumerate(as_completed(isler), start=1):
            kod, df, kaynak, hata = is_.result()
            if df.empty and isler[is_]:
                # Eski verisi var ama bu sefer indirilemedi (bağlantı sorunu olabilir).
                # Eski veri korunur, bir sonraki çalıştırmada tekrar denenir.
                durum, satir = "guncellenemedi", 0
                log.warning("        %s güncellenemedi: %s", kod, hata)
            elif df.empty:
                durum, satir = "veri_yok", 0
                durum_kaydet(kod, durum, None, hata)
            else:
                satir = fiyatlari_kaydet(kod, df)
                durum = "tamam" if df["tarih"].max() >= sinir else "islem_gormuyor"
                durum_kaydet(kod, durum, kaynak)
            sayac[durum] += 1
            toplam_satir += satir

            gecen = time.time() - baslama
            kalan = gecen / i * (len(liste) - i)
            log.info(
                "[%3d/%d] %-7s %-15s %5d gün  (kalan ~%d dk)",
                i, len(liste), kod, durum, satir, round(kalan / 60),
            )

    ozet_yazdir(sayac, toplam_satir, time.time() - baslama)


def ozet_yazdir(sayac: dict, toplam_satir: int, sure: float) -> None:
    durumlar = durumlari_oku()
    durumlar = durumlar[~durumlar["kod"].isin(ENDEKSLER)]  # özet sadece hisseler için
    log.info("-" * 60)
    log.info("ÖZET")
    log.info("  Verisi güncel olan        : %d", sayac["tamam"])
    log.info("  İşlem görmeyen (eski veri): %d", sayac["islem_gormuyor"])
    log.info("  Verisi bulunamayan        : %d", sayac["veri_yok"])
    if sayac["guncellenemedi"]:
        log.info("  Güncellenemeyen (tekrar dene): %d", sayac["guncellenemedi"])
    log.info("  Bu çalıştırmada yazılan   : %d satır", toplam_satir)
    if not durumlar.empty:
        tamam = durumlar[durumlar["durum"] == "tamam"]
        log.info("  Veritabanındaki toplam    : %d satır", int(durumlar["gun_sayisi"].sum()))
        if not tamam.empty:
            on_yillik = (pd.to_datetime(tamam["ilk_tarih"]) <= pd.Timestamp.today() - pd.DateOffset(years=9, months=11)).sum()
            log.info("  10 yıllık verisi olan     : %d hisse", on_yillik)
            log.info("  10 yıldan kısa geçmişli   : %d hisse (sonradan halka arz)", len(tamam) - on_yillik)
    log.info("  Süre                      : %.1f dakika", sure / 60)
    log.info("-" * 60)
    log.info("Tamamlandı. Tekrar çalıştırırsanız sadece yeni günler indirilir.")


if __name__ == "__main__":
    main()
