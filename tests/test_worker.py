import logging
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.clients.coingecko import CoinGeckoError
from app.clients.telegram import TelegramError
from app.models import AlertDirection, PriceSnapshot
from app.worker import configure_logging, main, run_cycle, run_once
from tests.conftest import TestingSessionLocal


class FakeCoinGecko:
    def __init__(self, prices=None, error=None):
        self.prices = prices or {}
        self.error = error
        self.calls = []

    def get_prices(self, coingecko_ids):
        self.calls.append(list(coingecko_ids))
        if self.error is not None:
            raise self.error
        return {
            key: value for key, value in self.prices.items() if key in coingecko_ids
        }


class FakeTelegram:
    def __init__(self, fail=False):
        self.fail = fail
        self.messages = []

    def send_message(self, text):
        if self.fail:
            raise TelegramError("falha simulada")
        self.messages.append(text)


@pytest.fixture
def telegram():
    return FakeTelegram()


def count_snapshots(db_session):
    return db_session.scalar(select(func.count()).select_from(PriceSnapshot))


def test_cycle_saves_prices_for_all_coins(db_session, bitcoin, ethereum, telegram):
    coingecko = FakeCoinGecko({"bitcoin": Decimal(450000), "ethereum": Decimal(15000)})

    result = run_cycle(db_session, coingecko, telegram)

    assert result.prices_saved == 2
    assert count_snapshots(db_session) == 2


def test_cycle_triggers_alert_and_sends_message(
    db_session, bitcoin, make_alert, telegram
):
    alert = make_alert(bitcoin, AlertDirection.ABOVE, "400000")
    coingecko = FakeCoinGecko({"bitcoin": Decimal(450000)})

    result = run_cycle(db_session, coingecko, telegram)

    assert result.alerts_triggered == 1
    assert result.notifications_sent == 1
    assert telegram.messages == [
        "Bitcoin (BTC) subiu para R$ 450.000,00.\nSeu alerta: acima de R$ 400.000,00."
    ]
    assert alert.notified_at is not None


def test_sent_notification_is_not_sent_again(db_session, bitcoin, make_alert, telegram):
    make_alert(bitcoin, AlertDirection.ABOVE, "400000")
    coingecko = FakeCoinGecko({"bitcoin": Decimal(450000)})

    run_cycle(db_session, coingecko, telegram)
    run_cycle(db_session, coingecko, telegram)

    assert len(telegram.messages) == 1


def test_failed_notification_is_retried_next_cycle(db_session, bitcoin, make_alert):
    alert = make_alert(bitcoin, AlertDirection.ABOVE, "400000")
    telegram = FakeTelegram(fail=True)

    first = run_cycle(db_session, FakeCoinGecko({"bitcoin": Decimal(450000)}), telegram)

    assert first.notifications_failed == 1
    assert alert.triggered_at is not None
    assert alert.notified_at is None

    telegram.fail = False
    second = run_cycle(
        db_session, FakeCoinGecko({"bitcoin": Decimal(380000)}), telegram
    )

    assert second.notifications_sent == 1
    assert "R$ 450.000,00" in telegram.messages[0]
    assert alert.notified_at is not None


def test_coingecko_failure_saves_nothing_and_does_not_raise(
    db_session, bitcoin, telegram
):
    coingecko = FakeCoinGecko(error=CoinGeckoError("falha simulada"))

    result = run_cycle(db_session, coingecko, telegram)

    assert result.prices_saved == 0
    assert count_snapshots(db_session) == 0


def test_coingecko_failure_still_sends_pending_notifications(
    db_session, bitcoin, make_alert
):
    make_alert(bitcoin, AlertDirection.ABOVE, "400000")
    telegram = FakeTelegram(fail=True)
    run_cycle(db_session, FakeCoinGecko({"bitcoin": Decimal(450000)}), telegram)

    telegram.fail = False
    result = run_cycle(
        db_session, FakeCoinGecko(error=CoinGeckoError("fora do ar")), telegram
    )

    assert result.notifications_sent == 1
    assert len(telegram.messages) == 1


def test_cycle_without_coins_does_not_call_coingecko(db_session, telegram):
    coingecko = FakeCoinGecko()

    run_cycle(db_session, coingecko, telegram)

    assert coingecko.calls == []


def test_run_once_survives_unexpected_error(monkeypatch, telegram):
    def broken_cycle(*args):
        raise RuntimeError("erro que ninguém previu")

    monkeypatch.setattr("app.worker.run_cycle", broken_cycle)
    monkeypatch.setattr("app.worker.SessionLocal", TestingSessionLocal)

    assert run_once(FakeCoinGecko(), telegram) is False


def test_run_once_reports_success(monkeypatch, db_session, telegram):
    monkeypatch.setattr("app.worker.SessionLocal", TestingSessionLocal)

    assert run_once(FakeCoinGecko(), telegram) is True


class FakeCoinGeckoContext(FakeCoinGecko):
    """Como o cliente real, pode ser usado com `with`."""

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return None


@pytest.fixture
def fake_clients(monkeypatch, telegram):
    monkeypatch.setattr("app.worker.create_telegram_client", lambda: telegram)
    monkeypatch.setattr(
        "app.worker.create_coingecko_client", lambda: FakeCoinGeckoContext()
    )


@pytest.mark.parametrize(("cycle_ok", "exit_code"), [(True, 0), (False, 1)])
def test_once_runs_a_single_cycle_and_exits(
    monkeypatch, fake_clients, cycle_ok, exit_code
):
    calls = []

    def fake_run_once(coingecko, telegram):
        calls.append(coingecko)
        return cycle_ok

    monkeypatch.setattr("app.worker.run_once", fake_run_once)

    assert main(["--once"]) == exit_code
    assert len(calls) == 1


def test_logging_does_not_record_request_urls():
    """A URL do Telegram contém o token do bot e não pode ir para o log."""
    configure_logging()

    assert not logging.getLogger("httpx").isEnabledFor(logging.INFO)


def test_coingecko_failure_is_logged_with_reason(db_session, bitcoin, telegram, caplog):
    coingecko = FakeCoinGecko(error=CoinGeckoError("CoinGecko returned status 401"))

    with caplog.at_level(logging.WARNING, logger="app.worker"):
        run_cycle(db_session, coingecko, telegram)

    assert "status 401" in caplog.text
