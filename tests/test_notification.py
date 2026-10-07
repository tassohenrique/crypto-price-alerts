from decimal import Decimal

import pytest

from app.models import Alert, AlertDirection, Coin
from app.services.notification import build_alert_message, format_brl


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("450000", "R$ 450.000,00"),
        ("1234.567", "R$ 1.234,57"),
        ("0.5", "R$ 0,5"),
        ("0.0000123456789", "R$ 0,00001235"),
    ],
)
def test_format_brl(value, expected):
    assert format_brl(Decimal(value)) == expected


def make_alert(direction, target, triggered):
    return Alert(
        coin=Coin(coingecko_id="bitcoin", symbol="BTC", name="Bitcoin"),
        direction=direction,
        target_price=Decimal(target),
        triggered_price=Decimal(triggered),
    )


def test_message_for_above_alert():
    alert = make_alert(AlertDirection.ABOVE, "400000", "450000")

    assert build_alert_message(alert) == (
        "Bitcoin (BTC) subiu para R$ 450.000,00.\nSeu alerta: acima de R$ 400.000,00."
    )


def test_message_for_below_alert():
    alert = make_alert(AlertDirection.BELOW, "300000", "299999.99")

    assert build_alert_message(alert) == (
        "Bitcoin (BTC) caiu para R$ 299.999,99.\nSeu alerta: abaixo de R$ 300.000,00."
    )