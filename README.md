# Küme fabrikası

Her gün GitHub Actions üzerinde çalışan, **gerçek ve yasal kaynaklı** görüntü veri setleri ile bunlarla eğitilmiş modeller üreten
ve kalite kapılarını geçenleri otomatik yayımlayan bir hat. Bilgisayar kapalı olsa da çalışır.

Hedef platform: EVREN (https://evren.ssyz.org.tr). Kod lisansı: MIT. Ürettiği veri setlerinin lisansı kaynaklarına bağlıdır
(OpenStreetMap kullanan setler ODbL 1.0, görüntü: Copernicus Sentinel verisi).

## Her koşuda ne olur

1. `egitimde` durumundaki işler izlenir. Biten işin README'si ve model kartı (sınıf bazlı ölçülerle) yazılır, model önce **özel** tutulur.
2. **Kapılar:** veri seti öğe sayısı >= 1000; başarı ölçüsü >= 0,50 (segmentasyon ve tespitte mAP50, sınıflandırmada top-1);
   lisans izin listesinde (CC0, PDDL, kamu malı, CC-BY-4.0, CC-BY-SA-4.0, ODbL; NC/ND asla); README ve kart dolu.
   Hepsi geçerse önce veri seti, sonra model açılır. Açılma sırasında ona bağlı **eski** bir model kendiliğinden açılırsa yeniden gizlenir
   (yalnız bu açılıştan doğan fark gizlenir; önceden açık olanlara dokunulmaz). Geçemeyen `zayif` olur ve gizli kalır.
3. Bugün başlatılan yeni iş sayısı `GUNLUK_YENI`'den (iş akışında 6, en çok 6) azsa önce günün `bekliyor` tarifleri kurulur: veri üretilir, ÖZEL yüklenir,
   öğe sayısı ve bölüm ayarı doğrulanır, sürüm oluşturulur, eğitim kuru koşusu 30 CR'yi (tahmin x 2,4) aşarsa iptal edilir, değilse eğitim başlar.
4. **Kazanç koruması:** ZIP yüklemeden önce `/billing/earning/overview` okunur; bugünkü CR > 60 ve bugünkü etiket sayısı < 300 ise (platform sayacı 300'de durur) yükleme yarına bırakılır.
5. **CR penceresi:** günlük 100 CR tavanı 00:00 TSİ'de sıfırlanır ve dolunca etiket puanı da durur. ZIP içe aktarma ve yayım gibi CR kazandıran
   adımlar yalnız 23:25-23:58 TSİ (20:25-20:58 UTC) penceresinde yapılır; bugünkü kazanç zaten >= 100 ise her an serbesttir. Veri önce kurulur,
   sonra pencere beklenir (en çok 4 saat); pencere kaçarsa yükleme ve yayım ertesi geceye kalır (durum değişmez). Günün setleri önce topluca kurulur; koşu ~18:30 TSİ'de
   (15:30 UTC) başlar; dış rutin tetiği ve cron yedeği bu saattedir.
6. Günlük sert sınırlar: en çok 10 veri seti yayımı, 10 model yayımı, 10 yeni yükleme. Yükleme penceresi 23:25-23:58 TSİ; günün etiket sayacı 300 ise 20:30 TSİ'de açılır.
7. `kuyruk.json`, `durum/ozet.json`, `durum/bildirim.json` yazılır ve çakışmasız (alıp-birleştir-yeniden dene) gönderilir. Başka hiçbir dosya commit edilmez.

## Dosyalar

```
fabrika.py            günlük koşu; --kuru ağda yazma yapmadan pilot kurar
cekirdek/             API istemcisi, kapılar, kuyruk durum makinesi, durum/gönderim, README ve kart yazımı, eğitim gövdesi
tarifler/             tarif modülleri (s2_osm.py genel motor, osm_cikar.py OSM çıkarımı), ADAYLAR.md
kuyruk.json           tarif sırası ve durumları
durum/                ozet.json (son koşu, yayımlananlar, kalan tarif), bildirim.json (Telegram için yeni mesajlar)
tetik/                dış rutinin her gece dosya ittiği klasör (push tetikler)
tests/                kapı, kuyruk ve sahte API ile yayım yolu testleri
.github/workflows/    fabrika.yml
```

Durum makinesi: `bekliyor -> yuklendi -> egitimde -> yayimlandi | zayif | hata`.

## Kurulum

1. Depoda `Settings > Secrets and variables > Actions` altına **`EVREN_PLATFORM_KEY`** sırrını ekleyin. Başka sır gerekmez
   (Sentinel-2 verisi anahtarsız; OpenStreetMap dökümü herkese açık).
2. Dış rutin gece `tetik/<tarih>.txt` dosyasını `main`'e iterse koşu başlar; cron (19:00 UTC = 22:00 TSİ) yedektir. Elle: Actions > fabrika > Run workflow.
3. `durum/bildirim.json` içindeki `mesajlar` o koşunun yeni Türkçe mesajlarıdır (yayımlandı, zayıf, hata, kuyruk azaldı); `gecmis` tekilleştirme içindir (`id` alanı).

## Yerel kullanım

```
set PYTHONIOENCODING=utf-8
python -P -m unittest discover -s tests
python -P fabrika.py --kuru --pilot 12          # ağda yazma yok, ilk tarifin küçük pilotu
set OSM_PBF=C:\yol\turkey-latest.osm.pbf        # yerel dökümü kullan
set YAYIM=0                                     # asla yayımlama
python -P fabrika.py --tarif <tarif_id>         # tek tarifi gerçekten yükle ve eğit
```

## Yeni tarif eklemek

`tarifler/` altına bir modül açın; `TARIF` sözlüğü (kimlik, Türkçe ad, açıklama, görev, sınıflar ve OSM etiket kuralları, kaynak URL'leri ve tam lisans,
`imgsz`, `epok`, `model_adi`, `sinirlar`) ve `hazirla(tarif, dizin, pilot=None)` işlevi (`images/{train,val,test}`, `labels/...`, `data.yaml` ve özet üretir)
yeterlidir. Sentinel-2 + OpenStreetMap konuları için `s2_osm.py` motoru hazırdır. Modülün kimliğini `tarifler/__init__.py` içindeki `SIRA`'ya ekleyin.
Lisansı kapıdan geçmeyecek (NC/ND) kaynak kabul edilmez. Bir konunun >= 1000 gerçek görüntüye ulaştığını eklemeden önce sayın.

## Dürüst sınırlar

OpenStreetMap etiketleri eksiktir; her setin README'sinde yazılıdır. 10 m çözünürlükte küçük nesneler ayırt edilemez, bu yüzden ölçü kapısı
(`>= 0,50`) bazı konuları `zayif` bırakır; bu beklenen davranıştır, sonuç gizli kalır.
