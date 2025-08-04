# Enhanced IQiyi M3U8 Extractor based on mainx.py reference
import json
import requests
import re
import logging
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any

class EnhancedIQiyiExtractor:
    """Enhanced IQiyi extractor using mainx.py methodology"""
    
    def __init__(self):
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
        }
        self.session = requests.Session()
        
    def _request(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """Enhanced request method with better error handling"""
        try:
            kwargs.setdefault('headers', self.headers)
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except Exception as e:
            logging.error(f'❌ Error making request to {url}: {str(e)}')
            return None

    def get_player_data(self, play_url: str) -> Optional[Dict[str, Any]]:
        """Get player data from __NEXT_DATA__ script tag like mainx.py"""
        logging.info(f"🔍 Fetching player data from: {play_url}")
        
        response = self._request('get', play_url)
        if not response:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        script_tag = soup.find('script', {'id': '__NEXT_DATA__'})

        if not script_tag:
            logging.warning("❌ No __NEXT_DATA__ script tag found")
            return None

        try:
            json_data = script_tag.string.strip()
            player_data = json.loads(json_data)
            logging.info("✅ Player data loaded successfully")
            return player_data
        except json.JSONDecodeError as e:
            logging.error(f"❌ Error parsing JSON data: {e}")
            return None

    def extract_dash_query(self, player_data: Dict[str, Any]) -> Optional[str]:
        """Extract DASH query from player data using mainx.py method"""
        logging.info("🔍 Extracting DASH query from player data...")
        
        try:
            # Navigate to ssrlog like in mainx.py
            ssrlog = player_data.get('props', {}).get('initialProps', {}).get('pageProps', {}).get('prePlayerData', {}).get('ssrlog', '')
            
            if not ssrlog:
                logging.warning("❌ No ssrlog found in player data")
                return None
            
            # Use regex pattern from mainx.py to extract DASH URL
            url_pattern = r'http://intel-cache\.video\.qiyi\.domain/dash\?([^\s]+)'
            urls = re.findall(url_pattern, ssrlog)
            
            if urls:
                dash_query = urls[0]
                logging.info(f"✅ DASH query extracted: {dash_query[:100]}...")
                return dash_query
            else:
                logging.warning("❌ No DASH URL found in ssrlog")
                return None
                
        except Exception as e:
            logging.error(f"❌ Error extracting DASH query: {e}")
            return None

    def get_m3u8_from_dash(self, dash_query: str) -> Optional[str]:
        """Get M3U8 content from DASH query using mainx.py method"""
        logging.info("🔍 Getting M3U8 from DASH query...")
        
        dash_url = f'https://cache.video.iqiyi.com/dash?{dash_query}'
        response = self._request('get', dash_url)
        
        if not response:
            return None
            
        try:
            data = response.json()
            
            # Check for API errors first
            if data.get('code') != 'A00000':
                error_code = data.get('code')
                error_msg = data.get('msg', 'Unknown error')
                logging.error(f"❌ iQiyi API error: {error_code} - {error_msg}")
                
                if error_code == 'A00020':
                    return f"ERROR_EXPIRED:{error_msg}"
                else:
                    return f"ERROR_API:{error_msg}"
            
            # Extract M3U8 content like mainx.py
            video_data = data.get('data', {}).get('program', {}).get('video', [])
            
            for video_item in video_data:
                if 'm3u8' in video_item and video_item['m3u8']:
                    m3u8_content = video_item['m3u8']
                    logging.info(f"✅ M3U8 content found: {len(m3u8_content)} characters")
                    return m3u8_content
            
            logging.warning("❌ No M3U8 content found in video data")
            return None
            
        except Exception as e:
            logging.error(f"❌ Error parsing DASH response: {e}")
            return None

def extract_m3u8_enhanced(play_url: str) -> Dict[str, Any]:
    """Main enhanced extraction function based on mainx.py methodology"""
    extractor = EnhancedIQiyiExtractor()
    
    logging.info("🎬 Starting enhanced M3U8 extraction (mainx.py method)")
    
    # Step 1: Get player data from page
    player_data = extractor.get_player_data(play_url)
    if not player_data:
        return {
            'success': False,
            'error': 'Could not load player data from iQiyi page',
            'method': 'enhanced_extraction'
        }
    
    # Step 2: Extract DASH query from ssrlog
    dash_query = extractor.extract_dash_query(player_data)
    if not dash_query:
        return {
            'success': False,
            'error': 'Could not extract DASH query from player data',
            'method': 'enhanced_extraction'
        }
    
    # Step 3: Get M3U8 from DASH API
    m3u8_result = extractor.get_m3u8_from_dash(dash_query)
    if not m3u8_result:
        return {
            'success': False,
            'error': 'No M3U8 content found in DASH response',
            'method': 'enhanced_extraction'
        }
    
    # Check for API errors
    if m3u8_result.startswith('ERROR_'):
        error_type, error_msg = m3u8_result.split(':', 1)
        if error_type == 'ERROR_EXPIRED':
            return {
                'success': False,
                'error': 'DASH URL has expired (Time expired)',
                'error_type': 'expired_url',
                'suggestion': 'URL needs to be refreshed from iQiyi page',
                'method': 'enhanced_extraction'
            }
        else:
            return {
                'success': False,
                'error': f'iQiyi API error: {error_msg}',
                'error_type': 'api_error',
                'method': 'enhanced_extraction'
            }
    
    # Success!
    return {
        'success': True,
        'm3u8_content': m3u8_result,
        'method': 'enhanced_extraction',
        'dash_query': dash_query
    }