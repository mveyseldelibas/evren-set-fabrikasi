"""Tarif: Türkiye Hastane ve Okul Yerleşkesi Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "hastane", "kurallar": [{'amenity': 'hospital'}], "en_az_alan_m2": 10000, "en_cok_alan_m2": 3000000},
    {"ad": "okul", "kurallar": [{'amenity': 'school'}], "en_az_alan_m2": 10000, "en_cok_alan_m2": 1000000},
]

TARIF = s2_osm.tarif_olustur(
    id="saglik_egitim_yerleskesi", ad="Türkiye Hastane ve Okul Yerleşkesi Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde hastane (amenity=hospital) ve okul (amenity=school) yerleşkelerinin çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-hastane-okul-seg-sentinel2-yolo11s-seg",
    sinirlar=["10 m'de yerleşke dokusu görünür, işlev görünmez; sınıflar konum ve doku farkıyla ayrılır.", 'Üniversiteler ayrı bir sette (üniversite kampüsü).'],
    hedef_pencere=900,
)
hazirla = partial(s2_osm.hazirla)
