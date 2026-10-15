from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_coingecko_client, require_api_key
from app.clients.coingecko import CoinGeckoClient
from app.db.session import get_db
from app.repositories.coin import CoinRepository
from app.repositories.price_snapshot import PriceSnapshotRepository
from app.schemas.coin import CoinCreate, CoinRead
from app.schemas.price import PriceRead
from app.services.coin import CoinService

router = APIRouter(
    prefix="/coins", tags=["coins"], dependencies=[Depends(require_api_key)]
)

DbDep = Annotated[Session, Depends(get_db)]
CoinGeckoDep = Annotated[CoinGeckoClient, Depends(get_coingecko_client)]


def get_coin_service(db: DbDep, coingecko: CoinGeckoDep) -> CoinService:
    return CoinService(CoinRepository(db), PriceSnapshotRepository(db), coingecko)


ServiceDep = Annotated[CoinService, Depends(get_coin_service)]


@router.get("", response_model=list[CoinRead])
def list_coins(service: ServiceDep):
    """Lista as moedas acompanhadas, em ordem alfabética."""
    return service.list_coins()


@router.post("", response_model=CoinRead, status_code=status.HTTP_201_CREATED)
def create_coin(data: CoinCreate, service: ServiceDep, db: DbDep):
    """Cadastra uma moeda. O símbolo e o nome vêm da CoinGecko."""
    coin = service.create_coin(data)
    db.commit()
    return coin


@router.get("/{coin_id}/prices", response_model=list[PriceRead])
def list_prices(
    coin_id: int,
    service: ServiceDep,
    start: Annotated[
        datetime | None,
        Query(description="Início do período (inclusivo). Sem fuso, vale UTC."),
    ] = None,
    end: Annotated[
        datetime | None,
        Query(description="Fim do período (exclusivo). Sem fuso, vale UTC."),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
):
    """Histórico de preços de uma moeda, do mais recente para o mais antigo."""
    return service.list_prices(coin_id, start, end, limit)
