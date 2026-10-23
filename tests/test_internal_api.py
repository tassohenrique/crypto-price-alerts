from decimal import Decimal

import pytest
from sqlalchemy import text

from app.api.deps import get_coingecko_client, get_telegram_client
from app.core.config import settings
from app.main import app
from app.worker import CYCLE_LOCK_ID, cycle_lock, run_locked_cycle
from tests.conftest import engine
from tests.fakes import FakeCoinGecko, FakeTelegram

URL = "/internal/run-cycle"
SECRET = "segredo-do-agendador"


@pytest.fixture
def cron_secret(monkeypatch):
    monkeypatch.setattr(settings, "cron_secret", SECRET)


@pytest.fixture
def fake_clients():
    coingecko = FakeCoinGecko({"bitcoin": Decimal(450000)})
    app.dependency_overrides[get_coingecko_client] = lambda: coingecko
    app.dependency_overrides[get_telegram_client] = lambda: FakeTelegram()
    yield coingecko
    app.dependency_overrides.pop(get_coingecko_client, None)
    app.dependency_overrides.pop(get_telegram_client, None)


@pytest.fixture
def lock_held_elsewhere():
    """Simula outro processo rodando um ciclo neste momento."""
    with engine.connect() as connection:
        connection.execute(text("SELECT pg_advisory_lock(:id)"), {"id": CYCLE_LOCK_ID})
        connection.commit()
        yield
        connection.execute(
            text("SELECT pg_advisory_unlock(:id)"), {"id": CYCLE_LOCK_ID}
        )


def test_route_is_off_without_cron_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "cron_secret", None)

    response = client.post(URL, headers={"X-Cron-Secret": "qualquer"})

    assert response.status_code == 404


@pytest.mark.usefixtures("cron_secret")
@pytest.mark.parametrize("headers", [{}, {"X-Cron-Secret": "errado"}])
def test_route_requires_the_cron_secret(client, headers):
    assert client.post(URL, headers=headers).status_code == 401


@pytest.mark.usefixtures("cron_secret")
def test_api_key_does_not_open_the_route(client, monkeypatch):
    """A chave da API e o segredo do agendador são credenciais separadas."""
    monkeypatch.setattr(settings, "api_key", "chave-da-api")

    response = client.post(URL, headers={"X-API-Key": "chave-da-api"})

    assert response.status_code == 401


@pytest.mark.usefixtures("cron_secret")
def test_route_runs_a_cycle(client, bitcoin, fake_clients):
    response = client.post(URL, headers={"X-Cron-Secret": SECRET})

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["prices_saved"] == 1
    assert fake_clients.calls == [["bitcoin"]]


@pytest.mark.usefixtures("cron_secret")
def test_route_can_run_twice_in_a_row(client, bitcoin, fake_clients):
    """A trava é liberada no fim do ciclo."""
    for _ in range(2):
        response = client.post(URL, headers={"X-Cron-Secret": SECRET})
        assert response.status_code == 200


@pytest.mark.usefixtures("cron_secret", "lock_held_elsewhere")
def test_route_refuses_while_another_cycle_runs(client, bitcoin, fake_clients):
    response = client.post(URL, headers={"X-Cron-Secret": SECRET})

    assert response.status_code == 409
    assert fake_clients.calls == []


def test_lock_is_released_after_an_error(db_session, monkeypatch):
    def broken_cycle(*args):
        raise RuntimeError("erro que ninguém previu")

    monkeypatch.setattr("app.worker.run_cycle", broken_cycle)

    with pytest.raises(RuntimeError):
        run_locked_cycle(db_session, FakeCoinGecko(), FakeTelegram())

    with cycle_lock(engine) as acquired:
        assert acquired is True


def test_lock_allows_only_one_holder():
    with cycle_lock(engine) as first, cycle_lock(engine) as second:
        assert first is True
        assert second is False
