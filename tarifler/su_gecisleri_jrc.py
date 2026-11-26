"""Tarif: Türkiye Yüzey Suyu Değişimi Segmentasyonu (kalıcı, mevsimlik, yeni oluşan, kaybolan su) - Sentinel-2 + JRC GSW."""
from functools import partial

from tarifler import s2_raster

SINIFLAR = [
    {"ad": "kalici_su", "tanim": "1 Kalıcı su + 7 Mevsimlikten kalıcıya dönen su (JRC GSW geçişleri, 1984-2020)"},
    {"ad": "mevsimlik_su", "tanim": "4 Mevsimlik su + 8 Kalıcıdan mevsimliğe dönen su"},
    {"ad": "yeni_su", "tanim": "2 Yeni kalıcı su + 5 Yeni mevsimlik su (ör. yeni baraj gölleri)"},
    {"ad": "kaybolan_su", "tanim": "3 Kaybolan kalıcı su + 6 Kaybolan mevsimlik su (kuruyan göl ve sulak alanlar)"},
]

RASTER = {
    "koleksiyon": "jrc-gsw", "varlik": "transitions", "yil": 2020,
    "deger_sinif": {1: 0, 7: 0, 4: 1, 8: 1, 2: 2, 5: 2, 3: 3, 6: 3},
    "hedefli": True, "en_az_kapsama": 0.005, "aday_carpani": 1.6,
    "kaynak_adi": "JRC Global Surface Water v1.3 su geçişleri (1984-2020, 30 m)",
    "kaynak_satiri": "Etiket haritası: JRC Global Surface Water v1.3 'transitions' katmanı (1984-2020, 30 m); görüntüler 2020 yılından",
}

TARIF = s2_raster.tarif_olustur(
    id="su_gecisleri_jrc",
    ad="Türkiye Yüzey Suyu Değişimi Segmentasyonu (kalıcı, mevsimlik, yeni, kaybolan) - Sentinel-2 + JRC GSW",
    aciklama="Türkiye'deki göl, baraj ve sulak alanlarda Sentinel-2 L2A (10 m, 2020) görüntüleri ve JRC Global Surface Water 1984-2020 "
             "su geçişi haritasından türetilmiş 4 sınıflı çokgen maskeleri: kalıcı su, mevsimlik su, yeni oluşan su (ör. yeni baraj gölleri) "
             "ve kaybolan su (kuruyan göl ve sulak alan tabanları). Kuraklık ve su kaynağı izleme için.",
    siniflar=SINIFLAR, model_adi="tr-su-degisimi-jrc-yolo11s-seg",
    sinirlar=["Etiket 30 m Landsat tabanlı bir haritadır; 10 m görüntüde kıyı çizgisi kademeli görünür.",
              "'Kaybolan su' 1984-1999 ile 2000-2020 dönemlerinin karşılaştırmasıdır; 2020 görüntüsünde bu alanlar kara olarak görünür.",
              "Etiketsiz pikseller su olmayan arka plandır (her yer etiketli değildir).",
              "Etiket bir algoritmanın ürünüdür, el ile denetlenmedi."],
    raster=RASTER,
    kaynaklar=[{"ad": "EC JRC / Google, Global Surface Water v1.3 (Microsoft Planetary Computer `jrc-gsw`); Pekel vd. 2016, Nature 540, 418-422",
                "url": "https://global-surface-water.appspot.com/",
                "lisans": "Copernicus programı: ücretsiz, kullanım kısıtı yok, atıf zorunlu ('Source: EC JRC/Google')"}],
    lisans="CC-BY-4.0", lisans_gorunen="CC BY 4.0 (JRC GSW'den türetilmiş etiket, atıf: Source: EC JRC/Google; görüntü: Copernicus Sentinel)",
    hedef_pencere=900,
)
hazirla = partial(s2_raster.hazirla)
