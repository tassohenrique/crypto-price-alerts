import logging
import signal
import threading
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.clients.coingecko import (
    CoinGeckoClient,
    CoinGeckoError,
    CoinGeckoRateLimitError,
    create_coingecko_client,
)
from app.clients.telegram import TelegramClient, TelegramError, create_telegram_client
from app.core.config import settings
from app.db.session import SessionLocal
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


def collect_prices(
    db: Session, coingecko: CoinGeckoClient, result: CycleResult
) -> None:
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
            logger.warning(
                "Falha ao enviar o aviso do alerta %s; nova tentativa no próximo ciclo.",
                alert.id,
            )
            result.notifications_failed += 1
            continue

        alert.notified_at = datetime.now(UTC)
        db.commit()
        result.notifications_sent += 1


def run_once(coingecko: CoinGeckoClient, telegram: TelegramClient) -> None:
    """Roda um ciclo numa sessão própria. Nenhum erro escapa daqui."""
    with SessionLocal() as db:
        try:
            result = run_cycle(db, coingecko, telegram)
        except Exception:
            db.rollback()
            logger.exception("Erro inesperado no ciclo; o worker continua no próximo.")
            return

    logger.info(
        "Ciclo concluído: %d preços, %d alertas disparados, %d avisos enviados, "
        "%d falhas de envio.",
        result.prices_saved,
        result.alerts_triggered,
        result.notifications_sent,
        result.notifications_failed,
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    stop = threading.Event()

    def request_stop(signum: int, _frame: object) -> None:
        logger.info("Sinal %s recebido; encerrando após o ciclo atual.", signum)
        stop.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    interval = settings.poll_interval_seconds
    logger.info("Worker iniciado; um ciclo a cada %d segundos.", interval)

    telegram = create_telegram_client()
    with create_coingecko_client() as coingecko:
        while not stop.is_set():
            run_once(coingecko, telegram)
            stop.wait(interval)

    logger.info("Worker encerrado.")


if __name__ == "__main__":
    main()
