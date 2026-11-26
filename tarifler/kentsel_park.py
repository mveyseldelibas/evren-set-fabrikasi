"""Tarif: Türkiye Kentsel Park Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "park", "kurallar": [{'leisure': 'park'}], "en_az_alan_m2": 10000, "en_cok_alan_m2": 3000000},
]

TARIF = s2_osm.tarif_olustur(
    id="kentsel_park", ad="Türkiye Kentsel Park Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde kentsel parkların (leisure=park) çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-kentsel-park-seg-sentinel2-yolo11s-seg",
    sinirlar=['10 m çözünürlükte küçük parklar birkaç pikseldir; yalnız 1 hektardan büyükler alındı.', 'Park içindeki sert zeminler (meydan, otopark) maskeye girebilir.'],
    hedef_pencere=900,
)
hazirla = partial(s2_osm.hazirla)
