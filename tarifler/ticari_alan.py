"""Tarif: Türkiye Ticari Alan ve Alışveriş Merkezi Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "ticari_alan", "kurallar": [{'landuse': 'retail'}, {'landuse': 'commercial'}, {'shop': 'mall'}], "en_az_alan_m2": 10000, "en_cok_alan_m2": 5000000},
]

TARIF = s2_osm.tarif_olustur(
    id="ticari_alan", ad="Türkiye Ticari Alan ve Alışveriş Merkezi Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde ticari alanların (landuse=retail/commercial) ve alışveriş merkezlerinin (shop=mall) çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-ticari-alan-seg-sentinel2-yolo11s-seg",
    sinirlar=["Ticari alan ile konut ya da sanayi dokusu 10 m'de benzer görünebilir.", 'Otoparklar ve çatı kaplamaları maskeye girer.'],
    hedef_pencere=800,
)
hazirla = partial(s2_osm.hazirla)
