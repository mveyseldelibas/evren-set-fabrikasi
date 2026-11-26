"""Tarif: Türkiye Konut Alanı Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "konut_alani", "kurallar": [{'landuse': 'residential'}], "en_az_alan_m2": 20000, "en_cok_alan_m2": 10000000},
]

TARIF = s2_osm.tarif_olustur(
    id="konut_alani", ad="Türkiye Konut Alanı Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde konut alanlarının (landuse=residential) çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-konut-alani-seg-sentinel2-yolo11s-seg",
    sinirlar=['Bina değil yerleşim dokusu etiketlidir; yollar ve bahçeler maskeye girer.', "Kırsal yerleşimlerin bir kısmı OSM'de çizilmemiştir (eksik etiket)."],
    hedef_pencere=1000,
)
hazirla = partial(s2_osm.hazirla)
