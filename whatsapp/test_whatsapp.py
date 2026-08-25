"""Tests for the WhatsApp notification feature."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from whatsapp.router import get_whatsapp_service, router
from whatsapp.services import WhatsAppService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MOCK_API_RESPONSE = {
    "messaging_product": "whatsapp",
    "contacts": [{"input": "+15550001234", "wa_id": "15550001234"}],
    "messages": [{"id": "wamid.abc123"}],
}


def _make_mock_http_client(status_code: int = 200, json_body: dict = None) -> AsyncMock:
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_body or MOCK_API_RESPONSE
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=mock_resp
        )
    else:
        mock_resp.raise_for_status.return_value = None

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = mock_resp
    return mock_client


def _make_app(mock_client: AsyncMock) -> FastAPI:
    """Return a FastAPI app with the WhatsApp router and a mock HTTP client."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_whatsapp_service] = lambda: WhatsAppService(mock_client)
    return app


# ---------------------------------------------------------------------------
# WhatsAppService unit tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_message_success():
    """Service returns the API response dict on success."""
    mock_client = _make_mock_http_client()

    with patch("whatsapp.services.WHATSAPP_ACCESS_TOKEN", "test-token"), \
         patch("whatsapp.services.WHATSAPP_API_BASE_URL", "https://example.com/messages"):
        svc = WhatsAppService(mock_client)
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
    mock_client = _make_mock_http_client()

    with patch("whatsapp.services.WHATSAPP_ACCESS_TOKEN", "my-secret-token"), \
         patch("whatsapp.services.WHATSAPP_API_BASE_URL", "https://example.com/messages"):
        await WhatsAppService(mock_client).send_message("+15550001234", "Hi")

    headers = mock_client.post.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer my-secret-token"
    assert headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_send_message_raises_on_http_error():
    """Service propagates HTTPStatusError from the API."""
    mock_client = _make_mock_http_client(status_code=401)

    with patch("whatsapp.services.WHATSAPP_ACCESS_TOKEN", "bad-token"), \
         patch("whatsapp.services.WHATSAPP_API_BASE_URL", "https://example.com/messages"):
        with pytest.raises(httpx.HTTPStatusError):
            await WhatsAppService(mock_client).send_message("+15550001234", "Hi")


# ---------------------------------------------------------------------------
# Router / integration tests
# ---------------------------------------------------------------------------

def test_post_whatsapp_send_success():
    """POST /whatsapp/send returns 200 and the API payload."""
    mock_client = _make_mock_http_client()

    with patch("whatsapp.services.WHATSAPP_ACCESS_TOKEN", "test-token"), \
         patch("whatsapp.services.WHATSAPP_API_BASE_URL", "https://example.com/messages"):
        with TestClient(_make_app(mock_client)) as tc:
            response = tc.post(
                "/whatsapp/send",
                params={"phone": "+15550001234", "message": "Hello from tests!"},
            )

    assert response.status_code == 200
    assert response.json() == MOCK_API_RESPONSE


def test_post_whatsapp_send_missing_params():
    """POST /whatsapp/send with missing query params returns 422."""
    mock_client = _make_mock_http_client()
    with TestClient(_make_app(mock_client)) as tc:
        response = tc.post("/whatsapp/send")
    assert response.status_code == 422
