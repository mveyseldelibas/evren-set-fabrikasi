"""Tarif: Türkiye Üniversite Kampüsü Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "universite_kampusu", "kurallar": [{'amenity': 'university'}, {'amenity': 'college'}, {'landuse': 'education'}], "en_az_alan_m2": 15000, "en_cok_alan_m2": 20000000},
]

TARIF = s2_osm.tarif_olustur(
    id="universite_kampusu", ad="Türkiye Üniversite Kampüsü Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde üniversite ve yüksekokul kampüslerinin (amenity=university/college, landuse=education) çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-universite-kampusu-seg-sentinel2-yolo11s-seg",
    sinirlar=["Kampüs sınırları OSM'de binaları ya da bütün arazi parçasını kapsayabilir; tutarsızdır.", 'Okul ve hastane kampüsleri ile karışabilir.'],
    hedef_pencere=700,
)
hazirla = partial(s2_osm.hazirla)
