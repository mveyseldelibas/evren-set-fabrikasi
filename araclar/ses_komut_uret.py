"""Türkçe sesli robot komutu seti: tr-robot-komut-yonlendirme cümlelerini Seslen TTS ile sese çevirir (bulutta).

Her cümle BİR kez seslendirilir (yazım gürültüsü kopyaları hariç); sesler cümleler arasında sırayla dağıtılır (aynı cümlenin çok sesli kopyası yok).
Çıktı: <cikti>/ses/<bolum>_<no>.wav (16 kHz mono), <cikti>/meta.jsonl (metin, etiket, ses adı, süre, bolum).
Kullanım: python araclar/ses_komut_uret.py <cikti> [en_cok=0]
"""
import json
import sys
import time
import wave
from pathlib import Path

import numpy as np
from huggingface_hub import hf_hub_download


def sesleri_bul(s):
    for ad in ("sesler", "SESLER", "ses_listesi", "konusmacilar"):
        v = getattr(s, ad, None)
        v = v() if callable(v) else v
        if v:
            return list(v.keys()) if isinstance(v, dict) else list(v)
    import seslen_tts
    for ad in dir(seslen_tts):
        v = getattr(seslen_tts, ad)
        if isinstance(v, (list, tuple, dict)) and ad.upper().startswith("SES"):
            return list(v.keys()) if isinstance(v, dict) else list(v)
    return ["zeynep"]


def yaz16(yol, ses, sr):
    from scipy.signal import resample_poly
    from math import gcd
    x = np.asarray(ses, dtype=np.float32).reshape(-1)
    if sr != 16000:
        g = gcd(int(sr), 16000)
        x = resample_poly(x, 16000 // g, int(sr) // g)
    x = np.clip(x, -1, 1)
    with wave.open(str(yol), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    return len(x) / 16000


def main(cikti: Path, en_cok: int):
    from seslen_tts import Seslen
    (cikti / "ses").mkdir(parents=True, exist_ok=True)
    s = Seslen()
    sesler = sesleri_bul(s)
    print("sesler:", sesler, flush=True)
    satir = []
    for b in ("train", "test"):
        p = hf_hub_download("mvdelibas/tr-robot-komut-yonlendirme", f"data/{b}.jsonl", repo_type="dataset")
        satir += [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    # yazım gürültüsü cümleleri (ör. "diskı ıt") konuşmada anlamsız: seslendirilmez
    satir = [o for o in satir if o.get("kaynak") != "yazim_gurultusu"]
    if en_cok:
        satir = satir[:en_cok]
    t0 = time.time(); meta = []
    for i, o in enumerate(satir):
        ses_ad = sesler[i % len(sesler)]
        try:
            r = s.tum(o["metin"], ses=ses_ad)
            ses, sr = (r if isinstance(r, tuple) else (r, getattr(s, "ornekleme", None) or getattr(s, "sr", None) or 24000))
            ad = f"{o['bolum']}_{i:05d}.wav"
            sure = yaz16(cikti / "ses" / ad, ses, sr)
            meta.append({"dosya": f"ses/{ad}", "metin": o["metin"], "etiket": o["etiket"], "komut_tr": o.get("komut_tr"),
                         "komut_en": o.get("komut_en"), "kaynak": o.get("kaynak"), "bolum": o["bolum"], "ses": ses_ad,
                         "sure_sn": round(sure, 2)})
        except Exception as e:
            print("HATA", i, type(e).__name__, str(e)[:120], flush=True)
        if i % 200 == 0:
            print(f"{i}/{len(satir)} {time.time() - t0:.0f} sn", flush=True)
    with open(cikti / "meta.jsonl", "w", encoding="utf-8") as f:
        for m in meta:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    print("bitti:", len(meta), "klip,", round(sum(m["sure_sn"] for m in meta) / 3600, 2), "saat", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 0)
