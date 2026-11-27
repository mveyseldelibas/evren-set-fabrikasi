"""Tarif: Türkiye Maden ve Taş Ocağı Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "maden_ocagi", "kurallar": [{"landuse": "quarry"}], "en_az_alan_m2": 10000, "en_cok_alan_m2": 20000000},
]

TARIF = s2_osm.tarif_olustur(
    id="maden_ocagi", ad="Türkiye Maden ve Taş Ocağı Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde açık maden ve taş ocaklarının (landuse=quarry) çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-maden-ocagi-seg-sentinel2-yolo11s-seg",
    sinirlar=["Ocak sınırları hızlı değişir; OSM çizimi ile görüntü tarihi arasında genişleme farkı olabilir.", "Çıplak kaya, kum ve inşaat alanıyla karışabilir."],
    hedef_pencere=550,
)
hazirla = partial(s2_osm.hazirla)
