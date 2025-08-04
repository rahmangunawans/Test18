#!/usr/bin/env python3
"""
Test script untuk memastikan basic scraping endpoint berfungsi
"""
import requests
import json

def test_basic_scraping():
    url = "http://localhost:5000/admin/api/scrape-basic"
    data = {
        "iqiyi_url": "https://www.iq.com/play/super-cube-115bxuuq7eo?lang=en_us",
        "batch_size": 15
    }
    
    try:
        # Test tanpa authentication terlebih dahulu
        response = requests.post(
            url,
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Text: {response.text[:500]}...")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ SUCCESS:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"\n❌ FAILED: {response.status_code}")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == "__main__":
    test_basic_scraping()