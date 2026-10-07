from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.core.config import settings
from app.models import AlertDirection

ABOVE = AlertDirection.ABOVE
BELOW = AlertDirection.BELOW


@pytest.fixture
def client(client):
    """Neste arquivo, todas as requisições levam a chave de API."""
    client.headers.update({"X-API-Key": settings.api_key})
    return client


def ids(response):
    return [alert["id"] for alert in response.json()]


def mark_triggered(db_session, alert, *, notified):
    now = datetime.now(UTC)
    alert.is_active = False
    alert.triggered_at = now
    alert.triggered_price = Decimal(550000)
    alert.notified_at = now if notified else None
    db_session.flush()


# --- Criação ---


def test_create_alert(client, bitcoin):
    response = client.post(
        "/alerts",
        json={"coin_id": bitcoin.id, "direction": "below", "target_price": "400000.50"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["coin"]["symbol"] == "BTC"
    assert data["direction"] == "below"
    assert Decimal(data["target_price"]) == Decimal("400000.50")
    assert data["is_active"] is True
    assert data["triggered_at"] is None


def test_create_alert_for_unknown_coin_returns_404(client):
    response = client.post(
        "/alerts", json={"coin_id": 999999, "direction": "above", "target_price": "1"}
    )

    assert response.status_code == 404


@pytest.mark.parametrize("target_price", ["0", "-1", "0.0000000000001"])
def test_create_alert_with_invalid_target_price_returns_422(
    client, bitcoin, target_price
):
    response = client.post(
        "/alerts",
        json={
            "coin_id": bitcoin.id,
            "direction": "above",
            "target_price": target_price,
        },
    )

    assert response.status_code == 422


def test_create_alert_with_invalid_direction_returns_422(client, bitcoin):
    response = client.post(
        "/alerts",
        json={"coin_id": bitcoin.id, "direction": "sideways", "target_price": "1"},
    )

    assert response.status_code == 422


# --- Leitura ---


def test_alerts_are_listed_newest_first(client, bitcoin, make_alert):
    first = make_alert(bitcoin, ABOVE, "500000")
    second = make_alert(bitcoin, BELOW, "300000")

    assert ids(client.get("/alerts")) == [second.id, first.id]


def test_filter_alerts_by_active(client, bitcoin, make_alert):
    active = make_alert(bitcoin, ABOVE, "500000")
    inactive = make_alert(bitcoin, BELOW, "300000", is_active=False)

    assert ids(client.get("/alerts", params={"active": "true"})) == [active.id]
    assert ids(client.get("/alerts", params={"active": "false"})) == [inactive.id]


def test_get_missing_alert_returns_404(client):
    assert client.get("/alerts/999999").status_code == 404


# --- Rearmar ---


def test_rearm_notified_alert(client, db_session, bitcoin, make_alert):
    alert = make_alert(bitcoin, ABOVE, "500000")
    mark_triggered(db_session, alert, notified=True)

    response = client.post(f"/alerts/{alert.id}/rearm")

    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is True
    assert data["triggered_at"] is None
    assert data["triggered_price"] is None
    assert data["notified_at"] is None


def test_rearm_active_alert_returns_409(client, bitcoin, make_alert):
    alert = make_alert(bitcoin, ABOVE, "500000")

    assert client.post(f"/alerts/{alert.id}/rearm").status_code == 409


def test_rearm_alert_with_pending_notification_returns_409(
    client, db_session, bitcoin, make_alert
):
    alert = make_alert(bitcoin, ABOVE, "500000")
    mark_triggered(db_session, alert, notified=False)

    assert client.post(f"/alerts/{alert.id}/rearm").status_code == 409


# --- Exclusão ---


def test_delete_alert(client, bitcoin, make_alert):
    alert = make_alert(bitcoin, ABOVE, "500000")

    response = client.delete(f"/alerts/{alert.id}")

    assert response.status_code == 204
    assert client.get(f"/alerts/{alert.id}").status_code == 404
