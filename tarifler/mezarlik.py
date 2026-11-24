"""Tarif: Türkiye Mezarlık Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "mezarlik", "kurallar": [{'landuse': 'cemetery'}, {'amenity': 'grave_yard'}], "en_az_alan_m2": 8000, "en_cok_alan_m2": 3000000},
]

TARIF = s2_osm.tarif_olustur(
    id="mezarlik", ad="Türkiye Mezarlık Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde mezarlık alanlarının (landuse=cemetery, amenity=grave_yard) çokgen maskeleri; her konum için farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-mezarlik-seg-sentinel2-yolo11s-seg",
    sinirlar=["Küçük köy mezarlıkları 10 m'de birkaç pikseldir; 0,8 hektardan küçükler alınmadı.", 'Mezarlık ağaçlı parklara ve bahçelere spektral olarak benzeyebilir.'],
    hedef_pencere=900,
)
hazirla = partial(s2_osm.hazirla)
