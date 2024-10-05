from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class SP500Constituent(BaseModel):
    index_name: str = "sp500"
    symbol: str
    security_name: str = Field(alias="security")
    gics_sector: str
    gics_sub_industry: str
    date_added: date


class Security(BaseModel):
    symbol: str
    underlyingSymbol: str
    isin: str
    shortName: str
    longName: str
    quoteType: str
    currency: str
    exchange: str
    industryKey: str
    sectorKey: str
    uuid: UUID
    longBusinessSummary: str
