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

Default bootstrap user is created automatically on first run:
- username: `admin`
- password: `admin123`

## Configuration

Environment variables:

- `APP_ENV` (optional): `development` / `testing` / `production`
- `SECRET_KEY`
- `DATABASE_URL`
  - Example PostgreSQL URL:
    - `******localhost:5432/elite_insurance`

If `DATABASE_URL` is not set, SQLite is used.

## REST/API Endpoints

- `GET /api/dashboard`
- `GET/POST /insurance/customers`
- `GET/POST /insurance/policies`
- `GET/POST /insurance/installments`
- `GET /insurance/api/reports`
- `GET/POST /vip/cards`
- `GET/POST /vip/installments`
- `GET /vip/api/reports`
- `GET /reports/api/overview`
- `GET /reports/export/insurance.xlsx`
- `GET /reports/export/vip.xlsx`
- `GET /reports/export/dashboard.pdf`

## Migration Strategy

Use `insurance/unified_admin/migrations.py` function `migrate_legacy_sqlite(...)` to import legacy `customers` and `policies` from old `insurance.db` into the unified schema.

## Testing

Run legacy CLI tests and new unified-app integration tests:

```bash
cd insurance
python test_insurance.py
python test_unified_admin.py
```

## Legacy CLI

The original CLI implementation remains available in:
- `insurance/app.py`
