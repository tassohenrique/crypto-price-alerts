from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.core.config import settings
from app.models import PriceSnapshot
from app.repositories.price_snapshot import PriceSnapshotRepository

BASE_TIME = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def hours(n):
    return BASE_TIME + timedelta(hours=n)


def fetched_times(response):
    return [datetime.fromisoformat(item["fetched_at"]) for item in response.json()]


@pytest.fixture
def client(client):
    """Neste arquivo, todas as requisições levam a chave de API."""
    client.headers.update({"X-API-Key": settings.api_key})
    return client


@pytest.fixture
def bitcoin_prices(db_session, bitcoin, ethereum):
    """Cinco preços do Bitcoin, de hora em hora, e um do Ethereum no meio."""
    PriceSnapshotRepository(db_session).add_many(
        [
            PriceSnapshot(
                coin_id=bitcoin.id,
                price=Decimal("400000.123456789012") + n,
                fetched_at=hours(n),
            )
            for n in range(5)
        ]
        + [
            PriceSnapshot(
                coin_id=ethereum.id, price=Decimal(15000), fetched_at=hours(2)
            )
        ]
    )
    return bitcoin


def test_list_prices_in_period_newest_first(client, bitcoin_prices):
    response = client.get(
        f"/coins/{bitcoin_prices.id}/prices",
        params={"start": hours(1).isoformat(), "end": hours(3).isoformat()},
    )

    assert response.status_code == 200
    assert fetched_times(response) == [hours(2), hours(1)]


def test_list_prices_respects_limit(client, bitcoin_prices):
    response = client.get(f"/coins/{bitcoin_prices.id}/prices", params={"limit": 2})

    assert fetched_times(response) == [hours(4), hours(3)]


def test_price_keeps_full_precision(client, bitcoin_prices):
    response = client.get(f"/coins/{bitcoin_prices.id}/prices", params={"limit": 1})

    data = response.json()[0]
    assert Decimal(data["price"]) == Decimal("400004.123456789012")
    assert data["currency"] == "brl"


def test_list_prices_of_unknown_coin_returns_404(client):
    assert client.get("/coins/999999/prices").status_code == 404


@pytest.mark.parametrize(("start", "end"), [(2, 2), (3, 1)])
def test_start_not_before_end_returns_422(client, bitcoin_prices, start, end):
    response = client.get(
        f"/coins/{bitcoin_prices.id}/prices",
        params={"start": hours(start).isoformat(), "end": hours(end).isoformat()},
    )

    assert response.status_code == 422


@pytest.mark.parametrize("limit", [0, 1001])
def test_limit_out_of_range_returns_422(client, bitcoin_prices, limit):
    response = client.get(f"/coins/{bitcoin_prices.id}/prices", params={"limit": limit})

    assert response.status_code == 422


def test_dates_without_timezone_are_treated_as_utc(client, bitcoin_prices):
    response = client.get(
        f"/coins/{bitcoin_prices.id}/prices",
        params={"start": "2026-10-01T13:00:00", "end": "2026-10-01T15:00:00"},
    )

    assert response.status_code == 200
    assert fetched_times(response) == [hours(2), hours(1)]
