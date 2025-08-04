#!/usr/bin/env python3
"""
Migration script to add dash_url column to Episode table
"""

from app import app, db
from models import Episode
from sqlalchemy import text
import logging

def add_dash_url_column():
    """Add dash_url column to Episode table if it doesn't exist"""
    
    with app.app_context():
        try:
            # Check if column already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('episode')]
            
            if 'dash_url' in columns:
                print("✅ dash_url column already exists in Episode table")
                return True
            
            print("📝 Adding dash_url column to Episode table...")
            
            # Add the column using raw SQL
            db.session.execute(text("""
                ALTER TABLE episode 
                ADD COLUMN dash_url TEXT
            """))
            
            db.session.commit()
            print("✅ Successfully added dash_url column to Episode table")
            
            # Verify the column was added
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('episode')]
            
            if 'dash_url' in columns:
                print("✅ Column verification successful")
                return True
            else:
                print("❌ Column verification failed")
                return False
                
        except Exception as e:
            print(f"❌ Error adding dash_url column: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("🔧 Starting database migration...")
    
    success = add_dash_url_column()
    
    if success:
        print("🎉 Migration completed successfully!")
    else:
        print("💥 Migration failed!")
        exit(1)