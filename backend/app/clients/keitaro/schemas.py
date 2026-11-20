"""Модели Keitaro Admin API (см. docs/keitaro-openapi.yaml). Лишние поля ответа игнорируем."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Domain(BaseModel):
    id: int
    name: str


class Group(BaseModel):
    id: int
    name: str


class TrafficSource(BaseModel):
    id: int
    name: str


class Offer(BaseModel):
    id: int
    name: str


class CampaignCreate(BaseModel):
    name: str
    alias: str
    domain_id: int
    group_id: int
    traffic_source_id: int


class Campaign(BaseModel):
    id: int
    name: str
    alias: str


class StreamOffer(BaseModel):
    offer_id: int
    share: int
    state: str = "active"


class StreamFilter(BaseModel):
    name: str
    mode: str
    payload: Any = None


class StreamCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    campaign_id: int
    name: str
    type: str
    position: int
    schema_: str = Field(alias="schema")
    action_type: str
    action_payload: str | None = None
    filters: list[StreamFilter] = []
    offers: list[StreamOffer] = []


class Stream(BaseModel):
    # Поле в API называется "schema", а это имя занято у BaseModel.
    model_config = ConfigDict(populate_by_name=True)

    id: int
    campaign_id: int
    name: str
    type: str
    position: int | None = None
    schema_: str | None = Field(default=None, alias="schema")
    action_type: str | None = None
    action_payload: Any = None
    state: str
    filters: list[StreamFilter] = []
    offers: list[StreamOffer] = []
