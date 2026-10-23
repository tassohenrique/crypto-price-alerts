from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    test_database_url: str | None = None

    coingecko_api_key: str
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"

    telegram_bot_token: str
    telegram_chat_id: str
    poll_interval_seconds: int = 300
    # Sem preço novo há mais que isso, GET /health/worker responde 503.
    # O dobro do ciclo de 15 min: tolera um ciclo perdido sem alarme falso.
    worker_stale_after_minutes: int = 30
    # "text" para ler no terminal; "json" em produção, para filtrar por campo.
    log_format: Literal["text", "json"] = "text"
    api_key: str
    # Segredo só do agendador externo (ex.: cron-job.org) para POST
    # /internal/run-cycle. Separado da API_KEY: se vazar, só dispara ciclos.
    # Sem valor, a rota fica desligada.
    cron_secret: str | None = None


settings = Settings()
