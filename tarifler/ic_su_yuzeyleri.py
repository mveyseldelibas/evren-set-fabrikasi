"""Tarif: Türkiye İç Su Yüzeyleri Segmentasyonu (baraj gölü, doğal göl, gölet, nehir) - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "baraj_golu", "kurallar": [{'water': 'reservoir'}, {'landuse': 'reservoir'}, {'landuse': 'basin'}], "en_az_alan_m2": 10000, "en_cok_alan_m2": 200000000},
    {"ad": "dogal_gol", "kurallar": [{'water': 'lake'}], "en_az_alan_m2": 10000, "en_cok_alan_m2": 2000000000},
    {"ad": "golet", "kurallar": [{'water': 'pond'}], "en_az_alan_m2": 5000, "en_cok_alan_m2": 1000000},
    {"ad": "nehir", "kurallar": [{'water': 'river'}, {'waterway': 'riverbank'}], "en_az_alan_m2": 10000, "en_cok_alan_m2": 50000000},
]

TARIF = s2_osm.tarif_olustur(
    id="ic_su_yuzeyleri", ad="Türkiye İç Su Yüzeyleri Segmentasyonu (baraj gölü, doğal göl, gölet, nehir) - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde baraj göllerinin, doğal göllerin, göletlerin ve geniş nehir yataklarının çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-ic-su-seg-sentinel2-yolo11s-seg",
    sinirlar=['Su seviyesi mevsimle değişir; maske tek bir OSM kıyı çizgisidir.', 'Baraj gölü ile doğal göl ayrımı OSM etiketine dayanır, görüntüden her zaman anlaşılmaz.'],
    hedef_pencere=1000,
)
hazirla = partial(s2_osm.hazirla)
