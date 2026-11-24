"""Tarif: Türkiye Futbol Sahası Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "futbol_sahasi", "kurallar": [{'leisure': 'pitch', 'sport': 'soccer'}, {'leisure': 'pitch', 'sport': 'football'}], "en_az_alan_m2": 3500, "en_cok_alan_m2": 30000},
]

TARIF = s2_osm.tarif_olustur(
    id="futbol_sahasi", ad="Türkiye Futbol Sahası Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde futbol sahalarının (leisure=pitch, sport=soccer/football) çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-futbol-sahasi-seg-sentinel2-yolo11s-seg",
    sinirlar=["Bir saha 10 m'de yaklaşık 6x10 pikseldir; küçük halı sahalar ve çim/toprak ayrımı güvenilir değildir.", 'Düşük başarı beklenir; kapı geçilemezse model yayımlanmaz.'],
    hedef_pencere=1200,
)
hazirla = partial(s2_osm.hazirla)
