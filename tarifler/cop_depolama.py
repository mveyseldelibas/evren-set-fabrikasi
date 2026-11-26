"""Tarif: Türkiye Katı Atık Depolama (Çöp Sahası) Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "cop_depolama", "kurallar": [{'landuse': 'landfill'}], "en_az_alan_m2": 10000, "en_cok_alan_m2": 10000000},
]

TARIF = s2_osm.tarif_olustur(
    id="cop_depolama", ad="Türkiye Katı Atık Depolama (Çöp Sahası) Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde katı atık depolama ve çöp sahalarının (landuse=landfill) çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-cop-depolama-seg-sentinel2-yolo11s-seg",
    sinirlar=['Kapatılmış ve rehabilite edilmiş sahalar etiketli kalmış olabilir.', 'Hafriyat döküm alanları da bu etiketle girilmiş olabilir.'],
    hedef_pencere=900,
)
hazirla = partial(s2_osm.hazirla)
