"""
Web uygulamasının veri katmanı.

Sayfalar veriyi doğrudan veritabanından değil bu dosyadaki fonksiyonlardan alır.
Analiz tabloları (getiriler, şirketler) bellekte tutulur (önbellek) ve veritabanı
dosyası değiştiğinde (örneğin günlük güncellemeden sonra) otomatik yeniden okunur.
Böylece her sayfa açılışında veritabanı baştan okunmaz, site hızlı çalışır.
"""

import os
import threading
import time
from pathlib import Path

import pandas as pd
from sqlalchemy import func, select, text

from config import VERITABANI_URL
from src.analiz.korelasyon import gunluk_getiriler, korelasyon_matrisi
from src.analiz.sektor import TUM_HISSELER
from src.tahmin.modeller import MODEL_BASLIKLARI
from src.veritabani import Fiyat, engine_al, tablo_oku

ENDEKS = "XU100"
DONEM_ADLARI = {
    "1a": "1 ay", "3a": "3 ay", "6a": "6 ay", "ytd": "Yılbaşı",
    "1y": "1 yıl", "5y": "5 yıl", "10y": "10 yıl",
}

_kilit = threading.Lock()
_onbellek: dict = {"anahtar": None}


def _veritabani_surumu():
    """SQLite dosyasının değişme zamanı; PostgreSQL için 10 dakikalık zaman dilimi."""
    if VERITABANI_URL.startswith("sqlite:///"):
        yol = Path(VERITABANI_URL.removeprefix("sqlite:///"))
        return os.path.getmtime(yol) if yol.exists() else None
    return int(time.time() // 600)


def _gunluk_degisim() -> pd.DataFrame:
    """Her kodun son iki kapanışından günlük değişimi hesaplar."""
    with engine_al().connect() as b:
        son = b.execute(select(func.max(Fiyat.tarih))).scalar()
    if son is None:
        return pd.DataFrame(columns=["kod", "gunluk_degisim"])
    sinir = pd.Timestamp(son) - pd.Timedelta(days=20)
    df = pd.read_sql(
        select(Fiyat.kod, Fiyat.tarih, Fiyat.kapanis).where(Fiyat.tarih >= sinir.date()).order_by(Fiyat.kod, Fiyat.tarih),
        engine_al(),
    )
    df["gunluk_degisim"] = df.groupby("kod")["kapanis"].pct_change()
    return df.groupby("kod").tail(1)[["kod", "gunluk_degisim"]]


def _yukle() -> dict:
    getiriler = tablo_oku("getiriler")
    if getiriler.empty:
        return {"getiriler": getiriler, "hisseler": getiriler, "endeksler": getiriler}
    getiriler = getiriler.merge(_gunluk_degisim(), on="kod", how="left")
    getiriler["unvan"] = getiriler["unvan"].fillna(getiriler["kod"])
    getiriler["sektor"] = getiriler["sektor"].fillna("Sektör bilgisi yok")
    for s in ("bist30", "bist100"):
        getiriler[s] = getiriler[s].fillna(False).astype(bool)
    endeks_mi = getiriler["sektor"] == "Endeks"
    return {
        "getiriler": getiriler,
        "hisseler": getiriler[~endeks_mi].sort_values("kod").reset_index(drop=True),
        "endeksler": getiriler[endeks_mi].set_index("kod"),
        # Hafta 5 tabloları (analiz eski sürümle çalıştırıldıysa boş gelir)
        "sektor_ozeti": tablo_oku("sektor_ozeti"),
        "benzerler": tablo_oku("benzer_hisseler"),
        # Hafta 6 tabloları (tahmin modelleri çalıştırılmadıysa boş gelir)
        "model_performans": tablo_oku("model_performans"),
        "tahmin_ozeti": tablo_oku("tahmin_ozeti"),
        # İnternetteki sitede: verilerin en son ne zaman güncellendiği (GitHub Actions yazar)
        "guncelleme": tablo_oku("guncelleme"),
    }


def son_guncelleme() -> str | None:
    """Son otomatik güncellemenin zamanı ('10.11.2026 14:32'); bilgisayardaki sitede None."""
    g = veri().get("guncelleme")
    if g is None or g.empty:
        return None
    return pd.Timestamp(g["zaman"].iloc[0]).strftime("%d.%m.%Y %H:%M")


def veri() -> dict:
    """Önbellekteki tabloları döndürür; veritabanı değiştiyse yeniden yükler."""
    anahtar = _veritabani_surumu()
    with _kilit:
        if _onbellek["anahtar"] != anahtar or "getiriler" not in _onbellek:
            _onbellek.update(_yukle())
            _onbellek["anahtar"] = anahtar
    return _onbellek


# ---------------------------------------------------------------------------
# Sayfaların kullandığı sorgular
# ---------------------------------------------------------------------------

def arama_bicimi(metin: str) -> str:
    """
    Aramada karşılaştırma için metni sadeleştirir: büyük harf ve noktasız I.
    Böylece "is", "İŞ" ve "IS" yazımlarının hepsi ISCTR ve "İŞ BANKASI" ile eşleşir.
    """
    return metin.replace("İ", "I").replace("ı", "i").upper()


def ara(sorgu: str, limit: int = 8) -> list[dict]:
    """Kod veya unvanda arama. Kodu sorguyla başlayanlar en üstte gelir."""
    sorgu = arama_bicimi(sorgu.strip())
    if not sorgu:
        return []
    h = veri()["hisseler"]
    kod_bas = h[h["kod"].str.startswith(sorgu)]
    unvan_icinde = h[h["unvan"].map(arama_bicimi).str.contains(sorgu, regex=False) & ~h["kod"].isin(kod_bas["kod"])]
    sonuc = pd.concat([kod_bas, unvan_icinde]).head(limit)
    return sonuc[["kod", "unvan", "sektor"]].to_dict("records")


def sirket(kod: str) -> dict | None:
    """Bir şirketin getiri satırı (yoksa None)."""
    h = veri()["hisseler"]
    satir = h[h["kod"] == kod.upper()]
    return None if satir.empty else satir.iloc[0].to_dict()


def endeks(kod: str = ENDEKS) -> dict | None:
    e = veri()["endeksler"]
    return e.loc[kod].to_dict() | {"kod": kod} if kod in e.index else None


def siralama(donem: str, artan: bool, limit: int = 8) -> list[dict]:
    """Bir dönemde en çok kazandıran (artan=False) veya kaybettiren hisseler."""
    s = f"getiri_{donem}"
    h = veri()["hisseler"].dropna(subset=[s])
    return h.sort_values(s, ascending=artan).head(limit).to_dict("records")


def piyasa_genisligi() -> dict:
    """Son işlem gününde yükselen, düşen ve değişmeyen hisse sayısı."""
    d = veri()["hisseler"]["gunluk_degisim"].dropna()
    return {"yukselen": int((d > 0).sum()), "dusen": int((d < 0).sum()), "degismeyen": int((d == 0).sum())}


def sektorler(donem: str = "1y") -> list[dict]:
    """Sektörlerin medyan getirisi ve hisse sayısı."""
    s = f"getiri_{donem}"
    h = veri()["hisseler"].dropna(subset=[s])
    h = h[h["sektor"] != "Sektör bilgisi yok"]
    t = h.groupby("sektor")[s].agg(medyan="median", adet="count").reset_index()
    return t[t["adet"] >= 3].sort_values("medyan", ascending=False).to_dict("records")


def fiyat_gecmisi(kod: str) -> dict:
    """Grafik için bir kodun ve BIST 100'ün tüm fiyat geçmişi."""
    def oku(k: str) -> pd.DataFrame:
        sorgu = select(Fiyat).where(Fiyat.kod == k).order_by(Fiyat.tarih)
        return pd.read_sql(sorgu, engine_al())

    df = oku(kod.upper())
    e = oku(ENDEKS)
    return {
        "kod": kod.upper(),
        "tarih": df["tarih"].astype(str).tolist(),
        "acilis": df["acilis"].round(4).tolist(),
        "yuksek": df["yuksek"].round(4).tolist(),
        "dusuk": df["dusuk"].round(4).tolist(),
        "kapanis": df["kapanis"].round(4).tolist(),
        "hacim": df["hacim"].fillna(0).tolist(),
        "endeks": {"tarih": e["tarih"].astype(str).tolist(), "kapanis": e["kapanis"].round(2).tolist()},
    }


# ---------------------------------------------------------------------------
# Hafta 5: sektörler, karşılaştırma, benzer hisseler, risk haritası
# ---------------------------------------------------------------------------

def hafta5_hazir() -> bool:
    """Hafta 5 analiz tabloları veritabanında var mı?"""
    return not veri()["sektor_ozeti"].empty


def sektor_listesi() -> list[dict]:
    """Tüm sektörlerin özet satırları (1 yıllık medyan getiriye göre sıralı)."""
    t = veri()["sektor_ozeti"]
    return [] if t.empty else t.sort_values("getiri_1y", ascending=False).to_dict("records")


def sektor_bilgisi(ad: str) -> dict | None:
    t = veri()["sektor_ozeti"]
    satir = t[t["sektor"] == ad]
    return None if satir.empty else satir.iloc[0].to_dict()


def sektor_hisseleri(ad: str) -> list[dict]:
    h = veri()["hisseler"]
    return h[h["sektor"] == ad].sort_values("getiri_1y", ascending=False, na_position="last").to_dict("records")


def sektor_endeksi(ad: str) -> dict:
    """Bir sektörün, 'Tüm hisseler' endeksinin ve BIST 100'ün grafik verisi."""
    def oku(sektor: str) -> dict:
        sorgu = text("SELECT tarih, deger FROM sektor_endeksleri WHERE sektor = :s ORDER BY tarih")
        df = pd.read_sql(sorgu, engine_al(), params={"s": sektor})
        return {"tarih": df["tarih"].astype(str).tolist(), "deger": df["deger"].tolist()}

    seriler = [{"ad": ad} | oku(ad)]
    if ad != TUM_HISSELER:
        seriler.append({"ad": f"{TUM_HISSELER} (eşit ağırlık)"} | oku(TUM_HISSELER))
    e = fiyat_gecmisi(ENDEKS)["endeks"]
    seriler.append({"ad": "BIST 100", "tarih": e["tarih"], "deger": e["kapanis"]})
    return {"seriler": seriler}


def benzer_hisseler(kod: str) -> list[dict]:
    b = veri()["benzerler"]
    if b.empty:
        return []
    b = b[b["kod"] == kod.upper()].sort_values("sira")
    h = veri()["hisseler"].set_index("kod")
    return [
        {"kod": r.benzer_kod, "korelasyon": r.korelasyon,
         "unvan": h.at[r.benzer_kod, "unvan"] if r.benzer_kod in h.index else r.benzer_kod,
         "getiri_1y": h.at[r.benzer_kod, "getiri_1y"] if r.benzer_kod in h.index else None}
        for r in b.itertuples()
    ]


def karsilastirma(kodlar: list[str]) -> dict:
    """Seçilen hisselerin getiri/risk satırları ve son 1 yılın korelasyon matrisi."""
    h = veri()["hisseler"].set_index("kod")
    gecerli = [k for k in dict.fromkeys(k.upper() for k in kodlar) if k in h.index][:5]
    satirlar = [h.loc[k].to_dict() | {"kod": k} for k in gecerli]
    matris = []
    if len(gecerli) >= 2:
        sorgu = select(Fiyat.kod, Fiyat.tarih, Fiyat.kapanis).where(Fiyat.kod.in_(gecerli))
        f = pd.read_sql(sorgu, engine_al())
        f["tarih"] = pd.to_datetime(f["tarih"])
        kor = korelasyon_matrisi(gunluk_getiriler(f, gecerli)).reindex(index=gecerli, columns=gecerli)
        matris = [[None if pd.isna(x) else round(float(x), 2) for x in satir] for satir in kor.values]
    # Her dönemde en yüksek getiriyi sağlayan hisse (tabloda kalın gösterilir)
    en_iyi = {}
    if len(satirlar) >= 2:
        for d in DONEM_ADLARI:
            adaylar = [(r[f"getiri_{d}"], r["kod"]) for r in satirlar if pd.notna(r[f"getiri_{d}"])]
            if len(adaylar) >= 2:
                en_iyi[d] = max(adaylar)[1]
    return {"kodlar": gecerli, "satirlar": satirlar, "korelasyon": matris, "en_iyi": en_iyi}


def harita_verisi(donem: str) -> list[dict]:
    """Risk-getiri haritası için her hissenin oynaklığı ve getirisi."""
    s = f"getiri_{donem}"
    h = veri()["hisseler"].dropna(subset=[s, "volatilite_1y"])
    return [
        {"kod": r.kod, "unvan": r.unvan, "sektor": r.sektor, "x": round(r.volatilite_1y * 100, 2),
         "y": round(getattr(r, s) * 100, 2), "bist100": bool(r.bist100)}
        for r in h.itertuples()
    ]


# ---------------------------------------------------------------------------
# Hafta 7: tahminler
# ---------------------------------------------------------------------------

def tahmin_hazir() -> bool:
    return not veri()["tahmin_ozeti"].empty


def model_basligi(ad: str, derece: str | None = None) -> str:
    """Modelin ekranda görünen adı; ARIMA için seçilen derece de eklenir."""
    if ad == "arima" and derece:
        return f"ARIMA{derece.replace(' ', '')}"
    return MODEL_BASLIKLARI.get(ad, ad)


def tahmin_bilgisi(kod: str) -> dict | None:
    """Bir hissenin tahmin özeti, 20. gün aralığı ve modellerin geçmiş test başarısı."""
    v = veri()
    oz = v["tahmin_ozeti"]
    if oz.empty:
        return None
    satir = oz[oz["kod"] == kod.upper()]
    if satir.empty:
        return None
    ozet = satir.iloc[0].to_dict()
    ozet["en_iyi_baslik"] = model_basligi(ozet["en_iyi_model"], ozet.get("arima_derecesi"))

    with engine_al().connect() as b:
        son = b.execute(
            text("SELECT alt, ust FROM tahminler WHERE kod = :k AND model = :m ORDER BY adim DESC LIMIT 1"),
            {"k": kod.upper(), "m": ozet["en_iyi_model"]},
        ).fetchone()
    ozet["alt_20g"], ozet["ust_20g"] = (son[0], son[1]) if son else (None, None)

    # Her modelin 20. gün tahmini (tabloda gösterilir)
    son_gun = pd.read_sql(
        text("SELECT model, tahmin FROM tahminler WHERE kod = :k AND adim = (SELECT MAX(adim) FROM tahminler WHERE kod = :k)"),
        engine_al(), params={"k": kod.upper()},
    ).set_index("model")["tahmin"].to_dict()

    perf = v["model_performans"]
    perf = perf[perf["kod"] == kod.upper()].copy()
    perf["tahmin_20g"] = perf["model"].map(son_gun)
    sira = {ad: i for i, ad in enumerate(MODEL_BASLIKLARI)}
    perf["sira"] = perf["model"].map(sira)
    modeller = [
        r | {"baslik": model_basligi(r["model"], ozet.get("arima_derecesi")), "en_iyi": r["model"] == ozet["en_iyi_model"]}
        for r in perf.sort_values("sira").to_dict("records")
    ]
    return {"ozet": ozet, "modeller": modeller}


def tahmin_grafigi(kod: str, gecmis_gun: int = 130) -> dict:
    """Grafik için son ~6 ayın kapanışları ve her modelin 20 günlük tahmini."""
    kod = kod.upper()
    fiyat = fiyat_gecmisi(kod)
    oz = veri()["tahmin_ozeti"]
    satir = oz[oz["kod"] == kod]
    en_iyi = satir.iloc[0]["en_iyi_model"] if not satir.empty else None
    derece = satir.iloc[0]["arima_derecesi"] if not satir.empty else None

    df = pd.read_sql(
        text("SELECT model, tarih, tahmin, alt, ust FROM tahminler WHERE kod = :k ORDER BY model, adim"),
        engine_al(), params={"k": kod},
    )
    modeller = []
    for ad in MODEL_BASLIKLARI:
        m = df[df["model"] == ad]
        if m.empty:
            continue
        modeller.append({
            "ad": ad, "baslik": model_basligi(ad, derece), "en_iyi": ad == en_iyi,
            "tarih": m["tarih"].astype(str).tolist(), "tahmin": m["tahmin"].round(4).tolist(),
            "alt": m["alt"].round(4).tolist() if m["alt"].notna().all() else None,
            "ust": m["ust"].round(4).tolist() if m["ust"].notna().all() else None,
        })
    return {
        "kod": kod,
        "gecmis": {"tarih": fiyat["tarih"][-gecmis_gun:], "kapanis": fiyat["kapanis"][-gecmis_gun:]},
        "modeller": modeller,
    }


def model_karsilastirmasi() -> dict:
    """Bütün borsada modellerin özeti (Modeller sayfası için)."""
    perf = veri()["model_performans"]
    oz = veri()["tahmin_ozeti"]
    if perf.empty:
        return {"satirlar": [], "hisse_sayisi": 0, "arima_en_iyi": []}
    en_iyi_sayisi = oz["en_iyi_model"].value_counts()
    satirlar = []
    for ad, baslik in MODEL_BASLIKLARI.items():
        p = perf[perf["model"] == ad]
        if p.empty:
            continue
        satirlar.append({
            "ad": ad, "baslik": baslik,
            "mape": p["mape"].median(),
            "yon": p["yon"].mean() if ad != "naif" else None,
            "naiften_iyi": (p["naife_gore_iyilesme"] > 0).mean() if ad != "naif" else None,
            "en_iyi": int(en_iyi_sayisi.get(ad, 0)),
        })
    hisseler = veri()["hisseler"].set_index("kod")
    arima = perf[perf["model"] == "arima"].nlargest(10, "naife_gore_iyilesme")
    arima_en_iyi = [
        {"kod": r.kod, "unvan": hisseler.at[r.kod, "unvan"] if r.kod in hisseler.index else r.kod,
         "iyilesme": r.naife_gore_iyilesme, "mape": r.mape, "yon": r.yon}
        for r in arima.itertuples()
    ]
    return {"satirlar": satirlar, "hisse_sayisi": int(perf["kod"].nunique()), "arima_en_iyi": arima_en_iyi}
