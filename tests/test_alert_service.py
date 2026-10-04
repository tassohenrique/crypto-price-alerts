from decimal import Decimal

import pytest

from app.models import Alert, AlertDirection
from app.repositories.alert import AlertRepository
from app.services.alert import AlertService

ABOVE = AlertDirection.ABOVE
BELOW = AlertDirection.BELOW


@pytest.fixture
def service(db_session):
    return AlertService(AlertRepository(db_session))


def test_above_alert_triggers_when_price_reaches_target(service, bitcoin, make_alert):
    alert = make_alert(bitcoin, ABOVE, "500000")

    triggered = service.check_alerts({"bitcoin": Decimal(500000)})

    assert [item.alert.id for item in triggered] == [alert.id]
    assert triggered[0].price == Decimal(500000)
    assert alert.is_active is False
    assert alert.triggered_at is not None


def test_below_alert_triggers_when_price_falls_to_target(service, bitcoin, make_alert):
    alert = make_alert(bitcoin, BELOW, "400000")

    triggered = service.check_alerts({"bitcoin": Decimal("399999.99")})

    assert [item.alert.id for item in triggered] == [alert.id]


def test_alert_not_reached_stays_active(service, bitcoin, make_alert):
    alert = make_alert(bitcoin, ABOVE, "500000")

    triggered = service.check_alerts({"bitcoin": Decimal("499999.99")})

    assert triggered == []
    assert alert.is_active is True
    assert alert.triggered_at is None


def test_triggered_alert_does_not_trigger_again(service, bitcoin, make_alert):
    make_alert(bitcoin, ABOVE, "100")

    first = service.check_alerts({"bitcoin": Decimal(200)})
    second = service.check_alerts({"bitcoin": Decimal(300)})

    assert len(first) == 1
    assert second == []


def test_inactive_alert_is_ignored(service, bitcoin, make_alert):
    make_alert(bitcoin, ABOVE, "100", is_active=False)

    assert service.check_alerts({"bitcoin": Decimal(200)}) == []


def test_alert_of_coin_missing_from_prices_is_not_checked(
    service, bitcoin, ethereum, make_alert
):
    alert = make_alert(ethereum, BELOW, "1000000")

    triggered = service.check_alerts({"bitcoin": Decimal(450000)})

    assert triggered == []
    assert alert.is_active is True


def test_only_matching_alerts_trigger_among_many(
    service, bitcoin, ethereum, make_alert
):
    btc_above = make_alert(bitcoin, ABOVE, "400000")
    make_alert(bitcoin, BELOW, "300000")
    eth_below = make_alert(ethereum, BELOW, "20000")
    make_alert(ethereum, ABOVE, "25000")
    prices = {"bitcoin": Decimal(450000), "ethereum": Decimal(18000)}

    triggered = service.check_alerts(prices)

    assert {item.alert.id for item in triggered} == {btc_above.id, eth_below.id}
    for item in triggered:
        assert item.price == prices[item.alert.coin.coingecko_id]


def test_empty_prices_triggers_nothing(service, bitcoin, make_alert):
    make_alert(bitcoin, ABOVE, "100")

    assert service.check_alerts({}) == []


def test_triggered_state_is_saved_after_commit(
    service, db_session, bitcoin, make_alert
):
    alert = make_alert(bitcoin, ABOVE, "100")
    service.check_alerts({"bitcoin": Decimal(200)})

    db_session.commit()
    db_session.expire_all()

    reloaded = db_session.get(Alert, alert.id)
    assert reloaded.is_active is False
    assert reloaded.triggered_at is not None
