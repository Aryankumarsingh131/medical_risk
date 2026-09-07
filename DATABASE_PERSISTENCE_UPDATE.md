# Database Persistence Update

**Date**: September 7, 2026  
**Change**: Removed `reset_tables()` function - Database now persists between runs

## What Changed

### 1. Removed Functions
- ❌ `reset_tables()` function removed from `api/database.py`
- ❌ `scripts/reset_db.py` deprecated (now shows helpful message)

### 2. Updated Files
- ✅ `run_all.py` - No longer calls `reset_db.py`
- ✅ `api/database.py` - Removed database reset function
- ✅ `scripts/reset_db.py` - Marked as deprecated with instructions

## How It Works Now

### Before (Old Behavior):
```bash
python run_all.py
# → Deleted ALL data
# → Created fresh database
# → Seeded demo accounts
```

### After (New Behavior):
```bash
python run_all.py
# → Keeps existing data
# → Only adds demo accounts if they don't exist
# → Preserves patient records, assessments, hospitals, etc.
```

## Benefits

✅ **Data Persistence** - Your data survives between runs  
✅ **No Data Loss** - Hospitals, patients, and assessments are preserved  
✅ **Idempotent Seeding** - Demo accounts are added only once  
✅ **Production Ready** - No accidental data deletion  

## Manual Database Reset (If Needed)

If you need to start fresh:

### Option 1: Delete Database File
```bash
rm medical_risk.db  # Linux/Mac
del medical_risk.db  # Windows
python run_all.py
```

### Option 2: Direct SQL
```bash
sqlite3 medical_risk.db
sqlite> DROP TABLE users;
sqlite> DROP TABLE patient_assessments;
# ... drop other tables
sqlite> .quit
python scripts/seed_demo_data.py
```

### Option 3: Python Script
```python
from api.database import Base, engine
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
```

## Seed Script Behavior

The `seed_demo_data.py` script is **idempotent**:
- ✅ Checks if admin exists before creating
- ✅ Checks if doctors exist before creating
- ✅ Updates passwords if accounts already exist
- ✅ Only creates new patients if count is low
- ✅ Skips hospital creation if they exist

## Demo Accounts

These accounts are seeded on first run (or if missing):
- **Admin**: admin@hospital.com / Demo@123
- **Doctors**: 5 specialists with Demo@123
- **Patients**: Sampled from real datasets with Demo@123

## Migration Notes

If you have existing code that calls `reset_tables()`:
1. Remove the function call
2. Manually delete the database file if fresh start is needed
3. Use `create_tables()` instead for schema creation only

## Testing

Verify the system works:
```bash
# Start the system
python run_all.py

# Verify existing data persists
# Add a hospital via admin dashboard
# Stop the system (Ctrl+C)
# Restart
python run_all.py

# Hospital should still be there ✅
```

---

**Summary**: The database now behaves like a production system - data persists between runs, and only missing demo accounts are added. This prevents accidental data loss and makes the system more robust.
