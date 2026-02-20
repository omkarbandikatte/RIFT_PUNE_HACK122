#!/usr/bin/env python3
"""
Migration script to add error_message column to agent_runs table
Run this after updating the model
"""
import os
import sys
from sqlalchemy import text, create_engine

# Get DATABASE_URL from environment or use the one in .env
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL or DATABASE_URL.startswith("file:"):
    print("❌ DATABASE_URL not set properly. Please set it to a valid PostgreSQL URL.")
    print("Example: postgresql+psycopg://user:pass@host/dbname")
    sys.exit(1)

engine = create_engine(DATABASE_URL)

def migrate():
    """Add error_message column if it doesn't exist"""
    print(f"🔧 Connecting to database...")
    with engine.connect() as conn:
        # Check if column exists
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='agent_runs' AND column_name='error_message';
        """)
        
        result = conn.execute(check_query)
        exists = result.fetchone()
        
        if not exists:
            print("Adding error_message column...")
            alter_query = text("""
                ALTER TABLE agent_runs 
                ADD COLUMN error_message TEXT;
            """)
            conn.execute(alter_query)
            conn.commit()
            print("✅ Migration completed: error_message column added")
        else:
            print("✅ Column already exists, no migration needed")

if __name__ == "__main__":
    migrate()
