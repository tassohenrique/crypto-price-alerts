"""Clientes falsos da CoinGecko e do Telegram, compartilhados pelos testes."""

from app.clients.telegram import TelegramError


class FakeCoinGecko:
    def __init__(self, prices=None, error=None):
        self.prices = prices or {}
        self.error = error
        self.calls = []

    def get_prices(self, coingecko_ids):
        self.calls.append(list(coingecko_ids))
        if self.error is not None:
            raise self.error
        return {
            key: value for key, value in self.prices.items() if key in coingecko_ids
        }


class FakeTelegram:
    def __init__(self, fail=False):
        self.fail = fail
        self.messages = []

    def send_message(self, text):
        if self.fail:
            raise TelegramError("falha simulada")
        self.messages.append(text)
