"""Tarif: Türkiye Çayır ve Mera Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "cayir_mera", "kurallar": [{'landuse': 'meadow'}, {'natural': 'grassland'}], "en_az_alan_m2": 20000, "en_cok_alan_m2": 10000000},
]

TARIF = s2_osm.tarif_olustur(
    id="cayir_mera", ad="Türkiye Çayır ve Mera Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde çayır ve mera alanlarının (landuse=meadow, natural=grassland) çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-cayir-mera-seg-sentinel2-yolo11s-seg",
    sinirlar=['Mevsimle yeşil/kuru görünüm çok değişir.', "Mera ile nadastaki tarla 10 m'de karışabilir."],
    hedef_pencere=1000,
)
hazirla = partial(s2_osm.hazirla)
