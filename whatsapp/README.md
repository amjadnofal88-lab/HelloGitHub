# WhatsApp Notification Service

A FastAPI micro-service that sends WhatsApp text messages using the [Meta WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api).

## Setup

### 1. Prerequisites

- Python 3.8+
- A Meta developer app with the WhatsApp product enabled
- A registered WhatsApp Business phone number

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `WHATSAPP_PHONE_NUMBER_ID` | The phone number ID from the Meta developer console |
| `WHATSAPP_ACCESS_TOKEN` | A system user or temporary access token |
| `WHATSAPP_API_VERSION` | API version (default: `v18.0`) |

### 4. Run the server

```bash
uvicorn whatsapp.main:app --reload
```

## API

### `POST /whatsapp/send`

Send a WhatsApp text message.

**Query parameters**

| Parameter | Type | Description |
|---|---|---|
| `phone` | `string` | Recipient phone in E.164 format (e.g. `+15550001234`) |
| `message` | `string` | Message text to send |

**Example request**

```bash
curl -X POST "http://localhost:8000/whatsapp/send?phone=%2B15550001234&message=Hello"
```

**Example response**

```json
{
  "messaging_product": "whatsapp",
  "contacts": [{ "input": "+15550001234", "wa_id": "15550001234" }],
  "messages": [{ "id": "wamid.abc123" }]
}
```

## Running tests

```bash
pip install pytest pytest-asyncio
pytest whatsapp/test_whatsapp.py -v
```
