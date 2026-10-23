from dataclasses import asdict
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.repositories.coin import CoinRepository
from app.repositories.price_snapshot import PriceSnapshotRepository
from app.services.worker_health import check_worker_health

router = APIRouter(tags=["health"])

DbDep = Annotated[Session, Depends(get_db)]


def database_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database unavailable",
    )


@router.get("/health")
def health_check(db: DbDep) -> dict[str, str]:
    """Verifica se a API e o banco de dados estão no ar."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise database_unavailable() from None

    return {"status": "ok", "database": "ok"}


@router.get(
    "/health/worker",
    responses={503: {"description": "Nenhum preço novo dentro do prazo"}},
)
def worker_health(db: DbDep) -> JSONResponse:
    """Verifica se o worker está gravando preços em dia.

    Responde 503 se o preço mais recente for mais antigo que
    WORKER_STALE_AFTER_MINUTES. Feito para monitores de disponibilidade.
    """
    try:
        health = check_worker_health(
            has_coins=bool(CoinRepository(db).list_all()),
            last_price_at=PriceSnapshotRepository(db).latest_fetched_at(),
            now=datetime.now(UTC),
            stale_after_minutes=settings.worker_stale_after_minutes,
        )
    except SQLAlchemyError:
        raise database_unavailable() from None

    status_code = (
        status.HTTP_200_OK if health.is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    content = jsonable_encoder(asdict(health))
    return JSONResponse(status_code=status_code, content=content)
