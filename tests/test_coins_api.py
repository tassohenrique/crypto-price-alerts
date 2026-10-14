import pytest

from app.api.deps import get_coingecko_client
from app.clients.coingecko import CoinGeckoError, CoinGeckoNotFoundError, CoinInfo
from app.core.config import settings
from app.main import app


class FakeCoinGecko:
    def __init__(self, coins):
        self.coins = coins
        self.error = None
        self.calls = []

    def get_coin(self, coingecko_id):
        self.calls.append(coingecko_id)
        if self.error is not None:
            raise self.error
        if coingecko_id not in self.coins:
            raise CoinGeckoNotFoundError("not found")
        return self.coins[coingecko_id]


@pytest.fixture
def client(client):
    """Neste arquivo, todas as requisições levam a chave de API."""
    client.headers.update({"X-API-Key": settings.api_key})
    return client


@pytest.fixture
def coingecko():
    fake = FakeCoinGecko({"solana": CoinInfo("solana", "SOL", "Solana")})
    app.dependency_overrides[get_coingecko_client] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_coingecko_client, None)


def test_create_coin_fetches_symbol_and_name(client, coingecko):
    response = client.post("/coins", json={"coingecko_id": "solana"})

    assert response.status_code == 201
    data = response.json()
    assert data["coingecko_id"] == "solana"
    assert data["symbol"] == "SOL"
    assert data["name"] == "Solana"
    assert coingecko.calls == ["solana"]


def test_create_existing_coin_returns_409_without_calling_coingecko(
    client, coingecko, bitcoin
):
    response = client.post("/coins", json={"coingecko_id": "bitcoin"})

    assert response.status_code == 409
    assert coingecko.calls == []


def test_create_unknown_coin_returns_422(client, coingecko):
    response = client.post("/coins", json={"coingecko_id": "moeda-que-nao-existe"})

    assert response.status_code == 422


def test_create_coin_when_coingecko_fails_returns_502(client, coingecko):
    coingecko.error = CoinGeckoError("falha simulada")

    response = client.post("/coins", json={"coingecko_id": "solana"})

    assert response.status_code == 502


@pytest.mark.parametrize("coingecko_id", ["../simple/price", "Bitcoin", "", "bit coin"])
def test_create_coin_with_invalid_id_returns_422(client, coingecko, coingecko_id):
    response = client.post("/coins", json={"coingecko_id": coingecko_id})

    assert response.status_code == 422
    assert coingecko.calls == []


def test_list_coins_in_alphabetical_order(client, ethereum, bitcoin):
    response = client.get("/coins")

    assert response.status_code == 200
    assert [coin["name"] for coin in response.json()] == ["Bitcoin", "Ethereum"]
