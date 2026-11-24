"""Tarif: Türkiye Hobi Bahçesi ve Bostan Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "hobi_bahcesi", "kurallar": [{'landuse': 'allotments'}], "en_az_alan_m2": 8000, "en_cok_alan_m2": 2000000},
]

TARIF = s2_osm.tarif_olustur(
    id="hobi_bahcesi", ad="Türkiye Hobi Bahçesi ve Bostan Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde hobi bahçesi ve bostan alanlarının (landuse=allotments) çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-hobi-bahcesi-seg-sentinel2-yolo11s-seg",
    sinirlar=["Hobi bahçeleri kent kenarında küçük parsellerden oluşur; 10 m'de çevre tarlalarla karışabilir."],
    hedef_pencere=700,
)
hazirla = partial(s2_osm.hazirla)
