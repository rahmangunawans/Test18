"""
Enhanced IQiyi Scraper - Based on user's fresh reference
Simplified and robust scraping system with proper title extraction
"""

import json
import requests
import urllib3
import re
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
import sys
import os
from datetime import datetime
import time

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

@dataclass
class EpisodeInfo:
    """Professional episode information structure"""
    title: str
    episode_number: Optional[int]
    url: str
    content_type: str  # "episode", "preview", "trailer", "unknown"
    description: Optional[str] = None
    duration: Optional[str] = None
    thumbnail: Optional[str] = None
    dash_url: Optional[str] = None
    is_valid: bool = False

@dataclass
class AlbumInfo:
    """Professional album information structure"""
    title: str
    current_episode: EpisodeInfo
    all_episodes: List[EpisodeInfo]
    episodes_only: List[EpisodeInfo]
    previews_only: List[EpisodeInfo]
    rating: Optional[float] = None
    year: Optional[int] = None
    country: Optional[str] = None
    genre: Optional[List[str]] = None
    description: Optional[str] = None

class EnhancedIQiyiScraper:
    """Enhanced Professional IQiyi Scraper with comprehensive data structures"""

    def __init__(self, url: str):
        self.url = url
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.verify = False
        self._player_data = None

    def _request(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """Enhanced request method with better error handling"""
        try:
            kwargs.setdefault('headers', self.headers)
            kwargs.setdefault('timeout', 10)
            kwargs.setdefault('verify', False)
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except Exception as e:
            print(f'❌ Error making request to {url}: {str(e)}')
            return None

    def get_player_data(self) -> Optional[Dict[str, Any]]:
        """Get and cache player data from the page"""
        if self._player_data:
            return self._player_data

        print("🔍 Fetching player data...")
        response = self._request('get', self.url)
        if not response:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        script_tag = soup.find('script', {'id': '__NEXT_DATA__'})

        if not script_tag:
            print("❌ No __NEXT_DATA__ script tag found")
            return None

        try:
            json_data = script_tag.string.strip()
            self._player_data = json.loads(json_data)
            print("✅ Player data loaded successfully")
            return self._player_data
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON data: {e}")
            return None

    def _extract_title_from_data(self, episode_data: Dict[str, Any]) -> str:
        """Extract title with comprehensive fallbacks and language preference"""
        print(f"🏷️ Extracting title from episode data...")
        
        # First check 'name' field which seems to be primary
        name_title = episode_data.get('name', '').strip()
        if name_title:
            print(f"🔍 Found name field: {name_title}")
            
            # Convert Chinese titles to English pattern if possible
            if "超能立方：超凡篇" in name_title:
                # Extract episode number from Chinese title
                import re
                match = re.search(r'第(\d+)集', name_title)
                if match:
                    episode_num = match.group(1)
                    # Check if it's a preview (有预告)
                    if "预告" in name_title:
                        english_title = f"Super Cube Episode {episode_num} Preview"
                        print(f"✅ Converted Chinese preview to English: {english_title}")
                        return english_title
                    else:
                        english_title = f"Super Cube Episode {episode_num}"
                        print(f"✅ Converted Chinese to English: {english_title}")
                        return english_title
            
            # For already English titles, use as-is
            print(f"✅ Using title from name: {name_title}")
            return name_title
        
        # Try alternate title field
        alt_title = episode_data.get('alterTitle', '').strip()
        if alt_title:
            print(f"✅ Using title from alterTitle: {alt_title}")
            return alt_title
        
        # Try subtitle field
        sub_title = episode_data.get('subTitle', '').strip()
        if sub_title:
            print(f"✅ Using title from subTitle: {sub_title}")
            return sub_title
        
        # Try album name
        album_name = episode_data.get('albumName', '').strip()
        if album_name:
            print(f"✅ Using title from albumName: {album_name}")
            return album_name
        
        # Try all fields as fallback
        for key, value in episode_data.items():
            if isinstance(value, str) and value.strip():
                if any(keyword in key.lower() for keyword in ['title', 'name']):
                    print(f"⚠️ Using fallback title from {key}: {value}")
                    return value.strip()
        
        print(f"❌ No title found, using default")
        return "Unknown Episode"

    def _extract_description(self, episode_data: Dict[str, Any]) -> Optional[str]:
        """Extract description from episode data with comprehensive fallbacks"""
        description_fields = [
            'description', 'desc', 'summary', 'brief', 'shortDesc', 'longDesc', 'content', 
            'synopsis', 'plot', 'storyline', 'playDesc', 'episodeDesc', 'albumDesc', 
            'tvDesc', 'videoDesc', 'briefDesc', 'introduce', 'playIntroduce', 'videoIntroduce'
        ]
        
        # Try direct fields
        for field in description_fields:
            if episode_data.get(field):
                desc = str(episode_data.get(field)).strip()
                if desc and desc.lower() not in ['null', 'none', '', 'undefined'] and len(desc) > 3:
                    return desc
        
        # Try nested objects
        for key, value in episode_data.items():
            if isinstance(value, dict):
                for field in description_fields:
                    if field in value and value[field]:
                        desc = str(value[field]).strip()
                        if desc and desc.lower() not in ['null', 'none', '', 'undefined'] and len(desc) > 3:
                            return desc
        
        return None

    def _extract_thumbnail(self, episode_data: Dict[str, Any]) -> Optional[str]:
        """Enhanced thumbnail extraction with comprehensive field search"""
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
                        final_url = thumbnail if thumbnail.startswith('http') else f"https:{thumbnail}"
                        print(f"✅ Using thumbnail from {field}: {final_url}")
                        return final_url

        # Search ALL nested objects thoroughly
        for key, value in episode_data.items():
            if isinstance(value, dict):
                for field in thumbnail_fields:
                    if field in value and value[field]:
                        thumbnail = str(value[field]).strip()
                        if thumbnail and thumbnail not in ['null', 'none', '']:
                            if any(thumbnail.startswith(prefix) for prefix in ['http://', 'https://', '//', '/', 'data:']):
                                final_url = thumbnail if thumbnail.startswith('http') else f"https:{thumbnail}"
                                print(f"✅ Using thumbnail from {key}.{field}: {final_url}")
                                return final_url

        # Look for any field containing 'img', 'pic', 'photo', or 'image' in the name
        for key, value in episode_data.items():
            if any(word in key.lower() for word in ['img', 'pic', 'photo', 'image', 'cover', 'poster']):
                if isinstance(value, str) and value.strip():
                    thumbnail = value.strip()
                    if any(thumbnail.startswith(prefix) for prefix in ['http://', 'https://', '//', '/', 'data:']):
                        final_url = thumbnail if thumbnail.startswith('http') else f"https:{thumbnail}"
                        print(f"✅ Using fallback thumbnail from {key}: {final_url}")
                        return final_url

        # Search nested objects for any image-like fields
        for key, value in episode_data.items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    if any(word in subkey.lower() for word in ['img', 'pic', 'photo', 'image', 'cover', 'poster']):
                        if isinstance(subvalue, str) and subvalue.strip():
                            thumbnail = subvalue.strip()
                            if any(thumbnail.startswith(prefix) for prefix in ['http://', 'https://', '//', '/', 'data:']):
                                final_url = thumbnail if thumbnail.startswith('http') else f"https:{thumbnail}"
                                print(f"✅ Using nested fallback thumbnail from {key}.{subkey}: {final_url}")
                                return final_url

        print(f"❌ No thumbnail found")
        return None

    def _extract_duration(self, episode_data: Dict[str, Any]) -> Optional[str]:
        """Enhanced duration extraction with comprehensive field search"""
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
                formatted_duration = self._format_duration(duration_val, field)
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
                            formatted_duration = self._format_duration(duration_val, f"{key}.{field}")
                            if formatted_duration:
                                print(f"✅ Using duration from {key}.{field}: {formatted_duration}")
                                return formatted_duration

        # Look for any field containing 'time', 'duration' in the name
        for key, value in episode_data.items():
            if any(word in key.lower() for word in ['time', 'duration', 'length', 'runtime']):
                if isinstance(value, (str, int, float)) and str(value).strip() not in ['null', 'none', '', '0']:
                    duration_val = str(value).strip()
                    formatted_duration = self._format_duration(duration_val, key)
                    if formatted_duration:
                        print(f"✅ Using fallback duration from {key}: {formatted_duration}")
                        return formatted_duration

        print(f"❌ No duration found")
        return None

    def _format_duration(self, duration_val: str, field_name: str) -> Optional[str]:
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

    def extract_single_episode(self) -> Optional[EpisodeInfo]:
        """Extract single episode information"""
        print("🎬 Extracting single episode...")
        
        player_data = self.get_player_data()
        if not player_data:
            return None
        
        try:
            # Navigate through the data structure to find episode info
            props = player_data.get('props', {})
            initial_state = props.get('initialState', {})
            play = initial_state.get('play', {})
            
            # Look for current episode data
            current_episode = play.get('curVideoInfo', {})
            if not current_episode:
                current_episode = play.get('videoInfo', {})
            if not current_episode:
                current_episode = play.get('episodeInfo', {})
            
            if current_episode:
                title = self._extract_title_from_data(current_episode)
                description = self._extract_description(current_episode)
                thumbnail = self._extract_thumbnail(current_episode)
                duration = self._extract_duration(current_episode)
                
                # Extract episode number from title or URL
                episode_number = None
                if 'episode' in title.lower():
                    match = re.search(r'episode\s*(\d+)', title.lower())
                    if match:
                        episode_number = int(match.group(1))
                
                episode_info = EpisodeInfo(
                    title=title,
                    episode_number=episode_number,
                    url=self.url,
                    content_type="episode",
                    description=description,
                    duration=duration,
                    thumbnail=thumbnail,
                    dash_url=None,
                    is_valid=True
                )
                
                print(f"✅ Single episode extracted: {title}")
                return episode_info
            
        except Exception as e:
            print(f"❌ Error extracting single episode: {e}")
        
        return None

    def _is_preview_or_trailer(self, title: str) -> bool:
        """Check if the title indicates a preview or trailer"""
        title_lower = title.lower()
        
        # Chinese preview indicators
        chinese_preview_keywords = ['预告', '先行版', '预览', 'pv']
        
        # English preview indicators  
        english_preview_keywords = [
            'preview', 'trailer', 'teaser', 'promo', 'coming soon', 
            'next episode', 'sneak peek'
        ]
        
        # Check for Chinese preview keywords
        for keyword in chinese_preview_keywords:
            if keyword in title_lower:
                print(f"🚫 Detected Chinese preview keyword '{keyword}' in: {title}")
                return True
        
        # Check for English preview keywords
        for keyword in english_preview_keywords:
            if keyword in title_lower:
                print(f"🚫 Detected English preview keyword '{keyword}' in: {title}")
                return True
        
        return False

    def extract_all_episodes(self, max_episodes: int = 100) -> List[EpisodeInfo]:
        """Extract all episodes from playlist, filtering out previews and trailers"""
        print("📺 Extracting all episodes from playlist...")
        
        player_data = self.get_player_data()
        if not player_data:
            return []
        
        episodes = []
        episode_counter = 1
        seen_episodes = set()  # Track unique episode numbers to avoid duplicates
        
        try:
            # Navigate through the data structure
            props = player_data.get('props', {})
            initial_state = props.get('initialState', {})
            play = initial_state.get('play', {})
            
            # Look for playlist data
            cache_playlist = play.get('cachePlayList', {})
            episode_data = cache_playlist.get('1', [])
            
            if not episode_data:
                print("❌ No episode data found in playlist")
                return []
            
            print(f"📺 Found {len(episode_data)} total items in playlist")
            
            # Limit episodes to prevent timeout
            process_count = min(len(episode_data), max_episodes)
            print(f"🎯 Processing {process_count} items (filtering out previews/trailers)")
            
            for i, episode in enumerate(episode_data[:process_count], 1):
                title = self._extract_title_from_data(episode)
                
                # Skip previews and trailers
                if self._is_preview_or_trailer(title):
                    print(f"⏭️ Skipping preview/trailer {i}: {title}")
                    continue
                
                # Extract episode number from title to check for duplicates
                import re
                episode_num_match = re.search(r'Episode (\d+)', title)
                if episode_num_match:
                    ep_num = int(episode_num_match.group(1))
                    if ep_num in seen_episodes:
                        print(f"⚠️ Skipping duplicate Episode {ep_num}: {title}")
                        continue
                    seen_episodes.add(ep_num)
                    actual_episode_number = ep_num
                else:
                    actual_episode_number = episode_counter
                
                description = self._extract_description(episode)
                thumbnail = self._extract_thumbnail(episode)
                duration = self._extract_duration(episode)
                
                # Build episode URL
                album_url = episode.get('albumPlayUrl', '')
                if album_url.startswith('//'):
                    full_url = f"https:{album_url}"
                elif album_url.startswith('/'):
                    full_url = f"https://www.iq.com{album_url}"
                else:
                    full_url = album_url or self.url
                
                episode_info = EpisodeInfo(
                    title=title,
                    episode_number=actual_episode_number,
                    url=full_url,
                    content_type="episode",
                    description=description,
                    duration=duration,
                    thumbnail=thumbnail,
                    dash_url=None,
                    is_valid=True
                )
                
                episodes.append(episode_info)
                print(f"✅ Episode {actual_episode_number}: {title}")
                episode_counter += 1
                
                # Small delay to avoid rate limiting
                if i < process_count:
                    time.sleep(0.1)
            
            # Sort episodes by episode number to ensure correct order
            episodes.sort(key=lambda x: x.episode_number)
            
            print(f"✅ Successfully extracted {len(episodes)} unique valid episodes (filtered out previews/trailers and duplicates)")
            return episodes
            
        except Exception as e:
            print(f"❌ Error extracting episodes: {e}")
            return []

# Public API functions
def scrape_single_episode(url: str) -> dict:
    """
    Scrape single episode information
    """
    try:
        scraper = EnhancedIQiyiScraper(url)
        episode = scraper.extract_single_episode()
        
        if episode:
            return {
                'success': True,
                'data': {
                    'title': episode.title,
                    'episode_number': episode.episode_number,
                    'url': episode.url,
                    'description': episode.description,
                    'duration': episode.duration,
                    'thumbnail_url': episode.thumbnail,
                    'dash_url': episode.dash_url,
                    'is_valid': episode.is_valid
                },
                'message': f'Single episode extracted: {episode.title}'
            }
        else:
            return {
                'success': False,
                'error': 'Failed to extract episode information'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Scraper error: {str(e)}'
        }

def scrape_all_episodes_playlist(url: str, max_episodes: int = 100) -> dict:
    """
    Scrape all episodes from playlist
    """
    try:
        scraper = EnhancedIQiyiScraper(url)
        episodes_data = scraper.extract_all_episodes(max_episodes=max_episodes)
        
        if episodes_data:
            episodes_list = []
            for episode in episodes_data:
                episodes_list.append({
                    'title': episode.title,
                    'episode_number': episode.episode_number,
                    'url': episode.url,
                    'description': episode.description,
                    'duration': episode.duration,
                    'thumbnail_url': episode.thumbnail,
                    'dash_url': episode.dash_url,
                    'is_valid': episode.is_valid
                })
            
            return {
                'success': True,
                'total_episodes': len(episodes_list),
                'valid_episodes': len(episodes_list),
                'episodes': episodes_list,
                'message': f'Successfully extracted {len(episodes_list)} episodes from playlist'
            }
        else:
            return {
                'success': False,
                'error': 'No episodes found in playlist'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Playlist scraper error: {str(e)}'
        }

if __name__ == "__main__":
    # Test the enhanced scraper
    test_url = 'https://www.iq.com/play/super-cube-episode-1-11eihk07dr8?lang=en_us'
    print("🧪 Testing Enhanced IQiyi Scraper...")
    
    # Test single episode
    print("\n=== Single Episode Test ===")
    result = scrape_single_episode(test_url)
    print(f"Result: {result}")
    
    # Test playlist
    print("\n=== Playlist Test ===")
    result = scrape_all_episodes_playlist(test_url, max_episodes=5)
    print(f"Result: {result}")