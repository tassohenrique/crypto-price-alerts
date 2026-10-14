from collections.abc import Sequence

from app.clients.coingecko import (
    CoinGeckoClient,
    CoinGeckoError,
    CoinGeckoNotFoundError,
)
from app.core.exceptions import BadGatewayError, ConflictError, UnprocessableError
from app.models import Coin
from app.repositories.coin import CoinRepository
from app.schemas.coin import CoinCreate


class CoinService:
    def __init__(self, coins: CoinRepository, coingecko: CoinGeckoClient) -> None:
        self.coins = coins
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
