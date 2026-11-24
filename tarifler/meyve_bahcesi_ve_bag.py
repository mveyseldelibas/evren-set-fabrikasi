"""Tarif: Türkiye Meyve Bahçesi ve Bağ Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "meyve_bahcesi", "kurallar": [{'landuse': 'orchard'}], "en_az_alan_m2": 15000, "en_cok_alan_m2": 5000000},
    {"ad": "bag", "kurallar": [{'landuse': 'vineyard'}], "en_az_alan_m2": 15000, "en_cok_alan_m2": 5000000},
]

TARIF = s2_osm.tarif_olustur(
    id="meyve_bahcesi_ve_bag", ad="Türkiye Meyve Bahçesi ve Bağ Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde meyve bahçesi ve bağ parsellerinin (landuse=orchard, landuse=vineyard) çokgen maskeleri; iki sınıf, farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-bahce-bag-seg-sentinel2-yolo11s-seg",
    sinirlar=["Bahçe ile bağ ayrımı 10 m'de zordur (ekim deseni görünmeyebilir); sınıflar birbirine karışabilir.", 'Zeytinlik ve fındıklık da `meyve_bahcesi` altındadır; tür ayrımı yoktur.'],
    hedef_pencere=1000,
)
hazirla = partial(s2_osm.hazirla)
