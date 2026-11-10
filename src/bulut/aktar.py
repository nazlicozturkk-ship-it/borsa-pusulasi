"""
Hafta 8 - Verileri internetteki veritabanına (Neon PostgreSQL) aktarma.

Bütün işler bilgisayardaki hızlı SQLite dosyasında (data/bist.db) yapılır. Bu program
sonuçları internetteki PostgreSQL veritabanına kopyalar; Vercel'deki site oradan okur.

- Fiyatlar: ilk seferde hepsi (1,1 milyon satır) kopyalanır. Sonraki seferlerde sadece
  değişen hisselerin yeni günleri gönderilir (birkaç saniye).
- Analiz ve tahmin tabloları küçüktür, her seferinde baştan yazılır.

Hızlı kopyalama için PostgreSQL'in COPY komutu kullanılır (satır satır eklemekten ~50 kat hızlı).

Çalıştırmak için: 8_buluta_aktar.bat
"""

import io
import sys
import time

import pandas as pd
from sqlalchemy import create_engine, inspect, text

from config import BULUT_VERITABANI_URL, VERI_KLASORU
from src.log_ayari import logger_olustur
from src.veritabani import Base

SQLITE_URL = f"sqlite:///{(VERI_KLASORU / 'bist.db').as_posix()}"

# Baştan yazılan tablolar ve hızlı sorgu için indeks konulacak sütunlar
ANALIZ_TABLOLARI = {
    "getiriler": None,
    "veri_kalitesi": None,
    "sektor_endeksleri": "sektor",
    "sektor_ozeti": None,
    "benzer_hisseler": "kod",
    "model_performans": "kod",
    "tahminler": "kod",
    "tahmin_ozeti": None,
}
FIYAT_SUTUNLARI = ["kod", "tarih", "acilis", "yuksek", "dusuk", "kapanis", "hacim"]

log = None


def kopyala(baglanti, tablo: str, df: pd.DataFrame) -> None:
    """DataFrame'i PostgreSQL COPY komutuyla tabloya ekler."""
    if df.empty:
        return
    tampon = io.StringIO()
    df.to_csv(tampon, index=False, header=False, na_rep="\\N")
    tampon.seek(0)
    sutunlar = ", ".join(f'"{s}"' for s in df.columns)
    imlec = baglanti.connection.cursor()
    imlec.copy_expert(f'COPY "{tablo}" ({sutunlar}) FROM STDIN WITH (FORMAT csv, NULL \'\\N\')', tampon)


def fiyatlari_aktar(yerel, bulut) -> None:
    """Fiyat tablosunu eşitler: sadece eksik veya değişmiş kısımları gönderir."""
    log.info("Fiyatlar karşılaştırılıyor...")
    yerel_df = pd.read_sql(text("SELECT * FROM fiyatlar"), yerel)
    yerel_df["tarih"] = pd.to_datetime(yerel_df["tarih"]).dt.date
    yerel_df = yerel_df[FIYAT_SUTUNLARI]

    with bulut.connect() as b:
        bulut_ozet = pd.read_sql(
            text("SELECT kod, COUNT(*) AS adet, MAX(tarih) AS son, SUM(kapanis) AS toplam FROM fiyatlar GROUP BY kod"), b
        ).set_index("kod")
    bulut_ozet["son"] = pd.to_datetime(bulut_ozet["son"]).dt.date

    # Her hisse için: buluttaki son tarihe kadarki kısım aynı mı?
    baslangiclar = {}  # kod -> bu tarihten itibaren silinip yeniden yazılacak (None = tamamı)
    for kod, grup in yerel_df.groupby("kod", sort=False):
        if kod not in bulut_ozet.index:
            baslangiclar[kod] = None
            continue
        b = bulut_ozet.loc[kod]
        eski = grup[grup["tarih"] <= b["son"]]
        ayni = len(eski) == b["adet"] and abs(eski["kapanis"].sum() - b["toplam"]) <= 1e-6 * max(1.0, abs(b["toplam"]))
        if not ayni:
            baslangiclar[kod] = None          # geçmiş değişmiş (örn. bölünme düzeltmesi): tamamını yaz
        elif grup["tarih"].max() > b["son"]:
            baslangiclar[kod] = b["son"]      # sadece yeni günler (son gün de yenilenir)
    fazla = sorted(set(bulut_ozet.index) - set(yerel_df["kod"]))

    if not baslangiclar and not fazla:
        log.info("Fiyatlar zaten güncel.")
        return

    tam = [k for k, v in baslangiclar.items() if v is None]
    kismi = {k: v for k, v in baslangiclar.items() if v is not None}
    kismi_bas = yerel_df["kod"].map(kismi)
    secim = yerel_df["kod"].isin(tam) | (kismi_bas.notna() & (yerel_df["tarih"] >= kismi_bas.fillna(yerel_df["tarih"])))
    gonderilecek = yerel_df[secim]
    log.info("Tamamı yazılacak hisse: %d, yeni günleri eklenecek hisse: %d, gönderilecek satır: %s",
             len(tam), len(kismi), f"{len(gonderilecek):,}".replace(",", "."))

    with bulut.begin() as b:
        if tam or fazla:
            b.execute(text("DELETE FROM fiyatlar WHERE kod = ANY(:kodlar)"), {"kodlar": tam + fazla})
        if kismi:
            b.execute(
                text("DELETE FROM fiyatlar f USING unnest(CAST(:kodlar AS text[]), CAST(:tarihler AS date[])) AS t(kod, tarih) "
                     "WHERE f.kod = t.kod AND f.tarih >= t.tarih"),
                {"kodlar": list(kismi), "tarihler": list(kismi.values())},
            )
        # Büyük gönderimi parça parça yap ki ilerleme görünsün
        parca = 200_000
        for i in range(0, len(gonderilecek), parca):
            kopyala(b, "fiyatlar", gonderilecek.iloc[i:i + parca])
            log.info("  %s / %s satır gönderildi",
                     f"{min(i + parca, len(gonderilecek)):,}".replace(",", "."),
                     f"{len(gonderilecek):,}".replace(",", "."))


def kucuk_tablo_aktar(yerel, bulut, ad: str, indeks: str | None = None, orm: bool = False) -> None:
    """Bir tabloyu buluttaki karşılığına baştan yazar."""
    if not inspect(yerel).has_table(ad):
        log.warning("%s tablosu bilgisayarda yok, atlandı.", ad)
        return
    df = pd.read_sql(text(f'SELECT * FROM "{ad}"'), yerel)
    with bulut.begin() as b:
        if orm:
            # Yapısı programda tanımlı tablo (sirketler, veri_durumu): içi boşaltılıp doldurulur
            b.execute(text(f'DELETE FROM "{ad}"'))
            for s in df.columns:
                if s in ("bist30", "bist100"):
                    df[s] = df[s].fillna(0).astype(bool)
        else:
            df.head(0).to_sql(ad, b, if_exists="replace", index=False)
        kopyala(b, ad, df)
        if indeks:
            b.execute(text(f'CREATE INDEX IF NOT EXISTS "ix_{ad}_{indeks}" ON "{ad}" ("{indeks}")'))
    log.info("%-18s %7s satır", ad, f"{len(df):,}".replace(",", "."))


def main() -> int:
    global log
    log = logger_olustur("buluta_aktar")

    if not BULUT_VERITABANI_URL.startswith("postgresql"):
        log.error("İnternetteki veritabanı adresi bulunamadı. .env dosyasına BULUT_VERITABANI_URL=... satırını ekleyin.")
        return 1

    baslangic = time.time()
    yerel = create_engine(SQLITE_URL)
    bulut = create_engine(BULUT_VERITABANI_URL, pool_pre_ping=True)
    try:
        with bulut.connect() as b:
            surum = b.execute(text("SHOW server_version")).scalar()
        log.info("İnternetteki veritabanına bağlanıldı (PostgreSQL %s).", surum)
    except Exception as hata:  # noqa: BLE001
        log.error("Bağlanılamadı: %s", str(hata).splitlines()[0])
        log.error(".env dosyasındaki adresi ve internet bağlantısını kontrol edin.")
        return 1

    Base.metadata.create_all(bulut)  # sirketler, fiyatlar, veri_durumu (ilk seferde)

    fiyatlari_aktar(yerel, bulut)
    log.info("Diğer tablolar yazılıyor...")
    kucuk_tablo_aktar(yerel, bulut, "sirketler", orm=True)
    kucuk_tablo_aktar(yerel, bulut, "veri_durumu", orm=True)
    for ad, indeks in ANALIZ_TABLOLARI.items():
        kucuk_tablo_aktar(yerel, bulut, ad, indeks)

    with bulut.connect() as b:
        boyut = b.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))")).scalar()
    log.info("BİTTİ: %.0f saniye. İnternetteki veritabanının boyutu: %s", time.time() - baslangic, boyut)
    return 0


if __name__ == "__main__":
    sys.exit(main())
