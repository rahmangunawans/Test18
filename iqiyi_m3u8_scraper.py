"""
IQiyi M3U8 Scraper - Direct M3U8 extraction from DASH URLs
Fixed approach based on working reference
"""

import requests
import json
import re
import logging
from urllib.parse import urlparse, parse_qs

class IQiyiM3U8Scraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json, text/javascript, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Origin': 'https://www.iqiyi.com',
            'Pragma': 'no-cache',
            'Referer': 'https://www.iqiyi.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        })
    
    def extract_m3u8_from_dash_url(self, dash_url):
        """Extract M3U8 URL from iQiyi DASH API endpoint"""
        logging.info(f"🔍 Extracting M3U8 from DASH URL: {dash_url}")
        
        try:
            # Get DASH data
            response = self.session.get(dash_url, timeout=30)
            
            if response.status_code != 200:
                logging.error(f"❌ DASH API failed: {response.status_code}")
                return None
            
            # Check if response is JSON
            try:
                data = response.json()
                logging.info("✅ Got JSON response from DASH API")
                
                # Extract M3U8 from JSON structure
                m3u8_url = self._extract_m3u8_from_json(data)
                if m3u8_url:
                    return m3u8_url
                    
            except json.JSONDecodeError:
                logging.info("⚠️ Response is not JSON, trying direct M3U8 extraction...")
                
            # Try direct M3U8 extraction from response text
            return self._extract_m3u8_from_text(response.text)
            
        except Exception as e:
            logging.error(f"❌ Error extracting M3U8: {str(e)}")
            return None
    
    def _extract_m3u8_from_json(self, data):
        """Extract M3U8 URL from JSON response structure"""
        try:
            # Check data.program.video[] array for M3U8 content
            if "data" in data and "program" in data["data"]:
                program = data["data"]["program"]
                
                if "video" in program and isinstance(program["video"], list):
                    videos = program["video"]
                    
                    # Check all video entries for M3U8 content
                    for i, video in enumerate(videos):
                        if "m3u8" in video:
                            m3u8_content = video["m3u8"]
                            logging.info(f"✅ Found M3U8 in video[{i}]: {len(m3u8_content)} chars")
                            
                            # Check if it's a direct M3U8 playlist
                            if m3u8_content.startswith("#EXTM3U"):
                                # Convert to blob URL for direct playback
                                return self._create_m3u8_blob_url(m3u8_content)
                            elif m3u8_content.startswith("http"):
                                # Direct M3U8 URL
                                return m3u8_content
                                
                        # Check dm3u8 field as alternative
                        if "dm3u8" in video:
                            dm3u8_content = video["dm3u8"]
                            logging.info(f"✅ Found dM3U8 in video[{i}]: {len(dm3u8_content)} chars")
                            
                            if dm3u8_content.startswith("#EXTM3U"):
                                return self._create_m3u8_blob_url(dm3u8_content)
                            elif dm3u8_content.startswith("http"):
                                return dm3u8_content
            
            logging.warning("⚠️ No M3U8 content found in JSON structure")
            return None
            
        except Exception as e:
            logging.error(f"❌ Error parsing JSON for M3U8: {str(e)}")
            return None
    
    def _extract_m3u8_from_text(self, text):
        """Extract M3U8 content from response text"""
        try:
            # Look for M3U8 playlist content
            if "#EXTM3U" in text:
                # Find M3U8 playlist content
                m3u8_match = re.search(r'(#EXTM3U.*?)(?=\n\n|\Z)', text, re.DOTALL)
                if m3u8_match:
                    m3u8_content = m3u8_match.group(1)
                    logging.info(f"✅ Extracted M3U8 from text: {len(m3u8_content)} chars")
                    return self._create_m3u8_blob_url(m3u8_content)
            
            # Look for M3U8 URLs in text
            m3u8_url_pattern = r'https?://[^\s"\']*\.m3u8[^\s"\']*'
            m3u8_urls = re.findall(m3u8_url_pattern, text)
            
            if m3u8_urls:
                logging.info(f"✅ Found {len(m3u8_urls)} M3U8 URLs in text")
                return m3u8_urls[0]  # Return first found URL
            
            logging.warning("⚠️ No M3U8 content found in response text")
            return None
            
        except Exception as e:
            logging.error(f"❌ Error extracting M3U8 from text: {str(e)}")
            return None
    
    def _create_m3u8_blob_url(self, m3u8_content):
        """Create a data URL for M3U8 content (for client-side blob creation)"""
        # Return the M3U8 content for client-side blob URL creation
        return f"data:application/vnd.apple.mpegurl;base64,{self._encode_base64(m3u8_content)}"
    
    def _encode_base64(self, content):
        """Encode content to base64"""
        import base64
        return base64.b64encode(content.encode('utf-8')).decode('utf-8')

# Test function
def test_m3u8_extraction():
    """Test M3U8 extraction with sample DASH URL"""
    scraper = IQiyiM3U8Scraper()
    
    # Sample DASH URL for testing
    dash_url = "https://cache-video.iqiyi.com/dash?..."
    
    m3u8_url = scraper.extract_m3u8_from_dash_url(dash_url)
    
    if m3u8_url:
        print(f"✅ M3U8 extracted successfully: {m3u8_url[:100]}...")
        return m3u8_url
    else:
        print("❌ Failed to extract M3U8")
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_m3u8_extraction()