from decimal import Decimal
from typing import Self

import httpx

from app.core.config import settings


class CoinGeckoError(Exception):
    """Falha ao consultar a CoinGecko."""


class CoinGeckoRateLimitError(CoinGeckoError):
    """A CoinGecko recusou a requisição por excesso de chamadas (HTTP 429)."""


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

    def get_prices(
        self, coin_ids: list[str], currency: str = "brl"
    ) -> dict[str, Decimal]:
        """Busca o preço atual de várias moedas numa única chamada.

        Moedas que a CoinGecko não reconhece ficam de fora do resultado.
        """
        if not coin_ids:
            return {}

        params = {
            "ids": ",".join(coin_ids),
            "vs_currencies": currency,
            "precision": "full",
        }

        try:
            response = self.http.get("/simple/price", params=params)
        except httpx.TimeoutException as exc:
            raise CoinGeckoError("CoinGecko did not respond in time") from exc
        except httpx.HTTPError as exc:
            raise CoinGeckoError(f"Could not reach CoinGecko: {exc}") from exc

        if response.status_code == 429:
            raise CoinGeckoRateLimitError("CoinGecko rate limit exceeded")
        if response.is_error:
            raise CoinGeckoError(f"CoinGecko returned status {response.status_code}")

        data = response.json(parse_float=Decimal)

        prices: dict[str, Decimal] = {}
        for coin_id in coin_ids:
            value = data.get(coin_id, {}).get(currency)
            if value is not None:
                prices[coin_id] = Decimal(value)
        return prices

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
