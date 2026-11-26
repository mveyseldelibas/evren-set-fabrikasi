"""Tarif: Türkiye Güneş Enerjisi Santrali Segmentasyonu - Sentinel-2 çok zamanlı (OSM)."""
from functools import partial

from tarifler import s2_osm

SINIFLAR = [
    {"ad": "gunes_santrali", "kurallar": [{"plant:source": "solar"}, {"generator:source": "solar"}], "en_az_alan_m2": 10000, "en_cok_alan_m2": 20000000},
]

TARIF = s2_osm.tarif_olustur(
    id="gunes_enerjisi", ad="Türkiye Güneş Enerjisi Santrali Segmentasyonu - Sentinel-2 çok zamanlı (OSM)",
    aciklama="Türkiye genelinde Sentinel-2 L2A (10 m) görüntülerinde yere kurulu güneş enerjisi santrallerinin (plant:source=solar, 1 hektardan büyük generator:source=solar) çokgen maskeleri; farklı mevsimlerden en çok 3 gerçek tarih.",
    siniflar=SINIFLAR, model_adi="tr-gunes-santrali-seg-sentinel2-yolo11s-seg",
    sinirlar=["Çatı üstü paneller 1 hektar eşiğinin altında kalır ve etiketlenmez.", "Kurulumu görüntü tarihinden sonra biten santraller boş arazi gibi görünebilir."],
    hedef_pencere=900,
)
hazirla = partial(s2_osm.hazirla)
