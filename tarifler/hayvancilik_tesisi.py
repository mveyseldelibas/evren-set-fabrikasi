"""Tarif: Türkiye Hayvancılık Tesisi (Çiftlik Avlusu) Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "hayvancilik_tesisi", "kurallar": [{'landuse': 'farmyard'}], "en_az_alan_m2": 8000, "en_cok_alan_m2": 2000000},
]

TARIF = s2_osm.tarif_olustur(
    id="hayvancilik_tesisi", ad="Türkiye Hayvancılık Tesisi (Çiftlik Avlusu) Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde çiftlik avlusu ve hayvancılık tesislerinin (landuse=farmyard) çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-hayvancilik-seg-sentinel2-yolo11s-seg",
    sinirlar=['Ahır, ağıl ve köy avluları aynı sınıftadır.', "Küçük tesisler 10 m'de birkaç pikseldir."],
    hedef_pencere=800,
)
hazirla = partial(s2_osm.hazirla)
