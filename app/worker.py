import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.clients.coingecko import (
    CoinGeckoClient,
    CoinGeckoError,
    CoinGeckoRateLimitError,
)
from app.clients.telegram import TelegramClient, TelegramError
from app.models import PriceSnapshot
from app.repositories.alert import AlertRepository
from app.repositories.coin import CoinRepository
from app.repositories.price_snapshot import PriceSnapshotRepository
from app.services.alert import AlertService
from app.services.notification import build_alert_message

logger = logging.getLogger(__name__)


@dataclass
class CycleResult:
    prices_saved: int = 0
    alerts_triggered: int = 0
    notifications_sent: int = 0
    notifications_failed: int = 0


def run_cycle(
    db: Session, coingecko: CoinGeckoClient, telegram: TelegramClient
) -> CycleResult:
    """Uma rodada completa: preços, histórico, alertas e avisos pendentes."""
    result = CycleResult()
    collect_prices(db, coingecko, result)
    send_pending_notifications(db, telegram, result)
    return result


def collect_prices(db: Session, coingecko: CoinGeckoClient, result: CycleResult) -> None:
    coins = CoinRepository(db).list_all()
    if not coins:
        logger.info("Nenhuma moeda cadastrada; nada a buscar.")
        return

    try:
        prices = coingecko.get_prices([coin.coingecko_id for coin in coins])
    except (CoinGeckoRateLimitError, CoinGeckoError):
        logger.warning("Falha ao buscar preços na CoinGecko; ciclo de preços pulado.")
        return

    coins_by_id = {coin.coingecko_id: coin for coin in coins}
    PriceSnapshotRepository(db).add_many(
        [
            PriceSnapshot(coin_id=coins_by_id[coingecko_id].id, price=price)
            for coingecko_id, price in prices.items()
        ]
    )
    triggered = AlertService(AlertRepository(db)).check_alerts(prices)
    db.commit()

    result.prices_saved = len(prices)
    result.alerts_triggered = len(triggered)


def send_pending_notifications(
    db: Session, telegram: TelegramClient, result: CycleResult
) -> None:
    for alert in AlertRepository(db).list_pending_notifications():
        try:
            telegram.send_message(build_alert_message(alert))
        except TelegramError:
            logger.warning("Falha ao enviar o aviso do alerta %s; nova tentativa no próximo ciclo.", alert.id)
            result.notifications_failed += 1
            continue

        alert.notified_at = datetime.now(UTC)
        db.commit()
        result.notifications_sent += 1