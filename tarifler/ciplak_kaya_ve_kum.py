"""Tarif: Türkiye Çıplak Kaya ve Kum Alanı Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "ciplak_kaya", "kurallar": [{'natural': 'bare_rock'}], "en_az_alan_m2": 20000, "en_cok_alan_m2": 10000000},
    {"ad": "kum", "kurallar": [{'natural': 'sand'}], "en_az_alan_m2": 10000, "en_cok_alan_m2": 10000000},
]

TARIF = s2_osm.tarif_olustur(
    id="ciplak_kaya_ve_kum", ad="Türkiye Çıplak Kaya ve Kum Alanı Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde çıplak kaya (natural=bare_rock) ve kum (natural=sand) alanlarının çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-kaya-kum-seg-sentinel2-yolo11s-seg",
    sinirlar=['Kum sınıfı az örneklidir.', 'Kış tarihleri dışlansa da yüksek dağlarda kar kalabilir.'],
    hedef_pencere=1000,
)
hazirla = partial(s2_osm.hazirla)
