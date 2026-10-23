import secrets
from collections.abc import Iterator
from typing import Annotated

from fastapi import Security
from fastapi.security import APIKeyHeader

from app.clients.coingecko import CoinGeckoClient, create_coingecko_client
from app.clients.telegram import TelegramClient, create_telegram_client
from app.core.config import settings
from app.core.exceptions import NotFoundError, UnauthorizedError

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
cron_secret_header = APIKeyHeader(name="X-Cron-Secret", auto_error=False)


def require_api_key(api_key: Annotated[str | None, Security(api_key_header)]) -> None:
    """Exige o cabeçalho X-API-Key com a chave configurada no .env."""
    if api_key is None or not secrets.compare_digest(
        api_key.encode(), settings.api_key.encode()
    ):
        raise UnauthorizedError("Chave de API inválida ou ausente.")


def require_cron_secret(
    secret: Annotated[str | None, Security(cron_secret_header)],
) -> None:
    """Exige o cabeçalho X-Cron-Secret. Sem CRON_SECRET configurado, a rota some."""
    if settings.cron_secret is None:
        raise NotFoundError("Not Found")
    if secret is None or not secrets.compare_digest(
        secret.encode(), settings.cron_secret.encode()
    ):
        raise UnauthorizedError("Segredo do agendador inválido ou ausente.")


def get_telegram_client() -> Iterator[TelegramClient]:
    with create_telegram_client() as client:
        yield client


def get_coingecko_client() -> Iterator[CoinGeckoClient]:
    """Entrega um cliente da CoinGecko e fecha as conexões ao fim da requisição."""
    with create_coingecko_client() as client:
        yield client
