from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Alert, Coin
from app.repositories.alert import AlertRepository
from app.repositories.coin import CoinRepository

engine = create_engine(settings.test_database_url)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    yield session
    session.close()
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def bitcoin(db_session):
    return CoinRepository(db_session).add(
        Coin(coingecko_id="bitcoin", symbol="BTC", name="Bitcoin")
    )


@pytest.fixture
def ethereum(db_session):
    return CoinRepository(db_session).add(
        Coin(coingecko_id="ethereum", symbol="ETH", name="Ethereum")
    )


@pytest.fixture
def make_alert(db_session):
    """Fábrica de alertas: cada teste cria exatamente os alertas de que precisa."""
    repository = AlertRepository(db_session)

    def _make(coin, direction, target_price, *, is_active=True):
        return repository.add(
            Alert(
                coin_id=coin.id,
                direction=direction,
                target_price=Decimal(target_price),
                is_active=is_active,
            )
        )

    return _make
