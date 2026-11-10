"""
Web uygulamasını başlatır (6_web_uygulamasi.bat bu dosyayı çalıştırır).

- Boş bir port bulur (8000 doluysa 8001, 8002 ... dener).
- Sunucu gerçekten hazır olduğunda tarayıcıyı açar.
- Tüm mesajları hem ekrana hem logs/web.log dosyasına yazar; bir hata olursa
  ayrıntısı bu dosyada kalır.
"""

import socket
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser

from config import LOG_KLASORU

HOST = "127.0.0.1"


class IkiYere:
    """Yazılanları hem ekrana hem dosyaya yazar."""

    def __init__(self, ekran, dosya):
        self.ekran, self.dosya = ekran, dosya

    def write(self, metin):
        self.ekran.write(metin)
        self.dosya.write(metin)
        self.dosya.flush()

    def flush(self):
        self.ekran.flush()
        self.dosya.flush()

    def isatty(self):
        return False


def bos_port(baslangic: int = 8000) -> int:
    for port in range(baslangic, baslangic + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((HOST, port)) != 0:
                return port
    raise RuntimeError("8000-8019 arasında boş port bulunamadı.")


def hazir_olunca_ac(adres: str) -> None:
    """Sunucu cevap verene kadar (en fazla 2 dakika) bekler, sonra tarayıcıyı açar."""
    for _ in range(240):
        try:
            urllib.request.urlopen(adres + "/api/ara?q=a", timeout=2)
            print(f"\nUygulama hazır, tarayıcı açılıyor: {adres}\n", flush=True)
            webbrowser.open(adres)
            return
        except Exception:
            time.sleep(0.5)
    print("\nUygulama 2 dakikada açılmadı. Ayrıntılar logs/web.log dosyasında.\n", flush=True)


def main() -> None:
    kayit = open(LOG_KLASORU / "web.log", "w", encoding="utf-8")
    sys.stdout = IkiYere(sys.__stdout__, kayit)
    sys.stderr = IkiYere(sys.__stderr__, kayit)

    try:
        print("Kütüphaneler yükleniyor (ilk açılışta 10-20 saniye sürebilir)...", flush=True)
        import uvicorn

        from src.web.app import app  # hata varsa burada görünür

        port = bos_port()
        adres = f"http://{HOST}:{port}"
        print(f"Sunucu başlatılıyor: {adres}", flush=True)
        threading.Thread(target=hazir_olunca_ac, args=(adres,), daemon=True).start()
        uvicorn.run(app, host=HOST, port=port, log_level="info")
    except Exception:
        print("\nHATA: Uygulama başlatılamadı.\n", flush=True)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
