# Elite Insurance Unified Admin Platform

This directory now includes a unified Flask-based administration platform that combines Insurance and VIP operations in one codebase.

## What's Included

- Unified dashboard metrics:
  - Total customers
  - Active insurance policies
  - Active VIP cards
  - Monthly revenue
  - Pending installments
- Shared authentication with roles (`admin`, `employee`)
- Insurance module:
  - Customer management
  - Policy management
  - Installment tracking
  - Reports API
- VIP module:
  - VIP card issuance/management
  - Installment tracking
  - Reports API
- Shared consolidated tables:
  - `users`, `customers`, `installments`
- Module tables:
  - `policies`, `vip_cards`
- Export endpoints:
  - Excel (`.xlsx`) exports
  - PDF dashboard export
- Environment-based configuration with PostgreSQL-ready `DATABASE_URL`

## Structure

- `insurance/webapp.py` - Flask entrypoint
- `insurance/unified_admin/` - app package
  - `__init__.py` app factory + blueprint registration
  - `auth.py`, `dashboard.py`, `insurance_module.py`, `vip.py`, `reports_module.py`
  - `models.py` consolidated schema models
  - `migrations.py` legacy migration helper
  - `templates/` responsive unified UI with single sidebar and Elite branding

## Setup

```bash
cd insurance
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run (Development)

```bash
cd insurance
python webapp.py
```

An `admin` user is created automatically on first run:
- username: `admin`
- password: set `INITIAL_ADMIN_PASSWORD` before the first run to choose it. If that
  variable is unset, a secure random password is generated and written once to the
  application log as a `WARNING` — retrieve it from the startup log and rotate it
  immediately.

## Configuration

Environment variables:

- `APP_ENV` (optional): `development` / `testing` / `production`
- `SECRET_KEY`
- `DATABASE_URL`
  - Example PostgreSQL URL:
    - `******localhost:5432/elite_insurance`
- `ANTHROPIC_API_KEY` (optional): enables live Claude-powered AI features. When unset,
  the AI endpoints fall back to deterministic logic so the app still runs offline.
- `AI_MODEL` (optional): Claude model id for AI features (default `claude-opus-5-5`).

If `DATABASE_URL` is not set, SQLite is used.

## AIG Portal (UI)

The AIG prototype pages are served by Flask and wired to the backend. Start the app and
open the login page at:

- `/aig/` (redirects to the login page, or the dashboard once signed in)
- `/aig/SSO/Login/GUI/Frmlogin.html` — login (posts to `/auth/login`)
- `/aig/Insurance/GUI/FrmInsurance.html` — dashboard (live KPIs)
- `/aig/Insurance/Customer/GUI/FrmCustomer.html` — customers CRUD
- `/aig/Insurance/Policy/GUI/FrmPolicy.html` — policies (with "Suggest Premium (AI)")
- `/aig/Insurance/Claims/GUI/FrmClaims.html` — claims + status workflow (with "AI Triage")

All pages except the login page require an authenticated session; writes are admin-only.

## REST/API Endpoints

- `GET /api/dashboard`
- `GET/POST /insurance/customers`, `PUT/DELETE /insurance/customers/<id>`
- `GET/POST /insurance/policies`, `PUT/DELETE /insurance/policies/<id>`
- `GET/POST /insurance/claims`, `PATCH /insurance/claims/<claim_number>/status`
- `GET/POST /insurance/installments`
- `GET /insurance/api/reports`
- `GET /insurance/api/dashboard-summary` (KPIs + recent policies/claims for the AIG dashboard)
- `GET/POST /vip/cards`
- `GET/POST /vip/installments`
- `GET /vip/api/reports`
- `GET /reports/api/overview`
- `GET /reports/export/insurance.xlsx`
- `GET /reports/export/vip.xlsx`
- `GET /reports/export/dashboard.pdf`

## AI Features

A chat page at `/ai/` plus four JSON endpoints (all require login). Each calls Claude when
`ANTHROPIC_API_KEY` is set and otherwise returns a deterministic fallback:

- `POST /ai/chat` — insurance assistant chat (`{message, history?}`)
- `POST /ai/risk-score` — risk + suggested premium (`{policy_type, coverage_amount, age|dob}`)
- `POST /ai/claims-triage` — approve/review/reject recommendation (`{amount, description, ...}`)
- `POST /ai/extract-document` — structured fields from document text (`{text}`)

## Migration Strategy

Use `insurance/unified_admin/migrations.py` function `migrate_legacy_sqlite(...)` to import legacy `customers` and `policies` from old `insurance.db` into the unified schema.

## Testing

Run legacy CLI tests and new unified-app integration tests:

```bash
cd insurance
python test_insurance.py
python test_unified_admin.py
python test_aig_ai.py
```

## Legacy CLI

The original CLI implementation remains available in:
- `insurance/app.py`
