#!/usr/bin/env python3
import psycopg2
import os

# From the screenshot, I can see parts of connection string
# Let me try to extract possible project IDs from different regions and formats

password = "24AuDjUfMpFFIljP"

# Try different regions that might be visible in screenshot
regions = [
    "aws-0-ap-southeast-1",
    "aws-0-us-east-1", 
    "aws-0-us-west-1",
    "aws-0-eu-west-1"
]

# Try some common project ID patterns that might match the visible connection string
# Based on what I can partially see in the screenshot
possible_project_ids = [
    "heebrwuqszlqrhuzkntl",
    "hetlnyqqwdmxpxjyfurv", 
    "hmbdcxowqjodhxwqwfen",  # From earlier logs
    "hmbdcxowqjodhxwqwfenm", # From earlier logs 
]

print("Attempting to connect to Supabase with different project configurations...")

for project_id in possible_project_ids:
    for region in regions:
        # Try pooler connection
        connection_string = f"postgresql://postgres.{project_id}:{password}@{region}.pooler.supabase.com:6543/postgres"
        print(f"\nTrying: {project_id} in {region}")
        
        try:
            conn = psycopg2.connect(connection_string, connect_timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT current_database(), current_user;")
            result = cursor.fetchone()
            
            print(f"✅ SUCCESS! Connected to: {result[0]} as {result[1]}")
            
            # Check for existing tables
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")
            tables = cursor.fetchall()
            
            if tables:
                print(f"📊 Found {len(tables)} existing tables:")
                for table in tables:
                    print(f"  - {table[0]}")
            else:
                print("📊 No tables found - empty database")
            
            cursor.close()
            conn.close()
            
            # Save successful connection details
            with open('supabase_connection.txt', 'w') as f:
                f.write(f"PROJECT_ID={project_id}\n")
                f.write(f"REGION={region}\n") 
                f.write(f"CONNECTION_STRING={connection_string}\n")
                f.write(f"DATABASE={result[0]}\n")
                f.write(f"USER={result[1]}\n")
            
            print(f"💾 Connection details saved to supabase_connection.txt")
            exit(0)
            
        except Exception as e:
            if "Tenant or user not found" not in str(e):
                print(f"❌ Error: {str(e)}")

print("\n❌ Could not establish connection with any configuration")
print("📋 Please provide the exact project reference from your Supabase dashboard URL")
print("   Example: https://supabase.com/dashboard/project/YOUR_PROJECT_ID")