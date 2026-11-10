"""
Kayıt (log) ayarları.

Programın yaptığı her şey hem ekrana hem de logs/ klasöründeki bir dosyaya yazılır.
Böylece bir hata çıktığında ne olduğunu sonradan dosyadan okuyabiliriz.
"""

import logging
import sys

from config import LOG_KLASORU


def logger_olustur(ad: str) -> logging.Logger:
    """Verilen ad için ekrana ve logs/<ad>.log dosyasına yazan bir logger döndürür."""
    logger = logging.getLogger(ad)
    if logger.handlers:  # daha önce ayarlandıysa tekrar ayarlama
        return logger

    logger.setLevel(logging.INFO)
    bicim = logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", "%Y-%m-%d %H:%M:%S")

    dosya = logging.FileHandler(LOG_KLASORU / f"{ad}.log", mode="w", encoding="utf-8")
    dosya.setFormatter(bicim)
    logger.addHandler(dosya)

    ekran = logging.StreamHandler(sys.stdout)
    ekran.setFormatter(bicim)
    logger.addHandler(ekran)

    return logger
