import pytest
from pydantic import ValidationError

from app.schemas.campaign import CampaignCreateRequest


def test_geo_string_is_split_normalized_and_deduplicated():
    request = CampaignCreateRequest(name="My campaign", geo=" mx, AU ,ro,mx ", offer_id=18813)

    assert request.geo == ["MX", "AU", "RO"]


def test_geo_accepts_list():
    request = CampaignCreateRequest(name="My campaign", geo=["au"], offer_id=18813)

    assert request.geo == ["AU"]


@pytest.mark.parametrize("geo", ["", " , ", "MEX", "M1", "Australia"])
def test_invalid_geo_is_rejected(geo):
    with pytest.raises(ValidationError):
        CampaignCreateRequest(name="My campaign", geo=geo, offer_id=18813)


def test_name_is_stripped_and_required():
    assert CampaignCreateRequest(name="  Test  ", geo="AU", offer_id=1).name == "Test"
    with pytest.raises(ValidationError):
        CampaignCreateRequest(name="   ", geo="AU", offer_id=1)


def test_offer_id_must_be_positive():
    with pytest.raises(ValidationError):
        CampaignCreateRequest(name="Test", geo="AU", offer_id=0)
