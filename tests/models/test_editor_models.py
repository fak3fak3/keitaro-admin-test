import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models.stream import OfferStatus, Stream, StreamOffer


def make_stream(**overrides):
    fields = {
        "keitaro_id": 1333643,
        "campaign_id": 217109,
        "name": "Offers",
        "position": 2,
        "type": "default",
    }
    return Stream(**{**fields, **overrides})


async def test_stream_keeps_offers_in_sort_order(db_session):
    stream = make_stream()
    stream.offers = [
        StreamOffer(offer_id=3717, offer_name="B", share=33, sort_order=1),
        StreamOffer(offer_id=3749, offer_name="A", share=34, sort_order=0),
    ]
    db_session.add(stream)
    await db_session.flush()
    db_session.expunge_all()

    loaded = await db_session.scalar(select(Stream).where(Stream.keitaro_id == 1333643))

    assert [o.offer_id for o in loaded.offers] == [3749, 3717]


async def test_new_stream_offer_defaults(db_session):
    stream = make_stream()
    stream.offers = [StreamOffer(offer_id=18813, offer_name="Flexacil", share=100, sort_order=0)]
    db_session.add(stream)
    await db_session.flush()

    offer = stream.offers[0]
    assert offer.status is OfferStatus.ACTIVE
    assert offer.pinned is False
    assert offer.published_status is None
    assert offer.published_share is None


async def test_offer_is_unique_within_stream(db_session):
    stream = make_stream()
    stream.offers = [
        StreamOffer(offer_id=18813, offer_name="X", share=50, sort_order=0),
        StreamOffer(offer_id=18813, offer_name="X", share=50, sort_order=1),
    ]
    db_session.add(stream)

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_deleting_stream_deletes_its_offers(db_session):
    stream = make_stream()
    stream.offers = [StreamOffer(offer_id=18813, offer_name="X", share=100, sort_order=0)]
    db_session.add(stream)
    await db_session.flush()

    await db_session.delete(stream)
    await db_session.flush()

    assert (await db_session.scalars(select(StreamOffer))).all() == []


def published(offer_id, share, status=OfferStatus.ACTIVE, **overrides):
    """Привязка, совпадающая с опубликованным в Keitaro состоянием."""
    fields = {
        "offer_id": offer_id,
        "offer_name": f"Offer {offer_id}",
        "status": status,
        "share": share,
        "sort_order": 0,
        "published_status": status,
        "published_share": share,
    }
    return StreamOffer(**{**fields, **overrides})


def test_offer_matching_published_state_is_not_changed():
    assert published(1, 50).is_changed is False


def test_never_published_offer_is_changed():
    offer = published(1, 50, published_status=None, published_share=None)

    assert offer.is_changed is True


@pytest.mark.parametrize(
    "changes",
    [{"share": 40}, {"status": OfferStatus.REMOVED, "share": 0}],
)
def test_offer_edited_after_publish_is_changed(changes):
    offer = published(1, 50)
    for field, value in changes.items():
        setattr(offer, field, value)

    assert offer.is_changed is True


def test_pin_alone_does_not_make_offer_changed():
    assert published(1, 50, pinned=True).is_changed is False


def test_stream_has_draft_when_any_offer_changed():
    clean = make_stream()
    clean.offers = [published(1, 50), published(2, 50)]
    dirty = make_stream()
    dirty.offers = [published(1, 50), published(2, 50)]
    dirty.offers[1].share = 40

    assert clean.has_draft is False
    assert dirty.has_draft is True


async def test_status_is_stored_as_lowercase_value(db_session):
    stream = make_stream()
    stream.offers = [StreamOffer(offer_id=1, offer_name="X", share=100, sort_order=0)]
    db_session.add(stream)
    await db_session.flush()

    raw = await db_session.scalar(text("select status from stream_offers"))

    assert raw == "active"
