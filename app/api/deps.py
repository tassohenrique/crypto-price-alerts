import secrets
from typing import Annotated

from fastapi import Security
from fastapi.security import APIKeyHeader

from app.core.config import settings
from app.core.exceptions import UnauthorizedError

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: Annotated[str | None, Security(api_key_header)]) -> None:
    """Exige o cabeçalho X-API-Key com a chave configurada no .env."""
    if api_key is None or not secrets.compare_digest(
        api_key.encode(), settings.api_key.encode()
    ):
        raise UnauthorizedError("Chave de API inválida ou ausente.")
