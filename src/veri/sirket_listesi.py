"""
Hafta 1 - Tüm BIST şirketlerinin listesini oluşturur.

Ne yapar?
  1. KAP'tan (Kamuyu Aydınlatma Platformu) Borsa İstanbul'daki tüm şirketleri çeker.
  2. Her şirketin sektörünü önce TradingView'dan, bulunamazsa KAP'tan bulur.
  3. Hangi şirketlerin BIST 30 ve BIST 100 endekslerinde olduğunu işaretler.
  4. Sonucu veritabanına (data/bist.db) ve Excel'de açılabilen bir CSV dosyasına
     (data/sirketler.csv) kaydeder.

Veriler borsapy kütüphanesi ile çekilir. borsapy KAP, İş Yatırım ve TradingView
gibi kaynaklardan veri alan, eğitim amaçlı ücretsiz bir Python kütüphanesidir.

Çalıştırmak için: 1_sirket_listesi.bat dosyasına çift tıklayın.
"""

import time
import warnings

import borsapy as bp
import pandas as pd

from config import ENDEKSLER, VERI_KLASORU
from src.log_ayari import logger_olustur
from src.veritabani import sirketleri_kaydet

log = logger_olustur("sirket_listesi")

# KAP'ın Excel dosyası okunurken çıkan zararsız bir uyarıyı gizle
warnings.filterwarnings("ignore", message="Workbook contains no default style")


def kap_sirket_listesi() -> pd.DataFrame:
    """KAP'taki tüm BIST şirketlerini kod, unvan ve şehir bilgisiyle döndürür."""
    df = bp.companies()
    df = df.rename(columns={"ticker": "kod", "name": "unvan", "city": "sehir"})
    df["kod"] = df["kod"].astype(str).str.strip().str.upper()
    # Aynı kod birden fazla kez geçiyorsa ilkini tut
    df = df.drop_duplicates(subset="kod").reset_index(drop=True)
    return df[["kod", "unvan", "sehir"]]


# TradingView sektör adlarını İngilizce verir; uygulamada Türkçe göstermek için çeviriyoruz.
SEKTOR_TURKCE = {
    "Commercial Services": "Ticari Hizmetler",
    "Communications": "İletişim",
    "Consumer Durables": "Dayanıklı Tüketim Malları",
    "Consumer Non-Durables": "Dayanıksız Tüketim Malları",
    "Consumer Services": "Tüketici Hizmetleri",
    "Distribution Services": "Dağıtım Hizmetleri",
    "Electronic Technology": "Elektronik Teknoloji",
    "Energy Minerals": "Enerji Madenleri",
    "Finance": "Finans",
    "Government": "Kamu",
    "Health Services": "Sağlık Hizmetleri",
    "Health Technology": "Sağlık Teknolojisi",
    "Industrial Services": "Endüstriyel Hizmetler",
    "Miscellaneous": "Diğer",
    "Non-Energy Minerals": "Enerji Dışı Madenler",
    "Process Industries": "Süreç Endüstrileri",
    "Producer Manufacturing": "Üretici İmalat",
    "Retail Trade": "Perakende Ticaret",
    "Technology Services": "Teknoloji Hizmetleri",
    "Transportation": "Ulaştırma",
    "Utilities": "Kamu Hizmetleri (Enerji, Su)",
}


def sektor_tradingview() -> dict[str, str]:
    """
    Borsa İstanbul'daki tüm hisselerin sektörünü TradingView'dan tek sorguda çeker.
    Dönen değer: {"THYAO": "Ulaştırma", ...}

    tradingview_screener kütüphanesi borsapy ile birlikte kurulur.
    """
    from tradingview_screener import Query

    _, df = (
        Query()
        .set_markets("turkey")
        .select("name", "sector")
        .limit(5000)
        .get_scanner_data()
    )
    if df.empty or "sector" not in df.columns:
        return {}

    # "ticker" sütunu "BIST:THYAO" biçimindedir; ":" sonrasını alıyoruz
    kodlar = df["ticker"].astype(str).str.split(":").str[-1].str.strip().str.upper()
    eslesme: dict[str, str] = {}
    for kod, sektor in zip(kodlar, df["sector"]):
        if isinstance(sektor, str) and sektor.strip():  # boş veya eksik (NaN) değerleri atla
            eslesme[kod] = SEKTOR_TURKCE.get(sektor.strip(), sektor.strip())
    return eslesme


def turkce_baslik(metin: str) -> str:
    """
    "ULAŞTIRMA VE DEPOLAMA" -> "Ulaştırma ve Depolama"
    Python'un kendi title() fonksiyonu Türkçe I/İ harflerini yanlış çevirdiği için yazıldı.
    """
    kucuk_kelimeler = {"ve", "ile", "veya"}
    kelimeler = []
    for i, kelime in enumerate(metin.strip().split()):
        kucuk = kelime.replace("I", "ı").replace("İ", "i").lower()
        if i > 0 and kucuk in kucuk_kelimeler:
            kelimeler.append(kucuk)
        else:
            ilk = kucuk[0].replace("i", "İ").replace("ı", "I").upper()
            kelimeler.append(ilk + kucuk[1:])
    return " ".join(kelimeler)


def sektor_kap(kodlar: list[str], bekleme: float = 0.3) -> dict[str, str]:
    """
    TradingView'da bulunamayan şirketlerin sektörünü KAP'taki şirket sayfasından okur.
    Her şirket için ayrı istek gerektiği için daha yavaştır; sunucuyu yormamak
    için istekler arasında kısa süre beklenir.
    """
    from borsapy._providers.kap import get_kap_provider

    kap = get_kap_provider()
    eslesme: dict[str, str] = {}
    for i, kod in enumerate(kodlar, start=1):
        try:
            sektor = kap.get_company_details(kod).get("sector")
            if sektor:
                eslesme[kod] = turkce_baslik(sektor)
        except Exception:
            pass  # bulunamazsa boş kalır
        if i % 50 == 0 or i == len(kodlar):
            log.info("    KAP: %d/%d şirket kontrol edildi, %d sektör bulundu", i, len(kodlar), len(eslesme))
        time.sleep(bekleme)
    return eslesme


# Otomatik kaynaklarda bulunamayan önemli hisseler için elle girilen sektörler
MANUEL_SEKTOR = {
    "ISCTR": "Finans",  # Türkiye İş Bankası (C)
}


def sektor_eslesmesi(kodlar: list[str]) -> dict[str, str]:
    """Önce TradingView, sonra KAP kullanarak mümkün olan tüm şirketlerin sektörünü bulur."""
    eslesme: dict[str, str] = {}
    try:
        eslesme = sektor_tradingview()
        bulunan = sum(1 for k in kodlar if k in eslesme)
        log.info("    TradingView: %d şirketin sektörü bulundu.", bulunan)
    except Exception as hata:
        log.warning("    TradingView'dan sektör alınamadı: %s", hata)

    eksikler = [k for k in kodlar if k not in eslesme]
    if eksikler:
        log.info("    Kalan %d şirket için KAP'a bakılıyor (1-3 dakika sürebilir)...", len(eksikler))
        eslesme.update(sektor_kap(eksikler))
    for kod, sektor in MANUEL_SEKTOR.items():
        eslesme.setdefault(kod, sektor)
    return eslesme


def endeks_uyeleri(endeks_kodu: str) -> set[str]:
    """Verilen endeksteki (örn. XU030) hisselerin kodlarını döndürür."""
    try:
        return {k.upper() for k in bp.Index(endeks_kodu).component_symbols}
    except Exception as hata:
        log.warning("%s endeks üyeleri alınamadı: %s", endeks_kodu, hata)
        return set()


def sirket_listesini_olustur() -> pd.DataFrame:
    """Tüm adımları birleştirip son şirket tablosunu döndürür."""
    log.info("1/3 KAP'tan şirket listesi çekiliyor...")
    df = kap_sirket_listesi()
    log.info("    %d şirket kodu bulundu.", len(df))

    log.info("2/3 Sektör bilgileri çekiliyor...")
    sektorler = sektor_eslesmesi(df["kod"].tolist())
    df["sektor"] = df["kod"].map(sektorler)

    log.info("3/3 Endeks üyelikleri çekiliyor...")
    bist30 = endeks_uyeleri("XU030")
    bist100 = endeks_uyeleri("XU100")
    df["bist30"] = df["kod"].isin(bist30)
    df["bist100"] = df["kod"].isin(bist100)
    log.info("    %s: %d hisse, %s: %d hisse", ENDEKSLER["XU030"], len(bist30), ENDEKSLER["XU100"], len(bist100))

    return df.sort_values("kod").reset_index(drop=True)


def ozet_yazdir(df: pd.DataFrame) -> None:
    """Sonuç hakkında kısa bir özet yazar."""
    sektorsuz = df["sektor"].isna().sum()
    log.info("-" * 60)
    log.info("ÖZET")
    log.info("  Toplam şirket          : %d", len(df))
    log.info("  Sektörü bulunan        : %d", len(df) - sektorsuz)
    log.info("  Sektörü bulunamayan    : %d", sektorsuz)
    log.info("  BIST 30 üyesi          : %d", df["bist30"].sum())
    log.info("  BIST 100 üyesi         : %d", df["bist100"].sum())
    log.info("  En kalabalık 5 sektör  :")
    for sektor, adet in df["sektor"].value_counts().head(5).items():
        log.info("      %-40s %d", sektor, adet)
    log.info("-" * 60)


def main() -> None:
    log.info("BIST şirket listesi güncellemesi başladı.")
    try:
        df = sirket_listesini_olustur()
    except Exception:
        log.exception("Şirket listesi oluşturulamadı. İnternet bağlantını kontrol et.")
        raise SystemExit(1)

    adet = sirketleri_kaydet(df)
    log.info("Veritabanına %d şirket kaydedildi: data/bist.db", adet)

    csv_yolu = VERI_KLASORU / "sirketler.csv"
    # utf-8-sig: Excel'in Türkçe karakterleri doğru göstermesi için
    df.to_csv(csv_yolu, index=False, encoding="utf-8-sig", sep=";")
    log.info("CSV dosyası kaydedildi: data/sirketler.csv")

    ozet_yazdir(df)
    log.info("Tamamlandı.")


if __name__ == "__main__":
    main()
