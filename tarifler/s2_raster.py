"""Genel tarif motoru 2: Sentinel-2 L2A + RASTER etiket haritası (ilk kullanım: ESA WorldCover 2021, 10 m).

OSM motorundan (s2_osm) farkı:
  1. Etiket her piksel için vardır (eksik etiket sorunu yok). Konumlar Türkiye sınırı (Natural Earth, kamu malı)
     içinde tohumlu rastgele seçilir; birbirine en az 1,5 km uzak.
  2. Etiket haritası pencerenin Sentinel-2 ızgarasına en yakın komşu ile yeniden örneklenir, 3x3 medyan süzgeçle
     tuz-biber gürültüsü azaltılır, her sınıfın dış sınırları YOLO çokgenine çevrilir.
  3. Görüntü tarihleri etiket haritasının yılıyla sınırlıdır (WorldCover 2021 -> 2021 geçişleri).
  4. Tek sınıfın %97'den fazlasını kapladığı ve o sınıfın yaygın olduğu pencereler tohumlu olarak seyreltilir
     (çeşitlilik için).
Sentinel-2 okuma, tarih seçimi, kümeleme ve bölme s2_osm ile aynıdır.
"""
from __future__ import annotations

import json
import math
import random
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tarifler import s2_osm
from tarifler.s2_osm import BOLUM_ORAN, KARO, PX_M, MIN_PENCERE_ARALIGI_M, Uretici, kumele_ve_bol, ozet_yaz

SINIR_URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/"
             "ne_50m_admin_0_countries.geojson")
YAYGIN_ESIK = 0.97


def turkiye_siniri(onbellek: Path):
    from shapely.geometry import shape
    onbellek.parent.mkdir(parents=True, exist_ok=True)
    if not onbellek.exists():
        with urllib.request.urlopen(SINIR_URL, timeout=120) as r:
            veri = json.loads(r.read().decode("utf-8"))
        tr = [f for f in veri["features"] if f["properties"].get("ADM0_A3") == "TUR"]
        if not tr:
            raise RuntimeError("Natural Earth dosyasında Türkiye yok")
        onbellek.write_text(json.dumps(tr[0]["geometry"]), encoding="utf-8")
    return shape(json.loads(onbellek.read_text(encoding="utf-8")))


def konum_planla(sinir, adet: int, tohum: int, bant_derece: float = 3.0):
    """Türkiye içinde eş alanlı rastgele noktalar; 'sinif' alanı bölgesel banttır (bölme coğrafyaya yayılsın)."""
    import shapely
    from pyproj import Transformer
    from tarifler.osm_cikar import ALAN_PROJ
    ileri = Transformer.from_crs(4326, ALAN_PROJ, always_xy=True)
    geri = Transformer.from_crs(ALAN_PROJ, 4326, always_xy=True)
    g = shapely.transform(sinir, lambda a: __import__("numpy").column_stack(ileri.transform(a[:, 0], a[:, 1])))
    ic = g.buffer(-PX_M * KARO / 2)                     # pencere tamamen kara/ülke içinde kalsın
    shapely.prepare(ic)
    x0, y0, x1, y1 = ic.bounds
    rng = random.Random(f"konum:{tohum}")
    secilen, hucre, deneme = [], {}, 0
    while len(secilen) < adet and deneme < adet * 200:
        deneme += 1
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        if not ic.contains(shapely.Point(x, y)):
            continue
        h = (int(x // MIN_PENCERE_ARALIGI_M), int(y // MIN_PENCERE_ARALIGI_M))
        if any(((x - a) ** 2 + (y - b) ** 2) ** 0.5 < MIN_PENCERE_ARALIGI_M
               for dx in (-1, 0, 1) for dy in (-1, 0, 1) for a, b in hucre.get((h[0] + dx, h[1] + dy), ())):
            continue
        hucre.setdefault(h, []).append((x, y))
        lon, lat = geri.transform(x, y)
        secilen.append({"konum_id": f"k{int(round(lat * 1e4))}_{int(round(lon * 1e4))}", "x": x, "y": y,
                        "lon": lon, "lat": lat, "sinif": int((lon - 26.0) // bant_derece)})
    return secilen


def hedefli_konumlar(tarif, sinir, adet: int, tohum: int, log=print, kaba_derece: float = 0.0025):
    """Seyrek konular (ör. su) için: etiket haritasının kaba önizlemesinde (~250 m) hedef sınıf piksellerini bul,
    sınıf başına dengeli ve birbirine en az 1,5 km uzak pencere merkezleri seç. 'sinif' = hedef sınıf (katmanlı bölme)."""
    import numpy as np
    import planetary_computer
    import pystac_client
    import rasterio
    import shapely
    from pyproj import Transformer
    from rasterio.enums import Resampling
    from tarifler.osm_cikar import ALAN_PROJ
    r = tarif["raster"]
    deger = {int(k): v for k, v in r["deger_sinif"].items()}
    ns = len(tarif["siniflar"])
    istemci = pystac_client.Client.open(s2_osm.STAC_URL)
    ic = sinir.buffer(-0.015)
    shapely.prepare(ic)
    if r.get("sabit_karolar"):
        kaynaklar = [(k["url"], k["url"].rsplit("/", 1)[1]) for k in r["sabit_karolar"]]
    else:
        ogeler = list(istemci.search(collections=[r["koleksiyon"]], bbox=list(sinir.bounds),
                                     datetime=f"{r['yil']}-01-01/{r['yil']}-12-31", limit=50).items_as_dicts())
        kaynaklar = [(planetary_computer.sign(o["assets"][r["varlik"]]["href"]), o["id"]) for o in ogeler]
    adaylar = {k: [] for k in range(ns)}
    for href, ad in kaynaklar:
        with rasterio.open(href) as ds:
            piksel_m = abs(ds.res[0]) * (111320.0 if ds.crs.is_geographic else 1.0)
            f = max(1, int(round(kaba_derece * 111320.0 / piksel_m)))
            v = ds.read(1, out_shape=(max(1, ds.height // f), max(1, ds.width // f)), resampling=Resampling.nearest)
            T = ds.transform * ds.transform.scale(ds.width / v.shape[1], ds.height / v.shape[0])
            donus = None if ds.crs.to_epsg() == 4326 else Transformer.from_crs(ds.crs, 4326, always_xy=True)
        for d, sn in deger.items():
            ys, xs = np.nonzero(v == d)
            if not len(xs):
                continue
            px, py = T * (xs + 0.5, ys + 0.5)
            lon, lat = (np.asarray(px), np.asarray(py)) if donus is None else map(np.asarray, donus.transform(px, py))
            icte = shapely.contains_xy(ic, lon, lat)
            adaylar[sn].extend(zip(lon[icte].tolist(), lat[icte].tolist()))
        log(f"  {ad}: {[len(adaylar[k]) for k in range(ns)]}")
    ileri = Transformer.from_crs(4326, ALAN_PROJ, always_xy=True)
    rng = random.Random(f"hedefli:{tohum}")
    secilen, hucre = [], {}
    sira = sorted(range(ns), key=lambda k: len(adaylar[k]))        # en seyrek sınıf önce; artan kota sonrakilere
    for i, sn in enumerate(sira):
        tavan = max(1, (adet - len(secilen)) // (ns - i))
        a = adaylar[sn]
        rng.shuffle(a)
        n = 0
        for lon, lat in a:
            x, y = ileri.transform(lon, lat)
            h = (int(x // MIN_PENCERE_ARALIGI_M), int(y // MIN_PENCERE_ARALIGI_M))
            if any(((x - p) ** 2 + (y - q) ** 2) ** 0.5 < MIN_PENCERE_ARALIGI_M
                   for dx in (-1, 0, 1) for dy in (-1, 0, 1) for p, q in hucre.get((h[0] + dx, h[1] + dy), ())):
                continue
            hucre.setdefault(h, []).append((x, y))
            secilen.append({"konum_id": f"k{int(round(lat * 1e4))}_{int(round(lon * 1e4))}", "x": x, "y": y,
                            "lon": lon, "lat": lat, "sinif": sn})
            n += 1
            if n >= tavan:
                break
    log(f"hedefli konum: {len(secilen)} ({Counter(s['sinif'] for s in secilen)})")
    rng.shuffle(secilen)
    return secilen


class RasterUretici(Uretici):
    """Etiketi raster haritadan okuyan üretici. tarif['raster']: koleksiyon, varlık, yıl, deger_sinif eşlemesi."""

    def __init__(self, tarif, cikti, tohum, log=print):
        super().__init__(tarif, [], cikti, tohum, log)
        self.r = tarif["raster"]
        self.deger = {int(k): v for k, v in self.r["deger_sinif"].items()}
        self.yaygin = set(self.r.get("yaygin_siniflar", []))
        self.etiket_onbellek = {}
        self.etiket_hazir = {}

    def _sec(self, adaylar, sinirlar, rng):
        """Önce etiket (ucuz) denetlenir: uygun değilse görüntü hiç okunmaz."""
        yil = str(self.r.get("goruntu_yili", self.r["yil"]))
        adaylar = [c for c in adaylar if c["tarih"][:4] == yil]
        if not adaylar:
            return []
        epsg = adaylar[0]["epsg"]
        sonuc = self._etiket(epsg, sinirlar)
        if not sonuc[0]:
            return []
        with self.kilit:
            self.etiket_hazir[(epsg, tuple(sinirlar))] = sonuc
        return super()._sec(adaylar, sinirlar, rng)

    def etiket_satirlari(self, epsg, sinirlar):
        with self.kilit:
            sonuc = self.etiket_hazir.pop((epsg, tuple(sinirlar)), None)
        return sonuc if sonuc is not None else self._etiket(epsg, sinirlar)

    def _etiket_href(self, lon, lat):
        """Etiket karosunun adresi (STAC, önbellekli; WorldCover karoları 3x3 derece)."""
        anahtar = (math.floor(lon / 3), math.floor(lat / 3))
        with self.kilit:
            if anahtar in self.etiket_onbellek:
                return self.etiket_onbellek[anahtar]

        def f():
            return list(self.kaynak.istemci.search(collections=[self.r["koleksiyon"]], intersects={
                "type": "Point", "coordinates": [lon, lat]}, datetime=f"{self.r['yil']}-01-01/{self.r['yil']}-12-31",
                limit=5).items_as_dicts())
        ogeler = s2_osm.yeniden_dene(f)
        href = ogeler[0]["assets"][self.r["varlik"]]["href"].split("?", 1)[0] if ogeler else None
        with self.kilit:
            self.etiket_onbellek[anahtar] = href
        return href

    def _etiket(self, epsg, sinirlar):
        import cv2
        import numpy as np
        from pyproj import Transformer
        from rasterio.enums import Resampling
        from rasterio.vrt import WarpedVRT
        from rasterio.windows import from_bounds
        x0, y0, x1, y1 = sinirlar
        geri = Transformer.from_crs(epsg, 4326, always_xy=True)
        koseler = [geri.transform(x, y) for x in (x0, x1) for y in (y0, y1)]
        if self.r.get("sabit_karolar"):
            adaylar = [k["url"] for k in self.r["sabit_karolar"]
                       if all(k["sinirlar"][0] <= a <= k["sinirlar"][2] and k["sinirlar"][1] <= b <= k["sinirlar"][3] for a, b in koseler)]
        else:
            hrefler = {self._etiket_href(*k) for k in koseler}
            adaylar = list(hrefler) if len(hrefler) == 1 and None not in hrefler else []

        def oku(ds):
            with WarpedVRT(ds, crs=f"EPSG:{epsg}", resampling=Resampling.nearest) as v:
                w = from_bounds(x0, y0, x1, y1, transform=v.transform)
                return v.read(1, window=w, out_shape=(KARO, KARO), resampling=Resampling.nearest)
        ham, bos = None, self.r.get("bos_deger")
        for href in adaylar:
            h = self.kaynak.oku(href, oku)
            if bos is None or float(np.mean(h == bos)) < 0.1:
                ham = h
                break
        if ham is None:
            self.say["etiket_karo_siniri"] += 1
            return [], Counter()
        maske = np.full((KARO, KARO), 255, np.uint8)
        for d, sn in self.deger.items():
            maske[ham == d] = sn
        maske = cv2.medianBlur(maske, 3)
        dagilim = Counter({int(k): int(v) for k, v in zip(*np.unique(maske[maske != 255], return_counts=True))})
        toplam = sum(dagilim.values())
        if toplam < KARO * KARO * self.r.get("en_az_kapsama", 0.9):
            self.say["etiket_bos"] += 1
            return [], Counter()
        baskin, n = dagilim.most_common(1)[0]
        if self.r.get("hedefli") and n > KARO * KARO * 0.97:
            self.say["tamamen_tek_sinif"] += 1        # ör. göl içi: tarihler neredeyse aynı, platform tekrar sayıp eliyor
            return [], Counter()
        if n / toplam > YAYGIN_ESIK and baskin in self.yaygin:
            rng = random.Random(f"seyrelt:{self.tohum}:{x0}:{y0}")
            if rng.random() < self.r.get("seyreltme", 0.6):
                self.say["tek_sinif_seyreltildi"] += 1
                return [], Counter()
        satir, piksel = [], Counter()
        for sn in sorted(dagilim):
            ik = (maske == sn).astype(np.uint8)
            piksel[sn] = int(ik.sum())
            for c in cv2.findContours(ik, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
                if cv2.contourArea(c) < 16:
                    continue
                c = cv2.approxPolyDP(c, 1.5, True).reshape(-1, 2)
                if len(c) < 3:
                    continue
                satir.append(f"{sn} " + " ".join(f"{x / KARO:.5f} {y / KARO:.5f}" for x, y in c))
        return satir, piksel


def hazirla(tarif: dict, cikti: Path, pilot: int | None = None, is_parcacigi: int = 8, tohum: int = 1,
            sure_sn: int = 3 * 3600, log=print) -> dict:
    cikti = Path(cikti)
    for b in BOLUM_ORAN:
        (cikti / "images" / b).mkdir(parents=True, exist_ok=True)
        (cikti / "labels" / b).mkdir(parents=True, exist_ok=True)
    sinir = turkiye_siniri(Path(__file__).resolve().parent.parent / "veri" / "onbellek" / "turkiye_ne50m.json")
    hedef = tarif.get("hedef_pencere", 1000)
    aday = max(pilot * 4, 40) if pilot else int(hedef * tarif["raster"].get("aday_carpani", 2.2))
    planla = hedefli_konumlar if tarif["raster"].get("hedefli") else (lambda t, s, a, h, log: konum_planla(s, a, h))
    penceler = kumele_ve_bol(planla(tarif, sinir, aday, tohum, log), tohum)
    if pilot:
        random.Random("pilot").shuffle(penceler)
    log(f"aday konum: {len(penceler)} (hedef pencere {hedef if not pilot else pilot})")
    u = RasterUretici(tarif, cikti, tohum, log)
    son = pilot or hedef
    t0 = time.time()
    try:
        with ThreadPoolExecutor(max_workers=is_parcacigi) as ex:
            for b in range(0, len(penceler), is_parcacigi * 4):
                if u.say["yazilan_pencere"] >= son:
                    break
                if time.time() - t0 > sure_sn:
                    log("süre sınırı doldu, eldeki ile devam ediliyor")
                    break
                list(ex.map(u.isle, penceler[b:b + is_parcacigi * 4]))
                log(f"  {min(b + is_parcacigi * 4, len(penceler))}/{len(penceler)} aday | {dict(u.say)} | {time.time() - t0:.0f} sn")
    finally:
        u.kaynak.kapat()
    ozet = ozet_yaz(tarif, u, Counter(), {"pbf_tarih": None}, cikti)
    ozet.pop("osm_kullanilabilir_cokgen", None)
    ozet.pop("osm_dokum_tarihi", None)
    ozet["kaynak_satiri"] = tarif["raster"]["kaynak_satiri"]
    (cikti / "ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"bitti: {ozet['goruntu_toplam']} görüntü, {ozet['pencere_toplam']} pencere")
    return ozet


def yontem_metni(tarif: dict, ozet: dict) -> str:
    r = tarif["raster"]
    if r.get("hedefli"):
        konum = ("1. Konumlar: etiket haritasının yaklaşık 250 m'lik kaba önizlemesinde hedef sınıf pikselleri bulundu; Türkiye sınırı "
                 "(Natural Earth 1:50m, kamu malı) içindekilerden sınıf başına dengeli (en seyrek sınıf önce), merkezleri birbirine en az "
                 "1,5 km uzak pencereler seçildi. Hedef sınıflar dışındaki pikseller etiketsiz arka plandır.")
        bolme = "kümeler hedef sınıfa göre katmanlı"
    else:
        konum = ("1. Konumlar: Türkiye sınırı (Natural Earth 1:50m, kamu malı) içinde tohumlu rastgele noktalar; pencere tamamen ülke içinde, "
                 "merkezler birbirine en az 1,5 km uzak. Tek bir yaygın sınıfın %97'den fazlasını kapladığı pencerelerin bir kısmı çeşitlilik için atlandı.")
        bolme = "kümeler 3 derecelik boylam bantlarına göre katmanlı"
    dogruluk = r.get("dogruluk_notu", "Etiket bir algoritmanın ürettiği haritadır, el ile çizilmiş değildir; haritanın kendi doğruluğu bu setin üst sınırıdır.")
    return f"""{konum}
2. Her konum için 224x224 piksellik (10 m, yaklaşık 2,24 km) pencere.
3. Görüntü: Microsoft Planetary Computer `sentinel-2-l2a`, yalnız {r.get('goruntu_yili', r['yil'])} yılı ({'etiket haritasıyla aynı yıl' if r.get('goruntu_yili', r['yil']) == r['yil'] else 'etiket ' + str(r['yil']) + '; Sentinel-2 L2A arşivi 2019 öncesini içermez'}). SCL ile bulut/gölge en çok %3, \
kar en çok %5, boş piksel en çok %0,5. Kış dışında farklı mevsimlerden en çok 3 **gerçek** tarih (aralarında en az 20 gün); kopya yok. \
Kırmızı-yeşil-mavi bantlar 0-3500 yansıtımdan 0-255'e ölçeklendi (gama 0,9).
4. Etiket: {r['kaynak_adi']} haritası pencerenin Sentinel-2 ızgarasına en yakın komşu ile yeniden örneklendi, 3x3 medyan süzgeçten geçirildi; \
her sınıfın dış sınırları YOLO çokgenine çevrildi (1,5 piksel sadeleştirme, 16 pikselden küçük parçalar atıldı, iç boşluklar korunmaz). \
{dogruluk}
5. Bölme: birbirine 4 km'den yakın pencereler tek kümede; {bolme}, yaklaşık 70/20/10 (train/val/test), sabit tohum."""


def tarif_olustur(id, ad, aciklama, siniflar, model_adi, sinirlar, raster, kaynaklar, lisans, lisans_gorunen,
                  hedef_pencere=1000, imgsz=320, epok=60) -> dict:
    return {
        "id": id, "ad": ad, "aciklama": aciklama, "gorev": "segment", "siniflar": siniflar,
        "kaynaklar": kaynaklar + [
            {"ad": "Copernicus Sentinel-2 L2A (Microsoft Planetary Computer)", "url": "https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a", "lisans": "Copernicus açık veri koşulları (CC-BY-4.0 ile uyumlu)"},
            {"ad": "Natural Earth 1:50m ülke sınırları", "url": "https://www.naturalearthdata.com/", "lisans": "kamu malı"},
        ],
        "lisans": lisans, "lisans_gorunen": lisans_gorunen, "mimari": "yolo11s-seg", "imgsz": imgsz, "epok": epok,
        "model_adi": model_adi, "sinirlar": sinirlar, "hedef_pencere": hedef_pencere, "raster": raster,
        "kural_basligi": "Sınıflar (etiket haritasındaki değer):", "yontem": yontem_metni,
    }
