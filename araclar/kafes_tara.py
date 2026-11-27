"""Balık çiftliği kafesi adayı tarayıcı (Sentinel-2 L2A, bulutta çalışır).

Kafesler 10 m görüntüde suyun içinde birkaç piksellik parlak lekelerdir. Tekneler de parlaktır ama yer değiştirir;
bu yüzden bir leke ancak farklı tarihlerin en az ikisinde aynı yerde görünüyorsa aday sayılır. Kıyıya ve büyük kara
parçalarına değen lekeler atılır. Sonuç yalnız ADAYDIR: her pencere sonra görsel olarak denetlenir.

Çıktı (cikti dizini):
  adaylar.json : pencere sınırları (EPSG), tarihler/sahneler, lekeler (piksel koordinatlı çokgen), su oranı
  onizleme/<id>.png : t0 RGB (2x büyütülmüş) + lekelerin kırmızı çerçevesi, denetim için
Kullanım: python araclar/kafes_tara.py <cikti> [sure_sn=18000]
"""
from __future__ import annotations

import json
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tarifler import s2_osm  # noqa: E402
from tarifler.s2_osm import KARO, PENCERE_M, Uretici  # noqa: E402

BOLGELER = {   # (batı, güney, doğu, kuzey)
    "gulluk_milas": (27.35, 37.05, 27.75, 37.35), "bodrum": (27.20, 36.95, 27.60, 37.10),
    "gokova_oren": (27.85, 36.95, 28.20, 37.05), "didim_akbuk": (27.25, 37.30, 27.50, 37.45),
    "cesme_karaburun": (26.25, 38.30, 26.75, 38.75), "dikili_candarli": (26.70, 38.85, 27.10, 39.15),
    "seferihisar_kusadasi": (26.70, 37.85, 27.10, 38.25), "dogu_karadeniz": (39.60, 40.90, 41.00, 41.10),
    "keban": (38.20, 38.60, 39.80, 39.00), "karakaya": (38.40, 38.20, 39.30, 38.60), "ataturk": (38.20, 37.30, 39.20, 37.90),
}
TARIH = ("2024-05-01", "2024-10-31")
PARLAK_NIR = 450          # BOA yansıtım (ofset düşülmüş); açık su genelde < 300
EN_AZ_TARIH = 2


def pencereler():
    from pyproj import Transformer
    for ad, (w, s, e, n) in BOLGELER.items():
        lat0 = (s + n) / 2
        dlat = PENCERE_M / 111320.0
        dlon = dlat / math.cos(math.radians(lat0))
        lat = s + dlat / 2
        while lat < n:
            lon = w + dlon / 2
            while lon < e:
                yield {"bolge": ad, "lon": lon, "lat": lat, "id": f"{ad}_{int(lat * 1e4)}_{int(lon * 1e4)}"}
                lon += dlon
            lat += dlat


class Tarayici(Uretici):
    def __init__(self, cikti):
        s2_osm.Kaynak.BANTLAR = ("B02", "B03", "B04", "B08", "SCL")
        super().__init__({"siniflar": []}, [], cikti, 1)
        self.sonuc, self.say = [], __import__("collections").Counter()

    def _bant_f(self, s, b, sinir):
        v = self._bant(s, b, sinir).astype(np.int32)
        if s["tarih"] >= s2_osm.OFSET_TARIHI:
            v = np.clip(v - s2_osm.OFSET, 0, None)
        return v

    def tara(self, w):
        import cv2
        import shapely
        from pyproj import Transformer
        from scipy import ndimage
        try:
            sahneler = self.kaynak.hucre_sahneleri(w["lon"], w["lat"])
            dlat = PENCERE_M / 2 / 111320.0
            dlon = dlat / max(0.2, abs(math.cos(math.radians(w["lat"]))))
            ayak = shapely.box(w["lon"] - dlon, w["lat"] - dlat, w["lon"] + dlon, w["lat"] + dlat)
            ad = [s for s in sahneler if s["geom"].contains(ayak) and TARIH[0] <= s["tarih"] <= TARIH[1]]
            if not ad:
                self.say["sahne_yok"] += 1
                return
            epsg = max(set(s["epsg"] for s in ad), key=lambda e: sum(1 for s in ad if s["epsg"] == e))
            ad = sorted([s for s in ad if s["epsg"] == epsg], key=lambda s: s["bulut"])
            cx, cy = Transformer.from_crs(4326, epsg, always_xy=True).transform(w["lon"], w["lat"])
            x0 = float(round((cx - PENCERE_M / 2) / 20) * 20); y0 = float(round((cy - PENCERE_M / 2) / 20) * 20)
            sinir = (x0, y0, x0 + PENCERE_M, y0 + PENCERE_M)
            # su oranı: en az bulutlu tek sahnenin SCL'si (ucuz eleme)
            scl0 = self._scl(ad[0], sinir)
            su0 = float(np.mean(scl0 == 6))
            if su0 < 0.25:
                self.say["su_az"] += 1
                return
            secilen, sayac = [], 0
            for s in ad:
                if len(secilen) >= 3 or sayac >= 8:
                    break
                sayac += 1
                if any(abs(s2_osm._gun(s["tarih"]) - s2_osm._gun(x["tarih"])) < 20 for x in secilen):
                    continue
                if self._gecerli(s, sinir) is None:
                    continue
                secilen.append(s)
            if len(secilen) < EN_AZ_TARIH:
                self.say["tarih_az"] += 1
                return
            nir, rgb, su = [], None, []
            for i, s in enumerate(secilen):
                nir.append(self._bant_f(s, "B08", sinir)) if "B08" in s["h"] else None
                scl = self._scl(s, sinir); su.append(scl == 6)
                if i == 0:
                    rgb = self._rgb(s, sinir)[0]
            if len(nir) < EN_AZ_TARIH:
                self.say["nir_yok"] += 1
                return
            su_cok = np.sum(su, axis=0) >= max(1, len(su) - 1)           # çoğu tarihte su
            deniz = ndimage.binary_fill_holes(su_cok)                        # kafes/tekne delikleri dolar
            kara, nk = ndimage.label(~su_cok)
            buyuk = np.zeros_like(su_cok)
            for k_, n_ in zip(*np.unique(kara[kara > 0], return_counts=True)):
                if n_ > 150:
                    buyuk |= kara == k_
            buyuk = ndimage.binary_dilation(buyuk, iterations=3)
            parlak = np.sum([n > PARLAK_NIR for n in nir], axis=0) >= EN_AZ_TARIH
            aday = parlak & deniz & ~buyuk
            lab, n = ndimage.label(aday)
            lekeler = []
            for k_ in range(1, n + 1):
                m = lab == k_
                a = int(m.sum())
                if a < 2 or a > 80:
                    continue
                c = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0][0].reshape(-1, 2)
                lekeler.append({"piksel": a, "kontur": c.tolist(), "merkez": [float(np.mean(np.nonzero(m)[1])), float(np.mean(np.nonzero(m)[0]))]})
            if len(lekeler) < 2:
                self.say["leke_az"] += 1
                return
            kayit = {"id": w["id"], "bolge": w["bolge"], "lon": w["lon"], "lat": w["lat"], "epsg": epsg, "sinir": sinir,
                     "su_orani": round(su0, 3), "tarihler": [s["tarih"] for s in secilen], "sahneler": [s["id"] for s in secilen],
                     "lekeler": lekeler}
            b = cv2.cvtColor(cv2.resize(rgb, (KARO * 2, KARO * 2), interpolation=cv2.INTER_NEAREST), cv2.COLOR_RGB2BGR)
            b = np.clip(b.astype(np.float32) * 1.6, 0, 255).astype(np.uint8)
            for l_ in lekeler:
                x, y, ww, hh = cv2.boundingRect(np.array(l_["kontur"]))
                cv2.rectangle(b, (2 * x - 3, 2 * y - 3), (2 * (x + ww) + 3, 2 * (y + hh) + 3), (0, 0, 255), 1)
            cv2.imwrite(str(self.cikti / "onizleme" / f"{w['id']}.png"), b)
            with self.kilit:
                self.sonuc.append(kayit); self.say["aday"] += 1
        except Exception as e:
            self.say["hata:" + type(e).__name__] += 1


def main(cikti: Path, sure_sn: int):
    (cikti / "onizleme").mkdir(parents=True, exist_ok=True)
    W = list(pencereler())
    print("pencere:", len(W), flush=True)
    t = Tarayici(cikti); t0 = time.time()
    try:
        with ThreadPoolExecutor(max_workers=12) as ex:
            for i in range(0, len(W), 96):
                if time.time() - t0 > sure_sn:
                    print("süre doldu", flush=True); break
                list(ex.map(t.tara, W[i:i + 96]))
                print(f"  {min(i + 96, len(W))}/{len(W)} | {dict(t.say)} | {time.time() - t0:.0f} sn", flush=True)
                (cikti / "adaylar.json").write_text(json.dumps(t.sonuc, ensure_ascii=False), encoding="utf-8")
    finally:
        t.kaynak.kapat()
    (cikti / "adaylar.json").write_text(json.dumps(t.sonuc, ensure_ascii=False), encoding="utf-8")
    print("bitti, aday:", len(t.sonuc), flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 18000)
