"""Küme fabrikası: günlük çalışma.

Sırayla:
  a) `egitimde` olan işleri izler; biten için README + model kartı yazar, kapıları uygular, geçerse yayımlar.
  b) Bugün başlatılan yeni iş sayısı GUNLUK_YENI'den azsa sıradaki tarifi kurar, ÖZEL yükler, eğitimi başlatır.
  c) ZIP yüklemeden önce kazanç korumasını uygular (aşılmaz).
  d) durum/ozet.json ve durum/bildirim.json yazar; yalnız durum dosyalarını çakışmasız gönderir.

Ortam: EVREN_PLATFORM_KEY (zorunlu), GUNLUK_YENI (varsayılan 1, en çok 2), YAYIM (0 ise hiçbir şey yayımlanmaz),
       CI=true ise durum dosyaları git'e gönderilir.
Kullanım: python -P fabrika.py [--kuru] [--tarif ID] [--pilot N]
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))

from cekirdek import durum as dm            # noqa: E402
from cekirdek import egitim, kapilar, kartlar, pencere  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from cekirdek import kuyruk as kq           # noqa: E402

BOY = 300                    # ZIP parçası başına görüntü
KAZANC_CR_ESIK, KAZANC_ETIKET_ESIK = 60, 400
EN_AZ_DISK_GB = 3.0
BITIS_DURUMLARI = ("COMPLETED", "SUCCEEDED")
HATA_DURUMLARI = ("FAILED", "CANCELLED", "ERROR")


class Ertelendi(Exception):
    """CR penceresi kaçtı: öğe bekliyor kalır, yarın yeniden denenir."""


def tarif_modulu(tarif_id: str):
    import tarifler
    return tarifler.yukle(tarif_id)


class Fabrika:
    def __init__(self, api, kok: Path = KOK, hazirla=None, yayim: bool = True, gunluk_yeni: int = 1,
                 bugun: str | None = None, tarifler_kaydi=None, bekle=time.sleep, log=print, simdi=None):
        self.api, self.kok, self.yayim = api, Path(kok), yayim
        self.gunluk_yeni = max(0, min(gunluk_yeni, dm.GUNLUK_SINIR["yeni_yukleme"]))
        self.d = dm.Durum(self.kok, bugun)
        self.hazirla = hazirla                   # (tarif, dizin) -> ozet ; testlerde sahte
        self.tarif_yukle = tarifler_kaydi or tarif_modulu
        self.bekle, self.log = bekle, log
        self.simdi = simdi or (lambda: datetime.now(timezone.utc))
        self.azami_bekleme_sn = 4 * 3600

    # ================================================================== a) eğitim izleme
    def izle(self) -> None:
        for o in kq.egitimdekiler(self.d.kuyruk):
            try:
                self._izle_bir(o)
            except Exception as e:           # tek öğenin hatası bütün koşuyu durdurmasın
                self.d.hata(f"{o['id']} izleme hatası: {type(e).__name__} {str(e)[:150]}")

    def _model_bul(self, ad):
        for _ in range(3):
            m = next((m for m in self.api.modeller() if m.get("name") == ad), None)
            if m:
                return m
            self.bekle(30)
        return None

    def _izle_bir(self, o: dict) -> None:
        tarif = self.tarif_yukle(o["id"]).TARIF
        j = self.api.is_getir(o["is_id"])
        durum = str(j.get("status", "")).upper()
        if durum in HATA_DURUMLARI:
            kq.gecis(o, "hata", neden=f"eğitim {durum}: {(j.get('error_message') or '')[:200]}")
            self.d.bildir("hata", f"Eğitim başarısız: {tarif['ad']} ({durum}).", o["id"])
            return
        if durum not in BITIS_DURUMLARI:
            self.d.eylem(f"{o['id']}: eğitim sürüyor ({durum or '?'})")
            return
        m = self._model_bul(tarif["model_adi"])
        if not m:
            self.d.eylem(f"{o['id']}: eğitim bitti ama model henüz listede yok, yarın bakılacak")
            return
        self.api.model_gorunurluk(m["id"], "PRIVATE")      # platform eğitimden sonra kendiliğinden açabiliyor
        metrik = j.get("final_metrics") or {}
        o.update(model_id=m["id"], metrik=_metrik_ozeti(tarif["gorev"], metrik), cr_gercek=j.get("actual_cr"))
        ozet = o["veri_ozeti"]
        readme = kartlar.set_readme(tarif, ozet, tarif["yontem"](tarif, ozet))
        kart = kartlar.model_karti(tarif, ozet, metrik, {"cr": j.get("actual_cr")})
        self.api.set_readme(o["set_id"], readme)
        self.api.model_karti(m["id"], kart)
        self._atif_yaz(m["id"], tarif)
        gecti, nedenler = kapilar.degerlendir(tarif["gorev"], o.get("item_sayisi"), metrik, tarif["lisans"], readme, kart)
        if not gecti:
            kq.gecis(o, "zayif", neden="; ".join(nedenler))
            self.d.bildir("zayif", f"Zayıf kaldı, gizli tutuldu: {tarif['ad']} ({'; '.join(nedenler)}).", o["id"])
            return
        if not self.yayim:
            self.d.eylem(f"{o['id']}: kapılar geçildi ama YAYIM=0, yayımlanmadı")
            return
        o["yayina_hazir"] = True      # yayım CR kazandırır: pencerede yayimla_hazirlar() yapar
        self.d.eylem(f"{o['id']}: kapılar geçildi, yayım penceresini bekliyor")

    def yayimla_hazirlar(self, bekle: bool = True) -> None:
        hazir = [o for o in self.d.kuyruk["ogeler"] if o["durum"] == "egitimde" and o.get("yayina_hazir")]
        if not hazir:
            return
        if not self.pencere_izni(bekle):
            self.d.eylem(f"yayım ertelendi (CR penceresi): {[o['id'] for o in hazir]}")
            return
        for o in hazir:
            if not (self.d.hakki_var("set_yayin") and self.d.hakki_var("model_yayin")):
                self.d.eylem(f"{o['id']}: günlük yayım sınırına ulaşıldı, yarına kaldı")
                continue
            try:
                tarif = self.tarif_yukle(o["id"]).TARIF
                m = next(x for x in self.api.modeller() if x["id"] == o["model_id"])
                self._yayimla(o, tarif, m)
                o.pop("yayina_hazir", None)
            except Exception as e:
                self.d.hata(f"{o['id']} yayım hatası: {type(e).__name__} {str(e)[:150]}")

    # -- CR penceresi -----------------------------------------------------------------------
    def _bugun_cr(self):
        try:
            return self.api.kazanc_ozeti().get("today_earned_cr") or 0
        except Exception:
            return None

    def pencere_izni(self, bekle: bool = True) -> bool:
        """CR kazandıran adım şimdi yapılabilir mi? Pencere yakında açılacaksa (azami_bekleme_sn) bekler."""
        while True:
            cr = self._bugun_cr()
            if cr is None:
                self.d.eylem("kazanç özeti okunamadı; CR kazandıran adım yapılmadı")
                return False
            ok, neden = pencere.izinli(self.simdi(), cr)
            if ok:
                return True
            kalan = pencere.kalan_bekleme_sn(self.simdi())
            if not bekle or kalan is None or kalan > self.azami_bekleme_sn:
                self.d.eylem(neden + "; sonraki koşuya bırakıldı")
                return False
            self.d.eylem(f"{neden}; pencereye {kalan / 60:.0f} dk var, bekleniyor")
            self.bekle(min(60.0, max(kalan, 1.0)) if kalan > 60 else max(kalan, 1.0))

    def _atif_yaz(self, model_id, tarif):
        kod = self.api.model_atif(model_id, tarif["lisans"], "; ".join(k["ad"] for k in tarif["kaynaklar"]),
                                  kartlar.atif_metni(tarif))
        if kod >= 300:       # platform lisans kodunu tanımıyorsa: genel kod
            self.api.model_atif(model_id, "CC-BY-4.0", "; ".join(k["ad"] for k in tarif["kaynaklar"]),
                                kartlar.atif_metni(tarif))
        self.api.model_aciklama(model_id, f"{tarif['ad']} - {tarif['mimari']}, Sentinel-2 + OpenStreetMap")

    def _acik_modeller(self) -> set:
        return {m["id"] for m in self.api.modeller() if str(m.get("visibility", "")).upper() == "PUBLIC"}

    def _yayimla(self, o, tarif, m) -> None:
        once = self._acik_modeller()
        self.api.set_gorunurluk(o["set_id"], "public")
        self.d.artir("set_yayin")
        self.api.model_gorunurluk(m["id"], "PUBLIC")
        self.d.artir("model_yayin")
        # veri seti açılınca ona bağlı ESKİ bir model de kendiliğinden açılabilir: yeni açılanlardan hedef dışını gizle
        sonra = self._acik_modeller()
        for mid in sorted((sonra - once) - {m["id"]}):
            self.api.model_gorunurluk(mid, "PRIVATE")
            self.d.eylem(f"kendiliğinden açılan model gizlendi: {mid}")
        kq.gecis(o, "yayimlandi")
        sahip = self.d.kuyruk.get("sahip", "")
        yayin = {"tarif": o["id"], "ad": tarif["ad"], "set_id": o["set_id"], "set_slug": o.get("set_slug"),
                 "model_adi": tarif["model_adi"], "model_id": m["id"], "model_slug": m.get("slug"),
                 "metrik": o.get("metrik"), "zaman": kq.simdi(),
                 "set_url": f"https://evren.ssyz.org.tr/datasets/{sahip}/{o.get('set_slug')}" if sahip and o.get("set_slug") else None,
                 "model_url": f"https://evren.ssyz.org.tr/models/{sahip}/{m.get('slug')}" if sahip and m.get("slug") else None}
        self.d.ozet.setdefault("yayinlananlar", []).append(yayin)
        v = (o.get("metrik") or {}).get("kapi_olcusu")
        self.d.bildir("yayimlandi", f"Yayımlandı: {tarif['ad']} (ölçü %{(v or 0) * 100:.1f}, {o.get('item_sayisi')} öğe)."
                                    + (f" {yayin['model_url']}" if yayin["model_url"] else ""), o["id"])
        self.d.eylem(f"{o['id']}: yayımlandı")

    def devam_et(self) -> None:
        """Yüklenmiş ama eğitimi başlamamış (ör. maliyet ya da geçici hata) öğelerin eğitimini yeniden dener."""
        for o in [x for x in self.d.kuyruk["ogeler"] if x["durum"] == "yuklendi"]:
            try:
                self._egitim_baslat(o, self.tarif_yukle(o["id"]).TARIF)
            except Exception as e:
                kq.gecis(o, "hata", neden=f"{type(e).__name__}: {str(e)[:250]}")
                self.d.bildir("hata", f"Eğitim başlatılamadı: {o['id']} ({str(e)[:120]}).", o["id"])
                self.d.hata(f"{o['id']}: {type(e).__name__} {str(e)[:200]}")

    # ================================================================== c) kazanç koruması
    def kazanc_koruma_engeli(self) -> str | None:
        try:
            s = self.api.kazanc_ozeti()
        except Exception as e:
            return f"kazanç özeti okunamadı ({type(e).__name__}); güvenli tarafta durduruldu"
        cr, et = s.get("today_earned_cr") or 0, s.get("today_annotation_count") or 0
        if cr >= 100:
            return None  # günlük tavan zaten dolu: o gün etiket puanı gelmez, yüklemenin kaybettireceği bir şey yok
        if cr > KAZANC_CR_ESIK and et < KAZANC_ETIKET_ESIK:
            return f"kazanç koruması: bugün {cr} CR kazanıldı, etiket {et} < {KAZANC_ETIKET_ESIK}; yükleme yarına"
        return None

    # ================================================================== b) yeni iş
    def yeni_baslat(self, zorla_tarif: str | None = None) -> None:
        while (kq.bugun_baslayan(self.d.kuyruk, self.d.bugun) < self.gunluk_yeni
               and self.d.hakki_var("yeni_yukleme")):
            o = kq.bul(self.d.kuyruk, zorla_tarif) if zorla_tarif else kq.sirada_bekleyen(self.d.kuyruk)
            if o is None or o["durum"] != "bekliyor":
                break
            if shutil.disk_usage(self.kok).free / 1e9 < EN_AZ_DISK_GB:
                self.d.hata("disk yetersiz, yeni tarif başlatılmadı")
                return
            self.d.artir("yeni_yukleme")
            try:
                self._kur_ve_baslat(o)
            except Ertelendi as e:
                self.d.artir("yeni_yukleme", -1)
                self.d.eylem(f"{o['id']}: ertelendi ({e})")
                return
            except Exception as e:
                kq.gecis(o, "hata", neden=f"{type(e).__name__}: {str(e)[:250]}")
                self.d.bildir("hata", f"Tarif başarısız: {o['id']} ({type(e).__name__}: {str(e)[:120]}).", o["id"])
                self.d.hata(f"{o['id']}: {type(e).__name__} {str(e)[:200]}")
            self.gonder()
            if zorla_tarif:
                break

    def _kur_ve_baslat(self, o: dict) -> None:
        tarif = self.tarif_yukle(o["id"]).TARIF
        calisma = Path(tempfile.mkdtemp(prefix=f"set_{o['id']}_", dir=os.environ.get("FABRIKA_GECICI") or None))
        try:
            self.d.eylem(f"{o['id']}: veri kuruluyor")
            ozet = self.hazirla(tarif, calisma)
            if ozet["goruntu_toplam"] < kapilar.EN_AZ_OGE:
                raise RuntimeError(f"yeterli görüntü üretilemedi: {ozet['goruntu_toplam']} < {kapilar.EN_AZ_OGE}")
            readme = kartlar.set_readme(tarif, ozet, tarif["yontem"](tarif, ozet))
            if not self.pencere_izni():
                raise Ertelendi("CR penceresi kaçtı; yükleme yarın gece")
            self.yayimla_hazirlar(bekle=False)       # yayımlar da pencerede, yüklemeden önce (kısa sürer)
            engel = self.kazanc_koruma_engeli()
            if engel:
                raise Ertelendi(engel)
            s = self.api.set_olustur(tarif["ad"], tarif["aciklama"], tarif["lisans"])
            o.update(set_id=s["id"], set_slug=s.get("slug"), veri_ozeti=ozet)
            self.d.eylem(f"{o['id']}: set oluşturuldu (özel)")
            self._zip_yukle(o["id"], s["id"], calisma)
            self._denetle(s["id"], calisma, ozet)
            self.api.set_readme(s["id"], readme)
            v = self.api.surum_olustur(s["id"], "v1.0", "Konum kümesine göre bölünmüş ilk sürüm")
            birak = (v.get("split_config") or {}).get("unassigned")
            if birak:
                raise RuntimeError(f"atanmamış bölüm var ({birak})")
            if (v.get("item_count") or 0) < kapilar.EN_AZ_OGE:
                raise RuntimeError(f"sürüm öğe sayısı {v.get('item_count')} < {kapilar.EN_AZ_OGE}")
            kq.gecis(o, "yuklendi", surum_id=v["id"], item_sayisi=v.get("item_count"), bolum_ayari=v.get("split_config"))
            self.gonder()
            self._egitim_baslat(o, tarif)
        finally:
            shutil.rmtree(calisma, ignore_errors=True)

    def _zip_yukle(self, tarif_id, set_id, dizin: Path) -> None:
        from cekirdek.evren_api import zip_parca
        import random
        for b in ("train", "val", "test"):
            g = sorted((dizin / "images" / b).glob("*.jpg"))
            random.Random(0).shuffle(g)
            for i in range(0, len(g), BOY):
                ad = f"{b}-{i:05d}"
                if not self.api.zip_yukle(set_id, ad, zip_parca(dizin, b, g[i:i + BOY])):
                    raise RuntimeError(f"{ad} yüklenemedi")
                self.bekle(3)
        self.d.eylem(f"{tarif_id}: ZIP yükleme bitti")

    def _denetle(self, set_id, dizin: Path, ozet: dict) -> None:
        ogeler = self.api.ogeler(set_id)
        sayim = {}
        for x in ogeler:
            sayim[x.get("split")] = sayim.get(x.get("split"), 0) + 1
        yerel = {b: len(list((dizin / "images" / b).glob("*.jpg"))) for b in ("train", "val", "test")}
        etiketsiz = sum(1 for x in ogeler if not x.get("annotation_count"))
        for b, n in yerel.items():
            pn = sayim.get(b, 0) + (sayim.get("validation", 0) if b == "val" else 0)  # platform 'val' bölümünü 'validation' adlandırıyor
            if n and pn < 0.98 * n:
                raise RuntimeError(f"yükleme eksik: {b} yerel {n}, platform {pn}")
        if etiketsiz > 0.02 * max(len(ogeler), 1):
            raise RuntimeError(f"etiketsiz öğe fazla: {etiketsiz}/{len(ogeler)}")
        self.d.eylem(f"yükleme doğrulandı: platform {sayim}, yerel {yerel}, etiketsiz {etiketsiz}")

    def _egitim_baslat(self, o: dict, tarif: dict) -> None:
        proje = self.api.proje_olustur(tarif["ad"], tarif["aciklama"])
        o["proje_id"] = proje
        epok = tarif["epok"]
        for deneme in range(2):
            govde = egitim.govde(tarif, o["surum_id"], epok)
            j = self.api.egitim_kuru(proje, govde)
            tahmin = float(j.get("estimated_cr") or 0)
            self.d.eylem(f"{o['id']}: kuru koşu epok={epok} tahmin={tahmin:.2f} CR (x{egitim.KATSAYI}={tahmin * egitim.KATSAYI:.1f})")
            if j.get("valid") and egitim.maliyet_uygun(tahmin):
                if os.environ.get("EGITIM_BASLATMA") == "1":
                    self.d.eylem(f"{o['id']}: EGITIM_BASLATMA=1, eğitim başlatılmadı")
                    return
                is_id = self.api.egitim_baslat(proje, govde)
                kq.gecis(o, "egitimde", is_id=is_id, epok=epok, tahmin_cr=tahmin)
                self.d.bildir("basladi", f"Eğitim başladı: {tarif['ad']} ({o.get('item_sayisi')} öğe, ~{tahmin * egitim.KATSAYI:.0f} CR).", o["id"])
                return
            epok = max(30, int(epok * 0.6))
        raise RuntimeError("eğitim maliyeti 30 CR sınırını aşıyor ya da kuru koşu geçersiz")

    # ================================================================== d) kapanış
    def gonder(self) -> None:
        self.d.kaydet()
        if os.environ.get("CI") == "true" and os.environ.get("DURUM_GONDER", "1") == "1":
            dm.gonder(self.kok)

    def bitir(self) -> None:
        if kq.kalan_tarif(self.d.kuyruk) < 5:
            self.d.bildir("kuyruk", f"Kuyrukta yalnız {kq.kalan_tarif(self.d.kuyruk)} tarif kaldı; yenilerini ekleyin.")
        self.gonder()


def _metrik_ozeti(gorev, m: dict) -> dict:
    anahtar = ("mAP50", "mask_mAP50", "mAP50_95", "mask_mAP50_95", "top1", "top5", "precision", "recall")
    s = {k: m[k] for k in anahtar if k in m}
    s["kapi_olcusu"] = kapilar.metrik_degeri(gorev, m)
    return s


def kuru_calistir(pilot: int, tarif_id: str | None) -> int:
    """Ağda hiçbir yazma yapmaz: ilk tarifin küçük bir pilotunu kurar, nelerin yükleneceğini yazdırır."""
    import tarifler
    from cekirdek.evren_api import zip_parca
    k = kq.yukle(KOK / "kuyruk.json")
    kq.esitle(k, tarifler.SIRA)
    o = kq.bul(k, tarif_id) if tarif_id else (kq.sirada_bekleyen(k) or k["ogeler"][0])
    tarif = tarifler.yukle(o["id"]).TARIF
    dizin = Path(tempfile.mkdtemp(prefix=f"kuru_{o['id']}_"))
    print(f"[kuru] tarif {o['id']}: {tarif['ad']}  -> {dizin}")
    ozet = tarifler.yukle(o["id"]).hazirla(tarif, dizin, pilot=pilot)
    readme = kartlar.set_readme(tarif, ozet, tarif["yontem"](tarif, ozet))
    print(f"[kuru] özet: görüntü {ozet['goruntu_toplam']} pencere {ozet['pencere_toplam']} bölüm {ozet['goruntu_bolum']}")
    print(f"[kuru] sınıf etiketleri: {ozet['etiket_satiri_bolum_sinif']}")
    for b in ("train", "val", "test"):
        g = sorted((dizin / "images" / b).glob("*.jpg"))
        parca = [len(g[i:i + BOY]) for i in range(0, len(g), BOY)]
        boyut = sum(len(zip_parca(dizin, b, g[i:i + BOY])) for i in range(0, len(g), BOY)) / 1e6 if g else 0
        print(f"[kuru] YÜKLENİRDİ: set '{tarif['ad']}' (özel, lisans {tarif['lisans']}) bölüm {b}: {len(g)} görüntü, "
              f"ZIP parçaları {parca}, ~{boyut:.1f} MB")
    print(f"[kuru] YÜKLENİRDİ: sürüm v1.0, proje, eğitim {tarif['mimari']} {tarif['imgsz']} px {tarif['epok']} epok (kuru koşu >30 CR ise iptal)")
    print(f"[kuru] README uzunluğu {len(readme)} karakter; ilk satırlar:\n" + "\n".join(readme.splitlines()[:8]))
    print(f"[kuru] örnek dosyalar: {[p.name for p in sorted((dizin / 'images' / 'train').glob('*.jpg'))[:3]]}")
    if os.environ.get("KURU_TEMIZLE", "1") == "1":
        shutil.rmtree(dizin, ignore_errors=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kuru", action="store_true", help="ağda yazma yok; ilk tarifin pilotunu kur ve yazdır")
    ap.add_argument("--pilot", type=int, default=12)
    ap.add_argument("--tarif", help="yalnız bu tarifi başlat (bekliyor olmalı)")
    a = ap.parse_args(argv)
    if a.kuru:
        return kuru_calistir(a.pilot, a.tarif)

    from cekirdek.evren_api import EvrenApi
    import tarifler
    api = EvrenApi()
    f = Fabrika(api, KOK, hazirla=lambda t, d: tarifler.yukle(t["id"]).hazirla(t, d),
                yayim=os.environ.get("YAYIM", "1") != "0",
                gunluk_yeni=int(os.environ.get("GUNLUK_YENI", "1") or 1))
    kq.esitle(f.d.kuyruk, tarifler.SIRA)
    f.izle()
    f.devam_et()
    f.gonder()
    f.yeni_baslat(a.tarif)
    f.yayimla_hazirlar()
    f.bitir()
    return 1 if f.d.hatalar and not f.d.eylemler else 0


if __name__ == "__main__":
    sys.exit(main())
