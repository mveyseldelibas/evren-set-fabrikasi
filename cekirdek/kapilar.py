"""Yayım kapıları (saf fonksiyonlar, ağ yok).

Bir veri seti ve modeli ancak tüm kapılar geçilirse herkese açılır:
  1. veri seti öğe sayısı >= EN_AZ_OGE
  2. başarı ölçüsü >= ESIK (segment ve tespitte mAP50, sınıflandırmada top-1)
  3. lisans izin listesinde (CC0, PDDL, kamu malı, CC-BY-4.0, CC-BY-SA-4.0, ODbL; NC/ND asla)
  4. veri seti README'si ve model kartı boş değil
"""
from __future__ import annotations

EN_AZ_OGE = 1000
ESIK = 0.50
EN_AZ_METIN = 200          # README ve kart için anlamlı uzunluk (karakter)

IZINLI_LISANSLAR = {
    "cc0", "cc0-1.0", "pddl", "pddl-1.0", "public-domain", "publicdomain", "kamu-mali",
    "cc-by-4.0", "cc-by-sa-4.0", "odbl", "odbl-1.0",
}
YASAKLI_PARCALAR = ("-nc", "-nd", "noncommercial", "noderiv", "nc-", "nd-")


def lisans_norm(s: str | None) -> str:
    return (s or "").strip().lower().replace("_", "-").replace(" ", "-")


def lisans_izinli(s: str | None) -> bool:
    n = lisans_norm(s)
    if not n or any(p in n for p in YASAKLI_PARCALAR):
        return False
    return n in IZINLI_LISANSLAR


def metrik_degeri(gorev: str, m: dict | None) -> float | None:
    """Kapı ölçüsü. segment: maske mAP50 (yoksa kutu mAP50); tespit: mAP50; sınıflandırma: top1."""
    if not m:
        return None
    if gorev == "classify":
        v = m.get("top1")
    elif gorev == "segment":
        v = m.get("mask_mAP50", m.get("mAP50"))
    else:
        v = m.get("mAP50")
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def degerlendir(gorev: str, oge_sayisi: int | None, metrik: dict | None, lisans: str | None,
                readme: str | None, kart: str | None, esik: float = ESIK, en_az_oge: int = EN_AZ_OGE):
    """(gecti, nedenler) döndürür. nedenler: geçilemeyen kapıların Türkçe açıklamaları."""
    nedenler = []
    if oge_sayisi is None or oge_sayisi < en_az_oge:
        nedenler.append(f"öğe sayısı {oge_sayisi} < {en_az_oge}")
    v = metrik_degeri(gorev, metrik)
    if v is None:
        nedenler.append("başarı ölçüsü okunamadı")
    elif v < esik:
        nedenler.append(f"başarı ölçüsü {v:.3f} < {esik:.2f}")
    if not lisans_izinli(lisans):
        nedenler.append(f"lisans izinli değil: {lisans!r}")
    if not readme or len(readme.strip()) < EN_AZ_METIN:
        nedenler.append("veri seti README'si boş ya da çok kısa")
    if not kart or len(kart.strip()) < EN_AZ_METIN:
        nedenler.append("model kartı boş ya da çok kısa")
    return (not nedenler), nedenler
