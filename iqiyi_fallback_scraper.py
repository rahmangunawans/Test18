"""
IQiyi Fallback Scraper - Simplified scraper that avoids SSL issues
Uses basic HTTP requests without complex API calls
"""

import requests
import re
import json
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from dataclasses import dataclass
import time

@dataclass
class FallbackEpisodeData:
    title: str
    episode_number: int
    url: str
    thumbnail: Optional[str] = None
    description: Optional[str] = None

class IQiyiFallbackScraper:
    def __init__(self, url: str):
        self.url = url
        self.session = requests.Session()
        
        # Simplified headers to avoid detection
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
    def _safe_request(self, url: str, timeout: int = 10) -> Optional[requests.Response]:
        """Make a safe HTTP request with timeout and error handling"""
        try:
            response = self.session.get(url, timeout=timeout, verify=False)
            response.raise_for_status()
            return response
        except Exception as e:
            print(f"❌ Request failed for {url}: {str(e)}")
            return None
    
    def extract_basic_episode_list(self, max_episodes: int = 15) -> List[FallbackEpisodeData]:
        """Extract basic episode information without complex API calls"""
        print("🔄 Using fallback scraper - basic episode extraction")
        
        response = self._safe_request(self.url)
        if not response:
            print("❌ Failed to get main page")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        episodes = []
        
        try:
            # Look for __NEXT_DATA__ script with episode information
            script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
            if not script_tag:
                print("❌ No __NEXT_DATA__ found")
                return []
            
            data = json.loads(script_tag.string)
            
            # Extract episode list from the data structure
            props = data.get('props', {})
            initial_state = props.get('initialState', {})
            play = initial_state.get('play', {})
            cache_playlist = play.get('cachePlayList', {})
            episode_data = cache_playlist.get('1', [])
            
            if not episode_data:
                print("❌ No episode data found in fallback scraper")
                return []
            
            print(f"📺 Found {len(episode_data)} episodes in playlist")
            
            # Limit episodes to prevent timeout
            process_count = min(len(episode_data), max_episodes)
            print(f"🎯 Processing {process_count} episodes (limited for stability)")
            
            for i, episode in enumerate(episode_data[:process_count], 1):
                episode_title = episode.get('subTitle', f'Episode {i}')
                album_url = episode.get('albumPlayUrl', '')
                
                # Build full URL
                if album_url.startswith('//'):
                    full_url = f"https:{album_url}"
                elif album_url.startswith('/'):
                    full_url = f"https://www.iq.com{album_url}"
                else:
                    full_url = album_url
                
                # Extract thumbnail if available
                thumbnail = episode.get('imageUrl', '')
                if thumbnail and thumbnail.startswith('//'):
                    thumbnail = f"https:{thumbnail}"
                
                episode_info = FallbackEpisodeData(
                    title=episode_title,
                    episode_number=i,
                    url=full_url,
                    thumbnail=thumbnail,
                    description=f"Episode {i} of the series"
                )
                
                episodes.append(episode_info)
                print(f"✅ Episode {i}: {episode_title}")
                
                # Small delay to avoid rate limiting
                if i < process_count:
                    time.sleep(0.2)
            
            print(f"✅ Successfully extracted {len(episodes)} episodes using fallback method")
            return episodes
            
        except Exception as e:
            print(f"❌ Error in fallback scraper: {e}")
            return []

def scrape_iqiyi_playlist_fallback(url: str, max_episodes: int = 15) -> dict:
    """
    Fallback function untuk scraping playlist IQiyi tanpa SSL issues
    """
    try:
        scraper = IQiyiFallbackScraper(url)
        episodes_data = scraper.extract_basic_episode_list(max_episodes=max_episodes)
        
        if episodes_data:
            episodes_list = []
            for episode in episodes_data:
                episodes_list.append({
                    'title': episode.title,
                    'episode_number': episode.episode_number,
                    'url': episode.url,
                    'dash_url': None,  # Not available in fallback mode
                    'm3u8_content': None,  # Not available in fallback mode
                    'thumbnail_url': episode.thumbnail,
                    'description': episode.description,
                    'is_valid': True  # Consider valid for basic info
                })
            
            return {
                'success': True,
                'total_episodes': len(episodes_list),
                'valid_episodes': len(episodes_list),
                'episodes': episodes_list,
                'message': f'Fallback scraper: Extracted {len(episodes_list)} episodes (basic info only - no streaming URLs)',
                'method': 'fallback'
            }
        else:
            return {
                'success': False,
                'error': 'Fallback scraper failed to extract episodes'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Fallback scraper error: {str(e)}'
        }

if __name__ == "__main__":
    # Test the fallback scraper
    test_url = 'https://www.iq.com/play/super-cube-episode-1-11eihk07dr8?lang=en_us'
    print("🧪 Testing IQiyi Fallback Scraper...")
    
    result = scrape_iqiyi_playlist_fallback(test_url, max_episodes=5)
    print(f"Result: {result}")