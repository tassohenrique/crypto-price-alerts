from decimal import Decimal

from app.models import Alert, AlertDirection

BRAZILIAN_SEPARATORS = str.maketrans(",.", ".,")


def format_brl(value: Decimal) -> str:
    """Formata em reais. Valores abaixo de R$ 1 mantêm até 8 casas decimais."""
    if value >= 1:
        text = f"{value:,.2f}"
    else:
        text = f"{value.quantize(Decimal('0.00000001')).normalize():f}"
    return "R$ " + text.translate(BRAZILIAN_SEPARATORS)


def build_alert_message(alert: Alert) -> str:
    coin = alert.coin
    if alert.direction is AlertDirection.ABOVE:
        movement, target = "subiu para", "acima de"
    else:
        movement, target = "caiu para", "abaixo de"
    return (
        f"{coin.name} ({coin.symbol}) {movement} {format_brl(alert.triggered_price)}.\n"
        f"Seu alerta: {target} {format_brl(alert.target_price)}."
    )