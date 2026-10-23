from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models import PriceSnapshot
from app.services.worker_health import check_worker_health

NOW = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)


# Regra pura: sem banco e sem relógio.


@pytest.mark.parametrize(
    ("minutes_ago", "expected"),
    [(0, "ok"), (29, "ok"), (30, "ok"), (31, "stale"), (600, "stale")],
)
def test_status_depends_on_the_age_of_the_last_price(minutes_ago, expected):
    health = check_worker_health(
        has_coins=True,
        last_price_at=NOW - timedelta(minutes=minutes_ago),
        now=NOW,
        stale_after_minutes=30,
    )

    assert health.status == expected
    assert health.is_healthy is (expected == "ok")


def test_coins_without_any_price_is_stale():
    health = check_worker_health(
        has_coins=True, last_price_at=None, now=NOW, stale_after_minutes=30
    )

    assert health.status == "stale"


def test_no_coins_is_idle_and_healthy():
    health = check_worker_health(
        has_coins=False, last_price_at=None, now=NOW, stale_after_minutes=30
    )

    assert health.status == "idle"
    assert health.is_healthy is True


# Rota


def add_snapshot(db_session, coin, minutes_ago):
    db_session.add(
        PriceSnapshot(
            coin_id=coin.id,
            price=Decimal(450000),
            fetched_at=datetime.now(UTC) - timedelta(minutes=minutes_ago),
        )
    )
    db_session.flush()


def test_route_is_public_and_ok_with_a_recent_price(client, db_session, bitcoin):
    add_snapshot(db_session, bitcoin, minutes_ago=5)

    response = client.get("/health/worker")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["stale_after_minutes"] == settings.worker_stale_after_minutes


def test_route_returns_503_when_the_last_price_is_old(client, db_session, bitcoin):
    add_snapshot(db_session, bitcoin, minutes_ago=90)

    response = client.get("/health/worker")

    assert response.status_code == 503
    assert response.json()["status"] == "stale"


def test_route_uses_the_most_recent_price(client, db_session, bitcoin, ethereum):
    add_snapshot(db_session, bitcoin, minutes_ago=90)
    add_snapshot(db_session, ethereum, minutes_ago=5)

    assert client.get("/health/worker").status_code == 200


def test_route_is_idle_without_coins(client):
    response = client.get("/health/worker")

    assert response.status_code == 200
    assert response.json() == {
        "status": "idle",
        "last_price_at": None,
        "stale_after_minutes": settings.worker_stale_after_minutes,
    }


class BrokenSession:
    def scalars(self, *args, **kwargs):
        raise SQLAlchemyError("Database is down")

    def scalar(self, *args, **kwargs):
        raise SQLAlchemyError("Database is down")


def test_route_returns_503_when_database_is_down(client):
    app.dependency_overrides[get_db] = lambda: BrokenSession()

    response = client.get("/health/worker")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}
