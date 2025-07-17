from datetime import date

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
    isin: str
    short_name: str = Field(alias="shortName")
    long_name: str = Field(alias="longName")
    quote_type: str = Field(alias="quoteType")
    currency: str = Field(min_length=3, max_length=3)
    exchange: str
    industry_key: str = Field(alias="industryKey")
    sector_key: str = Field(alias="sectorKey")
    long_business_summary: str = Field(alias="longBusinessSummary")
