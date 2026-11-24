"""Veri seti README'si ve model kartı (Türkçe). Sayıların hepsi gerçek özetten ve eğitim ölçülerinden gelir."""
from __future__ import annotations

from .kapilar import metrik_degeri


def _n(x) -> str:
    return f"{int(x):,}".replace(",", ".")


def _yuzde(v) -> str:
    return "-" if v is None else f"{float(v) * 100:.1f}%".replace(".", ",")


def _s(v, k=3) -> str:
    return "-" if v is None else f"{float(v):.{k}f}".replace(".", ",")


def _bolum_satiri(ozet: dict) -> str:
    g, p = ozet["goruntu_bolum"], ozet["pencere_bolum"]
    return "".join(f"| {b} | {_n(p.get(b, 0))} | {_n(g.get(b, 0))} |\n" for b in ("train", "val", "test"))


def _sinif_tablosu(ozet: dict) -> str:
    e = ozet["etiket_satiri_bolum_sinif"]
    gi = ozet["goruntu_sayisi_sinifi_iceren"]
    satir = ""
    for i, s in enumerate(ozet["siniflar"]):
        top = sum(e.get(b, {}).get(s, 0) for b in e)
        img = sum(gi.get(b, {}).get(s, 0) for b in gi)
        satir += f"| {i} | `{s}` | {_n(img)} | {_n(top)} |\n"
    return satir


def set_readme(tarif: dict, ozet: dict, yontem: str) -> str:
    kaynaklar = "".join(f"- {k['ad']}: {k['url']} ({k['lisans']})\n" for k in tarif["kaynaklar"])
    kurallar = "".join(f"- `{s['ad']}`: " + " veya ".join(
        "+".join(f"{k}={v}" for k, v in kural.items()) for kural in s["kurallar"]) + "\n" for s in tarif["siniflar"])
    sinirlar = "".join(f"- {x}\n" for x in tarif["sinirlar"])
    return f"""# {tarif['ad']}

{tarif['aciklama']}

## İçerik

- **{_n(ozet['goruntu_toplam'])} gerçek görüntü**, {_n(ozet['pencere_toplam'])} ayrı konum (224x224 px, 10 m, yaklaşık 2,24 km). Her konum için farklı mevsimlerden en çok 3 ayrı Sentinel-2 geçişi.
- Etiket türü: çokgen (YOLO segmentasyon). Görüntü biçimi: RGB JPEG.
- Mevsim dağılımı: {ozet['mevsim_dagilimi']}. Yıl dağılımı: {ozet['yil_dagilimi']}.
- OpenStreetMap dökümü tarihi: {ozet['osm_dokum_tarihi']}.

| Bölüm | Konum | Görüntü |
|---|--:|--:|
{_bolum_satiri(ozet)}
| YOLO sınıfı | Ad | Sınıfı içeren görüntü | Etiket (çokgen satırı) |
|--:|---|--:|--:|
{_sinif_tablosu(ozet)}
Sınıf kuralları (OpenStreetMap etiketleri):

{kurallar}
## Yöntem

{yontem}

## Sınırlar

{sinirlar}- **OpenStreetMap etiketleri eksiktir.** Çizilmemiş bir nesne bu sette "arka plan" görünür; modelin yanlış alarmı bu yüzden olduğundan kötü ölçülebilir, gerçek bir nesneyi kaçırmak ise etiketsiz kalmış olabilir.
- Konumlar OSM'de çizilmiş nesnelerden seçildiği için dağılım, haritacıların ilgi gösterdiği yerlere (kentler, turistik bölgeler) kayar.
- Hedef nesnenin bulunmadığı (etiketsiz) pencere yoktur; model yalnız "nesne var" pencerelerinde eğitilmiştir.
- 10 m çözünürlükte küçük nesneler (birkaç piksel) güvenilir ayrılamaz.
- Bu bir tarama veri setidir; kadastro, ruhsat ya da kamulaştırma kararında kullanılamaz.

## Veri kaynakları, lisans ve atıf

- Veri seti lisansı: **{tarif['lisans_gorunen']}**.
{kaynaklar}- Görüntü atfı: **Contains modified Copernicus Sentinel data {min(ozet['yil_dagilimi'], default='')}-{max(ozet['yil_dagilimi'], default='')}**.
- Etiket atfı: © OpenStreetMap katkıcıları (ODbL 1.0). Bu veri seti OSM'den türetilmiş bir veri tabanıdır; aynı lisansla paylaşılır.
- Üretim kodu (MIT): set fabrikası deposu, tarif kodu `{tarif['id']}`.
"""


def _sinif_metrik_tablosu(m: dict) -> str:
    pc = m.get("per_class") or {}
    if len(pc) < 1:
        return ""
    satir = "".join(f"| {c} | {_yuzde(v.get('ap50'))} | {_s(v.get('precision'), 2)} | {_s(v.get('recall'), 2)} |\n"
                    for c, v in sorted(pc.items(), key=lambda kv: -(kv[1].get('ap50') or 0)))
    return ("Sınıf bazında (kutu ölçüsü, platformun verdiği):\n\n| Sınıf | AP@50 | Kesinlik | Duyarlılık |\n"
            f"|---|--:|--:|--:|\n{satir}\n")


def model_karti(tarif: dict, ozet: dict, m: dict, is_bilgi: dict) -> str:
    gorev = tarif["gorev"]
    deger = metrik_degeri(gorev, m)
    pc = m.get("per_class") or {}
    zayif = [c for c, v in pc.items() if (v.get("ap50") or 0) < 0.3]
    ek = f"- Zayıf sınıf: {', '.join(zayif)} (AP@50 %30'un altında); bu sınıfın çıktısına güvenmeyin.\n" if zayif else ""
    sinirlar = "".join(f"- {x}\n" for x in tarif["sinirlar"])
    if gorev == "classify":
        tablo = f"| Ölçü | Değer |\n|---|--:|\n| top-1 | {_yuzde(m.get('top1'))} |\n| top-5 | {_yuzde(m.get('top5'))} |\n| F1 | {_s(m.get('f1'))} |\n"
    else:
        tablo = (f"| Ölçü | Maske | Kutu |\n|---|--:|--:|\n| mAP@50 | {_yuzde(m.get('mask_mAP50'))} | {_yuzde(m.get('mAP50'))} |\n"
                 f"| mAP@50-95 | {_yuzde(m.get('mask_mAP50_95'))} | {_yuzde(m.get('mAP50_95'))} |\n"
                 f"| Kesinlik | {_s(m.get('mask_precision'))} | {_s(m.get('precision'))} |\n"
                 f"| Duyarlılık | {_s(m.get('mask_recall'))} | {_s(m.get('recall'))} |\n")
    kaynaklar = "; ".join(f"{k['ad']} ({k['lisans']})" for k in tarif["kaynaklar"])
    return f"""# {tarif['ad']} modeli ({tarif['mimari']})

{tarif['aciklama']} Model her nesne için hem kutu hem maske üretir. Sınıflar: {', '.join(ozet['siniflar'])}.

## Ölçüm (platform doğrulama bölümü, {_n(ozet['goruntu_bolum'].get('val', 0))} görüntü)

Kapı ölçüsü: **{_yuzde(deger)}** (eşik %50).

{tablo}
{_sinif_metrik_tablosu(m)}Eğitim: {tarif['mimari']}, {tarif['imgsz']} px, {_s(m.get('total_epochs'), 0)} tur (en iyi {_s(m.get('best_epoch'), 0)}), {is_bilgi.get('cr', '-')} CR. Test bölümü bu kartta ölçülmedi.

## Sınırlar

{sinirlar}{ek}- Yalnız Türkiye'deki Sentinel-2 L2A (10 m, kış dışı) görüntüleri için eğitildi; başka sensör, çözünürlük ya da bölgede sonuç güvenilir değildir.
- Etiketler OpenStreetMap'ten gelir ve eksiktir; doğrulama ölçüsü bu yüzden iyimser ya da kötümser olabilir.
- Araştırma amaçlıdır; resmî karar için tek başına kullanılmamalıdır.

## Veri, lisans ve atıf

- Eğitim verisi: {tarif['ad']} veri seti. Kaynaklar: {kaynaklar}.
- Görüntü: Contains modified Copernicus Sentinel data. Etiket: © OpenStreetMap katkıcıları (ODbL 1.0).
- Mimari: {tarif['mimari']}, Ultralytics YOLO ile eğitildi (AGPL-3.0).
"""


def atif_metni(tarif: dict) -> str:
    return ("Contains modified Copernicus Sentinel data. © OpenStreetMap contributors, ODbL 1.0. "
            f"{tarif['ad']}.")
