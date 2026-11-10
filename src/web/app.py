"""
Hafta 4 - Web uygulaması (FastAPI).

Sayfalar:
  /                 Ana sayfa: BIST 100 grafiği, en çok kazandıran/kaybettirenler, sektörler
  /sirketler        Tüm şirketlerin listesi (arama, filtre, sıralama)
  /sirket/{kod}     Şirket detayı: fiyat grafiği, dönem getirileri, risk, benzer hisseler
  /sektorler        Sektörlerin dönem getirileri (Hafta 5)
  /sektor/{ad}      Sektör detayı: sektör endeksi, sektördeki hisseler (Hafta 5)
  /karsilastir      En fazla 5 hisseyi karşılaştırma, korelasyon (Hafta 5)
  /harita           Risk-getiri haritası (Hafta 5)
  /modeller         Tahmin modellerinin karşılaştırması (Hafta 7)
  /rapor/{kod}      Yazdırılabilir şirket raporu (Hafta 7)

Veri servisleri (JSON):
  /api/ara?q=...    Şirket arama (üstteki arama kutusu kullanır)
  /api/fiyat/{kod}  Grafik için fiyat geçmişi
  /api/sektor-endeksi?ad=...  Sektör endeksi grafiği
  /api/tahmin/{kod} Tahmin grafiği verisi (Hafta 7)

Çalıştırmak için: 6_web_uygulamasi.bat dosyasına çift tıklayın, tarayıcı açılır.
"""

import math

import pandas as pd
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.web import veri

KLASOR = Path(__file__).resolve().parent

app = FastAPI(title="Borsa Pusulası", docs_url="/api/belgeler", redoc_url=None)
app.mount("/static", StaticFiles(directory=KLASOR / "static"), name="static")
sablonlar = Jinja2Templates(directory=KLASOR / "templates")


# ---------------------------------------------------------------------------
# Şablonlarda kullanılan biçimlendirme fonksiyonları (Türkçe sayı biçimi)
# ---------------------------------------------------------------------------

def _bos(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def _tr(sayi: float, basamak: int) -> str:
    """1234.5 -> '1.234,50'"""
    return f"{sayi:,.{basamak}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def yuzde(x, basamak: int = 1, isaret: bool = True) -> str:
    if _bos(x):
        return "–"
    metin = _tr(abs(x) * 100, basamak)
    if not isaret:
        return f"%{metin}"
    return f"+%{metin}" if x > 0 else (f"−%{metin}" if x < 0 else f"%{metin}")


def fiyat(x, basamak: int = 2) -> str:
    return "–" if _bos(x) else _tr(x, basamak)


def yon(x) -> str:
    """CSS sınıfı: yükselişte 'art', düşüşte 'az'."""
    if _bos(x) or x == 0:
        return "notr"
    return "art" if x > 0 else "az"


# Getiri şeridinde rengin tam doygunluğa ulaştığı getiri (dönem uzadıkça büyür)
SERIT_OLCEK = {"1a": 0.15, "3a": 0.3, "6a": 0.5, "ytd": 0.6, "1y": 0.8, "5y": 5.0, "10y": 15.0}


def yogunluk(x, donem: str) -> str:
    if _bos(x):
        return "0"
    return f"{min(abs(x) / SERIT_OLCEK[donem], 1.0) * 0.85 + 0.08:.2f}"


def statik(dosya: str) -> str:
    """
    Statik dosyanın adresine değişme zamanını ekler (örn. /static/style.css?v=1731245000).
    Dosya her değiştiğinde adres de değişir; tarayıcı eski sürümü önbellekten göstermez.
    """
    yol = KLASOR / "static" / dosya
    surum = int(yol.stat().st_mtime) if yol.exists() else 0
    return f"/static/{dosya}?v={surum}"


sablonlar.env.filters.update(yuzde=yuzde, fiyat=fiyat, yon=yon)
sablonlar.env.globals.update(statik=statik)
sablonlar.env.globals.update(yogunluk=yogunluk, DONEMLER=veri.DONEM_ADLARI)


def _sayfa(request: Request, sablon: str, **icerik) -> HTMLResponse:
    v = veri.veri()
    icerik.setdefault("veri_var", not v["getiriler"].empty)
    if icerik["veri_var"]:
        icerik.setdefault("hesap_tarihi", pd.Timestamp(v["getiriler"]["hesap_tarihi"].iloc[0]).strftime("%d.%m.%Y"))
    return sablonlar.TemplateResponse(request, sablon, icerik)


# ---------------------------------------------------------------------------
# Sayfalar
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def ana_sayfa(request: Request, donem: str = "1y"):
    if donem not in veri.DONEM_ADLARI or donem in ("5y", "10y"):
        donem = "1y"
    if veri.veri()["getiriler"].empty:
        return _sayfa(request, "ana_sayfa.html", veri_var=False)
    return _sayfa(
        request, "ana_sayfa.html",
        donem=donem,
        xu100=veri.endeks("XU100"),
        xu030=veri.endeks("XU030"),
        # Bütün dönemler baştan hazırlanır; sekmeler sayfa yenilenmeden arasında geçiş yapar
        donemler={
            d: {
                "kazandiran": veri.siralama(d, artan=False),
                "kaybettiren": veri.siralama(d, artan=True),
                "sektorler": veri.sektorler(d),
            }
            for d in ("1a", "3a", "6a", "ytd", "1y")
        },
        genislik=veri.piyasa_genisligi(),
        hisse_sayisi=len(veri.veri()["hisseler"]),
    )


@app.get("/sirketler", response_class=HTMLResponse)
def sirketler(request: Request):
    h = veri.veri()["hisseler"]
    return _sayfa(
        request, "sirketler.html",
        hisseler=h.to_dict("records"),
        sektor_listesi=sorted(h["sektor"].dropna().unique()) if not h.empty else [],
    )


@app.get("/sirket/{kod}", response_class=HTMLResponse)
def sirket(request: Request, kod: str):
    s = veri.sirket(kod)
    if s is None:
        yanit = _sayfa(request, "bulunamadi.html", kod=kod.upper())
        yanit.status_code = 404
        return yanit
    return _sayfa(
        request, "sirket.html",
        s=s, xu100=veri.endeks("XU100"), benzerler=veri.benzer_hisseler(kod), tahmin=veri.tahmin_bilgisi(kod),
    )


@app.get("/rapor/{kod}", response_class=HTMLResponse)
def rapor(request: Request, kod: str):
    s = veri.sirket(kod)
    if s is None:
        yanit = _sayfa(request, "bulunamadi.html", kod=kod.upper())
        yanit.status_code = 404
        return yanit
    return _sayfa(
        request, "rapor.html",
        s=s, xu100=veri.endeks("XU100"), benzerler=veri.benzer_hisseler(kod), tahmin=veri.tahmin_bilgisi(kod),
        olusturma=pd.Timestamp.now().strftime("%d.%m.%Y %H:%M"),
    )


@app.get("/modeller", response_class=HTMLResponse)
def modeller(request: Request):
    return _sayfa(request, "modeller.html", m=veri.model_karsilastirmasi(), hazir=veri.tahmin_hazir())


@app.get("/sektorler", response_class=HTMLResponse)
def sektorler(request: Request):
    return _sayfa(
        request, "sektorler.html",
        sektorler=veri.sektor_listesi(), hafta5=veri.hafta5_hazir(), xu100=veri.endeks("XU100"),
    )


@app.get("/sektor/{ad}", response_class=HTMLResponse)
def sektor(request: Request, ad: str):
    bilgi = veri.sektor_bilgisi(ad)
    if bilgi is None:
        yanit = _sayfa(request, "bulunamadi.html", kod=ad, tur="sektör")
        yanit.status_code = 404
        return yanit
    return _sayfa(
        request, "sektor.html",
        sektor=bilgi, hisseler=veri.sektor_hisseleri(ad), xu100=veri.endeks("XU100"),
    )


@app.get("/karsilastir", response_class=HTMLResponse)
def karsilastir(request: Request, k: list[str] = Query(default=[])):
    # Adres çubuğunda "?k=THYAO&k=PGSUS" veya "?k=THYAO,PGSUS" biçimleri kabul edilir
    kodlar = [parca.strip() for deger in k for parca in deger.split(",") if parca.strip()]
    return _sayfa(request, "karsilastir.html", k=veri.karsilastirma(kodlar), xu100=veri.endeks("XU100"))


@app.get("/harita", response_class=HTMLResponse)
def harita(request: Request, donem: str = "1y"):
    if donem not in ("1a", "3a", "6a", "ytd", "1y"):
        donem = "1y"
    h = veri.veri()["hisseler"]
    return _sayfa(
        request, "harita.html",
        donem=donem, noktalar=veri.harita_verisi(donem), xu100=veri.endeks("XU100"),
        sektor_listesi=sorted(h["sektor"].dropna().unique()) if not h.empty else [],
    )


# ---------------------------------------------------------------------------
# Grafik kütüphanesi
# ---------------------------------------------------------------------------

@app.get("/kutuphane/plotly.min.js", include_in_schema=False)
def plotly_js():
    """
    Grafik kütüphanesini (plotly.js) sunar: önce public/kutuphane klasöründeki kopya, yoksa kurulu
    Python plotly paketinin içindeki dosya. Site internetsiz de (örneğin sunumda) grafik çizebilir.
    İnternetteki sitede (Vercel) public/ klasörü doğrudan Vercel'in hızlı sunucularından verilir,
    bu fonksiyona hiç gelinmez.
    """
    yol = KLASOR.parents[1] / "public" / "kutuphane" / "plotly.min.js"
    if not yol.exists():
        import plotly

        yol = Path(plotly.__file__).parent / "package_data" / "plotly.min.js"
    if not yol.exists():
        raise HTTPException(404, "plotly.min.js bulunamadı; kurulum.bat ile kütüphaneleri yeniden kurun.")
    return FileResponse(yol, media_type="application/javascript", headers={"Cache-Control": "max-age=86400"})


# ---------------------------------------------------------------------------
# JSON servisleri
# ---------------------------------------------------------------------------

@app.get("/api/ara")
def api_ara(q: str = ""):
    return veri.ara(q)


@app.get("/api/sektor-endeksi")
def api_sektor_endeksi(ad: str):
    if veri.sektor_bilgisi(ad) is None and ad != veri.TUM_HISSELER:
        raise HTTPException(404, f"{ad} sektörü bulunamadı")
    return JSONResponse(veri.sektor_endeksi(ad))


@app.get("/api/tahmin/{kod}")
def api_tahmin(kod: str):
    if veri.sirket(kod) is None:
        raise HTTPException(404, f"{kod.upper()} bulunamadı")
    return JSONResponse(veri.tahmin_grafigi(kod))


@app.get("/api/fiyat/{kod}")
def api_fiyat(kod: str):
    if veri.sirket(kod) is None and kod.upper() not in ("XU100", "XU030"):
        raise HTTPException(404, f"{kod.upper()} bulunamadı")
    return JSONResponse(veri.fiyat_gecmisi(kod))
