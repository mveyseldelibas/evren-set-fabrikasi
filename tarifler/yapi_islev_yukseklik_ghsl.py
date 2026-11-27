"""Tarif: Türkiye Yapı İşlevi ve Yükseklik Sınıfı Segmentasyonu - Sentinel-2 + JRC GHSL GHS-BUILT-C (MSZ 2018)."""
from functools import partial

from tarifler import s2_raster

SURUM = "https://github.com/mveyseldelibas/evren-set-fabrikasi/releases/download/etiket-v1"
KAROLAR = {"R4_C21": [23.485, 41.894, 39.541, 51.214], "R4_C22": [35.473, 41.894, 52.904, 51.214],
           "R5_C21": [21.944, 33.928, 35.473, 41.894], "R5_C22": [32.94, 33.061, 47.461, 41.894],
           "R5_C23": [44.073, 33.061, 59.449, 41.894]}

SINIFLAR = [
    {"ad": "konut_alcak", "tanim": "11-12 Konut, yükseklik 6 m'ye kadar"},
    {"ad": "konut_orta", "tanim": "13 Konut, 6-15 m"},
    {"ad": "konut_yuksek", "tanim": "14-15 Konut, 15 m'den yüksek"},
    {"ad": "konut_disi_alcak", "tanim": "21-22 Konut dışı (sanayi, ticaret, kamu), 6 m'ye kadar"},
    {"ad": "konut_disi_yuksek", "tanim": "23-25 Konut dışı, 6 m'den yüksek"},
]

RASTER = {
    "sabit_karolar": [{"url": f"{SURUM}/ghsl_msz2018_{k}.tif", "sinirlar": s} for k, s in KAROLAR.items()],
    "bos_deger": 255, "yil": 2018, "goruntu_yili": 2019,
    "deger_sinif": {11: 0, 12: 0, 13: 1, 14: 2, 15: 2, 21: 3, 22: 3, 23: 4, 24: 4, 25: 4},
    "hedefli": True, "en_az_kapsama": 0.01, "aday_carpani": 1.6,
    "kaynak_adi": "JRC GHSL GHS-BUILT-C MSZ (2018, 10 m, R2023A)",
    "kaynak_satiri": "Etiket haritası: JRC GHSL GHS-BUILT-C MSZ E2018 R2023A (10 m); görüntüler 2019 yılından",
    "dogruluk_notu": "Etiket JRC'nin uydu verisinden ürettiği bir haritadır (yapı işlevi ve yükseklik sınıfı), el ile denetlenmedi; "
                     "haritanın kendi doğruluğu bu setin üst sınırıdır. 10 m görüntüde yükseklik doğrudan görünmez, gölge ve doku ile sezilir.",
}

TARIF = s2_raster.tarif_olustur(
    id="yapi_islev_yukseklik_ghsl",
    ad="Türkiye Yapı İşlevi ve Yükseklik Sınıfı Segmentasyonu - Sentinel-2 + JRC GHSL (2018)",
    aciklama="Türkiye'deki yerleşim alanlarında Sentinel-2 L2A (10 m) görüntüleri ve JRC GHSL GHS-BUILT-C (2018) haritasından türetilmiş "
             "5 sınıflı çokgen maskeleri: alçak/orta/yüksek konut ve alçak/yüksek konut dışı yapı alanları. Kentsel doku, yoğunluk ve "
             "deprem riski çalışmalarında ön tarama için.",
    siniflar=SINIFLAR, model_adi="tr-yapi-islev-yukseklik-ghsl-yolo11s-seg",
    sinirlar=["Tek tek binalar değil 10 m'lik yapı hücreleri etiketlidir.",
              "Yükseklik sınıfı GHSL'nin tahminidir; 10 m'de yükseklik doğrudan görülmez.",
              "Etiket 2018, görüntüler 2019 (Sentinel-2 L2A arşivi 2019'dan başlar); arada yapılan binalar etiketsiz kalabilir.",
              "Açık alanlar (yol, yeşil alan, su) etiketsiz arka plandır.",
              "Konut dışı ve yüksek konut sınıfları az örneklidir."],
    raster=RASTER,
    kaynaklar=[{"ad": "JRC GHSL GHS-BUILT-C MSZ E2018 R2023A (Türkiye karoları COG'a çevrildi)",
                "url": "https://human-settlement.emergency.copernicus.eu/",
                "lisans": "CC-BY-4.0; (c) European Union, 1995-2026"}],
    lisans="CC-BY-4.0", lisans_gorunen="CC BY 4.0 (JRC GHSL'den türetilmiş etiket; görüntü: Copernicus Sentinel)",
    hedef_pencere=900,
)
hazirla = partial(s2_raster.hazirla)
