from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.main import app


def test_health_check_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


class BrokenSession:
    """Sessão falsa que simula o banco fora do ar."""

    def execute(self, *args, **kwargs):
        raise SQLAlchemyError("Database is down")


def test_health_check_returns_503_when_database_is_down(client):
    app.dependency_overrides[get_db] = lambda: BrokenSession()

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}


def test_root_redirects_to_docs(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/docs"
