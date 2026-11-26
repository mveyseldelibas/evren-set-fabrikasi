"""Tarif: Türkiye Havalimanı, Demiryolu ve Enerji Tesisi Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "havalimani", "kurallar": [{'aeroway': 'aerodrome'}], "en_az_alan_m2": 50000, "en_cok_alan_m2": 50000000},
    {"ad": "demiryolu_alani", "kurallar": [{'landuse': 'railway'}], "en_az_alan_m2": 10000, "en_cok_alan_m2": 10000000},
    {"ad": "trafo_merkezi", "kurallar": [{'power': 'substation'}], "en_az_alan_m2": 5000, "en_cok_alan_m2": 1000000},
    {"ad": "termik_santral", "kurallar": [{'plant:source': 'coal'}, {'plant:source': 'gas'}], "en_az_alan_m2": 10000, "en_cok_alan_m2": 20000000},
]

TARIF = s2_osm.tarif_olustur(
    id="ulasim_enerji_altyapisi", ad="Türkiye Havalimanı, Demiryolu ve Enerji Tesisi Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde havalimanlarının, demiryolu alanlarının, trafo merkezlerinin ve termik santrallerin çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-ulasim-enerji-seg-sentinel2-yolo11s-seg",
    sinirlar=['Askerî havalimanları ve hassas tesisler her zaman dışlanır.', 'Sınıflar dengesizdir: termik santral ve havalimanı az örneklidir.'],
    hedef_pencere=900,
)
hazirla = partial(s2_osm.hazirla)
