"""Tarif: Türkiye Arazi Örtüsü Segmentasyonu (10 sınıf) - Sentinel-2 2021 + ESA WorldCover 2021."""
from functools import partial

from tarifler import s2_raster

SINIFLAR = [
    {"ad": "agac", "tanim": "10 Ağaç örtüsü"},
    {"ad": "calilik", "tanim": "20 Çalılık"},
    {"ad": "cayir", "tanim": "30 Çayır / otsu örtü"},
    {"ad": "tarim", "tanim": "40 Ekili tarım alanı"},
    {"ad": "yapi", "tanim": "50 Yapılaşmış alan"},
    {"ad": "ciplak", "tanim": "60 Çıplak / seyrek bitkili alan"},
    {"ad": "kar_buz", "tanim": "70 Kalıcı kar ve buz"},
    {"ad": "su", "tanim": "80 Kalıcı su yüzeyi"},
    {"ad": "sulak_alan", "tanim": "90 Otsu sulak alan"},
    {"ad": "yosun_liken", "tanim": "100 Yosun ve liken"},
]

RASTER = {
    "koleksiyon": "esa-worldcover", "varlik": "map", "yil": 2021,
    "deger_sinif": {10: 0, 20: 1, 30: 2, 40: 3, 50: 4, 60: 5, 70: 6, 80: 7, 90: 8, 100: 9},
    "yaygin_siniflar": [0, 1, 2, 3, 5], "seyreltme": 0.6, "aday_carpani": 2.4,
    "kaynak_adi": "ESA WorldCover 2021 (v200)",
    "kaynak_satiri": "Etiket haritası: ESA WorldCover 2021 v200 (10 m); görüntüler 2021 yılından",
}

TARIF = s2_raster.tarif_olustur(
    id="arazi_ortusu_worldcover",
    ad="Türkiye Arazi Örtüsü Segmentasyonu (10 sınıf) - Sentinel-2 2021 + ESA WorldCover",
    aciklama="Türkiye genelinde rastgele konumlarda Sentinel-2 L2A (10 m, 2021) görüntüleri ve ESA WorldCover 2021 arazi örtüsü haritasından "
             "türetilmiş 10 sınıflı çokgen maskeleri (ağaç, çalılık, çayır, tarım, yapı, çıplak alan, kar-buz, su, sulak alan, yosun-liken). "
             "Her piksel etiketlidir; aynı yıldan farklı mevsimlerde en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-arazi-ortusu-worldcover-yolo11s-seg",
    sinirlar=["Etiket, ESA'nın bir model ile ürettiği haritadır (yaklaşık %75-80 genel doğruluk); el ile denetlenmedi.",
              "Çayır, çalılık ve seyrek bitkili alan sınıfları birbirine karışmaya yatkındır.",
              "Kar-buz, sulak alan ve yosun-liken sınıfları Türkiye'de çok az örneklidir.",
              "Etiket 2021 durumunu gösterir; görüntüler de yalnız 2021'den alındı."],
    raster=RASTER,
    kaynaklar=[{"ad": "ESA WorldCover 2021 v200 (Microsoft Planetary Computer `esa-worldcover`)", "url": "https://esa-worldcover.org/en",
                "lisans": "CC-BY-4.0; atıf: © ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium"}],
    lisans="CC-BY-4.0", lisans_gorunen="CC BY 4.0 (ESA WorldCover'dan türetilmiş etiket; görüntü: Copernicus Sentinel)",
    hedef_pencere=1000,
)
hazirla = partial(s2_raster.hazirla)
