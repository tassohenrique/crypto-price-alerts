from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.coin import Coin
from app.models.enums import AlertDirection


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint("target_price > 0", name="ck_alerts_target_price_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    coin_id: Mapped[int] = mapped_column(
        ForeignKey("coins.id", ondelete="CASCADE"), index=True
    )
    direction: Mapped[AlertDirection] = mapped_column(
        Enum(
            AlertDirection,
            native_enum=False,
            length=10,
            values_callable=lambda members: [member.value for member in members],
        )
    )
    target_price: Mapped[Decimal] = mapped_column(Numeric(30, 12))
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    triggered_price: Mapped[Decimal | None] = mapped_column(Numeric(30, 12))
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    coin: Mapped[Coin] = relationship()