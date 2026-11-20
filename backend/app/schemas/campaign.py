import re
from dataclasses import dataclass
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator

COUNTRY_CODE = re.compile(r"^[A-Z]{2}$")


class CampaignCreateRequest(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    geo: list[str] = Field(description="Коды стран ISO 3166-1 alpha-2: 'MX,AU' или ['MX', 'AU']")
    offer_id: int = Field(gt=0)

    @field_validator("geo", mode="before")
    @classmethod
    def parse_geo(cls, value: object) -> list[str]:
        items = value.split(",") if isinstance(value, str) else value
        if not isinstance(items, list):
            raise ValueError("geo должен быть строкой или списком")

        codes: list[str] = []
        for item in items:
            code = str(item).strip().upper()
            if not code:
                continue
            if not COUNTRY_CODE.match(code):
                raise ValueError(f"неверный код страны: {item!r}")
            if code not in codes:
                codes.append(code)

        if not codes:
            raise ValueError("укажите хотя бы одну страну")
        return codes


@dataclass(frozen=True)
class CreatedCampaign:
    keitaro_id: int
    name: str
    alias: str
    geo: list[str]
    offer_id: int
    geo_stream_id: int
    offer_stream_id: int
