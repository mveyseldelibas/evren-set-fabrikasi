"""Yeni tarif adayları için Türkiye OSM dökümünde etiket sayımı (kapalı yol + multipolygon) ve alan dağılımı.
Kullanım: python araclar/osm_aday_say.py <pbf> <konum_dizini> <cikti.json>"""
import sys, json, math, osmium
from collections import defaultdict
ADAY = {
 "baraj_golu":[{"water":"reservoir"},{"landuse":"reservoir"},{"landuse":"basin"}], "dogal_gol":[{"water":"lake"}], "golet":[{"water":"pond"}],
 "nehir_yatagi":[{"water":"river"},{"waterway":"riverbank"}], "kumsal":[{"natural":"beach"}], "cop_depolama":[{"landuse":"landfill"}],
 "atiksu_aritma":[{"man_made":"wastewater_plant"}], "havalimani":[{"aeroway":"aerodrome"}], "demiryolu_alani":[{"landuse":"railway"}],
 "hayvancilik_ciftligi":[{"landuse":"farmyard"}], "fidanlik":[{"landuse":"plant_nursery"}], "trafo":[{"power":"substation"}],
 "golf":[{"leisure":"golf_course"}], "stadyum":[{"leisure":"stadium"}], "hastane":[{"amenity":"hospital"}], "okul":[{"amenity":"school"}],
 "park":[{"leisure":"park"}], "ticari":[{"landuse":"retail"},{"landuse":"commercial"}], "konut":[{"landuse":"residential"}],
 "tarla":[{"landuse":"farmland"}], "orman":[{"landuse":"forest"},{"natural":"wood"}], "calilik":[{"natural":"scrub"}],
 "ciplak_kaya":[{"natural":"bare_rock"}], "kum":[{"natural":"sand"}], "cayir":[{"landuse":"meadow"},{"natural":"grassland"}],
 "tuzla":[{"landuse":"salt_pond"}], "bos_arsa":[{"landuse":"brownfield"},{"landuse":"greenfield"}], "spor_merkezi":[{"leisure":"sports_centre"}],
 "otopark":[{"amenity":"parking"}], "ruzgar_santrali":[{"plant:source":"wind"}], "termik_santral":[{"plant:source":"coal"},{"plant:source":"gas"}],
 "hes":[{"plant:source":"hydro"}], "kamp":[{"tourism":"camp_site"}], "su_parki":[{"leisure":"water_park"}], "bag":[{"landuse":"vineyard"}],
 "meyve_bahcesi":[{"landuse":"orchard"}], "findik":[{"trees":"hazel_plants"}], "cay":[{"crop":"tea"}], "pirinc":[{"crop":"rice"},{"landuse":"paddy"}],
 "zeytin":[{"trees":"olive_trees"}], "funda":[{"natural":"heath"}], "rekreasyon":[{"landuse":"recreation_ground"}], "tren_gari":[{"railway":"station"}],
 "pist":[{"aeroway":"runway"}], "kiyi_dolgu":[{"man_made":"breakwater"}], "baraj_govdesi":[{"waterway":"dam"}], "buzul":[{"natural":"glacier"}],
 "lojistik_depo":[{"landuse":"depot"},{"building":"warehouse"}], "akaryakit":[{"amenity":"fuel"}], "alisveris_merkezi":[{"shop":"mall"}],
}
def uy(t):
    out=[]
    for ad,kur in ADAY.items():
        for k in kur:
            if all(t.get(a)==v for a,v in k.items()): out.append(ad); break
    return out
R=6371008.8
def alan(pts):
    if len(pts)<4: return 0
    lat0=math.radians(sum(p[1] for p in pts)/len(pts)); s=0
    xy=[(math.radians(x)*R*math.cos(lat0), math.radians(y)*R) for x,y in pts]
    for i in range(len(xy)-1): s+=xy[i][0]*xy[i+1][1]-xy[i+1][0]*xy[i][1]
    return abs(s)/2
S=defaultdict(lambda: {"yol":0,"rel":0,"1ha":0,"5ha":0,"50ha":0})
class H(osmium.SimpleHandler):
    def way(self,w):
        if not w.is_closed(): return
        ads=uy({t.k:t.v for t in w.tags})
        if not ads: return
        try: a=alan([(n.lon,n.lat) for n in w.nodes])
        except Exception: a=0
        for ad in ads:
            d=S[ad]; d["yol"]+=1
            if a>=1e4: d["1ha"]+=1
            if a>=5e4: d["5ha"]+=1
            if a>=5e5: d["50ha"]+=1
    def relation(self,r):
        t={x.k:x.v for x in r.tags}
        if t.get("type")!="multipolygon": return
        for ad in uy(t): S[ad]["rel"]+=1
H().apply_file(sys.argv[1], locations=True, idx=("flex_mem" if sys.argv[2]=="-" else "sparse_file_array,"+sys.argv[2]))
json.dump(S, open(sys.argv[3],"w",encoding="utf-8"), ensure_ascii=False, indent=0)
for ad,d in sorted(S.items(), key=lambda x:-x[1]["1ha"]): print(ad, d)
