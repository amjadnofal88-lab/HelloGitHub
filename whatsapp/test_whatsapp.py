"""Tests for the WhatsApp notification feature."""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MOCK_API_RESPONSE = {
    "messaging_product": "whatsapp",
    "contacts": [{"input": "+15550001234", "wa_id": "15550001234"}],
    "messages": [{"id": "wamid.abc123"}],
}


def _make_mock_response(status_code: int = 200, json_body: dict = None) -> MagicMock:
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_body or MOCK_API_RESPONSE
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=mock_resp
        )
    else:
        mock_resp.raise_for_status.return_value = None
    return mock_resp


# ---------------------------------------------------------------------------
# WhatsAppService unit tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_message_success():
    """Service returns the API response dict on success."""
    import importlib
    import whatsapp.services as svc_module

    mock_response = _make_mock_response()
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response

    with patch("whatsapp.services.WHATSAPP_ACCESS_TOKEN", "test-token"), \
         patch("whatsapp.services.WHATSAPP_API_BASE_URL", "https://example.com/messages"), \
         patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

        from whatsapp.services import WhatsAppService
        svc = WhatsAppService()
        result = await svc.send_message("+15550001234", "Hello!")

    assert result == MOCK_API_RESPONSE
    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    payload = call_kwargs.kwargs["json"]
    assert payload["to"] == "+15550001234"
    assert payload["text"]["body"] == "Hello!"
    assert payload["messaging_product"] == "whatsapp"


@pytest.mark.asyncio
async def test_send_message_sets_auth_header():
    """Service sends the Bearer token in the Authorization header."""
    mock_response = _make_mock_response()
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response

    with patch("whatsapp.services.WHATSAPP_ACCESS_TOKEN", "my-secret-token"), \
         patch("whatsapp.services.WHATSAPP_API_BASE_URL", "https://example.com/messages"), \
         patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

        from whatsapp.services import WhatsAppService
        await WhatsAppService().send_message("+15550001234", "Hi")

    headers = mock_client.post.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer my-secret-token"
    assert headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_send_message_raises_on_http_error():
    """Service propagates HTTPStatusError from the API."""
    mock_response = _make_mock_response(status_code=401)
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response

    with patch("whatsapp.services.WHATSAPP_ACCESS_TOKEN", "bad-token"), \
         patch("whatsapp.services.WHATSAPP_API_BASE_URL", "https://example.com/messages"), \
         patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

        from whatsapp.services import WhatsAppService
        with pytest.raises(httpx.HTTPStatusError):
            await WhatsAppService().send_message("+15550001234", "Hi")


# ---------------------------------------------------------------------------
# Router / integration tests
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """Return a FastAPI TestClient with the WhatsApp router mounted."""
    from fastapi import FastAPI
    from whatsapp.router import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_post_whatsapp_send_success(client):
    """POST /whatsapp/send returns 200 and the API payload."""
    mock_response = _make_mock_response()
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response

    with patch("whatsapp.services.WHATSAPP_ACCESS_TOKEN", "test-token"), \
         patch("whatsapp.services.WHATSAPP_API_BASE_URL", "https://example.com/messages"), \
         patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

        response = client.post(
            "/whatsapp/send",
            params={"phone": "+15550001234", "message": "Hello from tests!"},
        )

    assert response.status_code == 200
    assert response.json() == MOCK_API_RESPONSE


def test_post_whatsapp_send_missing_params(client):
    """POST /whatsapp/send with missing query params returns 422."""
    response = client.post("/whatsapp/send")
    assert response.status_code == 422
