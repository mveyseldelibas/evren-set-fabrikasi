"""Tarif: Türkiye Sulak Alan Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "sulak_alan", "kurallar": [{'natural': 'wetland'}], "en_az_alan_m2": 20000, "en_cok_alan_m2": 10000000},
]

TARIF = s2_osm.tarif_olustur(
    id="sulak_alan", ad="Türkiye Sulak Alan Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde sulak alanların (natural=wetland) çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih. Mevsimsel su seviyesi değişimi görüntülere yansır.",
    siniflar=SINIFLAR, model_adi="tr-sulak-alan-seg-sentinel2-yolo11s-seg",
    sinirlar=['Sulak alan sınırı mevsimle değişir; maske tek bir (OSM) sınırı bütün tarihler için kullanır.', 'Sazlık, bataklık ve tuzlu bataklık ayrı sınıflanmadı.'],
    hedef_pencere=900,
)
hazirla = partial(s2_osm.hazirla)
