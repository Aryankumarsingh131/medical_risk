"""
scripts/init_db.py
------------------
Initializes the SQLite database tables.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.database import create_tables

if __name__ == "__main__":
    print("[init_db] Creating all database tables...")
    create_tables()
    print("[init_db] Tables created successfully.")
