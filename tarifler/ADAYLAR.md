# Aday açık karşılaştırma veri setleri (henüz kurulmadı)

Lisanslar 2026-11-25'te her kaydın resmî sayfasından okundu. "Kapıya uyar" sütunu, fabrikanın izin listesine
(CC0, PDDL, kamu malı, CC-BY-4.0, CC-BY-SA-4.0, ODbL) uyup uymadığını gösterir. Etiketsiz (kendi kendine öğrenme) setler
görüntü/etiket görevi gerektiren fabrikaya doğrudan uymaz; yine de listelendi.

| # | Veri seti | Kaynak | Lisans (sayfada yazan) | Boyut | Görev | Kapıya uyar |
|---|---|---|---|---|---|---|
| 1 | CloudSEN12 | https://huggingface.co/datasets/tacofoundation/cloudsen12 | CC0-1.0 | 248 GB | Sentinel-2 bulut/gölge anlamsal bölütleme (4 sınıf) | evet |
| 2 | HLS Burn Scars | https://huggingface.co/datasets/ibm-nasa-geospatial/hls_burn_scars | CC-BY-4.0 | 2,65 GB, 804 sahne 512x512 | yanık izi bölütleme | evet |
| 3 | HLS Çok Zamanlı Ürün Sınıflandırma | https://huggingface.co/datasets/ibm-nasa-geospatial/multi-temporal-crop-classification | CC-BY-4.0 | 11,8 GB, 3.854 parça | ürün türü bölütleme | evet |
| 4 | MARIDA (deniz çöpü arşivi) | https://zenodo.org/records/5151941 | CC-BY-4.0 | 1,2 GB sıkıştırılmış | zayıf denetimli piksel bölütleme (Sentinel-2) | evet |
| 5 | RarePlanes | https://registry.opendata.aws/rareplanes/ | CC-BY-SA-4.0 | gerçek: 253 sahne, 14.700 uçak; sentetik 50.000 görüntü | uydu görüntüsünde uçak tespiti | evet |
| 6 | EuroSAT | https://github.com/phelber/EuroSAT | MIT (+ Copernicus kullanım koşulları) | 27.000 görüntü, 64x64, 13 bant | arazi örtüsü sınıflandırma (10 sınıf) | hayır (MIT izin listesinde yok; elle karar) |
| 7 | FLAIR (IGN) | https://huggingface.co/datasets/IGNF/FLAIR | Etalab Açık Lisans 2.0 | 121 GB, 93.462 parça | hava görüntüsü arazi örtüsü bölütleme | hayır (Etalab 2.0 listede yok; CC-BY ile uyumlu, elle karar) |
| 8 | SSL4EO-S12 | https://huggingface.co/datasets/wangyi111/SSL4EO-S12 | CC-BY-4.0 | 1,59 TB | etiketsiz çok zamanlı Sentinel-1/2 (ön eğitim) | lisans evet, etiket yok |
| 9 | Major TOM Core-S2L2A | https://huggingface.co/datasets/Major-TOM/Core-S2L2A | CC-BY-SA-4.0 | 2,25 milyon parça, ~23 TB | etiketsiz küresel Sentinel-2 L2A | lisans evet, etiket yok |
| 10 | DROID-100 (LeRobot) | https://huggingface.co/datasets/lerobot/droid_100 | MIT (kartta) | 100 bölüm, 32.212 kare | robot manipülasyon gösterimleri | hayır (MIT listede yok; özgün DROID lisansı doğrulanamadı) |

## Doğrulanamayanlar (kuruma alınmadan önce lisansı resmî kaynaktan doğrulanmalı)

- Sen1Floods11 (https://github.com/cloudtostreet/Sen1Floods11): sayfa lisans yazmıyor; 14 GB, Sentinel-1 sel suyu bölütleme.
- Landslide4Sense (HF `ibm-nasa-geospatial/Landslide4sense`): kartta lisans yok; 8.590 parça, heyelan bölütleme.
- TACO (https://github.com/pedropro/TACO): depo kodu MIT; görüntü lisansı sayfada yok (görüntüler Flickr kaynaklı, tek tek lisanslı olabilir). Kurulmamalı.
- SpaceNet (AWS): "Çeşitli" lisans; her yarışma ayrı denetlenmeli.

## Elenenler

NC/ND lisanslular (LoveDA, OpenEarthMap, DeepGlobe yol, Mapillary Vistas, nuScenes, KITTI) kapı kuralı gereği alınmaz.
