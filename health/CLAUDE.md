# Health Tech Branching Demo — Agent Reference

## Overview

This demo showcases Xata Postgres branching with a health tech database. The main branch holds synthetic patient data (PHI/PII). A staging branch (maintained by Privacy Dynamics) provides an anonymized copy. Developers create branches from staging to get production-shaped data without exposing protected information.

```
main → staging (anonymized) → dev branches
```

## Setup

```bash
cd health
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env.local
# Edit .env.local with your Xata connection string and API key
```

## Seeding the main branch

```bash
source .venv/bin/activate
export $(grep -v '^#' .env.local | xargs)
python seed_database.py
```

Creates 10 tables with ~107K rows of synthetic health data.

## Branching

Create a branch (full copy of a database):

```sql
CREATE DATABASE my_branch TEMPLATE staging;
```

Connect to it:

```bash
psql "postgresql://xata:<password>@<workspace>.us-east-1.xata.tech/my_branch?sslmode=require"
```

List branches:

```sql
SELECT datname FROM pg_database WHERE datistemplate = false;
```

Delete a branch:

```sql
DROP DATABASE my_branch;
```

## Tables

| Table | Rows | Description |
|---|---|---|
| customers | 10,000 | SSN, DOB, email, phone, IP address |
| customer_addresses | 12,000 | Home/shipping/billing addresses |
| insurance_plans | 5,000 | Carrier, member ID, group number |
| payment_methods | 8,000 | Credit card numbers, billing info |
| consultations | 25,000 | Medical notes, diagnosis codes |
| prescriptions | 15,000 | Rx numbers, dosages, pharmacy notes |
| orders | 12,000 | Order tracking, shipping info |
| order_items | 20,000 | Line items with pricing |
| products | 500 | Rx and OTC health products |
| providers | 200 | Licensed medical providers |

## PHI/PII by table

| Table | PII Fields |
|---|---|
| customers | first_name, last_name, email, phone, ssn, date_of_birth, ip_address |
| customer_addresses | address_line_1, address_line_2, city, state, zip_code |
| insurance_plans | member_id, group_number, subscriber_name |
| payment_methods | card_number, card_last_four, billing_name, billing_zip |
| consultations | chief_complaint, diagnosis_code, notes |
| prescriptions | rx_number, pharmacy_notes |
| providers | first_name, last_name, email, phone, npi_number |

## Environment variables

| Variable | Purpose |
|---|---|
| `POSTGRES_URL_LOCALHOST` | Xata Postgres connection string |
| `XATA_API_KEY` | Xata API key |
