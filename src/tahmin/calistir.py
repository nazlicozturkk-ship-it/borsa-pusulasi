"""
Hafta 6 - Tahmin modellerini bütün hisselerde test eder ve gelecek 20 işlem gününü tahmin eder.

Her hisse için:
  1. ARIMA için en uygun derece seçilir (son 2 yılın verisiyle, AIC ölçütüne göre).
  2. Dört model 6 farklı geçmiş başlangıç noktasında test edilir (bkz. degerlendirme.py).
  3. Testte en düşük hatayı (RMSE) veren model o hissenin "en iyi modeli" olur.
  4. Bütün modellerle gelecek 20 işlem günü tahmin edilir (güven aralıklarıyla).

Sonuçlar veritabanına yazılır:
  model_performans : kod, model, mae, rmse, mape, yon, test_sayisi, naife_gore_iyilesme
  tahminler        : kod, model, adim, tarih, tahmin, alt, ust   (gelecek 20 gün)
  tahmin_ozeti     : kod, en_iyi_model, arima_derecesi, son_fiyat, tahmin_20g, tahmini_getiri_20g, ...
ve data/model_performans.csv dosyasına.

Hisseler bilgisayarın işlemci çekirdeklerine dağıtılarak paralel işlenir.

Kullanım:
  python -m src.tahmin.calistir                  # tüm hisseler (birkaç dakika)
  python -m src.tahmin.calistir --sadece bist30  # hızlı deneme
"""

import argparse
import os
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd

from config import VERI_KLASORU
from src.log_ayari import logger_olustur
from src.tahmin.degerlendirme import EGITIM, EN_AZ_EGITIM, UFUK, baslangic_noktalari, geriye_donuk_test
from src.tahmin.modeller import MODEL_BASLIKLARI, Arima, tum_modeller
from src.veritabani import durumlari_oku, sirketleri_oku, tablo_oku, tablo_yaz, tum_fiyatlari_oku

# Kayıt dosyası sadece ana programda açılır. Windows'ta paralel işlemler bu dosyayı
# yeniden içe aktarır; logger burada oluşturulsaydı her işlem kayıt dosyasını sıfırlardı.
log = None


def hisse_isle(kod: str, tarihler: np.ndarray, kapanis: np.ndarray) -> dict:
    """
    Tek bir hisse için bütün işlemler. Ayrı bir işlemde (process) çalışır; bu yüzden
    sadece sonuçları döndürür, veritabanına yazmaz.
    """
    warnings.filterwarnings("ignore")
    baslama = time.time()
    log_fiyat = np.log(kapanis)
    egitim = log_fiyat[-EGITIM:]

    # 1) ARIMA derecesi
    derece = Arima.derece_sec(egitim)
    modeller = tum_modeller(derece)

    # 2) Geriye dönük test
    performans = geriye_donuk_test(log_fiyat, modeller)
    naif_rmse = performans.get("naif", {}).get("rmse")
    for ad, p in performans.items():
        p["naife_gore_iyilesme"] = (1 - p["rmse"] / naif_rmse) if naif_rmse else np.nan

    # 3) En iyi model (en düşük RMSE)
    en_iyi = min(performans, key=lambda ad: performans[ad]["rmse"]) if performans else None

    # 4) Gelecek 20 işlem günü (hafta sonları atlanır; resmi tatiller hesaba katılmaz)
    son_tarih = pd.Timestamp(tarihler[-1])
    gelecek = pd.bdate_range(son_tarih + pd.Timedelta(days=1), periods=UFUK)
    tahminler = []
    for model in modeller:
        try:
            t = model.tahmin(egitim, UFUK)
        except Exception:
            continue
        for i in range(UFUK):
            tahminler.append({
                "kod": kod, "model": model.ad, "adim": i + 1, "tarih": gelecek[i].date(),
                "tahmin": float(np.exp(t.ortalama[i])),
                "alt": float(np.exp(t.alt[i])) if t.alt is not None else None,
                "ust": float(np.exp(t.ust[i])) if t.ust is not None else None,
            })

    return {"kod": kod, "derece": derece, "performans": performans, "en_iyi": en_iyi, "tahminler": tahminler,
            "son_fiyat": float(kapanis[-1]), "son_tarih": son_tarih.date(), "sure": time.time() - baslama}


def hisseleri_hazirla(sadece: str | None) -> dict[str, tuple]:
    """Analize uygun hisselerin fiyat serilerini döndürür: {kod: (tarihler, kapanışlar)}."""
    durum = durumlari_oku()
    aktif = set(durum.loc[durum["durum"] == "tamam", "kod"])
    sirketler = sirketleri_oku()
    if sadece:
        aktif &= set(sirketler.loc[sirketler[sadece], "kod"])
    else:
        aktif &= set(sirketler["kod"])  # endeksler hariç

    fiyatlar = tum_fiyatlari_oku()
    fiyatlar = fiyatlar[fiyatlar["kod"].isin(aktif)]
    seriler = {}
    for kod, g in fiyatlar.groupby("kod"):
        g = g.dropna(subset=["kapanis"])
        g = g[g["kapanis"] > 0]
        # En az bir geriye dönük test yapılabilecek kadar geçmiş gerekli
        if len(g) >= EN_AZ_EGITIM + UFUK:
            seriler[kod] = (g["tarih"].to_numpy(), g["kapanis"].to_numpy(dtype=float))
    return seriler


def eskileri_koru(ad: str, yeni: pd.DataFrame, kodlar: set[str]) -> pd.DataFrame:
    """Kısmi çalıştırmada (ör. sadece BIST 30) diğer hisselerin eski sonuçlarını korur."""
    eski = tablo_oku(ad)
    if eski.empty or "kod" not in eski.columns:
        return yeni
    return pd.concat([eski[~eski["kod"].isin(kodlar)], yeni], ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Tahmin modellerini çalıştırır")
    parser.add_argument("--sadece", choices=["bist30", "bist100"])
    args = parser.parse_args()

    global log
    log = logger_olustur("tahmin")
    seriler = hisseleri_hazirla(args.sadece)
    if not seriler:
        log.error("Uygun hisse bulunamadı. Önce 2_fiyat_verisi.bat dosyasını çalıştırın.")
        raise SystemExit(1)

    cekirdek = max(1, min(4, (os.cpu_count() or 2) - 1))
    # Her paralel işlem hesaplamalarda tek çekirdek kullansın. Aksi halde her işlem bütün
    # çekirdekleri kullanmaya çalışır ve işlemler birbirini yavaşlatır.
    for degisken in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[degisken] = "1"
    log.info("Tahmin modelleri: %s", ", ".join(MODEL_BASLIKLARI.values()))
    log.info("%d hisse işlenecek (%d paralel işlem). Her hisse %d ayrı geçmiş dönemde test edilir.",
             len(seriler), cekirdek, len(baslangic_noktalari(EGITIM + 200)))
    log.info("İlk hisseler 1-3 dakika sürebilir: paralel işlemler başlarken kütüphaneleri yüklüyor.")
    log.info("Sonraki hisselerin her biri birkaç saniye sürer.")
    baslama = time.time()

    sonuclar, hatalar = [], []
    with ProcessPoolExecutor(max_workers=cekirdek) as havuz:
        isler = {havuz.submit(hisse_isle, kod, t, k): kod for kod, (t, k) in seriler.items()}
        for i, is_ in enumerate(as_completed(isler), start=1):
            kod = isler[is_]
            gecen = time.time() - baslama
            kalan = round(gecen / i * (len(isler) - i) / 60)
            try:
                s = is_.result()
                sonuclar.append(s)
                log.info("  [%3d/%d] %-6s ARIMA%s, en iyi model: %-18s %4.0f sn  (kalan ~%d dk)",
                         i, len(isler), kod, s["derece"], s["en_iyi"], s["sure"], kalan)
            except Exception as hata:
                hatalar.append(kod)
                log.warning("  [%3d/%d] %s işlenemedi: %s", i, len(isler), kod, str(hata)[:120])

    # ---- Tabloları oluştur ----
    performans = pd.DataFrame([
        {"kod": s["kod"], "model": ad, **p} for s in sonuclar for ad, p in s["performans"].items()
    ])
    tahminler = pd.DataFrame([t for s in sonuclar for t in s["tahminler"]])
    ozet_satirlari = []
    for s in sonuclar:
        en_iyi = s["en_iyi"]
        t20 = next((t["tahmin"] for t in s["tahminler"] if t["model"] == en_iyi and t["adim"] == UFUK), np.nan)
        p = s["performans"].get(en_iyi, {})
        ozet_satirlari.append({
            "kod": s["kod"], "en_iyi_model": en_iyi, "arima_derecesi": str(s["derece"]),
            "son_tarih": s["son_tarih"], "son_fiyat": s["son_fiyat"], "tahmin_20g": t20,
            "tahmini_getiri_20g": t20 / s["son_fiyat"] - 1 if t20 == t20 else np.nan,
            "en_iyi_mape": p.get("mape"), "naife_gore_iyilesme": p.get("naife_gore_iyilesme"),
        })
    ozet = pd.DataFrame(ozet_satirlari)

    kodlar = set(seriler)
    if args.sadece:
        performans = eskileri_koru("model_performans", performans, kodlar)
        tahminler = eskileri_koru("tahminler", tahminler, kodlar)
        ozet = eskileri_koru("tahmin_ozeti", ozet, kodlar)
    tablo_yaz("model_performans", performans.round(6))
    tablo_yaz("tahminler", tahminler.round(4))
    tablo_yaz("tahmin_ozeti", ozet.round(6))
    csv = performans.copy()
    for s in ("mape", "yon", "naife_gore_iyilesme"):
        csv[s] = (csv[s] * 100).round(2)
    csv.to_csv(VERI_KLASORU / "model_performans.csv", index=False, sep=";", decimal=",", encoding="utf-8-sig")

    ozet_yazdir(performans[performans["kod"].isin(kodlar)], ozet[ozet["kod"].isin(kodlar)], time.time() - baslama, hatalar)


def ozet_yazdir(perf: pd.DataFrame, ozet: pd.DataFrame, sure: float, hatalar: list) -> None:
    log.info("-" * 78)
    log.info("MODEL KARŞILAŞTIRMASI (%d hisse, 20 işlem günü ileri tahmin)", perf["kod"].nunique())
    log.info("  %-32s %8s %10s %14s %12s", "Model", "MAPE", "Yön doğru", "Naiften iyi", "En iyi")
    en_iyi_sayilari = ozet["en_iyi_model"].value_counts()
    for ad, baslik in MODEL_BASLIKLARI.items():
        p = perf[perf["model"] == ad]
        if p.empty:
            continue
        yon = p["yon"].mean()
        naiften_iyi = (p["naife_gore_iyilesme"] > 0).mean() if ad != "naif" else np.nan
        log.info(
            "  %-32s %7.1f%% %10s %14s %8d hisse", baslik, p["mape"].median() * 100,
            "-" if pd.isna(yon) else f"%{yon * 100:.0f}",
            "-" if pd.isna(naiften_iyi) else f"%{naiften_iyi * 100:.0f} hisse",
            en_iyi_sayilari.get(ad, 0),
        )
    log.info("  MAPE: medyan ortalama yüzde hata. Yön doğru: 20 gün sonraki yönü bilme oranı.")
    log.info("  Naiften iyi: modelin 'fiyat değişmez' tahmininden daha az hata yaptığı hisse oranı.")
    if hatalar:
        log.info("  İşlenemeyen hisse: %d (%s)", len(hatalar), ", ".join(hatalar[:10]))
    log.info("  Süre: %.1f dakika", sure / 60)
    log.info("-" * 78)
    log.info("Sonuçlar: veritabanında model_performans, tahminler, tahmin_ozeti; data/model_performans.csv")
    log.info("Tamamlandı.")


if __name__ == "__main__":
    main()
