#!/usr/bin/env python3
"""
Alternative IQiyi scraper dengan approach yang lebih simple
Menggunakan basic requests tanpa SSL verification untuk menghindari handshake issues
"""
import requests
import json
import re
from typing import Dict, List, Optional

def simple_iqiyi_test(url: str = "https://www.iq.com/play/super-cube-115bxuuq7eo?lang=en_us") -> Dict:
    """
    Simple test untuk extract basic episode info dari IQiyi
    """
    print(f"🎬 Testing simple extraction for: {url}")
    
    try:
        # Very basic session
        session = requests.Session()
        session.verify = False
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Get page content
        response = session.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            content = response.text
            print(f"✅ Page loaded: {len(content)} characters")
            
            # Look for player data in script tags
            script_patterns = [
                r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
                r'window\.__NUXT__\s*=\s*({.+?});',
                r'__webpack_require__\.p\s*=\s*"([^"]+)"',
            ]
            
            for pattern in script_patterns:
                matches = re.findall(pattern, content, re.DOTALL)
                if matches:
                    print(f"✅ Found potential data with pattern: {pattern[:30]}...")
                    try:
                        # Try to parse as JSON
                        data = json.loads(matches[0])
                        print(f"✅ Successfully parsed JSON data")
                        return {
                            'success': True,
                            'data': data,
                            'method': 'simple_extraction'
                        }
                    except:
                        print(f"⚠️ Data found but not valid JSON")
                        continue
            
            # Look for episode list in HTML
            episode_patterns = [
                r'class="episode[^"]*"[^>]*>([^<]+)</.*?href="([^"]+)"',
                r'<a[^>]*href="([^"]*episode[^"]*)"[^>]*>([^<]+)</a>',
            ]
            
            episodes = []
            for pattern in episode_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                episodes.extend(matches)
            
            if episodes:
                print(f"✅ Found {len(episodes)} episodes using HTML parsing")
                return {
                    'success': True,
                    'episodes': episodes[:5],  # First 5 episodes
                    'method': 'html_parsing'
                }
            
            return {
                'success': False,
                'error': 'No episode data found in page content',
                'content_length': len(content)
            }
        else:
            return {
                'success': False,
                'error': f'HTTP {response.status_code}',
                'status_code': response.status_code
            }
            
    except requests.exceptions.SSLError as e:
        return {
            'success': False,
            'error': 'SSL_ERROR',
            'details': str(e)
        }
    except Exception as e:
        return {
            'success': False,
            'error': 'GENERAL_ERROR',
            'details': str(e)
        }

if __name__ == "__main__":
    result = simple_iqiyi_test()
    print("\n" + "="*50)
    print("RESULT:")
    print(json.dumps(result, indent=2, ensure_ascii=False))