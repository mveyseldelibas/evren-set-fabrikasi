"""Genel tarif motoru: Sentinel-2 L2A (Microsoft Planetary Computer) + OpenStreetMap konu çokgenleri.

Bir tarif şunları verir: sınıflar (OSM etiket kuralları), pencere hedefi, görüntü boyutu. Motor:
  1. OSM çokgenlerini çıkarır (osm_cikar), boyut süzgecinden geçirir.
  2. Her çokgene 224x224 px (10 m, 2,24 km) pencere planlar; büyük çokgenlere en çok 3 pencere;
     pencere merkezleri birbirine en az 1,5 km uzak. Sınıf başına tavanla dengeler.
  3. Pencereleri 4 km içindekileri bir küme sayarak konum kümelerine ayırır; böler: train/val/test ~70/20/10
     (tohumlu, kümeler bütün olarak bir bölüme gider -> konum sızıntısı yok).
  4. Her pencere için Planetary Computer'dan farklı mevsimlerden en çok 3 GERÇEK tarih seçer
     (SCL: bulut/gölge <= %3, kar <= %5, boş piksel <= %0,5; kış dışlanır; tarihler arası >= 20 gün).
     Tarih kopyalanmaz; hiç geçerli tarih yoksa pencere atılır. Etiketsiz (negatif) pencere yoktur.
  5. RGB JPEG + YOLO çokgen etiketi (pencerede görünen bütün sınıflar) yazar; data.yaml, ozet.json, meta.jsonl.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import random
import threading
import time
from collections import Counter, OrderedDict, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "4")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "2")
os.environ.setdefault("GDAL_HTTP_MERGE_CONSECUTIVE_RANGES", "YES")
os.environ.setdefault("GDAL_HTTP_TIMEOUT", "60")
os.environ.setdefault("GDAL_CACHEMAX", "256")

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
KOLEKSIYON = "sentinel-2-l2a"
DONEM_BASI = "2019-01-01"
KARO = 224
PX_M = 10.0
PENCERE_M = KARO * PX_M
EN_COK_SAHNE_BULUT = 40
SCL_BULUT = (3, 8, 9, 10)
SCL_KAR, SCL_NODATA = 11, 0
EN_COK_BULUT, EN_COK_BOS, EN_COK_KAR = 0.03, 0.005, 0.05
EN_COK_DENEME = 14
EN_AZ_ARALIK_GUN = 20
OFSET_TARIHI, OFSET = "2022-01-25", 1000
MIN_PENCERE_ARALIGI_M = 1500.0
KUME_M = 4000.0
BOLUM_ORAN = {"train": 0.70, "val": 0.20, "test": 0.10}
MEVSIM = {3: "ilkbahar", 4: "ilkbahar", 5: "ilkbahar", 6: "yaz", 7: "yaz", 8: "yaz", 9: "sonbahar", 10: "sonbahar",
          11: "sonbahar", 12: "kis", 1: "kis", 2: "kis"}


def mevsim(tarih: str) -> str:
    return MEVSIM[int(tarih[5:7])]


def _gun(t):
    return dt.date.fromisoformat(t).toordinal()


def yeniden_dene(islem, deneme=4, taban=2.0):
    son = None
    for i in range(deneme):
        try:
            return islem()
        except Exception as e:
            son = e
            if i < deneme - 1:
                time.sleep(taban * (2 ** i))
    raise son


# ================================================================== planlama (ağ yok, saf)
def pencere_planla(cokgenler, siniflar, hedef_pencere, tohum, sinif_tavani=None, log=print):
    """Çokgenlerden pencere merkezleri (aea metre + lon/lat) üretir. cokgenler: osm_cikar.cikar çıktısı."""
    import numpy as np
    import shapely
    from pyproj import Transformer
    from shapely.geometry import box
    from tarifler.osm_cikar import ALAN_PROJ

    ileri = Transformer.from_crs(4326, ALAN_PROJ, always_xy=True)
    geri = Transformer.from_crs(ALAN_PROJ, 4326, always_xy=True)
    rng = random.Random(tohum)
    aday = []                                    # (sinif, x, y, cokgen_id, alan)
    for c in cokgenler:
        g = shapely.transform(c["geom"], lambda a: np.column_stack(ileri.transform(a[:, 0], a[:, 1])))
        x0, y0, x1, y1 = g.bounds
        if max(x1 - x0, y1 - y0) <= PENCERE_M * 0.9:
            p = g.centroid
            if not g.contains(p):
                p = g.representative_point()
            aday.append((c["sinif"], p.x, p.y, c["id"], c["alan_m2"]))
        else:
            parcalar = []
            nx, ny = int((x1 - x0) // PENCERE_M) + 1, int((y1 - y0) // PENCERE_M) + 1
            for i in range(nx):
                for j in range(ny):
                    cx, cy = x0 + (i + 0.5) * PENCERE_M, y0 + (j + 0.5) * PENCERE_M
                    kutu = box(cx - PENCERE_M / 2, cy - PENCERE_M / 2, cx + PENCERE_M / 2, cy + PENCERE_M / 2)
                    if g.intersection(kutu).area >= 0.2 * kutu.area:
                        parcalar.append((cx, cy))
            if not parcalar:
                p = g.representative_point()
                parcalar = [(p.x, p.y)]
            rng.shuffle(parcalar)
            for cx, cy in parcalar[:3]:
                aday.append((c["sinif"], cx, cy, c["id"], c["alan_m2"]))
    rng.shuffle(aday)
    log(f"pencere adayı: {len(aday)} ({dict(Counter(siniflar[a[0]]['ad'] for a in aday))})")

    # sınıf tavanı: baskın sınıf diğerlerini ezmesin
    n_sinif = len(siniflar)
    tavan = sinif_tavani or max(1, int(hedef_pencere / n_sinif * 1.6))
    kovalar = defaultdict(list)
    for a in aday:
        kovalar[a[0]].append(a)
    sirali = []
    sayac = Counter()
    # sınıfları dönüşümlü doldur (en az örneklisi önce)
    sira_sinif = sorted(kovalar, key=lambda k: len(kovalar[k]))
    imleç = {k: 0 for k in kovalar}
    secilen, hucre = [], defaultdict(list)       # hücre: 1,5 km ızgara, uzaklık denetimi için
    ayni_cokgen = defaultdict(list)

    def uzak_mi(x, y, cid):
        hx, hy = int(x // MIN_PENCERE_ARALIGI_M), int(y // MIN_PENCERE_ARALIGI_M)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for (px, py, pid) in hucre.get((hx + dx, hy + dy), ()):
                    d = ((px - x) ** 2 + (py - y) ** 2) ** 0.5
                    if d < MIN_PENCERE_ARALIGI_M and not (pid == cid and d >= PENCERE_M * 0.9):
                        return False
        return True

    ilerleme = True
    while ilerleme and len(secilen) < hedef_pencere:
        ilerleme = False
        for k in sira_sinif:
            if len(secilen) >= hedef_pencere:
                break
            if sayac[k] >= tavan:
                continue
            while imleç[k] < len(kovalar[k]):
                a = kovalar[k][imleç[k]]
                imleç[k] += 1
                if uzak_mi(a[1], a[2], a[3]):
                    secilen.append(a)
                    sayac[k] += 1
                    hucre[(int(a[1] // MIN_PENCERE_ARALIGI_M), int(a[2] // MIN_PENCERE_ARALIGI_M))].append((a[1], a[2], a[3]))
                    ilerleme = True
                    break
    penceler = []
    for sn, x, y, cid, alan in secilen:
        lon, lat = geri.transform(x, y)
        penceler.append({"konum_id": f"k{int(round(lat * 1e4))}_{int(round(lon * 1e4))}", "sinif": sn,
                         "x": x, "y": y, "lon": lon, "lat": lat, "cokgen_id": cid, "alan_m2": alan})
    log(f"seçilen pencere: {len(penceler)} ({ {siniflar[k]['ad']: v for k, v in sayac.items()} })")
    return penceler


def kumele_ve_bol(penceler, tohum):
    """4 km içindeki pencereleri tek kümede topla (birleşim-bul), kümeleri sınıfa göre katmanlı 70/20/10 böl."""
    n = len(penceler)
    ata = list(range(n))

    def bul(i):
        while ata[i] != i:
            ata[i] = ata[ata[i]]
            i = ata[i]
        return i
    hucre = defaultdict(list)
    for i, p in enumerate(penceler):
        hucre[(int(p["x"] // KUME_M), int(p["y"] // KUME_M))].append(i)
    for (hx, hy), idx in hucre.items():
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in hucre.get((hx + dx, hy + dy), ()):
                    for i in idx:
                        if i < j and ((penceler[i]["x"] - penceler[j]["x"]) ** 2 + (penceler[i]["y"] - penceler[j]["y"]) ** 2) ** 0.5 < KUME_M:
                            ata[bul(i)] = bul(j)
    kume = defaultdict(list)
    for i in range(n):
        kume[bul(i)].append(i)
    rng = random.Random(f"bol:{tohum}")
    liste = list(kume.values())
    rng.shuffle(liste)
    # en nadir sınıfı içeren kümeler önce: nadir sınıf bölümlere yayılsın
    toplam = Counter(p["sinif"] for p in penceler)
    liste.sort(key=lambda g: min(toplam[penceler[i]["sinif"]] for i in g))
    sayim = {b: Counter() for b in BOLUM_ORAN}
    for g in liste:
        sinif_say = Counter(penceler[i]["sinif"] for i in g)
        baskin = sinif_say.most_common(1)[0][0]

        def acik(b):
            hedef = BOLUM_ORAN[b] * toplam[baskin]
            return (hedef - sayim[b][baskin]) / max(hedef, 1e-9)
        b = max(BOLUM_ORAN, key=lambda k: (acik(k), rng.random()))
        for i in g:
            penceler[i]["bolum"] = b
            penceler[i]["kume"] = bul(g[0])
        for s, v in sinif_say.items():
            sayim[b][s] += v
    return penceler


# ================================================================== Sentinel-2 okuma
class Kaynak:
    """Planetary Computer: hücre başına STAC araması (önbellekli) + açık COG LRU önbelleği."""

    HUCRE_DERECE = 0.2
    BANTLAR = ("B02", "B03", "B04", "SCL")    # alt sınıflar ek bant isteyebilir (ör. kafes taraması B08)

    def __init__(self, en_cok_acik=64):
        import pystac_client
        self.istemci = pystac_client.Client.open(STAC_URL)
        self.acik = OrderedDict()
        self.kilit = threading.Lock()
        self.en_cok_acik = en_cok_acik
        self.arama_onbellek = {}
        self.arama_kilitleri = defaultdict(threading.Lock)

    def hucre_sahneleri(self, lon, lat):
        from shapely.geometry import shape
        h = self.HUCRE_DERECE
        anahtar = (int(lon // h), int(lat // h))
        with self.arama_kilitleri[anahtar]:
            if anahtar in self.arama_onbellek:
                return self.arama_onbellek[anahtar]
            bbox = [anahtar[0] * h - 0.03, anahtar[1] * h - 0.03, (anahtar[0] + 1) * h + 0.03, (anahtar[1] + 1) * h + 0.03]
            alanlar = {"include": ["id", "geometry", "properties.datetime", "properties.eo:cloud_cover",
                                   "properties.s2:mgrs_tile", "properties.proj:epsg", "properties.proj:code"]
                                  + [f"assets.{b}.href" for b in self.BANTLAR],
                       "exclude": ["links"]}
            bugun = dt.date.today().isoformat()

            def f():
                return list(self.istemci.search(collections=[KOLEKSIYON], bbox=bbox,
                                                datetime=f"{DONEM_BASI}/{bugun}",
                                                query={"eo:cloud_cover": {"lt": EN_COK_SAHNE_BULUT}}, limit=500,
                                                fields=alanlar).items_as_dicts())
            ogeler = yeniden_dene(f)
            sahneler = []
            for o in ogeler:
                p = o["properties"]
                epsg = p.get("proj:epsg")
                if epsg is None and str(p.get("proj:code", "")).startswith("EPSG:"):
                    epsg = int(p["proj:code"].split(":")[1])
                v = o.get("assets", {})
                if epsg is None or any(b not in v for b in self.BANTLAR):
                    continue
                sahneler.append({"id": o["id"], "tarih": p["datetime"][:10], "bulut": float(p["eo:cloud_cover"]),
                                 "epsg": int(epsg), "geom": shape(o["geometry"]),
                                 "h": {b: v[b]["href"].split("?", 1)[0] for b in self.BANTLAR}})
            self.arama_onbellek[anahtar] = sahneler
            return sahneler

    def _ac(self, href, yeni=False):
        import planetary_computer
        import rasterio
        with self.kilit:
            if href in self.acik:
                if not yeni:
                    self.acik.move_to_end(href)
                    return self.acik[href]
                eski, ekl = self.acik.pop(href)
                with ekl:                      # 26.11: başka iş parçacığı okurken kapatma segfault veriyordu
                    eski.close()
        ds = yeniden_dene(lambda: rasterio.open(planetary_computer.sign(href)))
        with self.kilit:
            if href in self.acik:
                ds.close()
                return self.acik[href]
            self.acik[href] = (ds, threading.Lock())
            while len(self.acik) > self.en_cok_acik:
                _, (e, ekl) = self.acik.popitem(last=False)
                try:
                    with ekl:                  # okuyan iş parçacığı bitmeden kapatma (26.11 segfault)
                        e.close()
                except Exception:
                    pass
            return self.acik[href]

    def oku(self, href, islem):
        def bir(yeni):
            ds, kl = self._ac(href, yeni=yeni)
            with kl:
                return islem(ds)
        try:
            return bir(False)
        except Exception:
            return yeniden_dene(lambda: bir(True), deneme=3)

    def kapat(self):
        with self.kilit:
            for ds, _ in self.acik.values():
                try:
                    ds.close()
                except Exception:
                    pass
            self.acik.clear()


class Uretici:
    def __init__(self, tarif, cokgenler, cikti: Path, tohum, log=print):
        import shapely
        self.tarif, self.cikti, self.tohum, self.log = tarif, Path(cikti), tohum, log
        self.siniflar = tarif["siniflar"]
        self.kaynak = Kaynak()
        self.cokgenler = cokgenler
        self.geom = [c["geom"] for c in cokgenler]
        self.agac = shapely.STRtree(self.geom)
        self.kilit = threading.Lock()
        self.say = Counter()
        self.meta = []

    # ---- sahne seçimi ve okuma
    def _scl(self, s, sinirlar):
        from rasterio.enums import Resampling
        from rasterio.windows import from_bounds

        def f(ds):
            w = from_bounds(*sinirlar, transform=ds.transform)
            return ds.read(1, window=w, out_shape=(KARO, KARO), resampling=Resampling.nearest)
        return self.kaynak.oku(s["h"]["SCL"], f)

    def _bant(self, s, bant, sinirlar):
        from rasterio.windows import from_bounds

        def f(ds):
            w = from_bounds(*sinirlar, transform=ds.transform)
            if max(abs(w.col_off - round(w.col_off)), abs(w.row_off - round(w.row_off))) > 1e-3:
                raise ValueError("izgara hizasız")
            v = ds.read(1, window=w.round_offsets().round_lengths())
            if v.shape != (KARO, KARO):
                raise ValueError(f"boyut {v.shape}")
            return v
        return self.kaynak.oku(s["h"][bant], f)

    def _gecerli(self, s, sinirlar):
        import numpy as np
        scl = self._scl(s, sinirlar)
        bos = float(np.mean(scl == SCL_NODATA))
        bulut = float(np.mean(np.isin(scl, SCL_BULUT)))
        kar = float(np.mean(scl == SCL_KAR))
        if bos > EN_COK_BOS or bulut > EN_COK_BULUT or kar > EN_COK_KAR:
            return None
        return bulut, kar

    def _sec(self, adaylar, sinirlar, rng):
        gr = defaultdict(list)
        for c in adaylar:
            m = mevsim(c["tarih"])
            if m != "kis":
                gr[m].append(c)
        for m, g in gr.items():
            g.sort(key=lambda c: c["bulut"])
            iyi = [c for c in g if c["bulut"] < 15] or g[:12]
            rng.shuffle(iyi)
            gr[m] = iyi + [c for c in g if c not in iyi]
        secilen, deneme, denenen = [], 0, set()

        def uygun(c):
            return all(abs(_gun(c["tarih"]) - _gun(s["tarih"])) >= EN_AZ_ARALIK_GUN for s in secilen)

        def dene(c):
            nonlocal deneme
            deneme += 1
            denenen.add(c["id"])
            try:
                g = self._gecerli(c, sinirlar)
            except Exception:
                self.say["okumaHatasi"] += 1
                return False
            if g is None:
                self.say["bulutKarBos"] += 1
                return False
            secilen.append({**c, "karo_bulut": g[0], "karo_kar": g[1]})
            return True

        for mev in ("yaz", "ilkbahar", "sonbahar"):
            for c in gr.get(mev, [])[:4]:
                if len(secilen) >= 3 or deneme >= EN_COK_DENEME:
                    break
                if uygun(c) and dene(c):
                    break
        if len(secilen) < 3:
            kalan = [c for c in adaylar if c["id"] not in denenen and mevsim(c["tarih"]) != "kis"]
            rng.shuffle(kalan)
            for c in kalan:
                if len(secilen) >= 3 or deneme >= EN_COK_DENEME:
                    break
                if uygun(c):
                    dene(c)
        secilen.sort(key=lambda s: s["tarih"])
        return secilen

    def _rgb(self, s, sinirlar):
        import numpy as np
        ham = np.stack([self._bant(s, b, sinirlar) for b in ("B04", "B03", "B02")]).astype(np.int32)
        gecerli = (ham > 0).all(axis=0)
        if s["tarih"] >= OFSET_TARIHI:
            ham = np.clip(ham - OFSET, 0, None)
        bos = float(1 - gecerli.mean())
        x = np.clip(ham / 3500.0, 0, 1) ** 0.9 * 255
        return np.transpose(x, (1, 2, 0)).astype(np.uint8), bos

    # ---- etiket
    def etiket_satirlari(self, epsg, sinirlar):
        """Pencere içindeki bütün sınıf çokgenlerini maskeye çizip YOLO çokgen satırlarına çevirir."""
        import cv2
        import numpy as np
        import shapely
        from pyproj import Transformer
        from rasterio.features import rasterize
        x0, y0, x1, y1 = sinirlar
        geri = Transformer.from_crs(epsg, 4326, always_xy=True)
        ileri = Transformer.from_crs(4326, epsg, always_xy=True)
        w0, s0, w1, s1 = geri.transform_bounds(x0, y0, x1, y1, densify_pts=21)
        idx = self.agac.query(shapely.box(w0, s0, w1, s1), predicate="intersects")

        def piksele(a):
            xs, ys = ileri.transform(a[:, 0], a[:, 1])
            return np.column_stack([(np.asarray(xs) - x0) / PX_M, (y1 - np.asarray(ys)) / PX_M])
        liste = []
        for i in idx:
            g = shapely.transform(self.geom[i], piksele)
            g = shapely.make_valid(g) if not g.is_valid else g
            if not g.is_empty:
                liste.append((self.cokgenler[i]["sinif"], g))
        liste.sort(key=lambda t: -t[0])             # önce yüksek indeks, en üstte 0. sınıf
        maske = np.full((KARO, KARO), 255, np.uint8)
        for sn, g in liste:
            r = rasterize([(g, 1)], out_shape=(KARO, KARO), fill=0, dtype="uint8")
            maske[r == 1] = sn
        satir, piksel = [], Counter()
        for sn in range(len(self.siniflar)):
            ik = (maske == sn).astype(np.uint8)
            if not ik.any():
                continue
            piksel[sn] = int(ik.sum())
            for c in cv2.findContours(ik, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
                if cv2.contourArea(c) < 4:
                    continue
                c = cv2.approxPolyDP(c, 1.0, True).reshape(-1, 2)
                if len(c) < 3:
                    continue
                satir.append(f"{sn} " + " ".join(f"{x / KARO:.5f} {y / KARO:.5f}" for x, y in c))
        return satir, piksel

    # ---- pencere
    def isle(self, w):
        import cv2
        from pyproj import Transformer
        import shapely
        rng = random.Random(f"{self.tohum}:{w['konum_id']}")
        try:
            sahneler = self.kaynak.hucre_sahneleri(w["lon"], w["lat"])
            dlat = PENCERE_M / 2 / 111320.0
            dlon = dlat / max(0.2, abs(math.cos(math.radians(w["lat"]))))
            ayak = shapely.box(w["lon"] - dlon, w["lat"] - dlat, w["lon"] + dlon, w["lat"] + dlat)
            kapsayan = [s for s in sahneler if s["geom"].contains(ayak)]
            if not kapsayan:
                self.say["sahne_yok"] += 1
                return None
            epsg = Counter(s["epsg"] for s in kapsayan).most_common(1)[0][0]
            adaylar = [s for s in kapsayan if s["epsg"] == epsg]
            cx, cy = Transformer.from_crs(4326, epsg, always_xy=True).transform(w["lon"], w["lat"])
            x0 = float(round((cx - PENCERE_M / 2) / 20) * 20)
            y0 = float(round((cy - PENCERE_M / 2) / 20) * 20)
            sinirlar = (x0, y0, x0 + PENCERE_M, y0 + PENCERE_M)
            secilen = self._sec(adaylar, sinirlar, rng)
            if not secilen:
                self.say["gecerli_tarih_yok"] += 1
                return None
            gor = []
            for s in secilen:
                try:
                    img, bos = self._rgb(s, sinirlar)
                except Exception:
                    self.say["okumaHatasi"] += 1
                    continue
                if bos > EN_COK_BOS * 4:
                    self.say["bosPiksel"] += 1
                    continue
                gor.append((s, img))
            if not gor:
                self.say["gecerli_tarih_yok"] += 1
                return None
            satir, piksel = self.etiket_satirlari(epsg, sinirlar)
            if sum(piksel.values()) < 50:
                self.say["etiket_az"] += 1
                return None
            b = w["bolum"]
            adlar = []
            for k, (s, img) in enumerate(gor):
                ad = f"{b}__{w['konum_id']}_t{k}"
                cv2.imwrite(str(self.cikti / "images" / b / f"{ad}.jpg"), cv2.cvtColor(img, cv2.COLOR_RGB2BGR),
                            [cv2.IMWRITE_JPEG_QUALITY, 92])
                (self.cikti / "labels" / b / f"{ad}.txt").write_text("\n".join(satir) + "\n", encoding="utf-8")
                adlar.append(ad)
            kayit = {"konum_id": w["konum_id"], "bolum": b, "lon": round(w["lon"], 5), "lat": round(w["lat"], 5),
                     "epsg": epsg, "sinif_piksel": {self.siniflar[k]["ad"]: v for k, v in piksel.items()},
                     "etiket_satiri": [int(s.split()[0]) for s in satir],
                     "tarihler": [s["tarih"] for s, _ in gor], "mevsimler": [mevsim(s["tarih"]) for s, _ in gor],
                     "sahneler": [s["id"] for s, _ in gor], "gorseller": adlar}
            with self.kilit:
                self.meta.append(kayit)
                self.say["yazilan_pencere"] += 1
                self.say["goruntu"] += len(gor)
            return kayit
        except Exception as e:
            self.say["hata:" + type(e).__name__] += 1
            return None


def hazirla(tarif: dict, cikti: Path, pilot: int | None = None, is_parcacigi: int = 8, tohum: int = 1,
            sure_sn: int = 3 * 3600, log=print) -> dict:
    """Seti cikti/ altında kurar ve özet sözlüğü döndürür (aynı zamanda cikti/ozet.json)."""
    from tarifler import osm_cikar
    cikti = Path(cikti)
    siniflar = tarif["siniflar"]
    for b in BOLUM_ORAN:
        (cikti / "images" / b).mkdir(parents=True, exist_ok=True)
        (cikti / "labels" / b).mkdir(parents=True, exist_ok=True)
    cokgenler, pbf_bilgi = osm_cikar.cikar_onbellekli(tarif["id"], siniflar, cikti / "_osm", log)
    sayim_cokgen = Counter(siniflar[c["sinif"]]["ad"] for c in cokgenler)
    log(f"OSM kullanılabilir çokgen: {dict(sayim_cokgen)}")
    hedef = tarif.get("hedef_pencere", 900)
    penceler = pencere_planla(cokgenler, siniflar, hedef if not pilot else max(pilot * 6, 60), tohum,
                              tarif.get("sinif_tavani"), log)
    penceler = kumele_ve_bol(penceler, tohum)
    if pilot:
        r = random.Random("pilot")
        r.shuffle(penceler)
        # bütün bölümlerden örnek: bölüm başına en az pilot//5
        sec, say = [], Counter()
        for p in penceler:
            if say[p["bolum"]] < max(1, pilot // 3 if p["bolum"] != "test" else pilot // 6):
                sec.append(p)
                say[p["bolum"]] += 1
            if len(sec) >= pilot:
                break
        penceler = sec
    log(f"işlenecek pencere: {len(penceler)}")
    u = Uretici(tarif, cokgenler, cikti, tohum, log)
    t0 = time.time()
    try:
        with ThreadPoolExecutor(max_workers=is_parcacigi) as ex:
            for b in range(0, len(penceler), is_parcacigi * 4):
                if time.time() - t0 > sure_sn:
                    log("süre sınırı doldu, eldeki ile devam ediliyor")
                    break
                list(ex.map(u.isle, penceler[b:b + is_parcacigi * 4]))
                log(f"  {min(b + is_parcacigi * 4, len(penceler))}/{len(penceler)} pencere | {dict(u.say)} | {time.time() - t0:.0f} sn")
    finally:
        u.kaynak.kapat()
    ozet = ozet_yaz(tarif, u, sayim_cokgen, pbf_bilgi, cikti)
    log(f"bitti: {ozet['goruntu_toplam']} görüntü, {ozet['pencere_toplam']} pencere")
    return ozet


def ozet_yaz(tarif, u: Uretici, sayim_cokgen, pbf_bilgi, cikti: Path) -> dict:
    siniflar = tarif["siniflar"]
    bol_img, bol_pen = Counter(), Counter()
    etiket = {b: Counter() for b in BOLUM_ORAN}
    goruntulu = {b: Counter() for b in BOLUM_ORAN}
    yil, mev = Counter(), Counter()
    for m in u.meta:
        b, n = m["bolum"], len(m["gorseller"])
        bol_pen[b] += 1
        bol_img[b] += n
        for k in m["etiket_satiri"]:
            etiket[b][siniflar[k]["ad"]] += n
        for ad in m["sinif_piksel"]:
            goruntulu[b][ad] += n
        for t in m["tarihler"]:
            yil[t[:4]] += 1
        for t in m["mevsimler"]:
            mev[t] += 1
    (cikti / "data.yaml").write_text("path: .\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n"
                                     + "".join(f"  {i}: {s['ad']}\n" for i, s in enumerate(siniflar)), encoding="utf-8")
    with open(cikti / "meta.jsonl", "w", encoding="utf-8") as f:
        for m in sorted(u.meta, key=lambda m: m["konum_id"]):
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    ozet = {
        "tarif": tarif["id"], "siniflar": [s["ad"] for s in siniflar],
        "goruntu_bolum": dict(bol_img), "goruntu_toplam": sum(bol_img.values()),
        "pencere_bolum": dict(bol_pen), "pencere_toplam": sum(bol_pen.values()),
        "etiket_satiri_bolum_sinif": {b: dict(c) for b, c in etiket.items()},
        "goruntu_sayisi_sinifi_iceren": {b: dict(c) for b, c in goruntulu.items()},
        "osm_kullanilabilir_cokgen": dict(sayim_cokgen), "osm_dokum_tarihi": pbf_bilgi["pbf_tarih"],
        "yil_dagilimi": dict(sorted(yil.items())), "mevsim_dagilimi": dict(mev),
        "atlanan_ve_sayaclar": dict(u.say), "uretim_zamani": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()),
    }
    (cikti / "ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1), encoding="utf-8")
    return ozet


def yontem_metni(tarif: dict, ozet: dict) -> str:
    """README içindeki 'Yöntem' bölümü (motorun ne yaptığını açık yazar)."""
    return f"""1. Konum adayları: OpenStreetMap (Geofabrik Türkiye dökümü, {ozet['osm_dokum_tarihi']}) içinden aşağıdaki etiket kurallarına uyan çokgenler alındı; \
çok küçük ve çok büyük olanlar elendi, askerî ve hassas nesneler dışlandı.
2. Her çokgen için 224x224 piksellik (10 m çözünürlük, yaklaşık 2,24 km) bir pencere planlandı; büyük çokgenlerde en çok 3 pencere. \
Pencere merkezleri birbirine en az 1,5 km uzaktır. Sınıf başına bir tavan uygulandı ki baskın sınıf diğerlerini ezmesin.
3. Görüntü: Microsoft Planetary Computer `sentinel-2-l2a`, 2019 sonrası. Sahne sınıflandırma katmanıyla (SCL) bulut/gölge en çok %3, kar en çok %5, boş piksel en çok %0,5. \
Her pencere için kış dışında farklı mevsimlerden en çok 3 **gerçek** tarih seçildi (tarihler arası en az 20 gün); hiçbir tarih kopyalanmadı. \
2022-01-25 sonrası sahnelerde BOA ofseti (-1000) düşüldü. Kırmızı-yeşil-mavi bantlar 0-3500 yansıtımdan 0-255'e ölçeklendi (gama 0,9).
4. Etiket: penceredeki bütün sınıf çokgenleri maskeye çizildi, maskenin dış sınırları YOLO çokgenine çevrildi (1 piksel sadeleştirme, 4 pikselden küçük parçalar atıldı). \
Çokgenlerin iç boşlukları korunmaz. Bütün tarihler aynı etiketi paylaşır.
5. Bölme: birbirine 4 km'den yakın pencereler tek kümede toplandı; bir kümenin bütün pencereleri ve tarihleri aynı bölümdedir (konum sızıntısı yok). \
Kümeler sınıfa göre katmanlandı, yaklaşık 70/20/10 (train/val/test), sabit tohum.
6. Etiketsiz (hedef nesnesi olmayan) pencere yoktur."""


def tarif_olustur(id, ad, aciklama, siniflar, model_adi, sinirlar, hedef_pencere=900, imgsz=320, epok=60,
                  sinif_tavani=None) -> dict:
    """Sentinel-2 + OSM konu tarifi için standart TARIF sözlüğü."""
    return {
        "id": id, "ad": ad, "aciklama": aciklama, "gorev": "segment", "siniflar": siniflar,
        "kaynaklar": [
            {"ad": "OpenStreetMap katkıcıları (Geofabrik Türkiye dökümü)", "url": "https://download.geofabrik.de/europe/turkey.html", "lisans": "ODbL-1.0"},
            {"ad": "Copernicus Sentinel-2 L2A (Microsoft Planetary Computer)", "url": "https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a", "lisans": "Copernicus açık veri koşulları (CC-BY-4.0 ile uyumlu)"},
        ],
        "lisans": "ODbL-1.0", "lisans_gorunen": "ODbL 1.0 (OpenStreetMap'ten türetilmiş veri tabanı; görüntü: Copernicus Sentinel)",
        "mimari": "yolo11s-seg", "imgsz": imgsz, "epok": epok, "model_adi": model_adi, "sinirlar": sinirlar,
        "hedef_pencere": hedef_pencere, "sinif_tavani": sinif_tavani, "yontem": yontem_metni,
    }
