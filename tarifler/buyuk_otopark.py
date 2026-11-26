"""Tarif: Türkiye Büyük Otopark Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "otopark", "kurallar": [{'amenity': 'parking'}], "en_az_alan_m2": 10000, "en_cok_alan_m2": 1000000},
]

TARIF = s2_osm.tarif_olustur(
    id="buyuk_otopark", ad="Türkiye Büyük Otopark Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde 1 hektardan büyük açık otoparkların (amenity=parking) çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-buyuk-otopark-seg-sentinel2-yolo11s-seg",
    sinirlar=['Otoparkın dolu ya da boş olması tarihe göre değişir.', 'Katlı otoparklar bina olarak görünür.'],
    hedef_pencere=700,
)
hazirla = partial(s2_osm.hazirla)
