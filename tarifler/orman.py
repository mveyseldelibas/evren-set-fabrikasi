"""Tarif: Türkiye Orman Alanı Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "orman", "kurallar": [{'landuse': 'forest'}, {'natural': 'wood'}], "en_az_alan_m2": 50000, "en_cok_alan_m2": 20000000},
]

TARIF = s2_osm.tarif_olustur(
    id="orman", ad="Türkiye Orman Alanı Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde orman alanlarının (landuse=forest, natural=wood) çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-orman-seg-sentinel2-yolo11s-seg",
    sinirlar=['Ağaç türü (iğne/geniş yaprak) ayrılmadı.', 'OSM orman sınırları çoğu yerde kaba çizilmiştir; açıklıklar ve yeni kesimler maskede kalabilir.'],
    hedef_pencere=1000,
)
hazirla = partial(s2_osm.hazirla)
