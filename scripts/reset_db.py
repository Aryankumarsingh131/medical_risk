"""Reset the local Medical Risk demo database.

DEPRECATED: This script is no longer used by run_all.py
The database now persists data between runs.

If you need to reset the database manually, you can:
1. Delete the medical_risk.db file
2. Run: python scripts/seed_demo_data.py

Or use the create_tables() function directly from api.database
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


if __name__ == "__main__":
    print("[DEPRECATED] This script is no longer used.")
    print("Database now persists between runs.")
    print("\nTo manually reset the database:")
    print("  1. Delete medical_risk.db file")
    print("  2. Run: python scripts/seed_demo_data.py")
    sys.exit(0)
