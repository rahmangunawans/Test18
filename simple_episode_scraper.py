#!/usr/bin/env python3
"""
Simplified episode scraper yang hanya mengambil basic info
Tanpa M3U8 extraction untuk menghindari network issues
"""
import requests
import json
import re
from typing import Dict, List, Optional
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def scrape_basic_episodes(playlist_url: str, max_episodes: int = 5) -> Dict:
    """
    Scrape basic episode information tanpa M3U8 extraction
    """
    print(f"🎬 Scraping basic episode info from: {playlist_url}")
    print(f"📊 Maximum episodes: {max_episodes}")
    
    try:
        # Simple session setup
        session = requests.Session()
        session.verify = False
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        session.headers.update(headers)
        
        # Get main page
        print("📡 Fetching playlist page...")
        response = session.get(playlist_url, timeout=30)
        response.raise_for_status()
        
        content = response.text
        print(f"✅ Page loaded: {len(content)} characters")
        
        # Extract episodes using regex patterns
        episodes = []
        
        # Pattern 1: Multiple episode link patterns
        patterns = [
            r'href="([^"]*episode[^"]*)"[^>]*>([^<]*(?:Episode|episode|集)[^<]*)</a>',
            r'href="([^"]*super-cube[^"]*)"[^>]*>([^<]*(?:Episode|episode|集|第)[^<]*)</a>',
            r'data-link="([^"]*super-cube[^"]*)"[^>]*>([^<]*(?:Episode|episode|集|第)[^<]*)',
            r'"url":"([^"]*super-cube[^"]*)".*?"title":"([^"]*)"'
        ]
        
        all_matches = []
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            all_matches.extend(matches)
        
        # Also try to find more episodes by scanning the entire page
        super_cube_links = re.findall(r'href="([^"]*super-cube[^"]*)"', content, re.IGNORECASE)
        for link in super_cube_links:
            if 'episode' in link.lower() or 'play' in link.lower():
                # Extract episode number
                ep_match = re.search(r'episode[_-]?(\d+)', link, re.IGNORECASE)
                if ep_match:
                    episode_num = ep_match.group(1)
                    title = f"Super Cube Episode {episode_num}"
                    all_matches.append((link, title))
        
        matches = all_matches
        
        for i, (url, title) in enumerate(matches[:max_episodes], 1):
            # Clean up URL
            if url.startswith('//'):
                url = 'https:' + url
            elif url.startswith('/'):
                url = 'https://www.iq.com' + url
            
            # Clean up title
            title = re.sub(r'<[^>]+>', '', title).strip()
            if not title:
                title = f"Episode {i}"
            
            episodes.append({
                'episode_number': i,
                'title': title,
                'url': url,
                'thumbnail': None,
                'dash_url': None,
                'is_valid': True,  # Assume valid for basic scraping
                'method': 'basic_html_parsing'
            })
        
        print(f"✅ Found {len(episodes)} episodes using basic HTML parsing")
        
        if episodes:
            return {
                'success': True,
                'total_episodes': len(episodes),
                'valid_episodes': len(episodes),
                'episodes': episodes,
                'message': f'Successfully scraped {len(episodes)} episodes using basic method',
                'method': 'basic_scraping'
            }
        else:
            return {
                'success': False,
                'error': 'No episodes found using basic HTML parsing',
                'total_episodes': 0,
                'method': 'basic_scraping'
            }
            
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'error': 'Timeout: IQiyi servers took too long to respond',
            'suggestion': 'Try again later or check internet connection'
        }
    except requests.exceptions.ConnectionError as e:
        return {
            'success': False,
            'error': f'Connection error: {str(e)}',
            'suggestion': 'Cannot connect to IQiyi servers. May be blocked or down.'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'suggestion': 'General error occurred during scraping'
        }

if __name__ == "__main__":
    test_url = "https://www.iq.com/play/super-cube-115bxuuq7eo?lang=en_us"
    result = scrape_basic_episodes(test_url, max_episodes=10)
    print("\n" + "="*50)
    print("BASIC SCRAPING RESULT:")
    print(json.dumps(result, indent=2, ensure_ascii=False))