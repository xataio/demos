#!/usr/bin/env python
"""
Generate ~1GB of synthetic health tech data (Hims-style) on the Xata main branch.

Tables: products, providers, customers, customer_addresses, insurance_plans,
        payment_methods, consultations, prescriptions, orders, order_items

Usage:
    source .venv/bin/activate
    export $(grep -v '^#' .env.local | xargs)
    python seed_database.py
"""

import os
import random
import sys
import uuid
from datetime import date, datetime, timedelta

from faker import Faker
from sqlalchemy import (
    create_engine, text, MetaData, Table, Column, String, Integer, SmallInteger,
    Boolean, Date, DateTime, Text, Float, ForeignKey, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

fake = Faker("en_US")
Faker.seed(42)
random.seed(42)

# --- Config ---
BATCH_SIZE = 500

ROW_COUNTS = {
    "products": 500,
    "providers": 200,
    "customers": 10_000,
    "customer_addresses": 12_000,
    "insurance_plans": 5_000,
    "payment_methods": 8_000,
    "consultations": 25_000,
    "prescriptions": 15_000,
    "orders": 12_000,
    "order_items": 20_000,
}

# --- Reference data ---

CATEGORIES = ["hair", "skin", "sexual_health", "mental_health", "weight_loss", "supplements"]

PRODUCTS_BY_CATEGORY = {
    "hair": [
        ("Finasteride 1mg", "finasteride", "1mg", "tablet"),
        ("Minoxidil 5% Solution", "minoxidil", "5%", "bottle"),
        ("Minoxidil 5% Foam", "minoxidil", "5%", "can"),
        ("Biotin Gummies", "biotin", "5000mcg", "bottle"),
        ("Saw Palmetto Supplement", "saw palmetto", "320mg", "bottle"),
        ("Ketoconazole Shampoo", "ketoconazole", "2%", "bottle"),
        ("Topical Finasteride & Minoxidil", "finasteride/minoxidil", "0.1%/6%", "bottle"),
        ("Hair Growth Vitamin", "multivitamin", "n/a", "bottle"),
    ],
    "skin": [
        ("Tretinoin Cream 0.025%", "tretinoin", "0.025%", "tube"),
        ("Tretinoin Cream 0.05%", "tretinoin", "0.05%", "tube"),
        ("Niacinamide Serum", "niacinamide", "10%", "bottle"),
        ("Clindamycin Gel", "clindamycin", "1%", "tube"),
        ("Azelaic Acid Cream", "azelaic acid", "15%", "tube"),
        ("Hyaluronic Acid Moisturizer", "hyaluronic acid", "2%", "bottle"),
        ("Anti-Aging Night Cream", "retinol", "0.5%", "jar"),
        ("Vitamin C Serum", "ascorbic acid", "20%", "bottle"),
        ("SPF 50 Sunscreen", "zinc oxide/titanium dioxide", "n/a", "tube"),
        ("Acne Treatment Kit", "benzoyl peroxide/adapalene", "2.5%/0.1%", "kit"),
    ],
    "sexual_health": [
        ("Sildenafil 50mg", "sildenafil", "50mg", "tablet"),
        ("Sildenafil 100mg", "sildenafil", "100mg", "tablet"),
        ("Tadalafil 5mg", "tadalafil", "5mg", "tablet"),
        ("Tadalafil 10mg", "tadalafil", "10mg", "tablet"),
        ("Sertraline 25mg", "sertraline", "25mg", "tablet"),
        ("Paroxetine 7.5mg", "paroxetine", "7.5mg", "tablet"),
        ("Climax Delay Spray", "lidocaine", "4%", "bottle"),
    ],
    "mental_health": [
        ("Bupropion XL 150mg", "bupropion", "150mg", "tablet"),
        ("Bupropion XL 300mg", "bupropion", "300mg", "tablet"),
        ("Sertraline 50mg", "sertraline", "50mg", "tablet"),
        ("Sertraline 100mg", "sertraline", "100mg", "tablet"),
        ("Escitalopram 10mg", "escitalopram", "10mg", "tablet"),
        ("Buspirone 5mg", "buspirone", "5mg", "tablet"),
        ("Hydroxyzine 25mg", "hydroxyzine", "25mg", "tablet"),
    ],
    "weight_loss": [
        ("Semaglutide Injection", "semaglutide", "0.25mg/0.5mL", "injectable"),
        ("Compounded Semaglutide", "semaglutide", "varies", "injectable"),
        ("Metformin ER 500mg", "metformin", "500mg", "tablet"),
        ("Metformin ER 1000mg", "metformin", "1000mg", "tablet"),
        ("Naltrexone/Bupropion", "naltrexone/bupropion", "8mg/90mg", "tablet"),
    ],
    "supplements": [
        ("Daily Multivitamin", "multivitamin", "n/a", "bottle"),
        ("Vitamin D3 5000 IU", "cholecalciferol", "5000IU", "bottle"),
        ("Omega-3 Fish Oil", "omega-3 fatty acids", "1000mg", "bottle"),
        ("Ashwagandha Extract", "ashwagandha", "300mg", "bottle"),
        ("Melatonin 3mg", "melatonin", "3mg", "bottle"),
        ("Collagen Peptides", "collagen", "10g", "packet"),
        ("Probiotic Blend", "lactobacillus/bifidobacterium", "10B CFU", "bottle"),
        ("Zinc + Magnesium", "zinc/magnesium", "30mg/400mg", "bottle"),
    ],
}

SPECIALTIES = ["dermatology", "psychiatry", "primary_care", "urology", "endocrinology",
               "internal_medicine", "family_medicine", "nurse_practitioner"]
CREDENTIALS = ["MD", "DO", "NP", "PA", "MD", "MD", "DO", "NP"]

INSURANCE_CARRIERS = [
    "Aetna", "Blue Cross Blue Shield", "Cigna", "UnitedHealthcare", "Humana",
    "Kaiser Permanente", "Anthem", "Centene", "Molina Healthcare", "WellCare",
    "Oscar Health", "Ambetter", "CareFirst", "EmblemHealth", "Health Net",
]
PLAN_TYPES = ["HMO", "PPO", "EPO", "POS", "HDHP"]

ICD10_CODES = {
    "hair": ["L64.9", "L65.9", "L66.9", "L63.9"],
    "skin": ["L70.0", "L70.1", "L81.0", "L57.0", "L30.9"],
    "sexual_health": ["N52.9", "F52.4", "N48.89"],
    "mental_health": ["F32.1", "F41.1", "F41.0", "F33.1", "F40.10"],
    "weight_loss": ["E66.01", "E66.09", "E66.1", "E11.9"],
}

CHIEF_COMPLAINTS = {
    "hair": [
        "Noticing increased hair thinning at the crown over the past 6 months",
        "Receding hairline progressing, family history of MPB",
        "Diffuse hair loss, shedding more than usual in shower",
        "Thinning at temples, seeking treatment options",
        "Hair loss after COVID, concerned about progression",
    ],
    "skin": [
        "Persistent acne breakouts on chin and jawline",
        "Fine lines and wrinkles developing, interested in retinoids",
        "Dark spots and uneven skin tone, seeking treatment",
        "Dry skin with occasional eczema flares",
        "Hormonal acne, worse around menstrual cycle",
    ],
    "sexual_health": [
        "Difficulty maintaining erection, started about 3 months ago",
        "Occasional ED, performance anxiety contributing",
        "Premature ejaculation concerns, seeking treatment",
        "ED symptoms worsening with stress at work",
        "Looking for daily low-dose option for spontaneity",
    ],
    "mental_health": [
        "Feeling persistently low mood and lack of motivation for 2+ months",
        "Increased anxiety, difficulty sleeping, racing thoughts",
        "Panic attacks occurring 2-3 times per week",
        "Difficulty concentrating, feeling overwhelmed at work",
        "Seasonal depression returning, worse in winter months",
    ],
    "weight_loss": [
        "BMI 32, struggling with weight despite diet and exercise",
        "Want to lose 30-40 lbs, interested in GLP-1 medications",
        "Prediabetes diagnosis, doctor recommended weight management",
        "Weight gain after medication change, seeking support",
        "Plateau after losing 20 lbs, need additional intervention",
    ],
}

CONSULTATION_TYPES = ["async_message", "video", "phone", "follow_up"]
CONSULTATION_STATUSES = ["completed", "completed", "completed", "cancelled", "completed"]
ORDER_STATUSES = ["delivered", "delivered", "shipped", "processing", "delivered", "returned", "cancelled"]


def get_db_url():
    url = os.environ.get("POSTGRES_URL_LOCALHOST") or os.environ.get("POSTGRES_URL")
    if not url:
        print("ERROR: Set POSTGRES_URL_LOCALHOST or POSTGRES_URL")
        sys.exit(1)
    return url


def create_tables(engine):
    """Create all tables (drop first if they exist)."""
    print("Creating tables...")
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS order_items CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS orders CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS prescriptions CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS consultations CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS payment_methods CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS insurance_plans CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS customer_addresses CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS customers CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS providers CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS products CASCADE"))

        conn.execute(text("""
            CREATE TABLE products (
                product_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                sku VARCHAR(30) NOT NULL UNIQUE,
                name VARCHAR(200) NOT NULL,
                category VARCHAR(50) NOT NULL,
                subcategory VARCHAR(100),
                description TEXT,
                requires_prescription BOOLEAN NOT NULL DEFAULT TRUE,
                price_cents INTEGER NOT NULL,
                unit VARCHAR(30),
                active_ingredient VARCHAR(200),
                strength VARCHAR(50),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE providers (
                provider_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                phone VARCHAR(30),
                npi_number VARCHAR(10) NOT NULL UNIQUE,
                license_state VARCHAR(2) NOT NULL,
                specialty VARCHAR(100) NOT NULL,
                credentials VARCHAR(50),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE customers (
                customer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                middle_name VARCHAR(100),
                email VARCHAR(255) NOT NULL UNIQUE,
                phone VARCHAR(30) NOT NULL,
                date_of_birth DATE NOT NULL,
                ssn VARCHAR(11) NOT NULL,
                gender VARCHAR(20) NOT NULL,
                ip_address VARCHAR(45),
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                account_status VARCHAR(20) NOT NULL DEFAULT 'active'
            )
        """))
        conn.execute(text("""
            CREATE TABLE customer_addresses (
                address_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                customer_id UUID NOT NULL REFERENCES customers(customer_id),
                address_type VARCHAR(20) NOT NULL,
                address_line_1 VARCHAR(255) NOT NULL,
                address_line_2 VARCHAR(255),
                city VARCHAR(100) NOT NULL,
                state VARCHAR(2) NOT NULL,
                zip_code VARCHAR(10) NOT NULL,
                is_default BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE insurance_plans (
                insurance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                customer_id UUID NOT NULL REFERENCES customers(customer_id),
                carrier_name VARCHAR(200) NOT NULL,
                plan_type VARCHAR(50) NOT NULL,
                member_id VARCHAR(50) NOT NULL,
                group_number VARCHAR(50),
                bin_number VARCHAR(10),
                pcn VARCHAR(20),
                subscriber_name VARCHAR(200) NOT NULL,
                relationship_to_subscriber VARCHAR(20) NOT NULL,
                effective_date DATE NOT NULL,
                expiration_date DATE,
                is_primary BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE payment_methods (
                payment_method_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                customer_id UUID NOT NULL REFERENCES customers(customer_id),
                method_type VARCHAR(20) NOT NULL,
                card_number VARCHAR(19) NOT NULL,
                card_last_four VARCHAR(4) NOT NULL,
                card_brand VARCHAR(20) NOT NULL,
                expiration_month SMALLINT NOT NULL,
                expiration_year SMALLINT NOT NULL,
                billing_name VARCHAR(200) NOT NULL,
                billing_zip VARCHAR(10) NOT NULL,
                is_default BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE consultations (
                consultation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                customer_id UUID NOT NULL REFERENCES customers(customer_id),
                provider_id UUID NOT NULL REFERENCES providers(provider_id),
                consultation_type VARCHAR(30) NOT NULL,
                category VARCHAR(50) NOT NULL,
                status VARCHAR(20) NOT NULL,
                scheduled_at TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                chief_complaint TEXT,
                diagnosis_code VARCHAR(10),
                notes TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE prescriptions (
                prescription_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                consultation_id UUID NOT NULL REFERENCES consultations(consultation_id),
                provider_id UUID NOT NULL REFERENCES providers(provider_id),
                product_id UUID NOT NULL REFERENCES products(product_id),
                rx_number VARCHAR(20) NOT NULL UNIQUE,
                dosage VARCHAR(100) NOT NULL,
                quantity INTEGER NOT NULL,
                refills_authorized SMALLINT NOT NULL DEFAULT 0,
                refills_used SMALLINT NOT NULL DEFAULT 0,
                days_supply INTEGER NOT NULL,
                status VARCHAR(20) NOT NULL,
                prescribed_date DATE NOT NULL,
                expiration_date DATE NOT NULL,
                pharmacy_notes TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE orders (
                order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                customer_id UUID NOT NULL REFERENCES customers(customer_id),
                payment_method_id UUID REFERENCES payment_methods(payment_method_id),
                shipping_address_id UUID NOT NULL REFERENCES customer_addresses(address_id),
                order_number VARCHAR(20) NOT NULL UNIQUE,
                status VARCHAR(20) NOT NULL,
                subtotal_cents INTEGER NOT NULL,
                tax_cents INTEGER NOT NULL,
                shipping_cents INTEGER NOT NULL DEFAULT 0,
                discount_cents INTEGER NOT NULL DEFAULT 0,
                total_cents INTEGER NOT NULL,
                insurance_paid_cents INTEGER NOT NULL DEFAULT 0,
                tracking_number VARCHAR(50),
                shipped_at TIMESTAMP,
                delivered_at TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE order_items (
                order_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                order_id UUID NOT NULL REFERENCES orders(order_id),
                product_id UUID NOT NULL REFERENCES products(product_id),
                prescription_id UUID REFERENCES prescriptions(prescription_id),
                quantity SMALLINT NOT NULL DEFAULT 1,
                unit_price_cents INTEGER NOT NULL,
                total_cents INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
    print("Tables created.")


def insert_batch(conn, table, rows):
    """Insert a batch of rows using executemany."""
    if not rows:
        return
    cols = list(rows[0].keys())
    placeholders = ", ".join([f":{c}" for c in cols])
    col_names = ", ".join(cols)
    conn.execute(
        text(f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"),
        rows,
    )
    conn.commit()


def gen_products(conn):
    """Generate product catalog."""
    print(f"  products: {ROW_COUNTS['products']} rows...")
    rows = []
    idx = 0
    for cat, prods in PRODUCTS_BY_CATEGORY.items():
        for name, ingredient, strength, unit in prods:
            idx += 1
            rx = cat not in ("supplements",)
            rows.append({
                "product_id": str(uuid.uuid4()),
                "sku": f"HH-{cat[:3].upper()}-{idx:04d}",
                "name": name,
                "category": cat,
                "subcategory": unit,
                "description": f"{name}. {fake.sentence(nb_words=12)}",
                "requires_prescription": rx,
                "price_cents": random.choice([999, 1499, 1999, 2499, 2999, 3499, 4999, 7999, 8999, 14999, 19999]),
                "unit": unit,
                "active_ingredient": ingredient,
                "strength": strength,
                "is_active": True,
                "created_at": fake.date_time_between(start_date="-3y", end_date="-1y"),
            })

    # Pad to target with variations
    while len(rows) < ROW_COUNTS["products"]:
        idx += 1
        cat = random.choice(CATEGORIES)
        rows.append({
            "product_id": str(uuid.uuid4()),
            "sku": f"HH-{cat[:3].upper()}-{idx:04d}",
            "name": f"{fake.word().title()} {random.choice(['Cream', 'Gel', 'Tablet', 'Capsule', 'Serum', 'Spray'])} {random.choice(['5mg', '10mg', '25mg', '1%', '2%'])}",
            "category": cat,
            "subcategory": random.choice(["tablet", "topical", "injectable", "capsule"]),
            "description": fake.sentence(nb_words=15),
            "requires_prescription": random.random() > 0.3,
            "price_cents": random.randint(499, 29999),
            "unit": random.choice(["tablet", "bottle", "tube", "kit", "jar", "packet"]),
            "active_ingredient": fake.word(),
            "strength": random.choice(["1mg", "5mg", "10mg", "25mg", "50mg", "1%", "2%", "5%"]),
            "is_active": random.random() > 0.1,
            "created_at": fake.date_time_between(start_date="-3y", end_date="-6M"),
        })

    for i in range(0, len(rows), BATCH_SIZE):
        insert_batch(conn, "products", rows[i:i + BATCH_SIZE])
    return [r["product_id"] for r in rows]


def gen_providers(conn):
    """Generate provider records."""
    print(f"  providers: {ROW_COUNTS['providers']} rows...")
    rows = []
    for _ in range(ROW_COUNTS["providers"]):
        fn = fake.first_name()
        ln = fake.last_name()
        spec = random.choice(SPECIALTIES)
        cred = random.choice(CREDENTIALS)
        rows.append({
            "provider_id": str(uuid.uuid4()),
            "first_name": fn,
            "last_name": ln,
            "email": f"{fn.lower()}.{ln.lower()}{random.randint(1,999)}@himshealth.com",
            "phone": f"+1{random.randint(2000000000, 9999999999)}",
            "npi_number": str(random.randint(1000000000, 9999999999)),
            "license_state": fake.state_abbr(),
            "specialty": spec,
            "credentials": cred,
            "is_active": random.random() > 0.05,
            "created_at": fake.date_time_between(start_date="-4y", end_date="-1y"),
        })
    for i in range(0, len(rows), BATCH_SIZE):
        insert_batch(conn, "providers", rows[i:i + BATCH_SIZE])
    return [r["provider_id"] for r in rows]


def gen_customers(conn):
    """Generate customer records with full PII."""
    n = ROW_COUNTS["customers"]
    print(f"  customers: {n} rows...")
    customer_ids = []
    genders = ["male", "female", "non_binary", "prefer_not_to_say"]
    statuses = ["active", "active", "active", "active", "suspended", "closed"]

    batch = []
    for i in range(n):
        cid = str(uuid.uuid4())
        customer_ids.append(cid)
        gender = random.choices(genders, weights=[45, 45, 5, 5])[0]
        fn = fake.first_name_male() if gender == "male" else fake.first_name_female() if gender == "female" else fake.first_name()
        ln = fake.last_name()
        batch.append({
            "customer_id": cid,
            "first_name": fn,
            "last_name": ln,
            "middle_name": fake.first_name() if random.random() < 0.6 else None,
            "email": f"{fn.lower()}.{ln.lower()}.{random.randint(1, 99999)}@{fake.free_email_domain()}",
            "phone": f"+1{random.randint(2000000000, 9999999999)}",
            "date_of_birth": fake.date_of_birth(minimum_age=18, maximum_age=75),
            "ssn": f"{random.randint(100,999)}-{random.randint(10,99)}-{random.randint(1000,9999)}",
            "gender": gender,
            "ip_address": fake.ipv4() if random.random() < 0.9 else fake.ipv6(),
            "created_at": fake.date_time_between(start_date="-3y", end_date="-1M"),
            "updated_at": fake.date_time_between(start_date="-1y", end_date="now"),
            "is_active": random.random() > 0.08,
            "account_status": random.choice(statuses),
        })

        if len(batch) >= BATCH_SIZE:
            insert_batch(conn, "customers", batch)
            batch = []
            if (i + 1) % 50000 == 0:
                print(f"    {i + 1:,}/{n:,}")
    if batch:
        insert_batch(conn, "customers", batch)
    print(f"    {n:,}/{n:,}")
    return customer_ids


def gen_addresses(conn, customer_ids):
    """Generate customer addresses."""
    n = ROW_COUNTS["customer_addresses"]
    print(f"  customer_addresses: {n} rows...")
    address_ids_by_customer = {}
    batch = []
    for i in range(n):
        cid = customer_ids[i % len(customer_ids)]
        aid = str(uuid.uuid4())
        if cid not in address_ids_by_customer:
            address_ids_by_customer[cid] = []
        address_ids_by_customer[cid].append(aid)
        batch.append({
            "address_id": aid,
            "customer_id": cid,
            "address_type": "shipping" if len(address_ids_by_customer[cid]) == 1 else random.choice(["shipping", "billing"]),
            "address_line_1": fake.street_address(),
            "address_line_2": fake.secondary_address() if random.random() < 0.3 else None,
            "city": fake.city(),
            "state": fake.state_abbr(),
            "zip_code": fake.zipcode(),
            "is_default": len(address_ids_by_customer[cid]) == 1,
            "created_at": fake.date_time_between(start_date="-3y", end_date="-1M"),
        })
        if len(batch) >= BATCH_SIZE:
            insert_batch(conn, "customer_addresses", batch)
            batch = []
            if (i + 1) % 100000 == 0:
                print(f"    {i + 1:,}/{n:,}")
    if batch:
        insert_batch(conn, "customer_addresses", batch)
    print(f"    {n:,}/{n:,}")
    return address_ids_by_customer


def gen_insurance(conn, customer_ids):
    """Generate insurance plans for ~10% of customers."""
    n = ROW_COUNTS["insurance_plans"]
    print(f"  insurance_plans: {n} rows...")
    subset = random.sample(customer_ids, min(n, len(customer_ids)))
    batch = []
    for i, cid in enumerate(subset):
        eff = fake.date_between(start_date="-2y", end_date="-3M")
        batch.append({
            "insurance_id": str(uuid.uuid4()),
            "customer_id": cid,
            "carrier_name": random.choice(INSURANCE_CARRIERS),
            "plan_type": random.choice(PLAN_TYPES),
            "member_id": f"{random.choice(['MBR', 'ID', 'MEM'])}{random.randint(100000000, 999999999)}",
            "group_number": f"GRP{random.randint(10000, 99999)}" if random.random() < 0.8 else None,
            "bin_number": str(random.randint(100000, 999999)) if random.random() < 0.7 else None,
            "pcn": fake.bothify("???###") if random.random() < 0.6 else None,
            "subscriber_name": fake.name(),
            "relationship_to_subscriber": random.choices(["self", "spouse", "child", "other"], weights=[70, 15, 10, 5])[0],
            "effective_date": eff,
            "expiration_date": eff + timedelta(days=365) if random.random() < 0.8 else None,
            "is_primary": True,
            "created_at": fake.date_time_between(start_date="-2y", end_date="-1M"),
        })
        if len(batch) >= BATCH_SIZE:
            insert_batch(conn, "insurance_plans", batch)
            batch = []
            if (i + 1) % 10000 == 0:
                print(f"    {i + 1:,}/{n:,}")
    if batch:
        insert_batch(conn, "insurance_plans", batch)
    print(f"    {len(subset):,}/{n:,}")


def gen_payment_methods(conn, customer_ids):
    """Generate payment methods."""
    n = ROW_COUNTS["payment_methods"]
    print(f"  payment_methods: {n} rows...")
    pm_ids_by_customer = {}
    batch = []
    brands = ["Visa", "Mastercard", "Amex", "Discover"]
    types = ["credit_card", "debit_card", "hsa", "fsa"]

    for i in range(n):
        cid = customer_ids[i % len(customer_ids)]
        pmid = str(uuid.uuid4())
        if cid not in pm_ids_by_customer:
            pm_ids_by_customer[cid] = []
        pm_ids_by_customer[cid].append(pmid)
        card = fake.credit_card_number()
        batch.append({
            "payment_method_id": pmid,
            "customer_id": cid,
            "method_type": random.choices(types, weights=[50, 30, 10, 10])[0],
            "card_number": card,
            "card_last_four": card[-4:],
            "card_brand": random.choice(brands),
            "expiration_month": random.randint(1, 12),
            "expiration_year": random.randint(2025, 2030),
            "billing_name": fake.name(),
            "billing_zip": fake.zipcode(),
            "is_default": len(pm_ids_by_customer[cid]) == 1,
            "created_at": fake.date_time_between(start_date="-3y", end_date="-1M"),
        })
        if len(batch) >= BATCH_SIZE:
            insert_batch(conn, "payment_methods", batch)
            batch = []
            if (i + 1) % 100000 == 0:
                print(f"    {i + 1:,}/{n:,}")
    if batch:
        insert_batch(conn, "payment_methods", batch)
    print(f"    {n:,}/{n:,}")
    return pm_ids_by_customer


def gen_consultations(conn, customer_ids, provider_ids):
    """Generate consultation records."""
    n = ROW_COUNTS["consultations"]
    print(f"  consultations: {n} rows...")
    consultation_data = []
    batch = []

    for i in range(n):
        cid = random.choice(customer_ids)
        pid = random.choice(provider_ids)
        cat = random.choice(CATEGORIES[:-1])  # exclude supplements
        status = random.choice(CONSULTATION_STATUSES)
        sched = fake.date_time_between(start_date="-2y", end_date="-1w")
        started = sched + timedelta(minutes=random.randint(0, 30)) if status != "cancelled" else None
        completed = started + timedelta(minutes=random.randint(5, 45)) if started and status == "completed" else None

        complaint = random.choice(CHIEF_COMPLAINTS[cat])
        notes = f"Patient reports: {complaint}. " + fake.paragraph(nb_sentences=3) if status == "completed" else None

        con_id = str(uuid.uuid4())
        consultation_data.append({"id": con_id, "provider_id": pid, "category": cat, "date": sched})
        batch.append({
            "consultation_id": con_id,
            "customer_id": cid,
            "provider_id": pid,
            "consultation_type": random.choice(CONSULTATION_TYPES),
            "category": cat,
            "status": status,
            "scheduled_at": sched,
            "started_at": started,
            "completed_at": completed,
            "chief_complaint": complaint,
            "diagnosis_code": random.choice(ICD10_CODES[cat]) if status == "completed" else None,
            "notes": notes,
            "created_at": sched - timedelta(days=random.randint(0, 7)),
        })
        if len(batch) >= BATCH_SIZE:
            insert_batch(conn, "consultations", batch)
            batch = []
            if (i + 1) % 200000 == 0:
                print(f"    {i + 1:,}/{n:,}")
    if batch:
        insert_batch(conn, "consultations", batch)
    print(f"    {n:,}/{n:,}")
    return consultation_data


def gen_prescriptions(conn, consultation_data, product_ids):
    """Generate prescription records."""
    n = ROW_COUNTS["prescriptions"]
    print(f"  prescriptions: {n} rows...")
    rx_ids = []
    batch = []
    # Use completed consultations
    completed = [c for c in consultation_data]
    random.shuffle(completed)

    for i in range(n):
        c = completed[i % len(completed)]
        pid = random.choice(product_ids)
        rxid = str(uuid.uuid4())
        rx_ids.append({"id": rxid, "product_id": pid})
        pdate = c["date"].date() if isinstance(c["date"], datetime) else c["date"]
        days = random.choice([30, 60, 90])
        refills = random.randint(0, 11)
        batch.append({
            "prescription_id": rxid,
            "consultation_id": c["id"],
            "provider_id": c["provider_id"],
            "product_id": pid,
            "rx_number": f"RX{uuid.uuid4().hex[:12].upper()}",
            "dosage": random.choice(["1 tablet daily", "2 tablets daily", "apply once daily", "apply twice daily", "as directed", "1 tablet as needed"]),
            "quantity": random.choice([30, 60, 90, 28, 14, 7]),
            "refills_authorized": refills,
            "refills_used": random.randint(0, refills),
            "days_supply": days,
            "status": random.choices(["active", "active", "expired", "cancelled", "transferred"], weights=[40, 30, 15, 10, 5])[0],
            "prescribed_date": pdate,
            "expiration_date": pdate + timedelta(days=365),
            "pharmacy_notes": fake.sentence() if random.random() < 0.3 else None,
            "created_at": c["date"],
        })
        if len(batch) >= BATCH_SIZE:
            insert_batch(conn, "prescriptions", batch)
            batch = []
            if (i + 1) % 100000 == 0:
                print(f"    {i + 1:,}/{n:,}")
    if batch:
        insert_batch(conn, "prescriptions", batch)
    print(f"    {n:,}/{n:,}")
    return rx_ids


def gen_orders(conn, customer_ids, pm_ids_by_customer, addr_ids_by_customer):
    """Generate order records."""
    n = ROW_COUNTS["orders"]
    print(f"  orders: {n} rows...")
    order_data = []
    batch = []

    for i in range(n):
        cid = random.choice(customer_ids)
        pm_list = pm_ids_by_customer.get(cid, [])
        pmid = random.choice(pm_list) if pm_list else None
        addr_list = addr_ids_by_customer.get(cid, [])
        if not addr_list:
            continue
        aid = random.choice(addr_list)

        subtotal = random.randint(1499, 49999)
        tax = int(subtotal * random.uniform(0.04, 0.10))
        shipping = random.choice([0, 0, 0, 499, 799])
        discount = random.choice([0, 0, 0, 500, 1000, 1500]) if random.random() < 0.2 else 0
        ins_paid = random.randint(0, subtotal // 2) if random.random() < 0.1 else 0
        total = subtotal + tax + shipping - discount - ins_paid

        status = random.choice(ORDER_STATUSES)
        created = fake.date_time_between(start_date="-2y", end_date="-1w")
        shipped = created + timedelta(days=random.randint(1, 3)) if status in ("shipped", "delivered") else None
        delivered = shipped + timedelta(days=random.randint(2, 7)) if status == "delivered" and shipped else None

        oid = str(uuid.uuid4())
        order_data.append({"id": oid, "product_ids": []})
        batch.append({
            "order_id": oid,
            "customer_id": cid,
            "payment_method_id": pmid,
            "shipping_address_id": aid,
            "order_number": f"O{uuid.uuid4().hex[:12].upper()}",
            "status": status,
            "subtotal_cents": subtotal,
            "tax_cents": tax,
            "shipping_cents": shipping,
            "discount_cents": discount,
            "total_cents": max(total, 0),
            "insurance_paid_cents": ins_paid,
            "tracking_number": fake.bothify("1Z###???########") if shipped else None,
            "shipped_at": shipped,
            "delivered_at": delivered,
            "created_at": created,
        })
        if len(batch) >= BATCH_SIZE:
            insert_batch(conn, "orders", batch)
            batch = []
            if (i + 1) % 100000 == 0:
                print(f"    {i + 1:,}/{n:,}")
    if batch:
        insert_batch(conn, "orders", batch)
    print(f"    {len(order_data):,}/{n:,}")
    return order_data


def gen_order_items(conn, order_data, product_ids, rx_ids):
    """Generate order line items."""
    n = ROW_COUNTS["order_items"]
    print(f"  order_items: {n} rows...")
    batch = []
    for i in range(n):
        order = order_data[i % len(order_data)]
        pid = random.choice(product_ids)
        rxid = random.choice(rx_ids)["id"] if random.random() < 0.6 else None
        qty = random.choices([1, 2, 3], weights=[70, 20, 10])[0]
        price = random.randint(999, 19999)
        batch.append({
            "order_item_id": str(uuid.uuid4()),
            "order_id": order["id"],
            "product_id": pid,
            "prescription_id": rxid,
            "quantity": qty,
            "unit_price_cents": price,
            "total_cents": price * qty,
            "created_at": fake.date_time_between(start_date="-2y", end_date="-1w"),
        })
        if len(batch) >= BATCH_SIZE:
            insert_batch(conn, "order_items", batch)
            batch = []
            if (i + 1) % 200000 == 0:
                print(f"    {i + 1:,}/{n:,}")
    if batch:
        insert_batch(conn, "order_items", batch)
    print(f"    {n:,}/{n:,}")


def create_indexes(conn):
    """Create indexes on FK and frequently queried columns."""
    print("Creating indexes...")
    indexes = [
        "CREATE INDEX idx_addr_customer ON customer_addresses(customer_id)",
        "CREATE INDEX idx_ins_customer ON insurance_plans(customer_id)",
        "CREATE INDEX idx_pm_customer ON payment_methods(customer_id)",
        "CREATE INDEX idx_cons_customer ON consultations(customer_id)",
        "CREATE INDEX idx_cons_provider ON consultations(provider_id)",
        "CREATE INDEX idx_rx_consultation ON prescriptions(consultation_id)",
        "CREATE INDEX idx_rx_provider ON prescriptions(provider_id)",
        "CREATE INDEX idx_rx_product ON prescriptions(product_id)",
        "CREATE INDEX idx_orders_customer ON orders(customer_id)",
        "CREATE INDEX idx_orders_pm ON orders(payment_method_id)",
        "CREATE INDEX idx_orders_addr ON orders(shipping_address_id)",
        "CREATE INDEX idx_oi_order ON order_items(order_id)",
        "CREATE INDEX idx_oi_product ON order_items(product_id)",
        "CREATE INDEX idx_oi_rx ON order_items(prescription_id)",
        "CREATE INDEX idx_cust_email ON customers(email)",
    ]
    for idx_sql in indexes:
        conn.execute(text(idx_sql))
    print("Indexes created.")


def report_sizes(conn):
    """Report table sizes."""
    print("\nTable sizes:")
    result = conn.execute(text("""
        SELECT relname AS table_name,
               pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
               pg_total_relation_size(relid) AS raw_bytes
        FROM pg_catalog.pg_statio_user_tables
        ORDER BY pg_total_relation_size(relid) DESC
    """))
    total = 0
    for row in result:
        print(f"  {row[0]:30s} {row[1]:>12s}")
        total += row[2]
    print(f"  {'TOTAL':30s} {total / (1024**3):.2f} GB")


def main():
    db_url = get_db_url()
    print(f"Database: {db_url.split('@')[1] if '@' in db_url else db_url}")
    engine = create_engine(db_url)

    create_tables(engine)

    print("\nGenerating data...")
    with engine.connect() as conn:
        product_ids = gen_products(conn)
        provider_ids = gen_providers(conn)
        customer_ids = gen_customers(conn)
        addr_ids_by_customer = gen_addresses(conn, customer_ids)
        gen_insurance(conn, customer_ids)
        pm_ids_by_customer = gen_payment_methods(conn, customer_ids)
        consultation_data = gen_consultations(conn, customer_ids, provider_ids)
        rx_ids = gen_prescriptions(conn, consultation_data, product_ids)
        order_data = gen_orders(conn, customer_ids, pm_ids_by_customer, addr_ids_by_customer)
        gen_order_items(conn, order_data, product_ids, rx_ids)
        create_indexes(conn)
        conn.commit()

    with engine.connect() as conn:
        report_sizes(conn)

    print("\nDone!")


if __name__ == "__main__":
    main()
