"""Tarif: Türkiye Zeytinlik Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "zeytinlik", "kurallar": [{'trees': 'olive_trees'}, {'crop': 'olive'}], "en_az_alan_m2": 10000, "en_cok_alan_m2": 5000000},
]

TARIF = s2_osm.tarif_olustur(
    id="zeytinlik", ad="Türkiye Zeytinlik Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde zeytinlik parsellerinin (trees=olive_trees ya da crop=olive) çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-zeytinlik-seg-sentinel2-yolo11s-seg",
    sinirlar=["Zeytinlik, makilik ve seyrek ormandan 10 m'de zor ayrılır.", 'Yalnız zeytin olarak etiketlenmiş parseller vardır; etiketsiz zeytinlikler arka plan görünür.'],
    hedef_pencere=700,
)
hazirla = partial(s2_osm.hazirla)
