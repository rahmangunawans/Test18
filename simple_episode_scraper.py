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

def extract_enhanced_thumbnail(episode_data: Dict) -> Optional[str]:
    """Enhanced thumbnail extraction using comprehensive field search"""
    print(f"🖼️ Extracting thumbnail from episode data...")

    # More comprehensive thumbnail field list from reference
    thumbnail_fields = [
        'thumbnail', 'poster', 'image', 'cover', 'pic', 'img', 'picUrl', 'imageUrl',
        'posterUrl', 'coverUrl', 'thumbUrl', 'previewImage', 'snapshot', 'vpic', 'rseat',
        'imgUrl', 'picPath', 'imagePath', 'coverImage', 'posterImage', 'thumbImage',
        'previewImg', 'coverPic', 'albumImg', 'episodeImg', 'showImg', 'screencap'
    ]

    # Search direct fields
    for field in thumbnail_fields:
        if episode_data.get(field):
            thumbnail = str(episode_data.get(field)).strip()
            if thumbnail and thumbnail not in ['null', 'none', '']:
                # More flexible URL validation
                if any(thumbnail.startswith(prefix) for prefix in ['http://', 'https://', '//', '/', 'data:']):
                    print(f"✅ Using thumbnail from {field}: {thumbnail}")
                    return thumbnail if thumbnail.startswith('http') else f"https:{thumbnail}"

    # Search ALL nested objects thoroughly
    for key, value in episode_data.items():
        if isinstance(value, dict):
            for field in thumbnail_fields:
                if field in value and value[field]:
                    thumbnail = str(value[field]).strip()
                    if thumbnail and thumbnail not in ['null', 'none', '']:
                        if any(thumbnail.startswith(prefix) for prefix in ['http://', 'https://', '//', '/', 'data:']):
                            print(f"✅ Using thumbnail from {key}.{field}: {thumbnail}")
                            return thumbnail if thumbnail.startswith('http') else f"https:{thumbnail}"

    # Look for any field containing 'img', 'pic', 'photo', or 'image' in the name
    for key, value in episode_data.items():
        if any(word in key.lower() for word in ['img', 'pic', 'photo', 'image', 'cover', 'poster']):
            if isinstance(value, str) and value.strip():
                thumbnail = value.strip()
                if any(thumbnail.startswith(prefix) for prefix in ['http://', 'https://', '//', '/', 'data:']):
                    print(f"✅ Using fallback thumbnail from {key}: {thumbnail}")
                    return thumbnail if thumbnail.startswith('http') else f"https:{thumbnail}"

    # Search nested objects for any image-like fields
    for key, value in episode_data.items():
        if isinstance(value, dict):
            for subkey, subvalue in value.items():
                if any(word in subkey.lower() for word in ['img', 'pic', 'photo', 'image', 'cover', 'poster']):
                    if isinstance(subvalue, str) and subvalue.strip():
                        thumbnail = subvalue.strip()
                        if any(thumbnail.startswith(prefix) for prefix in ['http://', 'https://', '//', '/', 'data:']):
                            print(f"✅ Using nested fallback thumbnail from {key}.{subkey}: {thumbnail}")
                            return thumbnail if thumbnail.startswith('http') else f"https:{thumbnail}"

    print(f"❌ No thumbnail found")
    return None

def extract_enhanced_duration(episode_data: Dict) -> Optional[str]:
    """Enhanced duration extraction using comprehensive field search"""
    print(f"🕒 Extracting duration from episode data...")

    # Comprehensive duration field list
    duration_fields = [
        'duration', 'playTime', 'length', 'totalTime', 'runTime', 'time',
        'videoDuration', 'showTime', 'programDuration', 'episodeDuration',
        'runtime', 'playLength', 'videoTime', 'mediaTime', 'contentTime'
    ]

    # Search direct fields with better validation
    for field in duration_fields:
        if episode_data.get(field) and str(episode_data.get(field)).strip() not in ['null', 'none', '', '0']:
            duration_val = str(episode_data.get(field)).strip()
            formatted_duration = format_duration(duration_val, field)
            if formatted_duration:
                print(f"✅ Using duration from {field}: {formatted_duration}")
                return formatted_duration

    # Search ALL nested objects thoroughly
    for key, value in episode_data.items():
        if isinstance(value, dict):
            for field in duration_fields:
                if field in value and value[field]:
                    duration_val = str(value[field]).strip()
                    if duration_val and duration_val not in ['null', 'none', '', '0']:
                        formatted_duration = format_duration(duration_val, f"{key}.{field}")
                        if formatted_duration:
                            print(f"✅ Using duration from {key}.{field}: {formatted_duration}")
                            return formatted_duration

    # Look for any field containing 'time', 'duration' in the name
    for key, value in episode_data.items():
        if any(word in key.lower() for word in ['time', 'duration', 'length', 'runtime']):
            if isinstance(value, (str, int, float)) and str(value).strip() not in ['null', 'none', '', '0']:
                duration_val = str(value).strip()
                formatted_duration = format_duration(duration_val, key)
                if formatted_duration:
                    print(f"✅ Using fallback duration from {key}: {formatted_duration}")
                    return formatted_duration

    print(f"❌ No duration found")
    return None

def format_duration(duration_val: str, field_name: str) -> Optional[str]:
    """Format duration value to readable format"""
    try:
        # If it's already in time format, return as is
        if ':' in duration_val and len(duration_val.split(':')) >= 2:
            return duration_val

        # If it's a number (seconds), convert to readable format
        if duration_val.isdigit():
            seconds = int(duration_val)
            if seconds > 60:
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                remaining_seconds = seconds % 60
                if hours > 0:
                    return f"{hours}:{minutes:02d}:{remaining_seconds:02d}"
                else:
                    return f"{minutes:02d}:{remaining_seconds:02d}"
            elif seconds > 0:
                return f"00:{seconds:02d}"

        # If it contains numbers and colons, try to parse
        time_match = re.search(r'(\d+):(\d+)(?::(\d+))?', duration_val)
        if time_match:
            return duration_val

        return None
    except Exception as e:
        print(f"❌ Error formatting duration from {field_name}: {e}")
        return None

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
        
        # Try to extract from __NEXT_DATA__ using enhanced methods from reference
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
                    
                    # Enhanced thumbnail extraction using reference methods
                    thumbnail = extract_enhanced_thumbnail(episode)
                    
                    # Enhanced duration extraction using reference methods
                    duration = extract_enhanced_duration(episode)
                    
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
                        'thumbnail_url': thumbnail,
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