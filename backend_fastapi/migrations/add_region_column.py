"""
Migration script to add region column to forecasting_pricehistory table.
Run this script to update the database schema.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from core.database import SessionLocal

def migrate_up():
    """Add region column to forecasting_pricehistory table"""
    db = SessionLocal()
    try:
        # Check if column already exists
        result = db.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='forecasting_pricehistory' AND column_name='region'
        """))
        
        if result.fetchone():
            print("✓ Column 'region' already exists in forecasting_pricehistory table")
            return
        
        # Add the region column
        db.execute(text("""
            ALTER TABLE forecasting_pricehistory
            ADD COLUMN region VARCHAR(1)
        """))
        db.commit()
        print("✓ Successfully added 'region' column to forecasting_pricehistory table")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        db.close()


def migrate_down():
    """Remove region column from forecasting_pricehistory table (rollback)"""
    db = SessionLocal()
    try:
        db.execute(text("""
            ALTER TABLE forecasting_pricehistory
            DROP COLUMN IF EXISTS region
        """))
        db.commit()
        print("✓ Successfully removed 'region' column from forecasting_pricehistory table")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Rollback failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "down":
        migrate_down()
    else:
        migrate_up()
