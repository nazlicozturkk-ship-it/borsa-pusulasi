# Hafta 1 Notları – Proje Altyapısı ve Şirket Listesi

Bu not, 1. haftada yapılanları ve hocanın sorabileceği sorulara verebileceğin cevapları
sade bir dille anlatır.

## Bu hafta ne yaptık?

1. **Geliştirme ortamı:** Python 3.12, VS Code, Git ve projeye özel bir sanal ortam (`venv`) kuruldu.
2. **Proje yapısı:** Kodlar görevlerine göre klasörlere ayrıldı (`src/veri`, `data`, `logs`, `docs`).
3. **Veritabanı:** SQLite veritabanı ve ilk tablo (`sirketler`) oluşturuldu.
4. **Şirket listesi:** Borsa İstanbul'daki tüm şirketler; kod, unvan, şehir, sektör ve
   BIST 30 / BIST 100 üyeliği bilgileriyle otomatik olarak çekildi.

## Dosyalar ne işe yarıyor?

| Dosya | Görevi |
|---|---|
| `config.py` | Tüm ayarların tek yerde durduğu dosya. Veritabanının adresi burada. |
| `src/veritabani.py` | Veritabanı tablolarını Python sınıfı olarak tanımlar, kaydetme/okuma fonksiyonlarını içerir. |
| `src/veri/sirket_listesi.py` | Şirket listesini internetten çekip veritabanına ve CSV'ye kaydeder. |
| `src/log_ayari.py` | Programın yaptıklarını `logs/` klasörüne kaydeder. |
| `kurulum.bat`, `1_sirket_listesi.bat` | Çift tıklayarak çalıştırma dosyaları. |

## Veriler nereden geliyor?

`borsapy` adlı açık kaynak bir Python kütüphanesi kullanıyoruz. Bu kütüphane:

- Şirket listesini **KAP**'tan (Kamuyu Aydınlatma Platformu) alır. KAP, Borsa İstanbul
  şirketlerinin resmi bildirim platformudur.
- Endeks üyeliklerini (BIST 30, BIST 100) ve fiyat verilerini **TradingView**'dan alır.

Sektör bilgisini iki adımda buluyoruz: önce tek bir sorguyla **TradingView**'dan tüm hisselerin
sektörünü çekiyoruz, orada bulunamayan şirketler için **KAP**'taki şirket sayfasına bakıyoruz.
İlk denemede İş Yatırım'ın tarama aracını kullanmıştık, ancak site sayfa yapısını değiştirdiği
için sektör listesi boş geldi. Bu yüzden kaynak değiştirildi. Dış kaynaklara bağlı projelerde
böyle değişikliklere karşı yedek kaynak kullanmak iyi bir uygulamadır.

## Olası hoca soruları

**Neden SQLite, neden PostgreSQL değil?**
SQLite kurulum gerektirmez ve geliştirme aşaması için yeterlidir. Kodu SQLAlchemy ile
yazdığımız için PostgreSQL'e geçmek `config.py` içinde tek satırı değiştirmek demektir.
Uygulama sunucuya yüklenirken (14. hafta) PostgreSQL'e geçilecek.

**SQLAlchemy nedir?**
Python sınıflarını veritabanı tablolarına dönüştüren bir kütüphanedir (ORM). SQL sorgusu
yazmadan veritabanıyla çalışmayı ve veritabanı türünü kolayca değiştirmeyi sağlar.

**Sanal ortam (venv) neden kullanıldı?**
Projenin kütüphaneleri bilgisayardaki diğer Python projelerinden ayrı tutulur. Böylece
sürüm çakışması olmaz ve proje başka bilgisayara `requirements.txt` ile aynen kurulabilir.

**Bazı şirketlerin sektörü neden boş?**
KAP listesinde hisse senedi dışındaki kodlar da var (örneğin aynı şirketin farklı menkul
kıymet kodları veya borsada işlem görmeyen şirketler). Bunların çoğu TradingView'da yok ve
KAP sayfalarında da sektör bilgisi bulunmuyor. 2. haftada fiyat verisi çekerken, işlem
görmeyen bu kodlar listeden ayıklanacak.

**Log dosyaları ne işe yarıyor?**
Program çalışırken her adımı zaman bilgisiyle bir dosyaya yazar. Hata olduğunda nerede
olduğunu bulmayı kolaylaştırır; yazılım projelerinde standart bir uygulamadır.

## Gelecek hafta (Hafta 2)

Bu listedeki tüm şirketler için 10 yıllık günlük fiyat verisinin (açılış, en yüksek,
en düşük, kapanış, hacim) toplu olarak çekilip veritabanına kaydedilmesi.
