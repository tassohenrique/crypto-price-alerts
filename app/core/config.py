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
    api_key: str


settings = Settings()
