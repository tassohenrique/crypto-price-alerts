from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from app.core.exceptions import ConflictError, NotFoundError
from app.models import Alert, AlertDirection
from app.repositories.alert import AlertRepository
from app.repositories.coin import CoinRepository
from app.schemas.alert import AlertCreate


def is_triggered(
    direction: AlertDirection, target_price: Decimal, price: Decimal
) -> bool:
    """Decide se um preço atinge o alvo. O preço exatamente igual ao alvo dispara."""
    if direction is AlertDirection.ABOVE:
        return price >= target_price
    return price <= target_price


@dataclass(frozen=True)
class TriggeredAlert:
    alert: Alert
    price: Decimal


class AlertService:
    def __init__(self, alerts: AlertRepository, coins: CoinRepository) -> None:
        self.alerts = alerts
        self.coins = coins

    # --- Usado pelo worker ---

    def check_alerts(self, prices: Mapping[str, Decimal]) -> list[TriggeredAlert]:
        """Marca como disparados os alertas atingidos e devolve o que deve ser enviado.

        Recebe os preços indexados pelo id da CoinGecko. Não envia mensagens
        nem faz commit: isso é responsabilidade de quem orquestra.
        """
        triggered: list[TriggeredAlert] = []
        now = datetime.now(UTC)

        for alert in self.alerts.list_active_for_coingecko_ids(list(prices)):
            price = prices[alert.coin.coingecko_id]
            if is_triggered(alert.direction, alert.target_price, price):
                alert.is_active = False
                alert.triggered_at = now
                alert.triggered_price = price
                triggered.append(TriggeredAlert(alert=alert, price=price))

        self.alerts.flush()
        return triggered

    # --- Usado pela API ---

    def list_alerts(self, active: bool | None = None) -> Sequence[Alert]:
        return self.alerts.list_all(active)

    def get_alert(self, alert_id: int) -> Alert:
        alert = self.alerts.get(alert_id)
        if alert is None:
            raise NotFoundError("Alerta não encontrado.")
        return alert

    def create_alert(self, data: AlertCreate) -> Alert:
        coin = self.coins.get(data.coin_id)
        if coin is None:
            raise NotFoundError("Moeda não encontrada.")
        return self.alerts.add(
            Alert(coin=coin, direction=data.direction, target_price=data.target_price)
        )

    def rearm_alert(self, alert_id: int) -> Alert:
        """Reativa um alerta que já disparou e já teve o aviso enviado."""
        alert = self.get_alert(alert_id)
        if alert.is_active:
            raise ConflictError("O alerta já está ativo.")
        if alert.notified_at is None:
            raise ConflictError(
                "O aviso deste alerta ainda não foi enviado. Tente após o envio."
            )
        alert.is_active = True
        alert.triggered_at = None
        alert.triggered_price = None
        alert.notified_at = None
        self.alerts.flush()
        return alert

    def delete_alert(self, alert_id: int) -> None:
        self.alerts.delete(self.get_alert(alert_id))
