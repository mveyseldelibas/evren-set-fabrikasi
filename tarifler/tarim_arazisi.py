"""Tarif: Türkiye Tarım Arazisi (Tarla) Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "tarla", "kurallar": [{'landuse': 'farmland'}], "en_az_alan_m2": 20000, "en_cok_alan_m2": 5000000},
]

TARIF = s2_osm.tarif_olustur(
    id="tarim_arazisi", ad="Türkiye Tarım Arazisi (Tarla) Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde tarla parsellerinin (landuse=farmland) çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-tarla-seg-sentinel2-yolo11s-seg",
    sinirlar=['Ürün türü ayrılmadı; aynı tarla farklı tarihlerde ekili ya da nadasta görünebilir.', 'OSM tarla çokgenleri bazen birden çok parseli tek çokgende birleştirir.'],
    hedef_pencere=1000,
)
hazirla = partial(s2_osm.hazirla)
