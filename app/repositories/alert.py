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

    def list_pending_notifications(self) -> Sequence[Alert]:
        """Alertas que já dispararam, mas cujo aviso ainda não foi enviado."""
        query = (
            select(Alert)
            .join(Alert.coin)
            .options(contains_eager(Alert.coin))
            .where(Alert.triggered_at.is_not(None), Alert.notified_at.is_(None))
            .order_by(Alert.triggered_at, Alert.id)
        )
        return self.db.scalars(query).all()

    def flush(self) -> None:
        """Envia as alterações pendentes ao banco, sem confirmar a transação."""
        self.db.flush()

    def get(self, alert_id: int) -> Alert | None:
        return self.db.get(Alert, alert_id)

    def list_all(self, active: bool | None = None) -> Sequence[Alert]:
        """Todos os alertas, do mais recente para o mais antigo."""
        query = select(Alert).join(Alert.coin).options(contains_eager(Alert.coin))
        if active is not None:
            query = query.where(Alert.is_active.is_(active))
        return self.db.scalars(query.order_by(Alert.id.desc())).all()

    def delete(self, alert: Alert) -> None:
        self.db.delete(alert)
        self.db.flush()
