"""Kapılar, kuyruk geçişleri ve sahte API ile yayım yolu (ağ yok). Çalıştır: python -P -m unittest discover -s tests"""
import json
import sys
import tempfile
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from cekirdek import egitim, kapilar, kartlar, pencere  # noqa: E402
from cekirdek import durum as dm  # noqa: E402
from cekirdek import kuyruk as kq  # noqa: E402
import fabrika  # noqa: E402

BUGUN = kq.bugun()
PENCERE_ICI = lambda: datetime(2026, 11, 24, 20, 40, tzinfo=timezone.utc)   # 23:40 TSİ
UZUN = "x" * 300
OZET = {"siniflar": ["a"], "goruntu_bolum": {"train": 700, "val": 200, "test": 100}, "pencere_bolum": {"train": 300, "val": 90, "test": 40},
        "goruntu_toplam": 1000, "pencere_toplam": 430, "etiket_satiri_bolum_sinif": {"train": {"a": 10}},
        "goruntu_sayisi_sinifi_iceren": {"train": {"a": 10}}, "mevsim_dagilimi": {"yaz": 3}, "yil_dagilimi": {"2023": 3},
        "osm_dokum_tarihi": "2026-11-01"}
TARIF = {"id": "t1", "ad": "Deneme Seti", "aciklama": "açıklama", "gorev": "segment", "siniflar": [{"ad": "a", "kurallar": [{"x": "y"}]}],
         "kaynaklar": [{"ad": "OSM", "url": "u", "lisans": "ODbL-1.0"}], "lisans": "ODbL-1.0", "lisans_gorunen": "ODbL 1.0",
         "mimari": "yolo11s-seg", "imgsz": 224, "epok": 60, "model_adi": "deneme-seg", "sinirlar": ["sınır"],
         "yontem": lambda t, o: "yöntem"}


class KapiTesti(unittest.TestCase):
    M = {"mask_mAP50": 0.62, "mAP50": 0.6}

    def test_gecer(self):
        self.assertEqual(kapilar.degerlendir("segment", 1200, self.M, "ODbL-1.0", UZUN, UZUN), (True, []))

    def test_az_oge(self):
        g, n = kapilar.degerlendir("segment", 999, self.M, "CC0", UZUN, UZUN)
        self.assertFalse(g)
        self.assertIn("999", n[0])

    def test_dusuk_metrik(self):
        self.assertFalse(kapilar.degerlendir("segment", 5000, {"mask_mAP50": 0.49}, "CC0", UZUN, UZUN)[0])
        self.assertTrue(kapilar.degerlendir("segment", 5000, {"mask_mAP50": 0.50}, "CC0", UZUN, UZUN)[0])

    def test_siniflandirma_top1(self):
        self.assertTrue(kapilar.degerlendir("classify", 5000, {"top1": 0.9}, "CC0", UZUN, UZUN)[0])
        self.assertFalse(kapilar.degerlendir("classify", 5000, {"mAP50": 0.9}, "CC0", UZUN, UZUN)[0])

    def test_lisanslar(self):
        for ok in ("CC0", "CC-BY-4.0", "cc-by-sa-4.0", "ODbL-1.0", "PDDL", "public domain"):
            self.assertTrue(kapilar.lisans_izinli(ok), ok)
        for kotu in ("CC-BY-NC-4.0", "CC-BY-ND-4.0", "CC-BY-NC-SA-4.0", "MIT", "", None, "custom"):
            self.assertFalse(kapilar.lisans_izinli(kotu), kotu)

    def test_bos_readme_kart(self):
        self.assertFalse(kapilar.degerlendir("segment", 5000, self.M, "CC0", "", UZUN)[0])
        self.assertFalse(kapilar.degerlendir("segment", 5000, self.M, "CC0", UZUN, " ")[0])

    def test_maliyet(self):
        self.assertTrue(egitim.maliyet_uygun(12.5))
        self.assertFalse(egitim.maliyet_uygun(12.6))


class KuyrukTesti(unittest.TestCase):
    def test_gecisler(self):
        o = kq.yeni_oge("a")
        kq.gecis(o, "yuklendi", set_id="1")
        kq.gecis(o, "egitimde")
        kq.gecis(o, "yayimlandi")
        self.assertEqual(o["durum"], "yayimlandi")
        self.assertIn("yayimlandi", o["zamanlar"])
        with self.assertRaises(ValueError):
            kq.gecis(o, "bekliyor")
        with self.assertRaises(ValueError):
            kq.gecis(kq.yeni_oge("b"), "egitimde")

    def test_sira_ve_birlestirme(self):
        k = {"ogeler": [kq.yeni_oge("a"), kq.yeni_oge("b")]}
        kq.gecis(k["ogeler"][0], "yuklendi")
        self.assertEqual(kq.sirada_bekleyen(k)["id"], "b")
        uzak = {"ogeler": [{"id": "a", "durum": "egitimde"}, {"id": "b", "durum": "bekliyor"}, {"id": "c", "durum": "bekliyor"}]}
        s = kq.birlestir(k, uzak)
        self.assertEqual([o["durum"] for o in s["ogeler"]], ["egitimde", "bekliyor", "bekliyor"])
        self.assertEqual(kq.esitle({"ogeler": []}, ["x", "y"])["ogeler"][1]["id"], "y")

    def test_ozet_birlestir(self):
        a = {"gunluk": {BUGUN: {"set_yayin": 2}}, "yayinlananlar": [{"tarif": "x"}]}
        b = {"gunluk": {BUGUN: {"set_yayin": 3, "model_yayin": 1}}, "yayinlananlar": [{"tarif": "y"}]}
        s = dm.ozet_birlestir(a, b)
        self.assertEqual(s["gunluk"][BUGUN], {"set_yayin": 3, "model_yayin": 1})
        self.assertEqual({y["tarif"] for y in s["yayinlananlar"]}, {"x", "y"})


class SahteApi:
    def __init__(self, metrik, bitti=True, herkese_acilan=()):
        self.metrik, self.bitti = metrik, bitti
        self.cagrilar = []
        self.modeller_ = [{"id": "m1", "name": "deneme-seg", "visibility": "PRIVATE", "slug": "deneme-seg"},
                          {"id": "eski", "name": "eski-model", "visibility": "PRIVATE"},
                          {"id": "kullanici-acik", "name": "k", "visibility": "PUBLIC"}]
        self.herkese_acilan = herkese_acilan
        self.dongu = 0

    def kazanc_ozeti(self):
        return {"today_earned_cr": 0, "today_annotation_count": 0}

    def is_getir(self, i):
        return {"status": "COMPLETED" if self.bitti else "RUNNING", "final_metrics": self.metrik, "actual_cr": "5.0"}

    def modeller(self):
        return [dict(m) for m in self.modeller_]

    def _ek(self, *a):
        self.cagrilar.append(a)

    def model_gorunurluk(self, mid, g):
        self._ek("model_gorunurluk", mid, g)
        for m in self.modeller_:
            if m["id"] == mid:
                m["visibility"] = g

    def set_gorunurluk(self, sid, g):
        self._ek("set_gorunurluk", sid, g)
        for mid in self.herkese_acilan:       # platform: set açılınca eski bağlı model kendiliğinden açılır
            for m in self.modeller_:
                if m["id"] == mid:
                    m["visibility"] = "PUBLIC"

    def set_readme(self, *a): self._ek("set_readme")
    def model_karti(self, *a): self._ek("model_karti")
    def model_atif(self, *a): self._ek("model_atif"); return 200
    def model_aciklama(self, *a): self._ek("model_aciklama")


def fabrika_kur(api, kok, yayim=True, oge_sayisi=1500):
    kq.kaydet(Path(kok) / "kuyruk.json", {"sahip": "abc", "ogeler": [{
        "id": "t1", "durum": "egitimde", "is_id": "j1", "set_id": "s1", "set_slug": "deneme", "veri_ozeti": OZET,
        "item_sayisi": oge_sayisi, "zamanlar": {"egitimde": "2026-11-24T10:00:00Z"}}]})
    modul = types.SimpleNamespace(TARIF=TARIF)
    return fabrika.Fabrika(api, kok, yayim=yayim, bugun=BUGUN, tarifler_kaydi=lambda i: modul, bekle=lambda s: None, log=lambda *a: None, simdi=PENCERE_ICI)


class YayimYoluTesti(unittest.TestCase):
    def test_gecen_yayimlanir_ve_eski_model_gizlenir(self):
        with tempfile.TemporaryDirectory() as d:
            api = SahteApi({"mask_mAP50": 0.7, "mAP50": 0.7}, herkese_acilan=("eski",))
            f = fabrika_kur(api, d)
            f.izle()
            f.yayimla_hazirlar()
            o = f.d.kuyruk["ogeler"][0]
            self.assertEqual(o["durum"], "yayimlandi")
            gorunur = {m["id"]: m["visibility"] for m in api.modeller_}
            self.assertEqual(gorunur["m1"], "PUBLIC")
            self.assertEqual(gorunur["eski"], "PRIVATE")           # kendiliğinden açılan geri gizlendi
            self.assertEqual(gorunur["kullanici-acik"], "PUBLIC")  # önceden açık olana dokunulmadı
            self.assertEqual(f.d.sayac("set_yayin"), 1)
            self.assertEqual(f.d.sayac("model_yayin"), 1)
            self.assertEqual(f.d.yeni_mesajlar[0]["tur"], "yayimlandi")
            f.gonder()
            self.assertTrue((Path(d) / "durum" / "bildirim.json").exists())

    def test_zayif_gizli_kalir(self):
        with tempfile.TemporaryDirectory() as d:
            api = SahteApi({"mask_mAP50": 0.31})
            f = fabrika_kur(api, d)
            f.izle()
            self.assertEqual(f.d.kuyruk["ogeler"][0]["durum"], "zayif")
            self.assertFalse(any(c[0] == "set_gorunurluk" for c in api.cagrilar))
            self.assertEqual(f.d.yeni_mesajlar[0]["tur"], "zayif")

    def test_az_oge_zayif(self):
        with tempfile.TemporaryDirectory() as d:
            f = fabrika_kur(SahteApi({"mask_mAP50": 0.9}), d, oge_sayisi=500)
            f.izle()
            self.assertEqual(f.d.kuyruk["ogeler"][0]["durum"], "zayif")

    def test_yayim_kapali(self):
        with tempfile.TemporaryDirectory() as d:
            api = SahteApi({"mask_mAP50": 0.9})
            f = fabrika_kur(api, d, yayim=False)
            f.izle()
            self.assertEqual(f.d.kuyruk["ogeler"][0]["durum"], "egitimde")
            self.assertFalse(any(c[0] == "set_gorunurluk" for c in api.cagrilar))

    def test_gunluk_sinir(self):
        with tempfile.TemporaryDirectory() as d:
            api = SahteApi({"mask_mAP50": 0.9})
            f = fabrika_kur(api, d)
            f.d.ozet["gunluk"][BUGUN]["set_yayin"] = 10
            f.izle()
            f.yayimla_hazirlar()
            self.assertEqual(f.d.kuyruk["ogeler"][0]["durum"], "egitimde")

    def test_sureyor_ve_hata(self):
        with tempfile.TemporaryDirectory() as d:
            f = fabrika_kur(SahteApi({}, bitti=False), d)
            f.izle()
            self.assertEqual(f.d.kuyruk["ogeler"][0]["durum"], "egitimde")


class PencereTesti(unittest.TestCase):
    def U(self, sa, dk):
        return datetime(2026, 11, 24, sa, dk, tzinfo=timezone.utc)      # UTC; TSİ = +3

    def test_pencere(self):
        self.assertTrue(pencere.pencere_icinde(self.U(20, 25)))         # 23:25 TSİ
        self.assertTrue(pencere.pencere_icinde(self.U(20, 58)))         # 23:58 TSİ
        self.assertFalse(pencere.pencere_icinde(self.U(20, 24)))
        self.assertFalse(pencere.pencere_icinde(self.U(20, 59)))
        self.assertFalse(pencere.pencere_icinde(self.U(12, 0)))

    def test_izin_ve_istisna(self):
        self.assertFalse(pencere.izinli(self.U(12, 0), 40)[0])
        self.assertTrue(pencere.izinli(self.U(12, 0), 100)[0])          # tavan dolu: her an serbest
        self.assertTrue(pencere.izinli(self.U(12, 0), 130)[0])
        self.assertTrue(pencere.izinli(self.U(20, 40), 0)[0])
        self.assertFalse(pencere.izinli(self.U(20, 59), 99.9)[0])

    def test_kalan(self):
        self.assertEqual(pencere.kalan_bekleme_sn(self.U(20, 0)), 25 * 60)
        self.assertEqual(pencere.kalan_bekleme_sn(self.U(20, 30)), 0)
        self.assertIsNone(pencere.kalan_bekleme_sn(self.U(20, 59)))      # 23:59 TSİ: pencere kaçtı
        self.assertEqual(pencere.kalan_bekleme_sn(self.U(10, 0)), (10 * 60 + 25) * 60)   # 13:00 -> 23:25 TSİ

    def test_erken_pencere(self):                                       # 27.11: etiket sayacı 300 ise 20:30 TSİ
        self.assertFalse(pencere.izinli(self.U(17, 29), 50, 300)[0])     # 20:29 TSİ
        self.assertTrue(pencere.izinli(self.U(17, 30), 50, 300)[0])      # 20:30 TSİ
        self.assertFalse(pencere.izinli(self.U(17, 30), 50, 299)[0])
        self.assertFalse(pencere.izinli(self.U(20, 59), 50, 300)[0])     # 23:59 TSİ kapalı
        self.assertEqual(pencere.kalan_bekleme_sn(self.U(17, 0), 300), 30 * 60)
        self.assertEqual(pencere.kalan_bekleme_sn(self.U(17, 0), 10), (3 * 60 + 25) * 60)

    def _fabrika(self, api, saat, d):
        t = {"an": saat}

        def bekle(s):
            from datetime import timedelta
            t["an"] = t["an"] + timedelta(seconds=s)
        kq.kaydet(Path(d) / "kuyruk.json", {"sahip": "abc", "ogeler": [{
            "id": "t1", "durum": "egitimde", "is_id": "j1", "set_id": "s1", "set_slug": "x", "veri_ozeti": OZET,
            "item_sayisi": 1500, "zamanlar": {}, "yayina_hazir": True, "model_id": "m1"}]})
        modul = types.SimpleNamespace(TARIF=TARIF)
        return fabrika.Fabrika(api, d, bugun=BUGUN, tarifler_kaydi=lambda i: modul, bekle=bekle, log=lambda *a: None,
                               simdi=lambda: t["an"])

    def test_pencere_disi_yayim_ertelenir(self):
        with tempfile.TemporaryDirectory() as d:
            api = SahteApi({})
            f = self._fabrika(api, self.U(10, 0), d)          # 13:00 TSİ, pencereye 10 saat var (> azami 4 saat)
            f.yayimla_hazirlar()
            self.assertEqual(f.d.kuyruk["ogeler"][0]["durum"], "egitimde")
            self.assertFalse(any(c[0] == "set_gorunurluk" for c in api.cagrilar))

    def test_pencereye_yakinsa_bekler_ve_yayimlar(self):
        with tempfile.TemporaryDirectory() as d:
            api = SahteApi({})
            f = self._fabrika(api, self.U(19, 0), d)          # 22:00 TSİ: pencereye 85 dk
            f.yayimla_hazirlar()
            self.assertEqual(f.d.kuyruk["ogeler"][0]["durum"], "yayimlandi")

    def test_tavan_doluysa_her_an_yayimlar(self):
        with tempfile.TemporaryDirectory() as d:
            api = SahteApi({})
            api.kazanc_ozeti = lambda: {"today_earned_cr": 100}
            f = self._fabrika(api, self.U(10, 0), d)
            f.yayimla_hazirlar()
            self.assertEqual(f.d.kuyruk["ogeler"][0]["durum"], "yayimlandi")

    def test_pencere_kacti(self):
        with tempfile.TemporaryDirectory() as d:
            f = self._fabrika(SahteApi({}), self.U(20, 59), d)
            f.yayimla_hazirlar()
            self.assertEqual(f.d.kuyruk["ogeler"][0]["durum"], "egitimde")

    def test_yukleme_pencere_disinda_ertelenir(self):
        with tempfile.TemporaryDirectory() as d:
            api = SahteYuklemeApi()
            y = YuklemeYoluTesti()
            f = y._kur(api, d)
            f.simdi = lambda: self.U(10, 0)
            f.yeni_baslat()
            self.assertEqual(f.d.kuyruk["ogeler"][0]["durum"], "bekliyor")
            self.assertEqual(api.yuklenen, [])
            self.assertEqual(f.d.sayac("yeni_yukleme"), 0)


class SahteYuklemeApi(SahteApi):
    def __init__(self, tahmin=10.0, bugun_cr=0, etiket=0):
        super().__init__({})
        self.tahmin, self.cr, self.et = tahmin, bugun_cr, etiket
        self.yuklenen = []

    def kazanc_ozeti(self): return {"today_earned_cr": self.cr, "today_annotation_count": self.et}
    def set_olustur(self, ad, ac, lis, g="private"): self._ek("set_olustur"); return {"id": "s9", "slug": "yeni"}
    def zip_yukle(self, sid, ad, ic, deneme=5): self.yuklenen.append(ad); return True

    def ogeler(self, sid):
        return [{"split": b, "annotation_count": 1} for b, n in (("train", 7), ("val", 2), ("test", 1)) for _ in range(n)]

    def surum_olustur(self, *a): return {"id": "v9", "item_count": 1200, "split_config": {"unassigned": 0}}
    def proje_olustur(self, *a): return "p9"
    def egitim_kuru(self, p, g): return {"valid": True, "estimated_cr": self.tahmin}
    def egitim_baslat(self, p, g): self._ek("baslat"); return "j9"


class YuklemeYoluTesti(unittest.TestCase):
    def _kur(self, api, d):
        kq.kaydet(Path(d) / "kuyruk.json", {"sahip": "abc", "ogeler": [kq.yeni_oge("t1"), kq.yeni_oge("t2")]})
        modul = types.SimpleNamespace(TARIF=TARIF)

        def hazirla(t, dizin):
            for b, n in (("train", 7), ("val", 2), ("test", 1)):
                (dizin / "images" / b).mkdir(parents=True)
                (dizin / "labels" / b).mkdir(parents=True)
                for i in range(n):
                    (dizin / "images" / b / f"{i}.jpg").write_bytes(b"j")
                    (dizin / "labels" / b / f"{i}.txt").write_text("0 0 0 1 1 1")
            (dizin / "data.yaml").write_text("names:\n  0: a\n")
            return {**OZET, "goruntu_toplam": 1000}
        return fabrika.Fabrika(api, d, hazirla=hazirla, bugun=BUGUN, tarifler_kaydi=lambda i: modul,
                               bekle=lambda s: None, log=lambda *a: None, simdi=PENCERE_ICI)

    def test_basarili(self):
        with tempfile.TemporaryDirectory() as d:
            api = SahteYuklemeApi()
            f = self._kur(api, d)
            f.yeni_baslat()
            o = f.d.kuyruk["ogeler"]
            self.assertEqual(o[0]["durum"], "egitimde")
            self.assertEqual(o[1]["durum"], "bekliyor")                   # günde 1 yeni
            self.assertEqual(api.yuklenen, ["train-00000", "val-00000", "test-00000"])
            self.assertFalse(any(c[0] == "set_gorunurluk" for c in api.cagrilar))

    def test_kazanc_korumasi(self):
        with tempfile.TemporaryDirectory() as d:
            api = SahteYuklemeApi(bugun_cr=61, etiket=10)
            f = self._kur(api, d)
            f.yeni_baslat()
            self.assertEqual(f.d.kuyruk["ogeler"][0]["durum"], "bekliyor")
            self.assertEqual(api.yuklenen, [])
            api2 = SahteYuklemeApi(bugun_cr=61, etiket=400)
            f2 = self._kur(api2, d)
            f2.yeni_baslat()
            self.assertEqual(f2.d.kuyruk["ogeler"][0]["durum"], "egitimde")

    def test_kazanc_korumasi_etiket_300(self):                         # platform sayacı 300'de durur
        with tempfile.TemporaryDirectory() as d:
            f = self._kur(SahteYuklemeApi(bugun_cr=87, etiket=300), d)
            f.yeni_baslat()
            self.assertEqual(f.d.kuyruk["ogeler"][0]["durum"], "egitimde")

    def test_once_hepsi_kurulur(self):
        with tempfile.TemporaryDirectory() as d:
            api = SahteYuklemeApi()
            f = self._kur(api, d)
            f.gunluk_yeni = 6
            sira = []
            eski_h, eski_y = f.hazirla, f._yukle_ve_baslat
            f.hazirla = lambda t, dz: (sira.append("kur"), eski_h(t, dz))[1]
            f._yukle_ve_baslat = lambda *a: (sira.append("yukle"), eski_y(*a))[1]
            f.yeni_baslat()
            self.assertEqual(sira, ["kur", "kur", "yukle", "yukle"])
            self.assertEqual([o["durum"] for o in f.d.kuyruk["ogeler"]], ["egitimde", "egitimde"])

    def test_pahali_egitim_hata(self):
        with tempfile.TemporaryDirectory() as d:
            f = self._kur(SahteYuklemeApi(tahmin=40.0), d)
            f.gunluk_yeni = 1
            f.yeni_baslat()
            self.assertEqual(f.d.kuyruk["ogeler"][0]["durum"], "hata")

    def test_en_cok_iki_yukleme(self):
        with tempfile.TemporaryDirectory() as d:
            f = self._kur(SahteYuklemeApi(tahmin=40.0), d)   # hepsi hata verir -> sayaç sınırlar
            f.gunluk_yeni = 9
            f.yeni_baslat()
            self.assertEqual(f.d.sayac("yeni_yukleme"), 2)


if __name__ == "__main__":
    unittest.main()
