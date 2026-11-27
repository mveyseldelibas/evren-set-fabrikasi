"""Tarif: Türkiye Tarla Ürünü Segmentasyonu (kışlık tahıl, mısır, diğer) - Sentinel-2 2021 + ESA WorldCereal 2021."""
from functools import partial

from tarifler import s2_raster

SURUM = "https://github.com/mveyseldelibas/evren-set-fabrikasi/releases/download/etiket-v1"
KAROLAR = {"43134": [30.6664, 35.8, 44.9, 42.2], "43170": [25.6, 35.8, 35.3585, 42.2], "46171": [25.6, 36.0104, 37.9201, 42.2]}

SINIFLAR = [
    {"ad": "kislik_tahil", "tanim": "WorldCereal kışlık tahıl (buğday, arpa vb.) = 100"},
    {"ad": "misir", "tanim": "WorldCereal ana sezon mısır = 100"},
    {"ad": "diger_tarla", "tanim": "WorldCereal geçici ürün = 100, tahıl ve mısır değil"},
]

RASTER = {
    "sabit_karolar": [{"url": f"{SURUM}/worldcereal2021_tr_{k}.tif", "sinirlar": s} for k, s in KAROLAR.items()],
    "bos_deger": 255, "yil": 2021,
    "deger_sinif": {1: 0, 2: 1, 3: 2},
    "hedefli": True, "en_az_kapsama": 0.03, "aday_carpani": 1.6,
    "kaynak_adi": "ESA WorldCereal 2021 v100 (kışlık tahıl, ana sezon mısır ve geçici ürün haritaları birleştirildi)",
    "kaynak_satiri": "Etiket haritası: ESA WorldCereal 2021 v100 (10 m; kışlık tahıl, mısır, geçici ürün); görüntüler 2021 yılından",
    "dogruluk_notu": "Etiket ESA WorldCereal'in bir model ile ürettiği haritalardır, el ile denetlenmedi; haritanın kendi doğruluğu bu setin "
                     "üst sınırıdır. Birleştirmede öncelik: mısır > kışlık tahıl > diğer geçici ürün.",
}

TARIF = s2_raster.tarif_olustur(
    id="urun_turu_worldcereal",
    ad="Türkiye Tarla Ürünü Segmentasyonu (kışlık tahıl, mısır, diğer) - Sentinel-2 2021 + ESA WorldCereal",
    aciklama="Türkiye'nin tarım alanlarında Sentinel-2 L2A (10 m, 2021) görüntüleri ve ESA WorldCereal 2021 haritalarından türetilmiş "
             "3 sınıflı çokgen maskeleri: kışlık tahıl, ana sezon mısır ve diğer geçici ürünler. Ürün deseni ve rekolte izleme için.",
    siniflar=SINIFLAR, model_adi="tr-urun-turu-worldcereal-yolo11s-seg",
    sinirlar=["Kışlık tahıl temmuzda hasat edilir; sonbahar görüntüsünde aynı tarla anız ya da boş görünür (etiket yıl boyu aynıdır).",
              "Yazlık tahıl, şeker pancarı, ayçiçeği vb. 'diğer' sınıfında birleşir.",
              "Tarım dışı alanlar etiketsiz arka plandır.",
              "Etiketler model ürünüdür; küçük parsellerde karışma olabilir."],
    raster=RASTER,
    kaynaklar=[{"ad": "ESA WorldCereal 10 m 2021 v100 (Zenodo 7875105; Türkiye bölgeleri COG'a çevrildi)",
                "url": "https://zenodo.org/records/7875105",
                "lisans": "CC-BY-4.0; atıf: ESA WorldCereal consortium, Van Tricht vd. 2023, ESSD 15, 5491-5515"}],
    lisans="CC-BY-4.0", lisans_gorunen="CC BY 4.0 (ESA WorldCereal'den türetilmiş etiket; görüntü: Copernicus Sentinel)",
    hedef_pencere=900,
)
hazirla = partial(s2_raster.hazirla)
