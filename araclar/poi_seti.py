"""Türkiye OSM işletme/kurum adı -> tür metin seti ve taban sınıflandırıcı (bulutta çalışır; fabrikadan bağımsız).

Kaynak: Geofabrik Türkiye dökümü (OpenStreetMap katkıcıları, ODbL). Adı olan ve tür anahtarı (amenity, shop, tourism,
leisure, office, craft, healthcare, historic) taşıyan düğüm ve yollar alınır; askerî/hassas nesneler dışlanır.
Sınıf: en sık türler (en az EN_AZ benzersiz ad); ibadet yerlerinde din ayrılır. Aynı (ad, sınıf) bir kez tutulur.
Bölme: normalize ad özütüne göre (zincir işletmeler tek bölümde) ~80/10/10.
Taban model: karakter n-gram TF-IDF + lojistik regresyon; test doğruluğu ve makro F1 yazılır.
Kullanım: python araclar/poi_seti.py <pbf> <cikti_dizini>
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ANAHTARLAR = ("amenity", "shop", "tourism", "leisure", "office", "craft", "healthcare", "historic")
DISLA = {("amenity", "police"), ("amenity", "prison"), ("amenity", "embassy"), ("office", "diplomatic"),
         ("amenity", "parking"), ("amenity", "parking_space"), ("amenity", "bench"), ("amenity", "waste_basket"),
         ("amenity", "toilets"), ("amenity", "drinking_water"), ("amenity", "fountain"), ("leisure", "pitch"),
         ("amenity", "bicycle_parking"), ("amenity", "vending_machine"), ("amenity", "atm"), ("amenity", "shelter")}
EN_AZ = 150
TR_AD = {
    "amenity=restaurant": "restoran", "amenity=cafe": "kafe", "amenity=fast_food": "hizli_yemek", "amenity=pharmacy": "eczane",
    "amenity=school": "okul", "amenity=kindergarten": "anaokulu", "amenity=hospital": "hastane", "amenity=clinic": "klinik",
    "amenity=doctors": "muayenehane", "amenity=dentist": "dis_hekimi", "amenity=bank": "banka", "amenity=fuel": "akaryakit",
    "amenity=place_of_worship+muslim": "cami_mescit", "amenity=place_of_worship+christian": "kilise",
    "amenity=place_of_worship+jewish": "sinagog", "amenity=townhall": "belediye_muhtarlik", "amenity=post_office": "postane",
    "amenity=library": "kutuphane", "amenity=university": "universite", "amenity=college": "yuksekokul",
    "amenity=bar": "bar", "amenity=pub": "birahane", "amenity=car_wash": "oto_yikama", "amenity=car_rental": "arac_kiralama",
    "amenity=veterinary": "veteriner", "amenity=community_centre": "toplum_merkezi", "amenity=marketplace": "pazar_yeri",
    "amenity=bus_station": "otogar", "amenity=ice_cream": "dondurmaci", "amenity=driving_school": "surucu_kursu",
    "amenity=courthouse": "adliye", "amenity=fire_station": "itfaiye", "amenity=social_facility": "sosyal_tesis",
    "amenity=theatre": "tiyatro", "amenity=cinema": "sinema", "amenity=nightclub": "gece_kulubu",
    "shop=supermarket": "supermarket", "shop=convenience": "bakkal_market", "shop=bakery": "firin", "shop=clothes": "giyim",
    "shop=hairdresser": "kuafor_berber", "shop=butcher": "kasap", "shop=car_repair": "oto_tamir", "shop=mobile_phone": "cep_telefonu",
    "shop=jewelry": "kuyumcu", "shop=furniture": "mobilya", "shop=hardware": "hirdavat", "shop=shoes": "ayakkabi",
    "shop=optician": "optik", "shop=greengrocer": "manav", "shop=pastry": "pastane", "shop=confectionery": "sekerci",
    "shop=beauty": "guzellik_salonu", "shop=electronics": "elektronik", "shop=car": "oto_galeri", "shop=car_parts": "oto_yedek_parca",
    "shop=books": "kitapci", "shop=stationery": "kirtasiye", "shop=florist": "cicekci", "shop=kiosk": "bufe",
    "shop=tyres": "lastikci", "shop=bicycle": "bisikletci", "shop=dry_cleaning": "kuru_temizleme", "shop=pet": "evcil_hayvan",
    "shop=tailor": "terzi", "shop=gift": "hediyelik", "shop=cosmetics": "kozmetik", "shop=alcohol": "tekel", "shop=chemist": "bakim_urunleri",
    "shop=travel_agency": "seyahat_acentesi", "shop=computer": "bilgisayar", "shop=nuts": "kuruyemis", "shop=tea": "cay",
    "shop=coffee": "kahve", "shop=seafood": "balikci", "shop=deli": "sarkuteri", "shop=dairy": "sutcu",
    "shop=department_store": "magaza", "shop=mall": "avm", "shop=variety_store": "zuccaciye_ucuzluk", "shop=houseware": "ev_gerecleri",
    "shop=doityourself": "yapi_market", "shop=paint": "boya", "shop=glaziery": "camci", "shop=carpet": "hali",
    "shop=funeral_directors": "cenaze_hizmeti", "shop=laundry": "camasirhane", "shop=copyshop": "fotokopi",
    "shop=photo": "fotografci", "shop=sports": "spor_malzemesi", "shop=toys": "oyuncak", "shop=baby_goods": "bebek_urunleri",
    "shop=wine": "sarap", "shop=agrarian": "tarim_malzemesi", "shop=motorcycle": "motosiklet",
    "tourism=hotel": "otel", "tourism=guest_house": "pansiyon", "tourism=hostel": "hostel", "tourism=apartment": "apart",
    "tourism=museum": "muze", "tourism=attraction": "gezi_noktasi", "tourism=camp_site": "kamp", "tourism=motel": "motel",
    "tourism=viewpoint": "seyir_noktasi", "tourism=information": "turizm_danisma", "tourism=artwork": "sanat_eseri",
    "leisure=park": "park", "leisure=playground": "oyun_alani", "leisure=sports_centre": "spor_merkezi", "leisure=fitness_centre": "spor_salonu",
    "leisure=stadium": "stadyum", "leisure=swimming_pool": "yuzme_havuzu", "leisure=garden": "bahce", "leisure=marina": "marina",
    "leisure=picnic_table": "piknik", "leisure=beach_resort": "plaj_tesisi", "leisure=sports_hall": "spor_salonu",
    "office=company": "sirket", "office=government": "kamu_dairesi", "office=estate_agent": "emlakci", "office=lawyer": "avukat",
    "office=insurance": "sigorta", "office=accountant": "mali_musavir", "office=educational_institution": "egitim_kurumu",
    "office=association": "dernek", "office=ngo": "sivil_toplum", "office=political_party": "siyasi_parti",
    "office=architect": "mimarlik", "office=notary": "noter", "office=telecommunication": "telekom",
    "craft=carpenter": "marangoz", "craft=electrician": "elektrikci", "craft=plumber": "tesisatci", "craft=shoemaker": "kunduraci",
    "craft=metal_construction": "demirci", "craft=tailor": "terzi", "craft=key_cutter": "anahtarci",
    "healthcare=laboratory": "laboratuvar", "healthcare=physiotherapist": "fizyoterapi", "healthcare=centre": "saglik_merkezi",
    "historic=monument": "anit", "historic=memorial": "anit", "historic=ruins": "oren_yeri", "historic=archaeological_site": "arkeolojik_alan",
    "historic=castle": "kale", "historic=tomb": "turbe", "historic=building": "tarihi_yapi", "historic=fountain": "tarihi_cesme",
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s).replace("İ", "i").replace("I", "ı").lower()
    return re.sub(r"\s+", " ", s).strip()


def ozut(s: str) -> str:
    """Bölme grubu: ad içinden şube/şehir eklerini atıp ilk iki sözcük (zincirler tek grupta kalsın)."""
    s = re.sub(r"[^\wçğıöşü ]", " ", norm(s))
    w = [x for x in s.split() if x not in ("şubesi", "şube", "mağazası", "ve", "-")]
    return " ".join(w[:2]) or s


def cikar(pbf: str):
    import osmium

    kayit = []

    def tur(t):
        for k in ANAHTARLAR:
            v = t.get(k)
            if v and (k, v) not in DISLA:
                if k == "amenity" and v == "place_of_worship":
                    return f"{k}={v}+{t.get('religion', 'bilinmiyor')}"
                return f"{k}={v}"
        return None

    class H(osmium.SimpleHandler):
        def _al(self, o, lon, lat, tip):
            t = {x.k: x.v for x in o.tags}
            if any(t.get(k) for k in ("military", "military_service")):
                return
            ad = t.get("name:tr") or t.get("name")
            if not ad or len(ad) < 2 or len(ad) > 120:
                return
            k = tur(t)
            if k:
                kayit.append({"ad": ad.strip(), "osm_tur": k, "lon": round(lon, 4), "lat": round(lat, 4), "osm": f"{tip}{o.id}"})

        def node(self, n):
            if n.tags and n.location.valid():
                self._al(n, n.location.lon, n.location.lat, "n")

        def way(self, w):
            if w.tags and len(w.nodes) and w.nodes[0].location.valid():
                self._al(w, w.nodes[0].lon, w.nodes[0].lat, "w")
    H().apply_file(pbf, locations=True, idx="flex_mem")
    return kayit


def main(pbf, cikti: Path):
    cikti.mkdir(parents=True, exist_ok=True)
    ham = cikar(pbf)
    print("ham kayıt:", len(ham), flush=True)
    for r in ham:
        r["sinif"] = TR_AD.get(r["osm_tur"])
    gor, tekil = set(), []
    for r in ham:
        if not r["sinif"]:
            continue
        a = (norm(r["ad"]), r["sinif"])
        if a in gor:
            continue
        gor.add(a)
        tekil.append(r)
    say = Counter(r["sinif"] for r in tekil)
    siniflar = sorted(s for s, n in say.items() if n >= EN_AZ)
    veri = [r for r in tekil if r["sinif"] in siniflar]
    # aynı normalize ad birden çok sınıfta varsa belirsizdir: test/val'den çıkar, eğitimde kalır
    ad_sinif = defaultdict(set)
    for r in veri:
        ad_sinif[norm(r["ad"])].add(r["sinif"])
    for r in veri:
        h = int(hashlib.sha1(ozut(r["ad"]).encode()).hexdigest(), 16) % 10
        r["bolum"] = "test" if h == 0 else ("val" if h == 1 else "train")
        r["belirsiz_ad"] = len(ad_sinif[norm(r["ad"])]) > 1
        if r["belirsiz_ad"] and r["bolum"] != "train":
            r["bolum"] = "train"
    with open(cikti / "poi_ad_tur.jsonl", "w", encoding="utf-8") as f:
        for r in sorted(veri, key=lambda r: (r["bolum"], r["sinif"], r["ad"])):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    bol = Counter(r["bolum"] for r in veri)
    print("sınıf:", len(siniflar), "öğe:", len(veri), dict(bol), flush=True)

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, classification_report, f1_score
    from sklearn.pipeline import make_pipeline
    import joblib
    tr = [r for r in veri if r["bolum"] == "train"]
    te = [r for r in veri if r["bolum"] == "test"]
    model = make_pipeline(TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True, preprocessor=norm,
                                          max_features=400000),
                          LogisticRegression(C=4.0, max_iter=300, class_weight="balanced"))
    model.fit([r["ad"] for r in tr], [r["sinif"] for r in tr])
    tah = model.predict([r["ad"] for r in te])
    gercek = [r["sinif"] for r in te]
    sonuc = {"siniflar": siniflar, "sinif_sayisi": len(siniflar), "oge": len(veri), "bolum": dict(bol),
             "test_dogruluk": round(accuracy_score(gercek, tah), 4), "test_makro_f1": round(f1_score(gercek, tah, average="macro"), 4),
             "sinif_dagilimi": dict(Counter(r["sinif"] for r in veri).most_common()),
             "sinif_raporu": classification_report(gercek, tah, output_dict=True, zero_division=0)}
    (cikti / "sonuc.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    joblib.dump(model, cikti / "poi_tur_siniflandirici.joblib", compress=3)
    print("test doğruluk", sonuc["test_dogruluk"], "makro F1", sonuc["test_makro_f1"], flush=True)


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]))
