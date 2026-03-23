# Health Tech Database Branching Demo

Demonstrates [Xata Postgres branching](https://xata.io/docs/postgres) with a realistic health tech database. Create isolated database copies for development, testing, and analytics — without exposing production PHI/PII.

## Architecture

```
main (production)          → Raw patient data (SSNs, medical records, prescriptions)
  └── staging (anonymized) → Treated by Privacy Dynamics — PII masked/generalized
       ├── dev-feature-x   → Branch for feature development
       ├── qa-sprint-42    → Branch for QA testing
       └── analytics       → Branch for data science
```

**Main branch** contains synthetic (but realistic) health data modeled after a telehealth + pharmacy company. **Staging** is an anonymized copy maintained by [Privacy Dynamics](https://www.privacydynamics.io). Developers branch from staging to get production-shaped data without PHI.

## Quick start

### 1. Seed the main branch

```bash
cd health
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env.local
# Edit .env.local with your Xata Postgres connection string

export $(grep -v '^#' .env.local | xargs)
python seed_database.py
```

### 2. Create branches

Once the staging branch exists (anonymized via Privacy Dynamics), create dev branches from it:

```bash
# Connect to your Xata database
psql "$POSTGRES_URL_LOCALHOST"

# Create a branch from staging
CREATE DATABASE dev_feature_x TEMPLATE staging;

# List all branches
SELECT datname FROM pg_database WHERE datistemplate = false;
```

### 3. Connect to a branch

Each branch is a full Postgres database on the same Xata instance:

```bash
psql "postgresql://xata:<password>@<workspace>.us-east-1.xata.tech/dev_feature_x?sslmode=require"
```

### 4. Clean up

```bash
DROP DATABASE dev_feature_x;
```

## Dataset

| Table | Rows | Key PII |
|---|---|---|
| customers | 10,000 | SSN, DOB, email, phone |
| customer_addresses | 12,000 | Full street addresses |
| insurance_plans | 5,000 | Member IDs, group numbers |
| payment_methods | 8,000 | Credit card numbers |
| consultations | 25,000 | Medical notes, diagnosis codes |
| prescriptions | 15,000 | Rx numbers, pharmacy notes |
| orders | 12,000 | Shipping + billing info |
| order_items | 20,000 | Line items with pricing |
| products | 500 | Rx & OTC health products |
| providers | 200 | NPI numbers, credentials |

## Prerequisites

- Python 3.11+
- A [Xata](https://xata.io) database with Postgres access enabled

## Learn more

See [CLAUDE.md](CLAUDE.md) for detailed table schemas and PII field mappings.
