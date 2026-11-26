"""Tarif: Türkiye Kumsal (Plaj) Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "kumsal", "kurallar": [{'natural': 'beach'}], "en_az_alan_m2": 5000, "en_cok_alan_m2": 5000000},
]

TARIF = s2_osm.tarif_olustur(
    id="kumsal", ad="Türkiye Kumsal (Plaj) Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde kumsalların (natural=beach) çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-kumsal-seg-sentinel2-yolo11s-seg",
    sinirlar=["Dar kumsallar 10 m'de birkaç piksel genişliğindedir.", 'Deniz seviyesi ve dalga nedeniyle kıyı çizgisi tarihler arasında oynar.'],
    hedef_pencere=700,
)
hazirla = partial(s2_osm.hazirla)
