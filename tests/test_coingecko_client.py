from decimal import Decimal

import httpx
import pytest

from app.clients.coingecko import (
    CoinGeckoClient,
    CoinGeckoError,
    CoinGeckoRateLimitError,
)

BASE_URL = "https://api.test/api/v3"


def make_client(handler):
    """Cria um cliente que, em vez da internet, usa a função `handler` como servidor."""
    return CoinGeckoClient(
        api_key="chave-de-teste",
        base_url=BASE_URL,
        transport=httpx.MockTransport(handler),
    )


def test_get_prices_returns_exact_decimal_prices():
    def handler(request):
        assert request.url.path == "/api/v3/simple/price"
        assert request.url.params["ids"] == "bitcoin,ethereum"
        assert request.url.params["vs_currencies"] == "brl"
        assert request.headers["x-cg-demo-api-key"] == "chave-de-teste"
        return httpx.Response(
            200,
            text='{"bitcoin": {"brl": 350000.12}, "ethereum": {"brl": 18000.5}}',
        )

    prices = make_client(handler).get_prices(["bitcoin", "ethereum"])

    assert prices == {"bitcoin": Decimal("350000.12"), "ethereum": Decimal("18000.5")}


def test_get_prices_keeps_full_precision():
    def handler(request):
        return httpx.Response(200, text='{"bitcoin": {"brl": 0.1000000000000000055}}')

    prices = make_client(handler).get_prices(["bitcoin"])

    assert prices["bitcoin"] == Decimal("0.1000000000000000055")


def test_get_prices_ignores_unknown_coins():
    def handler(request):
        return httpx.Response(200, text='{"bitcoin": {"brl": 350000}}')

    prices = make_client(handler).get_prices(["bitcoin", "moeda-que-nao-existe"])

    assert prices == {"bitcoin": Decimal(350000)}


def test_get_prices_with_empty_list_does_not_call_the_api():
    def handler(request):
        raise AssertionError("A API não deveria ter sido chamada")

    assert make_client(handler).get_prices([]) == {}


def test_rate_limit_raises_specific_error():
    def handler(request):
        return httpx.Response(429)

    with pytest.raises(CoinGeckoRateLimitError):
        make_client(handler).get_prices(["bitcoin"])


def test_server_error_raises_coingecko_error():
    def handler(request):
        return httpx.Response(500)

    with pytest.raises(CoinGeckoError):
        make_client(handler).get_prices(["bitcoin"])


def test_timeout_raises_coingecko_error():
    def handler(request):
        raise httpx.ReadTimeout("timeout", request=request)

    with pytest.raises(CoinGeckoError):
        make_client(handler).get_prices(["bitcoin"])
