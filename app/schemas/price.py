from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PriceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    price: Decimal
    currency: str
    fetched_at: datetime
