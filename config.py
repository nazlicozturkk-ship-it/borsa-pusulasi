"""
Proje ayarları.

Tüm klasör yolları ve veritabanı bağlantısı burada tanımlanır.
Diğer dosyalar ayarları buradan okur; bir şeyi değiştirmek gerekirse
yalnızca bu dosyayı düzenlemek yeterlidir.
"""

import os
from pathlib import Path

# Bu dosyanın bulunduğu klasör = projenin ana klasörü
PROJE_KLASORU = Path(__file__).resolve().parent

VERI_KLASORU = PROJE_KLASORU / "data"   # veritabanı ve CSV dosyaları
LOG_KLASORU = PROJE_KLASORU / "logs"    # çalışma kayıtları

# İnternetteki sunucuda (Vercel) dosya sistemi salt okunur; klasör açılamazsa sorun değil
for _klasor in (VERI_KLASORU, LOG_KLASORU):
    try:
        _klasor.mkdir(exist_ok=True)
    except OSError:
        pass


def _env_dosyasini_oku() -> None:
    """Proje klasöründeki .env dosyasındaki AD=deger satırlarını ortam değişkeni yapar."""
    yol = PROJE_KLASORU / ".env"
    if not yol.exists():
        return
    for satir in yol.read_text(encoding="utf-8-sig").splitlines():
        satir = satir.strip()
        if not satir or satir.startswith("#") or "=" not in satir:
            continue
        ad, deger = satir.split("=", 1)
        os.environ.setdefault(ad.strip(), deger.strip().strip('"').strip("'"))


def postgresql_adresi(adres: str) -> str:
    """Supabase/Vercel'in verdiği postgres:// adresini SQLAlchemy'nin anlayacağı biçime çevirir."""
    for on_ek in ("postgres://", "postgresql://"):
        if adres.startswith(on_ek):
            return "postgresql+psycopg2://" + adres[len(on_ek):]
    return adres


_env_dosyasini_oku()

# Veritabanı bağlantısı
# Şimdilik Python ile birlikte gelen SQLite kullanılıyor (kurulum gerektirmez).
# PostgreSQL'e geçmek için alttaki satırı açıp SIFRE kısmını kendi şifrenle değiştirmen yeterli:
# VERITABANI_URL = "postgresql+psycopg2://postgres:SIFRE@localhost:5432/bist"
#
# İnternetteki sitede (Vercel) SUPABASE_DATABASE_URL değişkeni tanımlıdır ve site PostgreSQL'i (Supabase) kullanır.
# (DATABASE_URL eski Neon bağlantısıdır, sadece yedek olarak bakılır.)
# Senin bilgisayarında bu değişkenler yoktur; bütün işler hızlı çalışan SQLite dosyasıyla yapılır,
# sonuçlar 8_buluta_aktar.bat ile internetteki veritabanına kopyalanır.
_bulut = (
    os.environ.get("SUPABASE_DATABASE_URL")
    or os.environ.get("DATABASE_URL")
    or os.environ.get("POSTGRES_URL")
)
VERITABANI_URL = postgresql_adresi(_bulut) if _bulut else f"sqlite:///{(VERI_KLASORU / 'bist.db').as_posix()}"

# 8_buluta_aktar.bat'ın verileri kopyalayacağı internetteki veritabanı (.env dosyasından okunur)
BULUT_VERITABANI_URL = postgresql_adresi(os.environ.get("BULUT_VERITABANI_URL", ""))

# Takip edilen endeksler (kod: görünen ad)
ENDEKSLER = {
    "XU030": "BIST 30",
    "XU100": "BIST 100",
}
