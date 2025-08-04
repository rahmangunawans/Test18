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
        
        # Extract episodes using enhanced JSON-based approach
        episodes = []
        
        # Try to extract from __NEXT_DATA__ for better metadata
        json_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">([^<]+)</script>', content)
        if json_match:
            try:
                json_data = json.loads(json_match.group(1))
                print("✅ Found __NEXT_DATA__ - using enhanced extraction")
                
                # Navigate the JSON structure to find episodes
                props = json_data.get('props', {})
                initial_state = props.get('initialState', {})
                play = initial_state.get('play', {})
                cache_playlist = play.get('cachePlayList', {})
                episode_data = cache_playlist.get('1', [])
                
                print(f"📺 Found {len(episode_data)} episodes in JSON data")
                
                for i, episode in enumerate(episode_data[:max_episodes], 1):
                    episode_title = episode.get('subTitle', f'Episode {i}')
                    
                    # Extract thumbnail
                    thumbnail = None
                    for thumb_field in ['thumbnail', 'poster', 'image', 'cover', 'pic', 'img', 'picUrl', 'imageUrl', 'vpic', 'rseat']:
                        if episode.get(thumb_field):
                            thumb_url = str(episode.get(thumb_field)).strip()
                            if thumb_url and thumb_url not in ['null', 'none', '']:
                                thumbnail = thumb_url if thumb_url.startswith('http') else f"https:{thumb_url}"
                                break
                    
                    # Extract duration
                    duration = None
                    for duration_field in ['duration', 'playTime', 'length', 'totalTime', 'runTime', 'time']:
                        if episode.get(duration_field) and str(episode.get(duration_field)).strip() not in ['null', 'none', '', '0']:
                            duration_val = str(episode.get(duration_field)).strip()
                            try:
                                if duration_val.isdigit():
                                    seconds = int(duration_val)
                                    if seconds > 60:
                                        minutes = seconds // 60
                                        duration = f"{minutes:02d}:{seconds % 60:02d}"
                                elif ':' in duration_val:
                                    duration = duration_val
                            except:
                                continue
                            break
                    
                    # Build episode URL
                    album_url = episode.get('albumPlayUrl', '')
                    if album_url.startswith('//'):
                        full_url = f"https:{album_url}"
                    elif album_url.startswith('/'):
                        full_url = f"https://www.iq.com{album_url}"
                    else:
                        full_url = album_url
                    
                    episodes.append({
                        'episode_number': i,
                        'title': episode_title,
                        'url': full_url,
                        'thumbnail_url': thumbnail,  # Changed key name to match expected format
                        'duration': duration,
                        'dash_url': None,
                        'is_valid': True,
                        'method': 'enhanced_json_parsing'
                    })
                    
                    print(f"   📺 Episode {i}: {episode_title}")
                    print(f"      📷 Thumbnail: {'✅' if thumbnail else '❌'}")
                    print(f"      ⏱️ Duration: {duration if duration else '❌'}")
            
            except (json.JSONDecodeError, KeyError) as e:
                print(f"❌ JSON parsing failed: {e}, falling back to HTML parsing")
        
        # Fallback to HTML parsing if JSON extraction failed
        if not episodes:
            print("🔄 Using fallback HTML parsing method")
            # Pattern-based extraction as fallback
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
                    'thumbnail_url': None,  # HTML parsing can't extract thumbnails easily
                    'duration': None,       # HTML parsing can't extract duration easily
                    'dash_url': None,
                    'is_valid': True,
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