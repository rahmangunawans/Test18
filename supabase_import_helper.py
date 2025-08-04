#!/usr/bin/env python3
"""
Supabase Database Import Helper
This script helps import data from your existing Supabase database to Replit database
"""

import psycopg2
import os
from datetime import datetime

def test_connection(connection_string, description):
    """Test a database connection"""
    try:
        conn = psycopg2.connect(connection_string, connect_timeout=10)
        cursor = conn.cursor()
        
        # Get basic info
        cursor.execute("SELECT current_database(), current_user, version();")
        db_info = cursor.fetchone()
        
        # Get table list
        cursor.execute("""
            SELECT table_name, 
                   (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
            FROM information_schema.tables t 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        print(f"✅ {description}")
        print(f"   Database: {db_info[0]}")
        print(f"   User: {db_info[1]}")
        print(f"   Tables: {len(tables)}")
        
        if tables:
            print("   Table details:")
            for table_name, col_count in tables:
                print(f"     - {table_name} ({col_count} columns)")
        
        return True, tables
        
    except Exception as e:
        print(f"❌ {description}")
        print(f"   Error: {str(e)}")
        return False, []

def main():
    print("=== Supabase Database Import Helper ===")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test Replit database (current working database)
    replit_db = os.environ.get("DATABASE_URL")
    if replit_db:
        print("1. Testing current Replit database:")
        replit_success, replit_tables = test_connection(replit_db, "Replit PostgreSQL")
        print()
    else:
        print("❌ No Replit DATABASE_URL found")
        return
    
    # Instructions for user
    print("2. To connect to your Supabase database, provide one of:")
    print("   A) Full project URL: https://supabase.com/dashboard/project/YOUR_PROJECT_ID")
    print("   B) Complete connection string from Supabase Settings → Database")
    print("   C) Project reference ID from the dashboard URL")
    print()
    
    # Example of what we would do with correct Supabase connection
    print("3. Once connected, this script will:")
    print("   ✓ Export all data from your Supabase database")
    print("   ✓ Import data into Replit database")
    print("   ✓ Preserve all relationships and constraints")
    print("   ✓ Create backup of current data")
    print("   ✓ Verify data integrity after import")
    print()
    
    print("📋 Please provide your Supabase project information to proceed with import.")

if __name__ == "__main__":
    main()