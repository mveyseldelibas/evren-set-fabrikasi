"""EVREN platform API istemcisi. Anahtar yalnız EVREN_PLATFORM_KEY ortam değişkeninden gelir; asla yazdırılmaz."""
from __future__ import annotations

import io
import os
import time
import zipfile
from pathlib import Path

import requests

try:                                    # Windows yerel testi için; Linux'ta gerekmez
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

TABAN = "https://api.ssyz.org.tr/api/v1"


class ApiHata(RuntimeError):
    pass


def _veri(r):
    d = r.json()
    return d.get("data", d) if isinstance(d, dict) else d


class EvrenApi:
    def __init__(self, anahtar: str | None = None, taban: str = TABAN):
        anahtar = anahtar or os.environ.get("EVREN_PLATFORM_KEY", "").strip()
        if not anahtar:
            raise ApiHata("EVREN_PLATFORM_KEY ortam değişkeni yok")
        self.taban = taban
        self.h = {"X-API-Key": anahtar}
        self.hj = {**self.h, "Content-Type": "application/json"}

    # -- düşük düzey ---------------------------------------------------------------------
    def _iste(self, yontem, yol, deneme=3, timeout=90, **kw):
        son = None
        for i in range(deneme):
            try:
                r = requests.request(yontem, self.taban + yol, timeout=timeout, **kw)
                if r.status_code >= 500 and i < deneme - 1:
                    time.sleep(5 * (i + 1))
                    continue
                return r
            except requests.RequestException as e:
                son = e
                time.sleep(5 * (i + 1))
        raise ApiHata(f"{yontem} {yol}: ağ hatası {type(son).__name__}")

    def _tamam(self, r, ne):
        if r.status_code >= 300:
            raise ApiHata(f"{ne}: HTTP {r.status_code} {r.text[:200]}")
        return r

    # -- ödül/kota -----------------------------------------------------------------------
    def kazanc_ozeti(self) -> dict:
        r = self._tamam(self._iste("GET", "/billing/earning/overview", headers=self.h), "kazanç özeti")
        return _veri(r).get("stats", {})

    # -- veri seti -----------------------------------------------------------------------
    def set_olustur(self, ad, aciklama, lisans, gorunurluk="private") -> dict:
        r = self._tamam(self._iste("POST", "/datasets", headers=self.hj, json={
            "name": ad, "modality": "VISION", "visibility": gorunurluk, "license": lisans, "description": aciklama}),
            "set oluşturma")
        x = _veri(r)
        return {"id": x["id"], "slug": x.get("slug")}

    def zip_yukle(self, set_id, ad, icerik: bytes, deneme=5) -> bool:
        for i in range(deneme):
            try:
                r = requests.post(f"{self.taban}/datasets/{set_id}/import", headers=self.h,
                                  files={"file": (f"{ad}.zip", icerik, "application/zip")}, timeout=(60, 900))
                son = r.text.strip().splitlines()[-1][:240] if r.text.strip() else ""
                if r.status_code == 200 and '"t": "d"' in son:
                    return True
            except requests.RequestException:
                pass
            time.sleep(30 * (i + 1))
        return False

    def ogeler(self, set_id) -> list[dict]:
        sonuc, imlec = [], None
        while True:
            p = {"limit": 200, **({"cursor": imlec} if imlec else {})}
            r = self._tamam(self._iste("GET", f"/datasets/{set_id}/items", headers=self.h, params=p, timeout=120),
                            "öğe listesi")
            j = r.json()
            sonuc += j["items"]
            imlec = j.get("next_cursor")
            if not imlec:
                return sonuc

    def surum_olustur(self, set_id, etiket, aciklama) -> dict:
        r = self._tamam(self._iste("POST", f"/datasets/{set_id}/versions", headers=self.hj, deneme=1, timeout=900,
                                   json={"version_tag": etiket, "description": aciklama}), "sürüm oluşturma")
        return _veri(r)

    def set_readme(self, set_id, metin) -> None:
        self._tamam(self._iste("PATCH", f"/datasets/{set_id}", headers=self.hj, json={"readme": metin}), "set readme")

    def set_gorunurluk(self, set_id, gorunurluk) -> None:
        self._tamam(self._iste("PATCH", f"/datasets/{set_id}", headers=self.hj, json={"visibility": gorunurluk}),
                    "set görünürlüğü")

    # -- eğitim --------------------------------------------------------------------------
    def proje_olustur(self, ad, aciklama) -> str:
        r = self._tamam(self._iste("POST", "/projects", headers=self.hj, json={
            "name": ad, "description": aciklama[:300], "visibility": "private"}), "proje")
        return _veri(r)["id"]

    def egitim_kuru(self, proje_id, govde) -> dict:
        r = self._iste("POST", "/training/jobs/dry-run", headers=self.hj, json=govde, params={"project_id": proje_id})
        return r.json()

    def egitim_baslat(self, proje_id, govde) -> str:
        r = self._tamam(self._iste("POST", "/training/jobs", headers=self.hj, json=govde, deneme=1, timeout=120,
                                   params={"project_id": proje_id}), "eğitim başlatma")
        return _veri(r)["id"]

    def is_getir(self, is_id) -> dict:
        r = self._tamam(self._iste("GET", f"/training/jobs/{is_id}", headers=self.h), "eğitim işi")
        return _veri(r)

    # -- model ---------------------------------------------------------------------------
    def modeller(self) -> list[dict]:
        sonuc, ofs = [], 0
        while True:
            r = self._tamam(self._iste("GET", "/models", headers=self.h,
                                       params={"limit": 100, "offset": ofs, "mine": "true"}, timeout=60), "model listesi")
            j = r.json()
            ogeler = j.get("items", j) if isinstance(j, dict) else j
            sonuc += ogeler
            if len(ogeler) < 100:
                return sonuc
            ofs += 100

    def model_gorunurluk(self, model_id, gorunurluk) -> None:
        self._tamam(self._iste("PATCH", f"/models/{model_id}/visibility", headers=self.hj,
                               json={"visibility": gorunurluk}), "model görünürlüğü")

    def model_karti(self, model_id, icerik) -> None:
        self._tamam(self._iste("PUT", f"/models/{model_id}/card", headers=self.hj, json={"content": icerik}),
                    "model kartı")

    def model_atif(self, model_id, lisans, kaynak, atif) -> int:
        return self._iste("PATCH", f"/models/{model_id}/attribution", headers=self.hj,
                          json={"license": lisans, "source_info": kaynak, "citation_text": atif}).status_code

    def model_aciklama(self, model_id, aciklama) -> None:
        self._tamam(self._iste("PATCH", f"/models/{model_id}/description", headers=self.hj,
                               json={"description": aciklama}), "model açıklaması")


def zip_parca(set_dizini: Path, bolum: str, dosyalar: list[Path]) -> bytes:
    """YOLO çokgen ZIP parçası: data.yaml + images/<bolum> + labels/<bolum>."""
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_STORED) as z:
        z.write(set_dizini / "data.yaml", "data.yaml")
        for f in dosyalar:
            z.write(f, f"images/{bolum}/{f.name}")
            z.write(set_dizini / "labels" / bolum / f"{f.stem}.txt", f"labels/{bolum}/{f.stem}.txt")
    return tampon.getvalue()
