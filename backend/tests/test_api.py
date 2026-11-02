from fastapi.testclient import TestClient

from app.main import app

# Без контекстного менеджера lifespan не запускается: ни Telegram, ни БД не нужны
client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_me_without_auth_is_401() -> None:
    assert client.get("/api/v1/me").status_code == 401


def test_me_with_wrong_scheme_is_401(init_data: str) -> None:
    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {init_data}"})
    assert response.status_code == 401


def test_me_with_forged_init_data_is_401() -> None:
    response = client.get("/api/v1/me", headers={"Authorization": "tma user=1&hash=deadbeef"})
    assert response.status_code == 401


def test_webhook_without_secret_is_403() -> None:
    # В dev-режиме секрета нет — webhook всегда закрыт
    response = client.post(
        "/telegram/webhook",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "anything"},
    )
    assert response.status_code == 403
