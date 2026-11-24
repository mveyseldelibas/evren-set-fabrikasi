"""kuyruk.json: tarif sırası ve durum makinesi.

bekliyor -> yuklendi -> egitimde -> yayimlandi | zayif | hata
(bekliyor ve yuklendi doğrudan hata'ya düşebilir)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

DURUMLAR = ("bekliyor", "yuklendi", "egitimde", "yayimlandi", "zayif", "hata")
GECISLER = {
    "bekliyor": {"yuklendi", "hata"},
    "yuklendi": {"egitimde", "hata"},
    "egitimde": {"yayimlandi", "zayif", "hata"},
    "yayimlandi": set(), "zayif": set(), "hata": {"bekliyor"},   # hata -> bekliyor: elle yeniden deneme
}
# birleştirmede ilerlik sırası (uçtaki durumlar: hata < zayıf < yayımlandı)
SIRA = {"bekliyor": 0, "yuklendi": 1, "egitimde": 2, "hata": 3, "zayif": 4, "yayimlandi": 5}


def simdi() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def bugun() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def yeni_oge(tarif_id: str) -> dict:
    return {"id": tarif_id, "durum": "bekliyor"}


def yukle(yol: Path) -> dict:
    return json.loads(Path(yol).read_text(encoding="utf-8"))


def kaydet(yol: Path, k: dict) -> None:
    Path(yol).write_text(json.dumps(k, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def esitle(k: dict, tarif_idleri: list[str]) -> dict:
    """Kayıtlı tariflerle kuyruğu eşitle: yeni tarifler sona eklenir, mevcut olanlara dokunulmaz."""
    var = {o["id"] for o in k["ogeler"]}
    for t in tarif_idleri:
        if t not in var:
            k["ogeler"].append(yeni_oge(t))
    return k


def bul(k: dict, tarif_id: str) -> dict:
    return next(o for o in k["ogeler"] if o["id"] == tarif_id)


def gecis(oge: dict, yeni: str, **alanlar) -> dict:
    eski = oge["durum"]
    if yeni not in GECISLER.get(eski, ()):
        raise ValueError(f"izinsiz geçiş: {eski} -> {yeni} ({oge['id']})")
    oge["durum"] = yeni
    oge.setdefault("zamanlar", {})[yeni] = simdi()
    oge.update(alanlar)
    return oge


def sirada_bekleyen(k: dict) -> dict | None:
    return next((o for o in k["ogeler"] if o["durum"] == "bekliyor"), None)


def egitimdekiler(k: dict) -> list[dict]:
    return [o for o in k["ogeler"] if o["durum"] == "egitimde"]


def bugun_baslayan(k: dict, gun: str | None = None) -> int:
    """Bugün (UTC) yükleme/eğitim başlatılan öğe sayısı."""
    gun = gun or bugun()
    return sum(1 for o in k["ogeler"] if (o.get("zamanlar") or {}).get("egitimde", "")[:10] == gun
               or (o.get("zamanlar") or {}).get("yuklendi", "")[:10] == gun)


def kalan_tarif(k: dict) -> int:
    return sum(1 for o in k["ogeler"] if o["durum"] == "bekliyor")


def birlestir(bizim: dict, uzak: dict) -> dict:
    """İki kuyruğu birleştir: her tarif için daha ilerideki durum kazanır; eşitse bizimki."""
    sonuc = {**uzak, **bizim}
    u = {o["id"]: o for o in uzak.get("ogeler", [])}
    b = {o["id"]: o for o in bizim.get("ogeler", [])}
    sira = [o["id"] for o in bizim.get("ogeler", [])] + [i for i in u if i not in b]
    ogeler = []
    for i in sira:
        a, c = b.get(i), u.get(i)
        if a is None:
            ogeler.append(c)
        elif c is None or SIRA[a["durum"]] >= SIRA[c["durum"]]:
            ogeler.append(a)
        else:
            ogeler.append(c)
    sonuc["ogeler"] = ogeler
    return sonuc
