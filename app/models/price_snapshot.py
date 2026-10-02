from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PriceSnapshot(Base):
    """O preço de uma moeda num momento. Uma linha por moeda a cada busca do worker."""

    __tablename__ = "price_snapshots"
    __table_args__ = (
        Index("ix_price_snapshots_coin_id_fetched_at", "coin_id", "fetched_at"),
        CheckConstraint("price > 0", name="ck_price_snapshots_price_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    coin_id: Mapped[int] = mapped_column(ForeignKey("coins.id", ondelete="CASCADE"))
    price: Mapped[Decimal] = mapped_column(Numeric(30, 12))
    currency: Mapped[str] = mapped_column(String(3), default="brl")
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
