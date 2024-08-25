from datetime import date

from pydantic import BaseModel


class SP500Constituent(BaseModel):
    symbol: str
    security: str
    gics_sector: str
    gics_sub_industry: str
    date_added: date
