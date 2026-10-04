from collections.abc import Collection, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, contains_eager

from app.models import Alert, Coin


class AlertRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, alert: Alert) -> Alert:
        self.db.add(alert)
        self.db.flush()
        return alert

    def list_active_for_coingecko_ids(
        self, coingecko_ids: Collection[str]
    ) -> Sequence[Alert]:
        """Alertas ativos das moedas informadas, já com a moeda carregada."""
        if not coingecko_ids:
            return []
        query = (
            select(Alert)
            .join(Alert.coin)
            .options(contains_eager(Alert.coin))
            .where(Alert.is_active.is_(True), Coin.coingecko_id.in_(coingecko_ids))
            .order_by(Alert.id)
        )
        return self.db.scalars(query).all()

    def flush(self) -> None:
        """Envia as alterações pendentes ao banco, sem confirmar a transação."""
        self.db.flush()
