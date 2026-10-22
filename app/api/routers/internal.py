from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import (
    get_coingecko_client,
    get_telegram_client,
    require_cron_secret,
)
from app.clients.coingecko import CoinGeckoClient
from app.clients.telegram import TelegramClient
from app.core.exceptions import ConflictError
from app.db.session import get_db
from app.worker import run_locked_cycle

# Fora da documentação: é uma rota de máquina, chamada só pelo agendador externo.
router = APIRouter(
    prefix="/internal",
    tags=["internal"],
    include_in_schema=False,
    dependencies=[Depends(require_cron_secret)],
)


@router.post("/run-cycle")
def run_cycle(
    db: Annotated[Session, Depends(get_db)],
    coingecko: Annotated[CoinGeckoClient, Depends(get_coingecko_client)],
    telegram: Annotated[TelegramClient, Depends(get_telegram_client)],
) -> dict[str, int | str]:
    """Roda um ciclo do worker: preços, histórico, alertas e avisos pendentes."""
    result = run_locked_cycle(db, coingecko, telegram)
    if result is None:
        raise ConflictError("Outro ciclo já está em andamento.")
    return {"status": "ok", **asdict(result)}
