#!/usr/bin/env python3
import psycopg2
import os

# Test different Supabase connection formats
password = "24AuDjUfMpFFIljP"

# Different possible project references from screenshot analysis
project_refs = [
    "heebrwuqszlqrhuzkntl",  # From URL bar
    "hetlnyqqwdmxpxjyfurv",  # From connection string visible
]

# Different connection formats to try
connection_formats = [
    "postgresql://postgres.{project}:{password}@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres",
    "postgresql://postgres:{password}@db.{project}.supabase.co:5432/postgres",
    "postgresql://postgres.{project}:{password}@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres",
]

print("Testing Supabase connections...")

for project_ref in project_refs:
    print(f"\n=== Testing project: {project_ref} ===")
    for format_template in connection_formats:
        connection_string = format_template.format(project=project_ref, password=password)
        print(f"Trying: {connection_string.replace(password, 'PASSWORD_HIDDEN')}")
        
        try:
            conn = psycopg2.connect(connection_string, connect_timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT current_database(), current_user, version();")
            result = cursor.fetchone()
            print(f"✅ SUCCESS! Database: {result[0]}, User: {result[1]}")
            
            # Test if tables exist
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
            tables = cursor.fetchall()
            print(f"📊 Found {len(tables)} tables: {[t[0] for t in tables]}")
            
            cursor.close()
            conn.close()
            
            # Save successful connection
            with open('supabase_success.txt', 'w') as f:
                f.write(f"PROJECT_REF={project_ref}\n")
                f.write(f"CONNECTION_STRING={connection_string}\n")
            print(f"💾 Saved successful connection to supabase_success.txt")
            break
            
        except Exception as e:
            print(f"❌ Failed: {str(e)}")
    else:
        continue
    break
else:
    print("\n❌ All connection attempts failed")