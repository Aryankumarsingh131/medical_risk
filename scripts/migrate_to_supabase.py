"""
scripts/migrate_to_supabase.py
------------------------------
One-shot migration: copies all data from local SQLite -> Supabase PostgreSQL.

Run ONCE after updating .env to point to Supabase:
    python scripts/migrate_to_supabase.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# -- project root on path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# -- source: local SQLite
SQLITE_URL = f"sqlite:///{PROJECT_ROOT / 'medical_risk.db'}"
sqlite_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})

# -- destination: Supabase PostgreSQL
PG_URL = os.getenv("DATABASE_URL")
if not PG_URL or not PG_URL.startswith("postgresql"):
    print("ERROR: DATABASE_URL in .env is not a PostgreSQL URL. Aborting.")
    sys.exit(1)

pg_engine = create_engine(PG_URL, pool_pre_ping=True)

# -- create all tables in Supabase first
from api.database import Base
print("Creating tables in Supabase ...")
Base.metadata.create_all(bind=pg_engine)
print("Tables ready.\n")


def migrate_table(table_name, sqlite_conn, pg_conn):
    rows = sqlite_conn.execute(text(f"SELECT * FROM {table_name}")).mappings().all()
    if not rows:
        print(f"  {table_name}: empty, skipped.")
        return 0
    cols = list(rows[0].keys())
    col_list = ", ".join(f'"{c}"' for c in cols)
    val_list = ", ".join(f":{c}" for c in cols)
    stmt = text(
        f'INSERT INTO "{table_name}" ({col_list}) VALUES ({val_list}) ON CONFLICT DO NOTHING'
    )
    pg_conn.execute(stmt, [dict(r) for r in rows])
    pg_conn.commit()
    print(f"  {table_name}: {len(rows)} rows copied.")
    return len(rows)


TABLES = [
    "hospitals",
    "hospital_doctor_availability",
    "hospital_availability",
    "users",
    "patient_assessments",
    "blood_test_results",
    "doctor_diagnoses",
    "clinical_drafts",
    "medicines",
    "patient_registration_requests",
    "audit_logs",
    "prediction_logs",
]

print("Starting data migration SQLite -> Supabase PostgreSQL ...\n")
total = 0
with sqlite_engine.connect() as sqlite_conn, pg_engine.connect() as pg_conn:
    for table in TABLES:
        try:
            total += migrate_table(table, sqlite_conn, pg_conn)
        except Exception as e:
            print(f"  {table}: skipped -- {e}")
            pg_conn.rollback()

print(f"\nMigration complete! {total} total rows transferred to Supabase.")
