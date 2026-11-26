"""Durum dosyaları (kuyruk.json, durum/ozet.json, durum/bildirim.json) ve çakışmasız gönderim."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import kuyruk as kq

GUNLUK_SINIR = {"yeni_yukleme": 10, "set_yayin": 10, "model_yayin": 10}
DURUM_DOSYALARI = ("kuyruk.json", "durum/ozet.json", "durum/bildirim.json")


class Durum:
    def __init__(self, kok: Path, bugun: str | None = None):
        self.kok = Path(kok)
        self.bugun = bugun or kq.bugun()
        (self.kok / "durum").mkdir(exist_ok=True)
        self.kuyruk_yolu = self.kok / "kuyruk.json"
        self.ozet_yolu = self.kok / "durum" / "ozet.json"
        self.bildirim_yolu = self.kok / "durum" / "bildirim.json"
        self.kuyruk = kq.yukle(self.kuyruk_yolu) if self.kuyruk_yolu.exists() else {"sahip": "", "ogeler": []}
        self.ozet = self._oku(self.ozet_yolu, {"gunluk": {}, "yayinlananlar": [], "hatalar": []})
        eski = self._oku(self.bildirim_yolu, {"gecmis": []})
        self.gecmis = eski.get("gecmis", [])
        self.yeni_mesajlar: list[dict] = []
        self.eylemler: list[str] = []
        self.hatalar: list[str] = []
        self.ozet["gunluk"].setdefault(self.bugun, {"yeni_yukleme": 0, "set_yayin": 0, "model_yayin": 0})

    @staticmethod
    def _oku(yol, varsayilan):
        return json.loads(yol.read_text(encoding="utf-8")) if yol.exists() else varsayilan

    # -- günlük sayaçlar ----------------------------------------------------------------
    def sayac(self, ad: str) -> int:
        return self.ozet["gunluk"][self.bugun].get(ad, 0)

    def artir(self, ad: str, n: int = 1) -> None:
        self.ozet["gunluk"][self.bugun][ad] = self.sayac(ad) + n

    def hakki_var(self, ad: str) -> bool:
        return self.sayac(ad) < GUNLUK_SINIR[ad]

    # -- bildirim / eylem -----------------------------------------------------------------
    def bildir(self, tur: str, mesaj: str, tarif_id: str = "") -> None:
        m = {"id": f"{kq.simdi()}-{tur}-{tarif_id}", "zaman": kq.simdi(), "tur": tur, "tarif": tarif_id, "mesaj": mesaj}
        self.yeni_mesajlar.append(m)

    def eylem(self, metin: str) -> None:
        self.eylemler.append(metin)
        print("[eylem]", metin, flush=True)

    def hata(self, metin: str) -> None:
        self.hatalar.append(metin)
        print("[hata]", metin, flush=True)

    # -- yazma -----------------------------------------------------------------------------
    def kaydet(self, sorun_yok: bool = True) -> None:
        kq.kaydet(self.kuyruk_yolu, self.kuyruk)
        k = self.kuyruk
        durum_sayim = {}
        for o in k["ogeler"]:
            durum_sayim[o["durum"]] = durum_sayim.get(o["durum"], 0) + 1
        self.ozet.update({
            "son_calisma": kq.simdi(), "bu_calismada_yapilanlar": self.eylemler, "bu_calismada_hatalar": self.hatalar,
            "kuyruk_uzunlugu": len(k["ogeler"]), "kalan_tarif": kq.kalan_tarif(k), "durum_sayilari": durum_sayim,
        })
        self.ozet["gunluk"] = dict(sorted(self.ozet["gunluk"].items())[-30:])
        self.ozet["yayinlananlar"] = self.ozet.get("yayinlananlar", [])
        self.ozet_yolu.write_text(json.dumps(self.ozet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        gecmis = (self.gecmis + self.yeni_mesajlar)[-60:]
        self.bildirim_yolu.write_text(json.dumps({"mesajlar": self.yeni_mesajlar, "gecmis": gecmis},
                                                 ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


# ================================================================== birleştirme ve gönderim
def ozet_birlestir(bizim: dict, uzak: dict) -> dict:
    g = {k: dict(v) for k, v in uzak.get("gunluk", {}).items()}
    for gun, d in bizim.get("gunluk", {}).items():
        h = g.setdefault(gun, {})
        for k, v in d.items():
            h[k] = max(v, h.get(k, 0))
    yay = {y["tarif"]: y for y in uzak.get("yayinlananlar", [])}
    yay.update({y["tarif"]: y for y in bizim.get("yayinlananlar", [])})
    return {**uzak, **bizim, "gunluk": dict(sorted(g.items())), "yayinlananlar": list(yay.values())}


def bildirim_birlestir(bizim: dict, uzak: dict) -> dict:
    var = {m["id"] for m in bizim.get("mesajlar", [])}
    gecmis = {m["id"]: m for m in uzak.get("gecmis", [])}
    gecmis.update({m["id"]: m for m in bizim.get("gecmis", [])})
    mesajlar = bizim.get("mesajlar", []) + [m for m in uzak.get("mesajlar", []) if m["id"] not in var]
    return {"mesajlar": mesajlar, "gecmis": list(gecmis.values())[-60:]}


def dosya_birlestir(ad: str, bizim: dict, uzak: dict) -> dict:
    if not uzak:
        return bizim
    if ad == "kuyruk.json":
        return kq.birlestir(bizim, uzak)
    if ad.endswith("ozet.json"):
        return ozet_birlestir(bizim, uzak)
    return bildirim_birlestir(bizim, uzak)


def _git(kok, *a, kontrol=True):
    return subprocess.run(["git", *a], cwd=kok, check=kontrol, capture_output=True, text=True)


def gonder(kok: Path, dal: str | None = None, mesaj: str = "durum", deneme: int = 4) -> bool:
    """Durum dosyalarını uzak dalın son haliyle birleştirip commit eder ve gönderir (çakışmada yeniden dener).

    Yalnız durum dosyaları eklenir. Yerel değişikliklerin üzerine --hard sıfırlama yapar, bu yüzden
    yalnız CI içinde (CI=true) çalıştırılması içindir.
    """
    kok = Path(kok)
    dal = dal or os.environ.get("GITHUB_REF_NAME") or "main"
    yedek = Path(tempfile.mkdtemp())
    for d in DURUM_DOSYALARI:
        f = kok / d
        if f.exists():
            (yedek / d).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(f, yedek / d)
    for i in range(deneme):
        _git(kok, "fetch", "-q", "origin", dal)
        _git(kok, "reset", "-q", "--hard", f"origin/{dal}")
        for d in DURUM_DOSYALARI:
            y = yedek / d
            if not y.exists():
                continue
            hedef = kok / d
            hedef.parent.mkdir(parents=True, exist_ok=True)
            bizim = json.loads(y.read_text(encoding="utf-8"))
            uzak = json.loads(hedef.read_text(encoding="utf-8")) if hedef.exists() else {}
            hedef.write_text(json.dumps(dosya_birlestir(d, bizim, uzak), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        _git(kok, "add", *DURUM_DOSYALARI)
        if _git(kok, "diff", "--cached", "--quiet", kontrol=False).returncode == 0:
            print("durum: değişiklik yok")
            return True
        _git(kok, "commit", "-q", "-m", f"{mesaj}: {kq.simdi()}")
        if _git(kok, "push", "-q", "origin", f"HEAD:{dal}", kontrol=False).returncode == 0:
            print(f"durum gönderildi (deneme {i + 1})")
            return True
    print("durum gönderilemedi")
    return False
