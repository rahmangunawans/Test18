#!/usr/bin/env python3
"""
Test script untuk mengecek koneksi ke IQiyi
"""
import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_iqiyi_connection():
    """Test basic connection to IQiyi"""
    test_url = "https://www.iq.com/play/super-cube-115bxuuq7eo?lang=en_us"
    
    print("🔍 Testing IQiyi connection...")
    
    # Create session with robust settings
    session = requests.Session()
    session.verify = False
    
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.5',
        'connection': 'keep-alive',
    }
    session.headers.update(headers)
    
    # Setup retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    try:
        print(f"📡 Attempting to connect to: {test_url}")
        response = session.get(test_url, timeout=30)
        
        print(f"✅ Connection successful!")
        print(f"📊 Status code: {response.status_code}")
        print(f"📏 Response length: {len(response.text)} characters")
        print(f"🔧 Content type: {response.headers.get('content-type', 'unknown')}")
        
        # Check if we got actual content
        if len(response.text) > 1000:
            print("✅ Received substantial content from IQiyi")
            return True
        else:
            print("⚠️ Received minimal content - possible blocking")
            return False
            
    except requests.exceptions.SSLError as e:
        print(f"❌ SSL Error: {e}")
        return False
    except requests.exceptions.Timeout as e:
        print(f"❌ Timeout Error: {e}")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return False

if __name__ == "__main__":
    success = test_iqiyi_connection()
    if success:
        print("\n🎯 IQiyi connection test PASSED")
    else:
        print("\n❌ IQiyi connection test FAILED")
        print("💡 This explains why scraping is failing. IQiyi may be:")
        print("   - Blocking requests from this server")
        print("   - Having temporary connection issues")
        print("   - Requiring different SSL/TLS settings")