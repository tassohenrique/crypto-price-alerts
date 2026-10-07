import pytest

PROTECTED_ENDPOINTS = [
    ("get", "/alerts"),
    ("post", "/alerts"),
    ("get", "/alerts/1"),
    ("post", "/alerts/1/rearm"),
    ("delete", "/alerts/1"),
]


@pytest.mark.parametrize(("method", "url"), PROTECTED_ENDPOINTS)
def test_endpoint_requires_api_key(client, method, url):
    response = client.request(method, url)

    assert response.status_code == 401


@pytest.mark.parametrize(("method", "url"), PROTECTED_ENDPOINTS)
def test_endpoint_rejects_wrong_api_key(client, method, url):
    response = client.request(method, url, headers={"X-API-Key": "chave-errada"})

    assert response.status_code == 401


def test_health_is_public(client):
    assert client.get("/health").status_code == 200
