# Insurance Management System

A command-line Insurance Management System built with Python and SQLite. Manage customers, policies, and claims with automated premium calculation and reporting.

## Features

| Feature | Description |
|---|---|
| **Customer Management** | Create, read, update, delete customer records |
| **Policy Management** | Manage insurance policies (life, health, auto, home, travel) |
| **Claims Management** | File and track claims through approval workflow |
| **Premium Calculation** | Age-adjusted premium calculation by policy type |
| **Reports** | Summary, policy-type breakdown, and top-claims reports |

## Requirements

- Python 3.8+
- No external dependencies (uses built-in `sqlite3`)

## Quick Start

```bash
cd insurance
python app.py
```

The database file `insurance.db` is created automatically on first run.

## Project Structure

```
insurance/
├── app.py          # CLI entry point
├── database.py     # DB initialisation & connection
├── customer.py     # Customer CRUD operations
├── policy.py       # Policy CRUD operations
├── claims.py       # Claims CRUD operations
├── premium.py      # Premium calculation engine
├── reports.py      # Reporting queries
├── test_insurance.py # Unit tests
└── requirements.txt
```

## CLI Walkthrough

### Main Menu

```
╔══════════════════════════════════════╗
║   Insurance Management System v1.0   ║
╚══════════════════════════════════════╝

=== Main Menu ===
  1. Customer Management
  2. Policy Management
  3. Claims Management
  4. Premium Calculator
  5. Reports
  0. Exit
```

### Adding a Customer

```
=== Customer Management ===
  2. Add customer

Name: Jane Doe
Email: jane.doe@example.com
Phone (optional): 555-1234
Date of birth (YYYY-MM-DD, optional): 1985-03-15
Address (optional): 123 Main St
✓ Customer created with ID 1
```

### Creating a Policy

```
=== Policy Management ===
  3. Add policy

Customer ID: 1
Policy types: life, health, auto, home, travel
Policy type: auto
Coverage amount: 50000
Start date [2024-01-01]:
End date (YYYY-MM-DD): 2025-01-01
  Calculated premium: $750.00
Use calculated premium? (Y/n):
✓ Policy created: POL-A1B2C3D4 (ID 1)
```

### Filing a Claim

```
=== Claims Management ===
  3. File new claim

Policy ID: 1
Claim date [2024-06-01]:
Description: Rear-end collision on Highway 1
Amount claimed: 3500
✓ Claim filed: CLM-E5F6A7B8 (ID 1)
```

### Approving a Claim

```
  5. Update claim (approve / reject)

Claim ID: 1
Current status: pending, Amount claimed: 3500.0
Statuses: approved, rejected, pending, under_review
New status: approved
Amount approved [3500.0]: 3000
✓ Claim updated.
```

## Premium Calculation

Premiums are calculated as:

```
annual_premium = (coverage_amount / 1000) × base_rate × age_multiplier
total_premium  = annual_premium × (duration_months / 12)
```

### Base Rates (per $1,000 coverage)

| Policy Type | Rate |
|---|---|
| Life | $0.50 |
| Health | $2.00 |
| Auto | $1.50 |
| Home | $0.80 |
| Travel | $3.00 |

### Age Multipliers (Life & Health only)

| Age Range | Multiplier |
|---|---|
| Under 25 | 0.9× |
| 25–39 | 1.0× |
| 40–54 | 1.3× |
| 55–64 | 1.7× |
| 65+ | 2.2× |

## Running Tests

```bash
cd insurance
python test_insurance.py
```

## Database Schema

```sql
customers  (id, name, email, phone, date_of_birth, address, created_at)
policies   (id, customer_id, policy_number, policy_type, coverage_amount,
            premium_amount, start_date, end_date, status, created_at)
claims     (id, policy_id, claim_number, claim_date, description,
            amount_claimed, amount_approved, status, created_at)
```

Policy statuses: `active`, `expired`, `cancelled`, `suspended`  
Claim statuses: `pending`, `under_review`, `approved`, `rejected`
