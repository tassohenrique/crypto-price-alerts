from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PriceSnapshot


class PriceSnapshotRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_many(self, snapshots: list[PriceSnapshot]) -> None:
        """Grava os preços de uma busca inteira de uma vez."""
        self.db.add_all(snapshots)
        self.db.flush()

    def list_for_coin(
        self,
        coin_id: int,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 500,
    ) -> Sequence[PriceSnapshot]:
        """Histórico de uma moeda, do mais recente para o mais antigo.

        O período é fechado no início e aberto no fim: start <= fetched_at < end.
        """
        query = select(PriceSnapshot).where(PriceSnapshot.coin_id == coin_id)
        if start is not None:
            query = query.where(PriceSnapshot.fetched_at >= start)
        if end is not None:
            query = query.where(PriceSnapshot.fetched_at < end)
        query = query.order_by(PriceSnapshot.fetched_at.desc(), PriceSnapshot.id.desc())
        return self.db.scalars(query.limit(limit)).all()
