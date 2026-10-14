from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_coingecko_client, require_api_key
from app.clients.coingecko import CoinGeckoClient
from app.db.session import get_db
from app.repositories.coin import CoinRepository
from app.schemas.coin import CoinCreate, CoinRead
from app.services.coin import CoinService

router = APIRouter(
    prefix="/coins", tags=["coins"], dependencies=[Depends(require_api_key)]
)

DbDep = Annotated[Session, Depends(get_db)]
CoinGeckoDep = Annotated[CoinGeckoClient, Depends(get_coingecko_client)]


def get_coin_service(db: DbDep, coingecko: CoinGeckoDep) -> CoinService:
    return CoinService(CoinRepository(db), coingecko)


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
