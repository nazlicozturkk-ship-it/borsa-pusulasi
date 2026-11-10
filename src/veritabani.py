"""
Veritabanı katmanı.

SQLAlchemy kütüphanesi ile tabloları Python sınıfları olarak tanımlıyoruz.
Bu sayede aynı kod hem SQLite hem PostgreSQL ile çalışır; veritabanını
değiştirmek için sadece config.py içindeki VERITABANI_URL değişir.
"""

from datetime import date, datetime

import pandas as pd
from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, create_engine, delete, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from config import VERITABANI_URL


class Base(DeclarativeBase):
    """Tüm tabloların türediği temel sınıf."""


class Sirket(Base):
    """BIST'te işlem gören bir şirket (tablo adı: sirketler)."""

    __tablename__ = "sirketler"

    kod: Mapped[str] = mapped_column(String(12), primary_key=True)    # örn. THYAO
    unvan: Mapped[str] = mapped_column(String(255))                    # şirketin tam adı
    sehir: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sektor: Mapped[str | None] = mapped_column(String(150), nullable=True)
    bist30: Mapped[bool] = mapped_column(Boolean, default=False)
    bist100: Mapped[bool] = mapped_column(Boolean, default=False)
    guncelleme: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    def __repr__(self) -> str:
        return f"Sirket({self.kod}, {self.unvan})"


class Fiyat(Base):
    """
    Bir hissenin (veya endeksin) bir günlük fiyat bilgisi (tablo adı: fiyatlar).
    Her satır = bir kod + bir gün. Aynı kod ve gün iki kez kaydedilemez.
    Fiyatlar bedelsiz sermaye artırımlarına (bölünmelere) göre düzeltilmiştir.
    """

    __tablename__ = "fiyatlar"

    kod: Mapped[str] = mapped_column(String(12), primary_key=True)
    tarih: Mapped[date] = mapped_column(Date, primary_key=True)
    acilis: Mapped[float] = mapped_column(Float)
    yuksek: Mapped[float] = mapped_column(Float)
    dusuk: Mapped[float] = mapped_column(Float)
    kapanis: Mapped[float] = mapped_column(Float)
    hacim: Mapped[float | None] = mapped_column(Float, nullable=True)


class VeriDurumu(Base):
    """
    Her kod için fiyat verisinin durumunu tutar (tablo adı: veri_durumu).
    durum değerleri:
      - "tamam"           : veri güncel
      - "islem_gormuyor"  : verisi var ama son 30 günde işlem görmemiş
      - "veri_yok"        : hiçbir kaynaktan veri bulunamadı (hisse senedi olmayan kodlar)
    """

    __tablename__ = "veri_durumu"

    kod: Mapped[str] = mapped_column(String(12), primary_key=True)
    durum: Mapped[str] = mapped_column(String(20))
    kaynak: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ilk_tarih: Mapped[date | None] = mapped_column(Date, nullable=True)
    son_tarih: Mapped[date | None] = mapped_column(Date, nullable=True)
    gun_sayisi: Mapped[int] = mapped_column(Integer, default=0)
    mesaj: Mapped[str | None] = mapped_column(String(255), nullable=True)
    guncelleme: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


_engine = None


def engine_al():
    """Veritabanı bağlantısını döndürür (ilk çağrıda oluşturur)."""
    global _engine
    if _engine is None:
        if VERITABANI_URL.startswith("postgresql"):
            # İnternetteki veritabanı: kopan bağlantılar otomatik yenilenir
            _engine = create_engine(VERITABANI_URL, pool_pre_ping=True, pool_size=2, max_overflow=3)
        else:
            _engine = create_engine(VERITABANI_URL)
    return _engine


def tablolari_olustur() -> None:
    """Tablolar yoksa oluşturur; varsa dokunmaz."""
    Base.metadata.create_all(engine_al())


def _bos_ise_none(deger):
    """Boş metin veya eksik değeri (NaN) veritabanının anlayacağı None'a çevirir."""
    if deger is None or pd.isna(deger) or str(deger).strip() == "":
        return None
    return str(deger).strip()


def sirketleri_kaydet(df: pd.DataFrame) -> int:
    """
    Şirket listesini veritabanına yazar.
    Şirket zaten kayıtlıysa bilgilerini günceller, yoksa yeni ekler.
    Kaydedilen şirket sayısını döndürür.
    """
    tablolari_olustur()
    simdi = datetime.now()
    with Session(engine_al()) as oturum:
        for satir in df.itertuples(index=False):
            oturum.merge(
                Sirket(
                    kod=satir.kod,
                    unvan=satir.unvan,
                    sehir=_bos_ise_none(satir.sehir),
                    sektor=_bos_ise_none(satir.sektor),
                    bist30=bool(satir.bist30),
                    bist100=bool(satir.bist100),
                    guncelleme=simdi,
                )
            )
        oturum.commit()
    return len(df)


def sirketleri_oku() -> pd.DataFrame:
    """Veritabanındaki tüm şirketleri tablo (DataFrame) olarak döndürür."""
    tablolari_olustur()
    return pd.read_sql_table("sirketler", engine_al())


# ---------------------------------------------------------------------------
# Fiyat verileri (Hafta 2)
# ---------------------------------------------------------------------------

def fiyatlari_kaydet(kod: str, df: pd.DataFrame) -> int:
    """
    Bir kodun fiyat tablosunu veritabanına yazar.
    df sütunları: tarih, acilis, yuksek, dusuk, kapanis, hacim

    Yeni verinin başladığı tarihten sonraki eski kayıtlar silinip yenileri yazılır.
    Böylece aynı gün iki kez kaydedilmez ve son günlerin düzeltilmiş verisi güncellenir.
    """
    if df.empty:
        return 0
    df = df.copy()
    df["kod"] = kod
    ilk = df["tarih"].min()
    with engine_al().begin() as baglanti:
        baglanti.execute(delete(Fiyat).where(Fiyat.kod == kod, Fiyat.tarih >= ilk))
        df[["kod", "tarih", "acilis", "yuksek", "dusuk", "kapanis", "hacim"]].to_sql(
            "fiyatlar", baglanti, if_exists="append", index=False, chunksize=1000
        )
    return len(df)


def durum_kaydet(kod: str, durum: str, kaynak: str | None = None, mesaj: str | None = None) -> None:
    """Bir kodun veri durumunu, veritabanındaki gerçek tarih aralığıyla birlikte günceller."""
    with Session(engine_al()) as oturum:
        aralik = oturum.execute(
            select(Fiyat.tarih).where(Fiyat.kod == kod).order_by(Fiyat.tarih)
        ).scalars().all()
        oturum.merge(
            VeriDurumu(
                kod=kod,
                durum=durum,
                kaynak=kaynak,
                ilk_tarih=aralik[0] if aralik else None,
                son_tarih=aralik[-1] if aralik else None,
                gun_sayisi=len(aralik),
                mesaj=(mesaj or "")[:255] or None,
                guncelleme=datetime.now(),
            )
        )
        oturum.commit()


def durumlari_oku() -> pd.DataFrame:
    """Tüm kodların veri durumunu döndürür."""
    tablolari_olustur()
    return pd.read_sql_table("veri_durumu", engine_al())


def fiyatlari_oku(kod: str) -> pd.DataFrame:
    """Bir kodun tüm fiyat geçmişini tarihe göre sıralı döndürür."""
    sorgu = select(Fiyat).where(Fiyat.kod == kod).order_by(Fiyat.tarih)
    return pd.read_sql(sorgu, engine_al())


def tum_fiyatlari_oku() -> pd.DataFrame:
    """Tüm kodların tüm fiyatlarını tek tabloda döndürür (analizler için)."""
    df = pd.read_sql(select(Fiyat).order_by(Fiyat.kod, Fiyat.tarih), engine_al())
    df["tarih"] = pd.to_datetime(df["tarih"])
    return df


# ---------------------------------------------------------------------------
# Analiz sonuçları (Hafta 3)
# ---------------------------------------------------------------------------

def tablo_yaz(ad: str, df: pd.DataFrame) -> None:
    """
    Bir analiz sonucunu veritabanına tablo olarak yazar.
    Tablo her çalıştırmada baştan oluşturulur (eski sonuçlar silinir).
    """
    df.to_sql(ad, engine_al(), if_exists="replace", index=False, chunksize=1000)


def tablo_oku(ad: str) -> pd.DataFrame:
    """Veritabanındaki bir tabloyu okur; tablo yoksa boş tablo döndürür."""
    try:
        return pd.read_sql_table(ad, engine_al())
    except ValueError:
        return pd.DataFrame()
