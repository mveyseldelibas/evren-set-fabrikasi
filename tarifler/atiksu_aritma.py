"""Tarif: Türkiye Atık Su Arıtma Tesisi Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "atiksu_aritma", "kurallar": [{'man_made': 'wastewater_plant'}], "en_az_alan_m2": 5000, "en_cok_alan_m2": 3000000},
]

TARIF = s2_osm.tarif_olustur(
    id="atiksu_aritma", ad="Türkiye Atık Su Arıtma Tesisi Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde atık su arıtma tesislerinin (man_made=wastewater_plant) çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-atiksu-aritma-seg-sentinel2-yolo11s-seg",
    sinirlar=["Küçük tesisler 10 m'de birkaç pikseldir; havuzlar en belirgin işarettir.", 'OSM kapsaması belediyeden belediyeye değişir.'],
    hedef_pencere=600,
)
hazirla = partial(s2_osm.hazirla)
