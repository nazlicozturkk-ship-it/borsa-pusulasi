"""
Tanılama: ARIMA'nın bu bilgisayarda ne kadar sürdüğünü ölçer.

THYAO'nun son 2 yılı üzerinde her ARIMA derecesini ayrı ayrı eğitir ve süreleri
logs/hiz_testi.log dosyasına yazar. Ayrıca paralel işlemlerin (multiprocessing)
düzgün başlayıp başlamadığını kontrol eder. Her satır hemen dosyaya yazılır;
program bir yerde takılırsa nerede takıldığı görülebilir.

Çalıştırmak için: 7_tahmin_hiz_testi.bat
"""

import os
import platform
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor

from config import LOG_KLASORU

DOSYA = LOG_KLASORU / "hiz_testi.log"


def yaz(metin: str) -> None:
    satir = f"{time.strftime('%H:%M:%S')} | {metin}"
    print(satir, flush=True)
    with open(DOSYA, "a", encoding="utf-8") as f:
        f.write(satir + "\n")


def kare(x: int) -> int:
    return x * x


def main() -> None:
    DOSYA.write_text("", encoding="utf-8")
    warnings.filterwarnings("ignore")
    yaz(f"Python {sys.version.split()[0]}, {platform.platform()}, çekirdek: {os.cpu_count()}")

    t = time.time()
    import numpy as np
    import statsmodels
    from statsmodels.tsa.arima.model import ARIMA
    yaz(f"statsmodels {getattr(statsmodels, '__version__', '?')}, numpy {np.__version__} yüklendi ({time.time() - t:.1f} sn)")
    try:
        bilgi = np.show_config(mode="dicts")
        yaz(f"numpy BLAS: {bilgi.get('Build Dependencies', {}).get('blas', {}).get('name', '?')}")
    except Exception:
        pass

    from src.veritabani import fiyatlari_oku

    k = fiyatlari_oku("THYAO")["kapanis"].to_numpy(dtype=float)
    y = np.log(k[-500:])
    yaz(f"THYAO: {len(y)} gün")

    for trend in ("t", "n"):
        for derece in [(0, 1, 0), (1, 1, 0), (0, 1, 1), (1, 1, 1)]:
            t = time.time()
            try:
                sonuc = ARIMA(y, order=derece, trend=trend).fit(method_kwargs={"maxiter": 50})
                yaz(f"ARIMA{derece} trend={trend}: {time.time() - t:6.2f} sn  (AIC {sonuc.aic:.1f})")
            except Exception as hata:
                yaz(f"ARIMA{derece} trend={trend}: HATA {hata}")

    yaz("Paralel işlem testi başlıyor (4 işlem)...")
    t = time.time()
    with ProcessPoolExecutor(max_workers=4) as havuz:
        sonuc = list(havuz.map(kare, range(8)))
    yaz(f"Paralel işlem testi tamam: {sonuc} ({time.time() - t:.1f} sn)")
    yaz("Bitti.")


if __name__ == "__main__":
    main()
