"""CR kazandıran adımlar (ZIP içe aktarma, yayım) için zaman penceresi.

Platformun günlük 100 CR tavanı 00:00 TSİ'de sıfırlanır; tavan dolunca o gün etiket puanı da durur. Bu yüzden CR kazandıran
adımlar gecenin son penceresinde (23:25-23:58 TSİ = 20:25-20:58 UTC) yapılır. İstisna: bugünkü kazanç zaten >= 100 ise
kaybedilecek bir şey kalmadığından adım her an yapılabilir.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

TSI = timezone(timedelta(hours=3))
BASLA = (23, 25)
BITIS = (23, 58)
TAVAN_CR = 100


def tsi(an: datetime) -> datetime:
    return an.astimezone(TSI)


def pencere_icinde(an: datetime) -> bool:
    t = tsi(an)
    dk = t.hour * 60 + t.minute
    return BASLA[0] * 60 + BASLA[1] <= dk <= BITIS[0] * 60 + BITIS[1]


def kalan_bekleme_sn(an: datetime) -> float | None:
    """Bugünkü pencerenin başlangıcına kalan saniye; pencere içindeyse 0; bugün kaçtıysa None."""
    t = tsi(an)
    bas = t.replace(hour=BASLA[0], minute=BASLA[1], second=0, microsecond=0)
    bit = t.replace(hour=BITIS[0], minute=BITIS[1], second=59, microsecond=0)
    if t > bit:
        return None
    return max(0.0, (bas - t).total_seconds())


def izinli(an: datetime, bugun_kazanilan_cr) -> tuple[bool, str]:
    cr = float(bugun_kazanilan_cr or 0)
    if cr >= TAVAN_CR:
        return True, f"günlük tavan dolu ({cr:g} CR), adım serbest"
    if pencere_icinde(an):
        return True, "23:25-23:58 TSİ penceresinde"
    return False, f"pencere dışı ({tsi(an):%H:%M} TSİ) ve bugünkü kazanç {cr:g} < {TAVAN_CR}"
