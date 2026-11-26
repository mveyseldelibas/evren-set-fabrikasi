"""CR kazandıran adımlar (ZIP içe aktarma, yayım) için zaman penceresi.

Platformun günlük 100 CR tavanı 00:00 TSİ'de sıfırlanır; tavan dolunca o gün etiket puanı da durur. Bu yüzden CR kazandıran
adımlar gecenin son penceresinde (23:25-23:58 TSİ = 20:25-20:58 UTC) yapılır. İstisna: bugünkü kazanç zaten >= 100 ise
kaybedilecek bir şey kalmadığından adım her an yapılabilir.

27.11: Erken pencere. Platform günlük etiket sayacını 300'de keser (annotation-save max_daily 300); sayaç 300'e
ulaştıysa o günün etiket kazanımı bitmiştir ve CR tavanının dolması artık bir şey kaybettirmez. O durumda pencere
20:30 TSİ'de açılır (günde 6 set yüklemesine yetecek süre).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

TSI = timezone(timedelta(hours=3))
BASLA = (23, 25)
BITIS = (23, 58)
TAVAN_CR = 100
ERKEN_BASLA = (20, 30)
ETIKET_DOLU = 300


def tsi(an: datetime) -> datetime:
    return an.astimezone(TSI)


def etiket_dolu(etiket) -> bool:
    return etiket is not None and float(etiket) >= ETIKET_DOLU


def pencere_icinde(an: datetime, etiket=None) -> bool:
    t = tsi(an)
    dk = t.hour * 60 + t.minute
    bas = ERKEN_BASLA if etiket_dolu(etiket) else BASLA
    return bas[0] * 60 + bas[1] <= dk <= BITIS[0] * 60 + BITIS[1]


def kalan_bekleme_sn(an: datetime, etiket=None) -> float | None:
    """Bugünkü pencerenin başlangıcına kalan saniye; pencere içindeyse 0; bugün kaçtıysa None."""
    t = tsi(an)
    b = ERKEN_BASLA if etiket_dolu(etiket) else BASLA
    bas = t.replace(hour=b[0], minute=b[1], second=0, microsecond=0)
    bit = t.replace(hour=BITIS[0], minute=BITIS[1], second=59, microsecond=0)
    if t > bit:
        return None
    return max(0.0, (bas - t).total_seconds())


def izinli(an: datetime, bugun_kazanilan_cr, etiket=None) -> tuple[bool, str]:
    cr = float(bugun_kazanilan_cr or 0)
    if cr >= TAVAN_CR:
        return True, f"günlük tavan dolu ({cr:g} CR), adım serbest"
    if pencere_icinde(an):
        return True, "23:25-23:58 TSİ penceresinde"
    if pencere_icinde(an, etiket):
        return True, f"erken pencere (20:30-23:58 TSİ, bugünkü etiket {etiket} >= {ETIKET_DOLU})"
    return False, f"pencere dışı ({tsi(an):%H:%M} TSİ) ve bugünkü kazanç {cr:g} < {TAVAN_CR}"
