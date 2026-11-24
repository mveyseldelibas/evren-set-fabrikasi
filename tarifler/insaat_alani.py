"""Tarif: Türkiye İnşaat Alanı Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "insaat_alani", "kurallar": [{'landuse': 'construction'}], "en_az_alan_m2": 6000, "en_cok_alan_m2": 5000000},
]

TARIF = s2_osm.tarif_olustur(
    id="insaat_alani", ad="Türkiye İnşaat Alanı Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde inşaat alanlarının (landuse=construction) çokgen maskeleri; farklı tarihlerde aynı alanın evreleri.",
    siniflar=SINIFLAR, model_adi="tr-insaat-alani-seg-sentinel2-yolo11s-seg",
    sinirlar=['OSM etiketi inşaatın bittiği tarihi bilmez; eski tarihlerde alan boş, yeni tarihlerde yerleşim olabilir.', 'Çok zamanlı görüntüler aynı etiketi paylaşır; bu etiket gürültüsü ölçüyü düşürür.'],
    hedef_pencere=700,
)
hazirla = partial(s2_osm.hazirla)
