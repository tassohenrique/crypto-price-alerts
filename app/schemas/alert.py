from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import AlertDirection
from app.schemas.coin import CoinRead


class AlertCreate(BaseModel):
    coin_id: int
    direction: AlertDirection
    target_price: Decimal = Field(gt=0, max_digits=30, decimal_places=12)


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    coin: CoinRead
    direction: AlertDirection
    target_price: Decimal
    is_active: bool
    triggered_at: datetime | None
    triggered_price: Decimal | None
    notified_at: datetime | None
    created_at: datetime
