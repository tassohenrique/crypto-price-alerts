from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Classe base de todos os models. O Alembic lê as tabelas a partir dela."""
