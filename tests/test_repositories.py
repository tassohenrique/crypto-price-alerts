from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models import AlertDirection, PriceSnapshot
from app.repositories.alert import AlertRepository
from app.repositories.coin import CoinRepository
from app.repositories.price_snapshot import PriceSnapshotRepository

BASE_TIME = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def hours(n):
    return BASE_TIME + timedelta(hours=n)


def test_get_coin_by_coingecko_id(db_session, bitcoin):
    repository = CoinRepository(db_session)

    assert repository.get_by_coingecko_id("bitcoin").id == bitcoin.id
    assert repository.get_by_coingecko_id("dogecoin") is None


def test_list_snapshots_filters_by_coin_and_period(db_session, bitcoin, ethereum):
    repository = PriceSnapshotRepository(db_session)
    repository.add_many(
        [
            PriceSnapshot(coin_id=bitcoin.id, price=Decimal(100), fetched_at=hours(n))
            for n in range(4)
        ]
        + [PriceSnapshot(coin_id=ethereum.id, price=Decimal(10), fetched_at=hours(2))]
    )

    result = repository.list_for_coin(bitcoin.id, start=hours(1), end=hours(3))

    assert [snapshot.fetched_at for snapshot in result] == [hours(2), hours(1)]


def test_list_snapshots_respects_limit(db_session, bitcoin):
    repository = PriceSnapshotRepository(db_session)
    repository.add_many(
        [
            PriceSnapshot(coin_id=bitcoin.id, price=Decimal(100), fetched_at=hours(n))
            for n in range(5)
        ]
    )

    result = repository.list_for_coin(bitcoin.id, limit=2)

    assert [snapshot.fetched_at for snapshot in result] == [hours(4), hours(3)]


def test_list_active_alerts_only_returns_active_alerts_of_requested_coins(
    db_session, bitcoin, ethereum, make_alert
):
    active = make_alert(bitcoin, AlertDirection.ABOVE, "500000")
    make_alert(bitcoin, AlertDirection.BELOW, "300000", is_active=False)
    make_alert(ethereum, AlertDirection.ABOVE, "30000")

    result = AlertRepository(db_session).list_active_for_coingecko_ids(["bitcoin"])

    assert [alert.id for alert in result] == [active.id]
    assert result[0].coin.symbol == "BTC"


def test_list_active_alerts_with_no_ids_returns_empty(db_session, bitcoin, make_alert):
    make_alert(bitcoin, AlertDirection.ABOVE, "500000")

    assert AlertRepository(db_session).list_active_for_coingecko_ids([]) == []
