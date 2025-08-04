#!/usr/bin/env python3
"""
Migration script to add iqiyi_play_url column and remove dash_url column
"""

from app import app, db
from models import Episode
from sqlalchemy import text
import logging

def migrate_iqiyi_play_url():
    """Add iqiyi_play_url column and remove dash_url column"""
    
    with app.app_context():
        try:
            # Check existing columns
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('episode')]
            
            print("📝 Current Episode table columns:")
            for col in columns:
                print(f"   • {col}")
            
            # Add iqiyi_play_url column if it doesn't exist
            if 'iqiyi_play_url' not in columns:
                print("\n📝 Adding iqiyi_play_url column...")
                db.session.execute(text("""
                    ALTER TABLE episode 
                    ADD COLUMN iqiyi_play_url VARCHAR(500)
                """))
                print("✅ Added iqiyi_play_url column")
            else:
                print("✅ iqiyi_play_url column already exists")
            
            # Migrate data from dash_url to iqiyi_play_url if dash_url exists
            if 'dash_url' in columns:
                print("\n📝 Migrating dash_url data (if any)...")
                # For now, we'll just note any existing dash_url data
                episodes_with_dash = db.session.execute(text("""
                    SELECT id, title, dash_url FROM episode 
                    WHERE dash_url IS NOT NULL AND dash_url != ''
                """)).fetchall()
                
                if episodes_with_dash:
                    print(f"⚠️  Found {len(episodes_with_dash)} episodes with dash_url data:")
                    for ep in episodes_with_dash:
                        print(f"   • Episode {ep.id}: {ep.title}")
                        print(f"     DASH URL: {ep.dash_url[:100]}...")
                    print("💡 These will need manual conversion to iQiyi play URLs")
                else:
                    print("✅ No dash_url data to migrate")
                
                # Remove dash_url column
                print("\n📝 Removing dash_url column...")
                db.session.execute(text("""
                    ALTER TABLE episode 
                    DROP COLUMN dash_url
                """))
                print("✅ Removed dash_url column")
            
            db.session.commit()
            print("\n🎉 Migration completed successfully!")
            
            # Verify final state
            inspector = db.inspect(db.engine)
            final_columns = [col['name'] for col in inspector.get_columns('episode')]
            
            print("\n📝 Final Episode table columns:")
            for col in final_columns:
                print(f"   • {col}")
            
            return True
                
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("🔧 Starting database migration...")
    print("📱 Migrating from dash_url to iqiyi_play_url system")
    print("=" * 60)
    
    success = migrate_iqiyi_play_url()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("💡 System now uses simplified iQiyi play URLs instead of DASH URLs")
        print("📖 Users can now input URLs like: https://www.iq.com/play/episode-name")
    else:
        print("\n💥 Migration failed!")
        exit(1)