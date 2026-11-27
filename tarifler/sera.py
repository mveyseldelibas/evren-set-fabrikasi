"""Tarif: Türkiye Sera Alanı Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "sera", "kurallar": [{"landuse": "greenhouse_horticulture"}], "en_az_alan_m2": 2000, "en_cok_alan_m2": 5000000},
]

TARIF = s2_osm.tarif_olustur(
    id="sera", ad="Türkiye Sera Alanı Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde örtü altı tarım (sera) alanlarının (landuse=greenhouse_horticulture) çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-sera-seg-sentinel2-yolo11s-seg",
    sinirlar=["Tek tek sera binaları değil sera kümeleri etiketlidir; aradaki yollar maskeye girebilir.", "OSM kapsaması Antalya ve Mersin kıyısında yoğun, iç bölgelerde seyrektir."],
    hedef_pencere=800,
)
hazirla = partial(s2_osm.hazirla)
