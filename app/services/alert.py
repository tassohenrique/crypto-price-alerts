from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from app.models import Alert, AlertDirection
from app.repositories.alert import AlertRepository


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
    def __init__(self, alerts: AlertRepository) -> None:
        self.alerts = alerts

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
                triggered.append(TriggeredAlert(alert=alert, price=price))

        self.alerts.flush()
        return triggered
