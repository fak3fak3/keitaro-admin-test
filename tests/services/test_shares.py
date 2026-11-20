import pytest

from app.services.errors import ServiceError
from app.services.shares import ShareError, ShareSlot, rebalance


def active(share=0, pinned=False):
    return ShareSlot(active=True, pinned=pinned, share=share)


def removed(share=0):
    return ShareSlot(active=False, pinned=False, share=share)


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (1, [100]),
        (3, [34, 33, 33]),  # видео: три оффера, остаток 1% — первому сверху
        (4, [25, 25, 25, 25]),  # видео: после добавления четвёртого — по 25%
        (6, [17, 17, 17, 17, 16, 16]),
    ],
)
def test_unpinned_offers_split_100_evenly_remainder_goes_to_top(count, expected):
    assert rebalance([active() for _ in range(count)]) == expected


def test_removed_offers_get_zero_and_active_split_100():
    # видео: удалили один из четырёх — он 0%, остальные 34/33/33
    slots = [active(25), active(25), active(25), removed(25)]

    assert rebalance(slots) == [34, 33, 33, 0]


def test_removed_offer_in_the_middle_keeps_its_position():
    assert rebalance([active(), removed(), active()]) == [50, 0, 50]


def test_stream_without_active_offers_gets_all_zeros():
    # DISPUTED.md №2: удалить последний оффер можно
    assert rebalance([removed(100), removed()]) == [0, 0]
    assert rebalance([]) == []


def test_pinned_share_is_kept_and_others_split_the_rest():
    # видео: пин 25% у третьего оффера, вернули оффер — остальные 38/37, пин остался 25
    slots = [active(33), active(34), active(25, pinned=True), removed()]

    assert rebalance(slots) == [38, 37, 25, 0]


def test_several_pins_are_kept():
    slots = [active(10, pinned=True), active(), active(30, pinned=True), active()]

    assert rebalance(slots) == [10, 30, 30, 30]


def test_all_active_pinned_with_total_100_is_kept_as_is():
    assert rebalance([active(70, pinned=True), active(30, pinned=True)]) == [70, 30]


def test_pinned_removed_offer_gets_zero():
    # пин у удалённого оффера не держит долю
    slots = [active(), ShareSlot(active=False, pinned=True, share=40), active()]

    assert rebalance(slots) == [50, 0, 50]


@pytest.mark.parametrize(
    ("slots", "reason"),
    [
        ([active(60, pinned=True), active(50, pinned=True), active()], "больше 100%"),
        ([active(100, pinned=True), active()], "не остаётся доли"),
        ([active(99, pinned=True), active(), active()], "не остаётся доли"),
        ([active(25, pinned=True), active(50, pinned=True)], "некому отдать"),
        ([active(25, pinned=True), removed()], "некому отдать"),
        ([active(101, pinned=True)], "от 0 до 100"),
        ([active(-1, pinned=True), active()], "от 0 до 100"),
    ],
)
def test_impossible_pins_are_rejected(slots, reason):
    with pytest.raises(ShareError, match=reason):
        rebalance(slots)


def test_share_error_is_a_service_error():
    assert issubclass(ShareError, ServiceError)
