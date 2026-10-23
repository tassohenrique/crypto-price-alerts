from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

WorkerStatus = Literal["ok", "stale", "idle"]


@dataclass(frozen=True)
class WorkerHealth:
    status: WorkerStatus
    last_price_at: datetime | None
    stale_after_minutes: int

    @property
    def is_healthy(self) -> bool:
        return self.status != "stale"


def check_worker_health(
    *,
    has_coins: bool,
    last_price_at: datetime | None,
    now: datetime,
    stale_after_minutes: int,
) -> WorkerHealth:
    """Decide se o worker está em dia pela data do preço mais recente.

    Um preço novo só aparece no banco se tudo funcionou de ponta a ponta: o
    agendador chamou, a CoinGecko respondeu e o banco gravou. Por isso ele é o
    sinal: se qualquer peça parar, o preço mais recente envelhece.
    """
    if not has_coins:
        # Nenhuma moeda cadastrada: o worker não tem o que buscar, e tudo bem.
        status = "idle"
    elif last_price_at is None:
        status = "stale"
    elif now - last_price_at > timedelta(minutes=stale_after_minutes):
        status = "stale"
    else:
        status = "ok"
    return WorkerHealth(status, last_price_at, stale_after_minutes)
