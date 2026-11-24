"""Tarif: Türkiye Balık Çiftliği Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "balik_ciftligi", "kurallar": [{'landuse': 'aquaculture'}, {'man_made': 'fish_farm'}, {'aquaculture': '*'}], "en_az_alan_m2": 1500, "en_cok_alan_m2": 2000000},
]

TARIF = s2_osm.tarif_olustur(
    id="balik_ciftligi", ad="Türkiye Balık Çiftliği Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye kıyı ve iç sularında Sentinel-2 L2A (10 m) görüntülerinde balık çiftliklerinin (landuse=aquaculture, man_made=fish_farm) çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-balik-ciftligi-seg-sentinel2-yolo11s-seg",
    sinirlar=['Deniz kafesleri küçüktür (birkaç piksel); su üstündeki parlak yansımalar kafesle karışabilir.'],
    hedef_pencere=600,
)
hazirla = partial(s2_osm.hazirla)
