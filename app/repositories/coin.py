from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Coin


class CoinRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_coingecko_id(self, coingecko_id: str) -> Coin | None:
        return self.db.scalar(select(Coin).where(Coin.coingecko_id == coingecko_id))

    def list_all(self) -> Sequence[Coin]:
        return self.db.scalars(select(Coin).order_by(Coin.name)).all()

    def add(self, coin: Coin) -> Coin:
        self.db.add(coin)
        self.db.flush()
        return coin

    def get(self, coin_id: int) -> Coin | None:
        return self.db.get(Coin, coin_id)
