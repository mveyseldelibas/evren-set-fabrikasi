"""Tarif: Türkiye Çalılık (Maki) ve Funda Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "calilik", "kurallar": [{'natural': 'scrub'}], "en_az_alan_m2": 20000, "en_cok_alan_m2": 10000000},
    {"ad": "funda", "kurallar": [{'natural': 'heath'}], "en_az_alan_m2": 20000, "en_cok_alan_m2": 10000000},
]

TARIF = s2_osm.tarif_olustur(
    id="calilik_ve_funda", ad="Türkiye Çalılık (Maki) ve Funda Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde çalılık/maki (natural=scrub) ve fundalık (natural=heath) alanlarının çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-calilik-funda-seg-sentinel2-yolo11s-seg",
    sinirlar=['Çalılık ile funda arasındaki ayrım OSM katkıcısının yorumuna bağlıdır.', 'Yangın sonrası ya da yeni ağaçlandırılmış alanlar güncel olmayabilir.'],
    hedef_pencere=1000,
)
hazirla = partial(s2_osm.hazirla)
