from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SP500Constituent(BaseModel):
    index_name: str = "sp500"
    symbol: str
    security_name: str
    gics_sector: str
    gics_sub_industry: str
    date_added: date


class Security(BaseModel):
    symbol: str
    isin: str
    short_name: str = Field(alias="shortName")
    long_name: str = Field(alias="longName")
    quote_type: str = Field(alias="quoteType")
    currency: str
    exchange: str
    industry_key: str = Field(alias="industryKey")
    sector_key: str = Field(alias="sectorKey")
    long_business_summary: str = Field(alias="longBusinessSummary")


class MarketData(BaseModel):
    symbol: str = Field(..., max_length=14)
    item_id: int = Field(...)
    value_date: date = Field(...)
    value: Decimal = Field(
        ...,
        max_digits=30,
    )

    @field_validator("value", mode="before")
    @classmethod
    def validate_value(cls, value: float | int) -> Decimal | int:
        if isinstance(value, int):
            return value
        return Decimal(value).quantize(Decimal("0.0001"), rounding="ROUND_HALF_UP")


class SecMaster(BaseModel):
    symbol: str
    underlying_symbol: str
    isin: str
    short_name: str
    long_name: str
    quote_type: str
    currency: str
    exchange: str
    industry_key: str
    sector_key: str
    uuid: UUID
    long_business_summary: str


class ItemMaster(BaseModel):
    item_id: int
    item_name: str
    item_desc: str
