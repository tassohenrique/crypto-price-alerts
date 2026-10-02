import json

import httpx
import pytest

from app.clients.telegram import TelegramClient, TelegramError

TOKEN = "123456:TOKEN-DE-TESTE"


def make_client(handler):
    return TelegramClient(
        bot_token=TOKEN,
        chat_id="999",
        transport=httpx.MockTransport(handler),
    )


def test_send_message_posts_json_to_bot_api():
    def handler(request):
        assert request.method == "POST"
        assert request.url.path == f"/bot{TOKEN}/sendMessage"
        assert json.loads(request.content) == {
            "chat_id": "999",
            "text": "Bitcoin caiu!",
        }
        return httpx.Response(200, json={"ok": True, "result": {}})

    make_client(handler).send_message("Bitcoin caiu!")


def test_send_message_raises_when_telegram_rejects():
    def handler(request):
        return httpx.Response(
            400, json={"ok": False, "description": "Bad Request: chat not found"}
        )

    with pytest.raises(TelegramError, match="chat not found"):
        make_client(handler).send_message("Oi")


def test_send_message_raises_when_ok_is_false():
    def handler(request):
        return httpx.Response(200, json={"ok": False, "description": "Forbidden"})

    with pytest.raises(TelegramError, match="Forbidden"):
        make_client(handler).send_message("Oi")


def test_send_message_raises_on_non_json_response():
    def handler(request):
        return httpx.Response(502, text="<html>Bad Gateway</html>")

    with pytest.raises(TelegramError):
        make_client(handler).send_message("Oi")


def test_send_message_raises_on_timeout():
    def handler(request):
        raise httpx.ReadTimeout("timeout", request=request)

    with pytest.raises(TelegramError):
        make_client(handler).send_message("Oi")


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: httpx.Response(
            401, json={"ok": False, "description": "Unauthorized"}
        ),
        lambda request: (_ for _ in ()).throw(
            httpx.ConnectError("falha", request=request)
        ),
    ],
    ids=["api_error", "connection_error"],
)
def test_error_messages_never_contain_the_token(handler):
    with pytest.raises(TelegramError) as exc_info:
        make_client(handler).send_message("Oi")

    assert TOKEN not in str(exc_info.value)
    assert exc_info.value.__cause__ is None
