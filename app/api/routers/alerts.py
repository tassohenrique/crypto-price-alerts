from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_api_key
from app.db.session import get_db
from app.repositories.alert import AlertRepository
from app.repositories.coin import CoinRepository
from app.schemas.alert import AlertCreate, AlertRead
from app.services.alert import AlertService

router = APIRouter(
    prefix="/alerts", tags=["alerts"], dependencies=[Depends(require_api_key)]
)

DbDep = Annotated[Session, Depends(get_db)]


def get_alert_service(db: DbDep) -> AlertService:
    return AlertService(AlertRepository(db), CoinRepository(db))


ServiceDep = Annotated[AlertService, Depends(get_alert_service)]


@router.get("", response_model=list[AlertRead])
def list_alerts(
    service: ServiceDep,
    active: Annotated[
        bool | None, Query(description="true para ativos, false para disparados")
    ] = None,
):
    """Lista os alertas, do mais recente para o mais antigo."""
    return service.list_alerts(active)


@router.get("/{alert_id}", response_model=AlertRead)
def get_alert(alert_id: int, service: ServiceDep):
    """Busca um alerta pelo ID."""
    return service.get_alert(alert_id)


@router.post("", response_model=AlertRead, status_code=status.HTTP_201_CREATED)
def create_alert(data: AlertCreate, service: ServiceDep, db: DbDep):
    """Cria um alerta. Envie o target_price como texto para não perder precisão."""
    alert = service.create_alert(data)
    db.commit()
    return alert


@router.post("/{alert_id}/rearm", response_model=AlertRead)
def rearm_alert(alert_id: int, service: ServiceDep, db: DbDep):
    """Reativa um alerta que já disparou e já teve o aviso enviado."""
    alert = service.rearm_alert(alert_id)
    db.commit()
    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(alert_id: int, service: ServiceDep, db: DbDep) -> None:
    """Apaga um alerta."""
    service.delete_alert(alert_id)
    db.commit()
