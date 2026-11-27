"""Bulutta bir kez çalışır: büyük açık etiket haritalarının Türkiye parçalarını indirir, uzaktan okunabilir COG'a çevirir.

Kullanım: python araclar/etiket_hazirla.py <worldcereal|ghsl> <cikti_dizini>
Çıktı: <cikti>/*.tif (COG, önizlemeli) + <cikti>/<is>_karolar.json (dosya adı, sınırlar, değer dağılımı).
Bu dosyalar depo sürümüne (release) yüklenir; tarifler raster['sabit_karolar'] ile okur.

worldcereal: ESA WorldCereal 2021 v100 (Zenodo 7875105, CC-BY-4.0). Değerler: 0 ürün tarım dışı ya da başka ürün,
  1 kışlık tahıl, 2 mısır (ana sezon), 3 diğer geçici ürün, 255 bölge (AEZ) dışı. Öncelik: mısır > kışlık tahıl > diğer.
ghsl: GHS-BUILT-C MSZ E2018 R2023A 10 m (JRC, CC-BY-4.0); değerler olduğu gibi kopyalanır (Mollweide 54009).
"""
from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import requests

TR_KUTU = (25.6, 35.8, 44.9, 42.2)
ZENODO = "https://zenodo.org/records/7875105/files"
WC_URUN = {"kislik_tahil": "tc-wintercereals_wintercereals", "misir": "tc-maize-main_maize",
           "gecici": "tc-annual_temporarycrops"}
GHSL = ("https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_BUILT_C_GLOBE_R2023A/"
        "GHS_BUILT_C_MSZ_E2018_GLOBE_R2023A_54009_10/V1-0/tiles/GHS_BUILT_C_MSZ_E2018_GLOBE_R2023A_54009_10_V1_0_{}.zip")
GHSL_KAROLAR = ["R4_C21", "R4_C22", "R5_C21", "R5_C22", "R5_C23"]


class HttpDosya(io.RawIOBase):
    """Aralıklı (Range) HTTP okuma: büyük zip'in yalnız gereken üyelerini indirmek için."""

    def __init__(self, url):
        self.url, self.p, self.s = url, 0, requests.Session()
        self.n = int(self.s.head(url, allow_redirects=True, timeout=120).headers["Content-Length"])

    def seekable(self):
        return True

    def readable(self):
        return True

    def seek(self, o, w=0):
        self.p = o if w == 0 else (self.p + o if w == 1 else self.n + o)
        return self.p

    def tell(self):
        return self.p

    def readinto(self, b):
        k = len(b)
        if k == 0 or self.p >= self.n:
            return 0
        for deneme in range(5):
            try:
                r = self.s.get(self.url, headers={"Range": f"bytes={self.p}-{min(self.n, self.p + k) - 1}"}, timeout=600)
                r.raise_for_status()
                d = r.content
                break
            except Exception:
                if deneme == 4:
                    raise
        b[:len(d)] = d
        self.p += len(d)
        return len(d)


def cog_yaz(gecici: Path, hedef: Path):
    import rasterio.shutil
    rasterio.shutil.copy(str(gecici), str(hedef), driver="COG", compress="DEFLATE", predictor=2,
                         overview_resampling="nearest", blocksize=512, BIGTIFF="YES", NUM_THREADS="ALL_CPUS")
    gecici.unlink()


def turkiye():
    from shapely.geometry import shape
    u = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/ne_50m_admin_0_countries.geojson"
    v = requests.get(u, timeout=120).json()
    return shape(next(f for f in v["features"] if f["properties"].get("ADM0_A3") == "TUR")["geometry"])


def worldcereal(cikti: Path):
    import rasterio
    from rasterio.windows import Window, from_bounds
    from shapely.geometry import shape
    tr = turkiye().buffer(0.05)
    aez = requests.get(f"{ZENODO}/WorldCereal_AEZ.geojson", timeout=120).json()
    idler = [f["properties"]["aez_id"] for f in aez["features"] if shape(f["geometry"]).intersects(tr)]
    print("Türkiye AEZ:", idler, flush=True)
    zipler = {k: zipfile.ZipFile(io.BufferedReader(HttpDosya(f"{ZENODO}/WorldCereal_2021_{v}_classification.zip"),
                                                    buffer_size=16 << 20)) for k, v in WC_URUN.items()}
    kayit = []
    for a in idler:
        yollar = {}
        for k, z in zipler.items():
            uye = [i for i in z.infolist() if f"/{a}_" in i.filename and i.filename.endswith("classification.tif")]
            if not uye:
                print(f"  {a} {k}: yok", flush=True)
                continue
            p = cikti / f"_ham_{a}_{k}.tif"
            with z.open(uye[0]) as kaynak, open(p, "wb") as f:
                while True:
                    blok = kaynak.read(64 << 20)
                    if not blok:
                        break
                    f.write(blok)
            yollar[k] = p
            print(f"  {a} {k}: {uye[0].filename.rsplit('/', 1)[1]} {p.stat().st_size / 1e6:.0f} MB", flush=True)
        if "gecici" not in yollar:
            continue
        acik = {k: rasterio.open(p) for k, p in yollar.items()}
        ana = acik["gecici"]
        from rasterio.enums import Resampling
        from rasterio.vrt import WarpedVRT
        for k in list(acik):
            if k != "gecici" and (acik[k].transform, acik[k].shape) != (ana.transform, ana.shape):
                print(f"  {a} {k}: ızgara farklı ({acik[k].shape} / {ana.shape}), ana ızgaraya hizalanıyor", flush=True)
                acik[k] = WarpedVRT(acik[k], crs=ana.crs, transform=ana.transform, width=ana.width, height=ana.height,
                                    resampling=Resampling.nearest, nodata=255)
        b = ana.bounds
        kutu = (max(b.left, TR_KUTU[0]), max(b.bottom, TR_KUTU[1]), min(b.right, TR_KUTU[2]), min(b.top, TR_KUTU[3]))
        if kutu[0] >= kutu[2] or kutu[1] >= kutu[3]:
            continue
        w = from_bounds(*kutu, transform=ana.transform).round_offsets().round_lengths()
        profil = dict(driver="GTiff", width=w.width, height=w.height, count=1, dtype="uint8", crs=ana.crs,
                      transform=ana.window_transform(w), nodata=255, tiled=True, blockxsize=512, blockysize=512,
                      compress="DEFLATE", BIGTIFF="YES")
        gecici = cikti / f"_ara_{a}.tif"
        say = np.zeros(256, np.int64)
        with rasterio.open(gecici, "w", **profil) as d:
            B = 4096
            for r in range(0, w.height, B):
                for c in range(0, w.width, B):
                    ww = Window(w.col_off + c, w.row_off + r, min(B, w.width - c), min(B, w.height - r))
                    g = ana.read(1, window=ww)
                    o = np.full(g.shape, 255, np.uint8)
                    o[g != 255] = 0
                    o[g == 100] = 3
                    for k, deger in (("kislik_tahil", 1), ("misir", 2)):
                        if k in acik:
                            x = acik[k].read(1, window=ww)
                            o[x == 100] = deger
                    say += np.bincount(o.ravel(), minlength=256)
                    d.write(o, 1, window=Window(c, r, ww.width, ww.height))
        for x in acik.values():
            x.close()
        for p in yollar.values():
            p.unlink()
        hedef = cikti / f"worldcereal2021_tr_{a}.tif"
        cog_yaz(gecici, hedef)
        kayit.append({"dosya": hedef.name, "sinirlar": list(kutu), "crs": "EPSG:4326",
                      "deger": {str(i): int(v) for i, v in enumerate(say) if v}})
        print(f"  {a}: yazıldı {hedef.stat().st_size / 1e6:.0f} MB, değerler {kayit[-1]['deger']}", flush=True)
    (cikti / "worldcereal_karolar.json").write_text(json.dumps(kayit, indent=1), encoding="utf-8")


def ghsl(cikti: Path):
    import rasterio
    from pyproj import Transformer
    kayit = []
    geri = Transformer.from_crs("ESRI:54009", 4326, always_xy=True)
    for k in GHSL_KAROLAR:
        z = cikti / f"_{k}.zip"
        with requests.get(GHSL.format(k), stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(z, "wb") as f:
                for blok in r.iter_content(16 << 20):
                    f.write(blok)
        with zipfile.ZipFile(z) as zz:
            uye = next(i for i in zz.infolist() if i.filename.endswith(".tif"))
            ham = cikti / f"_ham_{k}.tif"
            with zz.open(uye) as s, open(ham, "wb") as f:
                while True:
                    blok = s.read(64 << 20)
                    if not blok:
                        break
                    f.write(blok)
        z.unlink()
        hedef = cikti / f"ghsl_msz2018_{k}.tif"
        cog_yaz(ham, hedef)
        with rasterio.open(hedef) as ds:
            b = ds.bounds
            o = ds.read(1, out_shape=(ds.height // 50, ds.width // 50))
            say = np.bincount(o.ravel(), minlength=256)
            ks = [geri.transform(x, y) for x in (b.left, b.right) for y in (b.bottom, b.top)]
            nd = ds.nodata
        kayit.append({"dosya": hedef.name, "sinirlar": [min(p[0] for p in ks), min(p[1] for p in ks), max(p[0] for p in ks), max(p[1] for p in ks)],
                      "crs": "ESRI:54009", "nodata": nd, "deger_ornek": {str(i): int(v) for i, v in enumerate(say) if v}})
        print(f"  {k}: {hedef.stat().st_size / 1e6:.0f} MB, nodata {nd}, değer örneği {kayit[-1]['deger_ornek']}", flush=True)
    (cikti / "ghsl_karolar.json").write_text(json.dumps(kayit, indent=1), encoding="utf-8")




CLC_KAYNAK = "https://sdi.eea.europa.eu/data/a65428d3-bd66-4b47-bcf9-6bfd6fa5df0c"


def clc(cikti: Path):
    """CORINE Land Cover 2024 (100 m, EEA). Önce kaynağın içeriği listelenir; Türkiye kapsaması ve sınıf dağılımı raporlanır.
    Türkiye karesine kırpılmış COG yazılır (EPSG:3035)."""
    import re
    import rasterio
    from rasterio.windows import from_bounds
    from pyproj import Transformer
    r = requests.get(CLC_KAYNAK + "/", timeout=120)
    print("liste", r.status_code, r.headers.get("content-type"), flush=True)
    linkler = sorted(set(re.findall(r'href="([^"?#]+\.(?:zip|tif|tiff|gpkg|txt|pdf|xml|csv|lyr|qml|sld))"', r.text, re.I)))
    print("dosyalar:", linkler[:40], flush=True)
    zipler = [l for l in linkler if l.lower().endswith((".zip", ".tif", ".tiff"))]
    if not zipler:
        print(r.text[:3000], flush=True)
        raise SystemExit("indirilebilir raster yok")
    hedef = zipler[0] if zipler[0].startswith("http") else CLC_KAYNAK + "/" + zipler[0].lstrip("/")
    print("indiriliyor:", hedef, flush=True)
    yerel = cikti / ("_clc" + Path(hedef).suffix)
    with requests.get(hedef, stream=True, timeout=1800) as q:
        q.raise_for_status()
        with open(yerel, "wb") as f:
            for blok in q.iter_content(16 << 20):
                f.write(blok)
    print("boyut MB", round(yerel.stat().st_size / 1e6), flush=True)
    tif = yerel
    if yerel.suffix == ".zip":
        with zipfile.ZipFile(yerel) as z:
            adlar = [i.filename for i in z.infolist()]
            print("zip içeriği:", adlar[:30], flush=True)
            secim = max((i for i in z.infolist() if i.filename.lower().endswith((".tif", ".tiff"))), key=lambda i: i.file_size)
            tif = cikti / "_clc.tif"
            with z.open(secim) as s_, open(tif, "wb") as f:
                while True:
                    b = s_.read(64 << 20)
                    if not b:
                        break
                    f.write(b)
            for i in z.infolist():
                if i.filename.lower().endswith((".txt", ".csv", ".clr", ".qml", ".xml")) and i.file_size < 2_000_000:
                    (cikti / ("_" + Path(i.filename).name)).write_bytes(z.read(i))
        yerel.unlink()
    with rasterio.open(tif) as ds:
        print("crs", ds.crs, "boyut", ds.shape, "nodata", ds.nodata, "dtype", ds.dtypes, flush=True)
        t = Transformer.from_crs(4326, ds.crs, always_xy=True)
        xs, ys = zip(*[t.transform(x, y) for x in (TR_KUTU[0], TR_KUTU[2]) for y in (TR_KUTU[1], TR_KUTU[3])])
        w = from_bounds(min(xs), min(ys), max(xs), max(ys), transform=ds.transform).round_offsets().round_lengths()
        a = ds.read(1, window=w, boundless=True, fill_value=ds.nodata if ds.nodata is not None else 0)
        prof = ds.profile.copy()
        prof.update(width=a.shape[1], height=a.shape[0], transform=ds.window_transform(w), driver="GTiff", compress="DEFLATE",
                    tiled=True, blockxsize=512, blockysize=512, BIGTIFF="YES")
    import numpy as np
    v, n = np.unique(a, return_counts=True)
    dag = {int(x): int(y) for x, y in zip(v, n)}
    print("Türkiye karesi değer dağılımı:", dag, flush=True)
    ara = cikti / "_clc_tr.tif"
    with rasterio.open(ara, "w", **prof) as d:
        d.write(a, 1)
    hedef_cog = cikti / "clc2024_tr.tif"
    cog_yaz(ara, hedef_cog)
    tif.unlink(missing_ok=True)
    (cikti / "clc_karolar.json").write_text(json.dumps([{"dosya": hedef_cog.name, "sinirlar": list(TR_KUTU), "crs": str(prof["crs"]),
                                                          "deger": {str(k): v for k, v in dag.items()}, "kaynak": CLC_KAYNAK}], indent=1), encoding="utf-8")


if __name__ == "__main__":
    is_, c = sys.argv[1], Path(sys.argv[2])
    c.mkdir(parents=True, exist_ok=True)
    {"worldcereal": worldcereal, "ghsl": ghsl, "clc": clc}[is_](c)
