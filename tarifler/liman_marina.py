"""Tarif: Türkiye Liman ve Marina Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "liman", "kurallar": [{'landuse': 'port'}, {'harbour': 'yes'}], "en_az_alan_m2": 10000, "en_cok_alan_m2": 5000000},
    {"ad": "marina", "kurallar": [{'leisure': 'marina'}], "en_az_alan_m2": 5000, "en_cok_alan_m2": 5000000},
]

TARIF = s2_osm.tarif_olustur(
    id="liman_marina", ad="Türkiye Liman ve Marina Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye kıyılarında Sentinel-2 L2A (10 m) görüntülerinde liman (landuse=port) ve marina (leisure=marina) alanlarının çokgen maskeleri; iki sınıf, farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-liman-marina-seg-sentinel2-yolo11s-seg",
    sinirlar=["Liman ile marina arasındaki sınır OSM'de tutarsız çizilir.", 'Kıyı çizgisindeki dar alanlar su ile karışabilir.'],
    hedef_pencere=600,
)
hazirla = partial(s2_osm.hazirla)
