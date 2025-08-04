import requests
import json
import re
import os
import time
from urllib.parse import urlparse, parse_qs
import logging

class IQiyiM3U8Fetcher:
    def __init__(self):
        self.session = requests.Session()
        # Headers yang mirip dengan referensi
        self.session.headers.update({
            'Accept': 'application/json, text/javascript',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,ru;q=0.6',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Origin': 'https://www.iqiyi.com',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        })
    
    def fetch_dash_data(self, dash_url):
        """Fetch DASH data and try to parse JSON response"""
        logging.info("🔍 Fetching DASH data...")
        
        try:
            start_time = time.time()
            response = self.session.get(dash_url, timeout=30)
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            logging.info(f"📡 Response: Status {response.status_code}, Time: {int(response_time)}ms")
            
            if response.status_code == 200:
                # Try to parse as JSON first (like in reference)
                try:
                    json_data = response.json()
                    logging.info("✅ Got JSON response!")
                    return json_data, response.text
                except json.JSONDecodeError:
                    logging.info("⚠️  Response is not JSON, trying text parsing...")
                    return None, response.text
            else:
                logging.error(f"❌ HTTP Error: {response.status_code}")
                return None, None
                
        except requests.RequestException as e:
            logging.error(f"❌ Request failed: {e}")
            return None, None
    
    def extract_m3u8_from_json(self, json_data):
        """Extract M3U8 data from JSON response (based on reference logic)"""
        if not json_data:
            return None
            
        logging.info("🔍 Searching for M3U8 data in JSON...")
        
        try:
            # Logic dari referensi: check data.program.video[0] dan video[1]
            if "data" in json_data and "program" in json_data["data"]:
                program = json_data["data"]["program"]
                
                if "video" in program and isinstance(program["video"], list):
                    videos = program["video"]
                    
                    # Check video[0]
                    if len(videos) > 0 and "m3u8" in videos[0]:
                        logging.info("✅ Found M3U8 in video[0]!")
                        return videos[0]["m3u8"]
                    
                    # Check video[1]
                    if len(videos) > 1 and "m3u8" in videos[1]:
                        logging.info("✅ Found M3U8 in video[1]!")
                        return videos[1]["m3u8"]
            
            # Alternative paths to search for M3U8
            def search_m3u8_recursive(obj, path=""):
                """Recursively search for M3U8 data in JSON"""
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if key == "m3u8" and isinstance(value, str) and "#EXTM3U" in value:
                            logging.info(f"✅ Found M3U8 at: {path}.{key}")
                            return value
                        elif isinstance(value, (dict, list)):
                            result = search_m3u8_recursive(value, f"{path}.{key}")
                            if result:
                                return result
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        result = search_m3u8_recursive(item, f"{path}[{i}]")
                        if result:
                            return result
                return None
            
            # Search recursively if standard paths failed
            m3u8_data = search_m3u8_recursive(json_data)
            if m3u8_data:
                return m3u8_data
                
        except Exception as e:
            logging.error(f"❌ Error parsing JSON: {e}")
        
        logging.info("❌ No M3U8 data found in JSON")
        return None
    
    def extract_m3u8_from_text(self, text_response):
        """Try to extract M3U8 from text response"""
        logging.info("🔍 Searching for M3U8 in text response...")
        
        # Look for M3U8 content patterns
        m3u8_patterns = [
            r'#EXTM3U.*?(?=#EXTM3U|\Z)',  # Complete M3U8 blocks
            r'"m3u8":\s*"([^"]*#EXTM3U[^"]*)"',  # JSON embedded M3U8
            r"'m3u8':\s*'([^']*#EXTM3U[^']*)'",  # Single quotes
        ]
        
        for pattern in m3u8_patterns:
            matches = re.findall(pattern, text_response, re.DOTALL | re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                if "#EXTM3U" in match:
                    logging.info("✅ Found M3U8 in text!")
                    return match.replace('\\n', '\n').replace('\\"', '"')
        
        logging.info("❌ No M3U8 found in text")
        return None
    
    def analyze_url_params(self, url):
        """Analyze URL parameters"""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        flat_params = {k: v[0] if v else '' for k, v in params.items()}
        
        logging.info("📊 URL Parameters analyzed")
        return flat_params

def extract_m3u8_from_dash_url(dash_url):
    """Main function to extract M3U8 from DASH URL"""
    fetcher = IQiyiM3U8Fetcher()
    
    logging.info("🎬 Starting M3U8 extraction from DASH URL")
    
    # Analyze parameters
    params = fetcher.analyze_url_params(dash_url)
    
    # Fetch DASH data
    json_data, text_response = fetcher.fetch_dash_data(dash_url)
    
    # Check for API errors first
    if json_data:
        # Handle iQiyi API error responses
        if json_data.get('code') and str(json_data.get('code')) != '0':
            error_code = json_data.get('code')
            error_msg = json_data.get('msg', 'Unknown error')
            
            if error_code == 'A00020':
                logging.error(f"❌ DASH URL expired: {error_msg}")
                return {
                    'success': False,
                    'error': 'DASH URL has expired (Time expired)',
                    'error_type': 'expired_url',
                    'suggestion': 'URL needs to be refreshed from iQiyi page',
                    'api_response': json_data
                }
            else:
                logging.error(f"❌ iQiyi API error: {error_code} - {error_msg}")
                return {
                    'success': False,
                    'error': f'iQiyi API error: {error_msg} (Code: {error_code})',
                    'error_type': 'api_error',
                    'api_response': json_data
                }
        
        # Try to extract M3U8 from successful response
        m3u8_content = fetcher.extract_m3u8_from_json(json_data)
        if m3u8_content:
            logging.info("✅ SUCCESS: M3U8 extracted from JSON!")
            return {
                'success': True,
                'm3u8_content': m3u8_content,
                'method': 'json',
                'raw_data': json_data
            }
    
    # Method 2: Try to extract from text response
    if text_response:
        m3u8_content = fetcher.extract_m3u8_from_text(text_response)
        if m3u8_content:
            logging.info("✅ SUCCESS: M3U8 extracted from text!")
            return {
                'success': True,
                'm3u8_content': m3u8_content,
                'method': 'text',
                'raw_data': text_response
            }
    
    logging.error("❌ No M3U8 found in response")
    return {
        'success': False,
        'error': 'No M3U8 data found in DASH response',
        'raw_data': text_response or json_data
    }

# Test function
def test_extraction():
    """Test the extraction with provided DASH URL"""
    dash_url = "https://cache.video.iqiyi.com/dash?tvid=3672014441006600&bid=200&ds=1&vid=abe2c4788688b54418ebe6a4119bf1a5&src=01010031010018000000&vt=0&rs=1&uid=0&ori=pcw&ps=0&k_uid=4d8239f8e7e86acec9b8e4892c783a6b&pt=0&d=1&s=&lid=&slid=0&cf=&ct=&authKey=42137e8b905ab43deed845db376fc327&k_tag=1&ost=0&ppt=0&dfp=&prio=%7B%22ff%22%3A%22f4v%22%2C%22code%22%3A2%7D&k_err_retries=0&up=&su=2&applang=en_us&sver=2&X-USER-MODE=&qd_v=2in&tm=1753933550332&k_ft1=2748779069572&k_ft4=1572868&k_ft7=4&k_ft5=16777217&bop=%7B%22version%22%3A%2210.0%22%2C%22dfp%22%3A%22%22%2C%22b_ft1%22%3A0%7D&ut=0&vf=eb938fe2c3514da11e2f2c3ebd1c614b"
    
    result = extract_m3u8_from_dash_url(dash_url)
    
    if result['success']:
        print("🎉 M3U8 BERHASIL DIEKSTRAK!")
        print(f"Method: {result['method']}")
        print(f"M3U8 Length: {len(result['m3u8_content'])} characters")
        print("First 200 characters:")
        print(result['m3u8_content'][:200])
    else:
        print("❌ Ekstraksi gagal:")
        print(result['error'])
    
    return result

if __name__ == "__main__":
    test_extraction()