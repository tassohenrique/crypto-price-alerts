from collections.abc import Sequence
from datetime import UTC, datetime

from app.clients.coingecko import (
    CoinGeckoClient,
    CoinGeckoError,
    CoinGeckoNotFoundError,
)
from app.core.exceptions import (
    BadGatewayError,
    ConflictError,
    NotFoundError,
    UnprocessableError,
)
from app.models import Coin, PriceSnapshot
from app.repositories.coin import CoinRepository
from app.repositories.price_snapshot import PriceSnapshotRepository
from app.schemas.coin import CoinCreate


def as_utc(value: datetime | None) -> datetime | None:
    """Datas sem fuso horário são tratadas como UTC."""
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


class CoinService:
    def __init__(
        self,
        coins: CoinRepository,
        snapshots: PriceSnapshotRepository,
        coingecko: CoinGeckoClient,
    ) -> None:
        self.coins = coins
        self.snapshots = snapshots
        self.coingecko = coingecko

    def list_coins(self) -> Sequence[Coin]:
        return self.coins.list_all()

    def create_coin(self, data: CoinCreate) -> Coin:
        """Cadastra uma moeda, buscando o símbolo e o nome na CoinGecko."""
        if self.coins.get_by_coingecko_id(data.coingecko_id) is not None:
            raise ConflictError("Esta moeda já está cadastrada.")

        try:
            info = self.coingecko.get_coin(data.coingecko_id)
        except CoinGeckoNotFoundError as exc:
            raise UnprocessableError("Moeda não encontrada na CoinGecko.") from exc
        except CoinGeckoError as exc:
            raise BadGatewayError(
                "Não foi possível consultar a CoinGecko. Tente novamente."
            ) from exc

        return self.coins.add(
            Coin(coingecko_id=info.coingecko_id, symbol=info.symbol, name=info.name)
        )

    def list_prices(
        self,
        coin_id: int,
        start: datetime | None,
        end: datetime | None,
        limit: int,
    ) -> Sequence[PriceSnapshot]:
        """Histórico de uma moeda, do mais recente para o mais antigo."""
        if self.coins.get(coin_id) is None:
            raise NotFoundError("Moeda não encontrada.")

        start, end = as_utc(start), as_utc(end)
        if start is not None and end is not None and start >= end:
            raise UnprocessableError("O início do período precisa ser anterior ao fim.")

        return self.snapshots.list_for_coin(coin_id, start=start, end=end, limit=limit)
