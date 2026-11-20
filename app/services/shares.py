"""Пересчёт долей офферов в потоке (DISPUTED.md №1–3)."""

from collections.abc import Sequence
from dataclasses import dataclass

from app.services.errors import ShareError

__all__ = ["ShareError", "ShareSlot", "rebalance"]

TOTAL = 100


@dataclass(frozen=True)
class ShareSlot:
    active: bool
    pinned: bool
    share: int


def rebalance(slots: Sequence[ShareSlot]) -> list[int]:
    """Новые доли в том же порядке.

    removed — 0; активные запиненные сохраняют долю; активные незапиненные делят
    `100 − сумма пинов` поровну, остаток по 1% сверху списка.
    """
    shares = [0] * len(slots)
    pinned = [i for i, slot in enumerate(slots) if slot.active and slot.pinned]
    free = [i for i, slot in enumerate(slots) if slot.active and not slot.pinned]

    for i in pinned:
        shares[i] = slots[i].share
    _validate(shares, pinned, free)
    if not free:
        return shares

    rest = TOTAL - sum(shares)
    base, remainder = divmod(rest, len(free))
    for rank, i in enumerate(free):
        shares[i] = base + (1 if rank < remainder else 0)
    return shares


def _validate(shares: list[int], pinned: list[int], free: list[int]) -> None:
    if any(not 0 <= shares[i] <= TOTAL for i in pinned):
        raise ShareError("Доля оффера должна быть от 0 до 100%")

    pinned_total = sum(shares[i] for i in pinned)
    if pinned_total > TOTAL:
        raise ShareError(f"Закреплённые доли в сумме {pinned_total}% — больше 100%")
    if free and TOTAL - pinned_total < len(free):
        raise ShareError(
            f"Закреплено {pinned_total}%: незакреплённым офферам ({len(free)}) не остаётся доли"
        )
    if pinned and not free and pinned_total != TOTAL:
        raise ShareError(
            f"Закреплено {pinned_total}%, а остаток {TOTAL - pinned_total}% некому отдать: "
            "все активные офферы закреплены"
        )
