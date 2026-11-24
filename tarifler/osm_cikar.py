"""OpenStreetMap (Geofabrik Türkiye dökümü, ODbL) içinden etiket kurallarıyla çokgen çıkarır.

Sınıf tanımı: {"ad": "mezarlik", "kurallar": [{"landuse": "cemetery"}, ...], "en_az_alan_m2": 10000}
 - kurallar listesi VEYA ilişkisidir; bir kuralın içindeki anahtarlar VE ilişkisidir; değer "*" = herhangi bir değer.
 - Bir çokgen birden çok sınıfa uyarsa listedeki ilk sınıf kazanır.
 - Askerî ve hassas nesneler (military=*, landuse=military, amenity=prison, ...) her zaman dışlanır.

Hızlandırma: PATH'te osmium-tool varsa önce `osmium tags-filter` ile küçük bir PBF üretilir; yoksa
döküm doğrudan pyosmium ile okunur (yavaş ama aynı sonuç).
"""
from __future__ import annotations

import hashlib
import os
import pickle
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np

KOK = Path(__file__).resolve().parent.parent
VARSAYILAN_PBF = KOK / "veri" / "turkey-latest.osm.pbf"
GEOFABRIK_URL = "https://download.geofabrik.de/europe/turkey-latest.osm.pbf"
ALAN_PROJ = "+proj=aea +lat_1=36 +lat_2=42 +lat_0=39 +lon_0=35 +datum=WGS84 +units=m +no_defs"

DISLANAN_ETIKETLER = ("military", "military_service")
DISLANAN_DEGERLER = (("landuse", "military"), ("amenity", "prison"), ("amenity", "police"), ("amenity", "embassy"),
                     ("barrier", "border_control"), ("man_made", "surveillance"), ("access", "military"),
                     ("landuse", "prison"))


def pbf_yolu() -> Path:
    return Path(os.environ.get("OSM_PBF") or VARSAYILAN_PBF)


def hassas_mi(t) -> bool:
    if any(t.get(k) is not None for k in DISLANAN_ETIKETLER):
        return True
    return any(t.get(k) == v for k, v in DISLANAN_DEGERLER)


def kural_uyar(t, kurallar) -> bool:
    for kural in kurallar:
        if all((t.get(k) is not None) if v == "*" else (t.get(k) == v) for k, v in kural.items()):
            return True
    return False


def sinif_bul(t, siniflar) -> int | None:
    for i, s in enumerate(siniflar):
        if kural_uyar(t, s["kurallar"]):
            return i
    return None


def _filtre_ifadeleri(siniflar) -> list[str]:
    """osmium tags-filter için: her kuralın ilk koşulu (VE koşulları sonradan Python'da denetlenir)."""
    ifade = set()
    for s in siniflar:
        for kural in s["kurallar"]:
            k, v = next(iter(kural.items()))
            ifade.add(f"nwr/{k}" if v == "*" else f"nwr/{k}={v}")
    return sorted(ifade)


def _on_filtre(pbf: Path, siniflar, hedef_dizin: Path, log=print) -> Path:
    arac = shutil.which("osmium")
    if not arac:
        return pbf
    hedef_dizin.mkdir(parents=True, exist_ok=True)
    cikis = hedef_dizin / "on_filtre.osm.pbf"
    komut = [arac, "tags-filter", str(pbf), *_filtre_ifadeleri(siniflar), "-o", str(cikis), "--overwrite"]
    t0 = time.time()
    subprocess.run(komut, check=True)
    log(f"osmium tags-filter: {cikis.stat().st_size / 1e6:.0f} MB, {time.time() - t0:.0f} sn")
    return cikis


def cikar(pbf: Path, siniflar, calisma_dizini: Path, log=print) -> list[dict]:
    """[{id, geom (shapely, WGS84), sinif (indeks), alan_m2, ad}] döndürür; alan süzgeci uygulanmış."""
    import osmium
    import shapely
    from pyproj import Transformer
    from shapely import wkb

    kaynak = _on_filtre(pbf, siniflar, calisma_dizini, log)
    anahtarlar = sorted({k for s in siniflar for kural in s["kurallar"] for k in kural})
    fp = osmium.FileProcessor(str(kaynak)).with_areas(osmium.filter.KeyFilter(*anahtarlar))
    fab = osmium.geom.WKBFactory()
    ham, t0, n = [], time.time(), 0
    for o in fp:
        if not o.is_area():
            continue
        n += 1
        t = o.tags
        si = sinif_bul(t, siniflar)
        if si is None or hassas_mi(t):
            continue
        try:
            g = wkb.loads(fab.create_multipolygon(o), hex=True)
        except Exception:
            continue
        if g.is_empty:
            continue
        if not g.is_valid:
            g = shapely.make_valid(g)
        ham.append({"id": ("w" if o.from_way() else "r") + str(o.orig_id()), "geom": g, "sinif": si,
                    "ad": t.get("name")})
    log(f"OSM: {n} alan tarandı, {len(ham)} aday, {time.time() - t0:.0f} sn")
    ileri = Transformer.from_crs(4326, ALAN_PROJ, always_xy=True)
    geoms = np.array([h["geom"] for h in ham], dtype=object)
    m = shapely.transform(geoms, lambda a: np.column_stack(ileri.transform(a[:, 0], a[:, 1])))
    alan = shapely.area(m)
    son = []
    for h, a in zip(ham, alan):
        s = siniflar[h["sinif"]]
        if a < s.get("en_az_alan_m2", 0) or a > s.get("en_cok_alan_m2", 1e12):
            continue
        h["alan_m2"] = float(a)
        son.append(h)
    return son


def _imza(siniflar, pbf: Path) -> str:
    st = pbf.stat()
    ham = repr([(s["ad"], s["kurallar"], s.get("en_az_alan_m2"), s.get("en_cok_alan_m2")) for s in siniflar])
    return hashlib.sha1(f"{ham}|{st.st_size}|{int(st.st_mtime)}".encode()).hexdigest()[:12]


def cikar_onbellekli(tarif_id: str, siniflar, calisma_dizini: Path, log=print) -> tuple[list[dict], dict]:
    """Aynı PBF ve aynı kurallar için sonucu veri/onbellek altında saklar (yerel denemeleri hızlandırır)."""
    pbf = pbf_yolu()
    if not pbf.exists():
        raise FileNotFoundError(f"OSM dökümü yok: {pbf}")
    imza = _imza(siniflar, pbf)
    yol = KOK / "veri" / "onbellek" / f"osm_{tarif_id}_{imza}.pkl"
    bilgi = {"pbf_boyut": pbf.stat().st_size, "pbf_tarih": time.strftime("%Y-%m-%d", time.gmtime(pbf.stat().st_mtime))}
    if yol.exists():
        log(f"OSM önbellek: {yol.name}")
        return pickle.loads(yol.read_bytes()), bilgi
    sonuc = cikar(pbf, siniflar, calisma_dizini, log)
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_bytes(pickle.dumps(sonuc))
    return sonuc, bilgi
