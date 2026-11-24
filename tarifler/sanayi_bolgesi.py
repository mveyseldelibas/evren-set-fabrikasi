"""Tarif: Türkiye Sanayi Bölgesi Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "sanayi_bolgesi", "kurallar": [{'landuse': 'industrial'}], "en_az_alan_m2": 40000, "en_cok_alan_m2": 6000000},
]

TARIF = s2_osm.tarif_olustur(
    id="sanayi_bolgesi", ad="Türkiye Sanayi Bölgesi Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) gerçek renk görüntülerinde sanayi bölgelerinin (OpenStreetMap landuse=industrial) çokgen maskeleri; her konum için farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-sanayi-bolgesi-seg-sentinel2-yolo11s-seg",
    sinirlar=['Organize sanayi bölgeleri ile küçük sanayi siteleri aynı sınıftadır; depo, lojistik ve fabrika ayrımı yoktur.', "Sanayi çokgenlerinin sınırı OSM'de sık sık gevşek çizilir; kenar doğruluğu sınırlıdır."],
    hedef_pencere=900,
)
hazirla = partial(s2_osm.hazirla)
