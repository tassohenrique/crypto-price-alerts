from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Self
from urllib.parse import quote

import httpx

from app.core.config import settings


class CoinGeckoError(Exception):
    """Falha ao consultar a CoinGecko."""


class CoinGeckoRateLimitError(CoinGeckoError):
    """A CoinGecko recusou a requisição por excesso de chamadas (HTTP 429)."""


class CoinGeckoNotFoundError(CoinGeckoError):
    """A CoinGecko não reconhece o recurso pedido (HTTP 404)."""


@dataclass(frozen=True)
class CoinInfo:
    coingecko_id: str
    symbol: str
    name: str


class CoinGeckoClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.http = httpx.Client(
            base_url=base_url,
            headers={"x-cg-demo-api-key": api_key, "accept": "application/json"},
            timeout=timeout,
            transport=transport,
        )

    def _get(self, path: str, params: dict[str, str]) -> Any:
        """Faz um GET e converte qualquer falha num erro da CoinGecko."""
        try:
            response = self.http.get(path, params=params)
        except httpx.TimeoutException as exc:
            raise CoinGeckoError("CoinGecko did not respond in time") from exc
        except httpx.HTTPError as exc:
            raise CoinGeckoError(f"Could not reach CoinGecko: {exc}") from exc

        if response.status_code == 404:
            raise CoinGeckoNotFoundError(f"CoinGecko has no resource at {path}")
        if response.status_code == 429:
            raise CoinGeckoRateLimitError("CoinGecko rate limit exceeded")
        if response.is_error:
            raise CoinGeckoError(f"CoinGecko returned status {response.status_code}")

        return response.json(parse_float=Decimal)

    def get_prices(
        self, coin_ids: list[str], currency: str = "brl"
    ) -> dict[str, Decimal]:
        """Busca o preço atual de várias moedas numa única chamada.

        Moedas que a CoinGecko não reconhece ficam de fora do resultado.
        """
        if not coin_ids:
            return {}

        data = self._get(
            "/simple/price",
            {"ids": ",".join(coin_ids), "vs_currencies": currency, "precision": "full"},
        )

        prices: dict[str, Decimal] = {}
        for coin_id in coin_ids:
            value = data.get(coin_id, {}).get(currency)
            if value is not None:
                prices[coin_id] = Decimal(value)
        return prices

    def get_coin(self, coingecko_id: str) -> CoinInfo:
        """Busca o símbolo e o nome de uma moeda pelo id da CoinGecko."""
        data = self._get(
            f"/coins/{quote(coingecko_id, safe='')}",
            {
                "localization": "false",
                "tickers": "false",
                "market_data": "false",
                "community_data": "false",
                "developer_data": "false",
                "sparkline": "false",
            },
        )
        return CoinInfo(
            coingecko_id=data["id"], symbol=data["symbol"].upper(), name=data["name"]
        )

    def close(self) -> None:
        self.http.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()


def create_coingecko_client() -> CoinGeckoClient:
    return CoinGeckoClient(
        api_key=settings.coingecko_api_key,
        base_url=settings.coingecko_base_url,
    )
