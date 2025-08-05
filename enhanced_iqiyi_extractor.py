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
            'cookie': 'QC005=91f7468819d6389e92fbfb26249b03dd; lang=id_id; mod=id; random-uuid=c98c16f1580c43719fb6d49b7dc52a27; QC173=0; b_ext_ip=182.3.45.217; QC006=63e3cc4c1d047e08d11aa4bc4b77f582; _ga=GA1.1.159462571.1754163381; _gcl_au=1.1.1813734661.1754163407; QC007=DIRECT; QC008=1754163385.1754164853.1754170808.12; nu=0; adcookie=1; ak_bmsc=D4E573C2962F91863C13C51E11157C77~000000000000000000000000000000~YAAQC7QRYDHPZD2YAQAA9F26bBw7iPwXvR8eMqoUK7TPKzrVu3aHRZbAgQtdt33pHEODonkJMxSf15OOl9U/JNLaeJmBnkOw2pNLuoRtiBAvIJd3fuvZjxX+lRxSskGh+hJ10siS7M0kPMFsg4TwZJ2142i+m3Spf65VTZLS86bSOllN0gYZBKtjngtBFZ/2M+5iKbiR0+huR3iB8DY/0R6kJd1Jrre/Vv6j5Db3L5Hklw//GgCwzaCMa7C63SrqXMIyWmtFePgnf2VY5k/9WRkEhHaFpl8X9xrK2KyDGkJH/yxIvLBTORPQD5ohi+1UrhFLKhWxdGyO73f2a3AeSymGnjgxkkt2W2GlG+GNXkTbVIzKyIAlDirXj6hzf5TXadDgMtk=; QiyiPlayerSupported=%7B%22v%22%3A3%2C%22dp%22%3A1%2C%22dm%22%3A%7B%22wv%22%3A1%7D%2C%22m%22%3A%7B%22wm-vp9%22%3A1%2C%22wm-av1%22%3A1%7D%2C%22hvc%22%3Atrue%7D; QCVtype=; intl_playbackRate=1; QiyiPlayerVD=5; QiyiPlayerBID=600; I00040=CnhUVXBRYzFWUmEza3ZSamxYVmpKeFlqWjVlRU5wUXpSdVltMVRVSE5ZVFVGSWRsZDBiR1o2T0hrM0wwUnJOa0ZRWmpCa1dqRlJkVVZzZGpOdWEySk9UV2cxUjNoR01sZ3lOVU5qT0RsbGRsbFJTWGx0WmxFOVBRPT0QqgNQIGIgOTFmNzQ2ODgxOWQ2Mzg5ZTkyZmJmYjI2MjQ5YjAzZGR6P2h0dHBzOi8vcGFzc3BvcnQuaXEuY29tL2ludGwvdGhpcmRwYXJ0eS9jYWxsYmFjay5hY3Rpb24%2FZnJvbT0zMqoBFDAxMDEwMDMxMDEwMDE4MDAwMDAw4gE8aHR0cHM6Ly93d3cuaXEuY29tL2ludGwtY29tbW9uL2ludGxfdGhpcmRwYXJ0eV90cmFuc2Zlci5odG1s6gEBMQ%3D%3D; __dfp=e01b5e74016c8a49df92d9f41954ee2ebeb3468856d7cb0aa9c41724c07748da54@1755459402609@1754163403609; abtest=%7B%22pcw_play_comment%22%3A%228546_A%2C8706_C%22%7D; _ga_VTJGB1PRBJ=GS2.1.s1754170811$o2$g1$t1754172283$j9$l0$h0; _ga_PCTZRE9688=GS2.1.s1754170811$o2$g1$t1754172283$j9$l0$h0; QC010=4815159; bm_sv=F7B2885772414DD94539BAB5C0B0CD6C~YAAQpOQ+F2sHgGaYAQAA1OvQbBzBJ8y19XmwbBMXmqy+fNMgMLp2LVZphHQ5XmaSqxd1kOns9aLDt8FbMVGRn+LdIeeI1rtpP8lVaQzhYvTr0LeCMOr778mpIfedOwzo5UH8mo371pBQPop4oLNMTNreIkdoEEXyuAPb5Of7UGoekxZ9ZQJeQmgFAXqSOFCAiOITVg6deFX+kafjJ87WsPaOMqZVrETlw1YQoW4eokNzkCGYPFWLOGY1o0rd~1',
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