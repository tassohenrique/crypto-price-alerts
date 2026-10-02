from typing import Self

import httpx

from app.core.config import settings


class TelegramError(Exception):
    """Falha ao enviar uma mensagem pelo Telegram."""


class TelegramClient:
    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.chat_id = chat_id
        self.http = httpx.Client(
            base_url=f"https://api.telegram.org/bot{bot_token}",
            timeout=timeout,
            transport=transport,
        )

    def send_message(self, text: str) -> None:
        """Envia uma mensagem de texto para o chat configurado.

        As mensagens de erro nunca incluem a URL, porque ela contém o token do bot.
        """
        try:
            response = self.http.post(
                "/sendMessage",
                json={"chat_id": self.chat_id, "text": text},
            )
        except httpx.TimeoutException:
            raise TelegramError("Telegram did not respond in time") from None
        except httpx.HTTPError:
            raise TelegramError("Could not reach Telegram") from None

        try:
            data = response.json()
        except ValueError:
            data = {}

        if response.is_error or not data.get("ok"):
            description = data.get("description", "unknown error")
            raise TelegramError(
                f"Telegram rejected the message (status {response.status_code}): {description}"
            )

    def close(self) -> None:
        self.http.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()


def create_telegram_client() -> TelegramClient:
    return TelegramClient(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
    )
