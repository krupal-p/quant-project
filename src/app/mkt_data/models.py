from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class SP500Constituent(BaseModel):
    index_name: str = "sp500"
    symbol: str
    security_name: str
    gics_sector: str
    gics_sub_industry: str
    date_added: date


class Security(BaseModel):
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
