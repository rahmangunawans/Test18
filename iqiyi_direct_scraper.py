#!/usr/bin/env python3
"""
Direct iQiyi DASH URL scraper
Extracts actual DASH URLs from iQiyi play pages
"""

import requests
import re
import json
import logging
from urllib.parse import unquote

def extract_dash_url_from_play_page(play_url):
    """
    Extract DASH URL directly from iQiyi play page
    
    Args:
        play_url (str): iQiyi play URL
        
    Returns:
        dict: Result with success status and DASH URL
    """
    try:
        logging.info(f"🔍 Extracting DASH URL from play page: {play_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        # Get the page content
        response = requests.get(play_url, headers=headers, timeout=15)
        response.raise_for_status()
        content = response.text
        
        logging.info(f"📄 Page content loaded, size: {len(content)} characters")
        
        # Method 1: Look for direct DASH URLs in various formats
        dash_patterns = [
            # Standard DASH cache URLs
            r'https://cache\.video\.iqiyi\.com/dash\?[^"\'<>\s]+',
            # Alternative DASH URLs
            r'https://[^"\'<>\s]*\.iqiyi\.com/[^"\'<>\s]*dash[^"\'<>\s]*',
            # JSON embedded DASH URLs
            r'"dash_url":\s*"([^"]+)"',
            r'"dashUrl":\s*"([^"]+)"',
            r'"url":\s*"(https://[^"]*dash[^"]*)"'
        ]
        
        for i, pattern in enumerate(dash_patterns):
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                dash_url = matches[0]
                if isinstance(dash_url, tuple):
                    dash_url = dash_url[0] if dash_url[0] else dash_url[1]
                
                # Decode URL if needed
                dash_url = unquote(dash_url)
                
                logging.info(f"✅ Found DASH URL with pattern {i+1}: {dash_url[:100]}...")
                return {
                    'success': True,
                    'dash_url': dash_url,
                    'method': f'pattern_{i+1}',
                    'source': 'direct_page_scraping'
                }
        
        # Method 2: Look for embedded video configuration
        video_config_patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
            r'window\.Q\s*=\s*({.+?});',
            r'playerConfig\s*[=:]\s*({.+?})[,;]',
            r'videoInfo\s*[=:]\s*({.+?})[,;]'
        ]
        
        for pattern in video_config_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches:
                try:
                    config = json.loads(match)
                    dash_url = find_dash_in_config(config)
                    if dash_url:
                        logging.info(f"✅ Found DASH URL in config: {dash_url[:100]}...")
                        return {
                            'success': True,
                            'dash_url': dash_url,
                            'method': 'config_extraction',
                            'source': 'video_config'
                        }
                except json.JSONDecodeError:
                    continue
        
        # Method 3: Look for API endpoints that might return DASH URLs
        api_patterns = [
            r'(/api/[^"\'<>\s]*video[^"\'<>\s]*)',
            r'(/[^"\'<>\s]*dash[^"\'<>\s]*\.json)',
            r'(https://[^"\'<>\s]*api[^"\'<>\s]*video[^"\'<>\s]*)'
        ]
        
        for pattern in api_patterns:
            matches = re.findall(pattern, content)
            if matches:
                api_url = matches[0]
                if not api_url.startswith('http'):
                    api_url = 'https://www.iq.com' + api_url
                
                try:
                    api_response = requests.get(api_url, headers=headers, timeout=10)
                    if api_response.status_code == 200:
                        api_data = api_response.json()
                        dash_url = find_dash_in_config(api_data)
                        if dash_url:
                            logging.info(f"✅ Found DASH URL via API: {dash_url[:100]}...")
                            return {
                                'success': True,
                                'dash_url': dash_url,
                                'method': 'api_extraction',
                                'source': 'api_endpoint'
                            }
                except:
                    continue
        
        # No DASH URL found
        logging.warning("❌ No DASH URL found in page content")
        return {
            'success': False,
            'error': 'No DASH URL found in play page',
            'details': 'Page content does not contain extractable DASH URLs'
        }
        
    except requests.RequestException as e:
        logging.error(f"❌ Network error: {e}")
        return {
            'success': False,
            'error': f'Network error: {str(e)}',
            'details': 'Could not fetch play page content'
        }
    except Exception as e:
        logging.error(f"❌ Unexpected error: {e}")
        return {
            'success': False,
            'error': f'Extraction error: {str(e)}',
            'details': 'Unexpected error during DASH URL extraction'
        }

def find_dash_in_config(config, path=""):
    """
    Recursively search for DASH URL in configuration object
    
    Args:
        config: Configuration object (dict, list, or primitive)
        path: Current path for logging
        
    Returns:
        str: DASH URL if found, None otherwise
    """
    if isinstance(config, dict):
        # Check direct keys
        for key in ['dash_url', 'dashUrl', 'dash', 'url', 'stream_url', 'video_url']:
            if key in config and isinstance(config[key], str):
                if 'dash' in config[key].lower() and 'iqiyi.com' in config[key]:
                    return config[key]
        
        # Recursively search in nested objects
        for key, value in config.items():
            if key in ['video', 'player', 'stream', 'media', 'content']:
                result = find_dash_in_config(value, f"{path}.{key}")
                if result:
                    return result
                    
    elif isinstance(config, list):
        for i, item in enumerate(config):
            result = find_dash_in_config(item, f"{path}[{i}]")
            if result:
                return result
    
    return None

if __name__ == "__main__":
    # Test with Super Cube episode
    test_url = "https://www.iq.com/play/super-cube-episode-1-11eihk07dr8?lang=en_us"
    
    logging.basicConfig(level=logging.INFO)
    result = extract_dash_url_from_play_page(test_url)
    
    print("=" * 60)
    print("DASH URL EXTRACTION TEST")
    print("=" * 60)
    print(f"URL: {test_url}")
    print(f"Success: {result.get('success')}")
    
    if result.get('success'):
        print(f"Method: {result.get('method')}")
        print(f"Source: {result.get('source')}")
        print(f"DASH URL: {result.get('dash_url')}")
    else:
        print(f"Error: {result.get('error')}")
        print(f"Details: {result.get('details')}")