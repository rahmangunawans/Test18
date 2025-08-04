# -*- coding: utf8 -*-
"""
IQiyi Auto Scraper untuk AniFlix
Mengintegrasikan auto scraping DASH URL dan M3U8 extraction untuk episode streaming
"""
import json
import requests
import urllib3
import re
import ssl
import time
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
import sys
import os
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

@dataclass
class EpisodeData:
    """Data episode yang di-scrape dari IQiyi"""
    title: str
    episode_number: Optional[int]
    url: str
    dash_url: Optional[str] = None
    m3u8_url: Optional[str] = None
    thumbnail: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[str] = None
    is_valid: bool = False

class IQiyiScraper:
    """Auto scraper untuk IQiyi dengan integrasi AniFlix"""

    def __init__(self, url: str):
        self.url = url
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.5',
            'accept-encoding': 'gzip, deflate',
            'connection': 'keep-alive',
            'upgrade-insecure-requests': '1',
        }
        
        # Create session with SSL configuration
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update(self.headers)
        
        # Setup retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        # Custom HTTPAdapter with SSL context
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self._player_data = None

    def _request(self, method: str, url: str, max_retries: int = 3, **kwargs) -> Optional[requests.Response]:
        """Enhanced request method dengan error handling dan retry logic"""
        import time
        
        for attempt in range(max_retries):
            try:
                kwargs.setdefault('timeout', 20)
                kwargs.setdefault('verify', False)
                
                # Add delay between retries
                if attempt > 0:
                    delay = attempt * 2  # 2s, 4s delays
                    print(f'⏳ Retry attempt {attempt + 1} after {delay}s delay...')
                    time.sleep(delay)
                
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                
                # Check if response is actually HTML when we expect JSON
                content_type = response.headers.get('content-type', '').lower()
                if 'json' in kwargs.get('headers', {}).get('accept', '') and 'text/html' in content_type:
                    print(f'❌ Received HTML response when expecting JSON for {url}')
                    if attempt < max_retries - 1:
                        continue
                    return None
                
                # Additional check for HTML content when expecting JSON (only for DASH API)
                if hasattr(response, 'text') and 'cache.video.iqiyi.com' in url and response.text.strip().startswith('<'):
                    print(f'❌ DASH API returned HTML instead of JSON for {url}')
                    print('🔄 DASH API is returning HTML - likely blocked or rate limited')
                    if attempt < max_retries - 1:
                        time.sleep(5)  # Longer delay for API requests
                        continue
                    return None
                
                return response
                
            except requests.exceptions.SSLError as e:
                print(f'❌ SSL Error for {url} (attempt {attempt + 1}): {str(e)}')
                if attempt == max_retries - 1:
                    return None
                    
            except requests.exceptions.Timeout as e:
                print(f'❌ Timeout Error for {url} (attempt {attempt + 1}): {str(e)}')
                if attempt == max_retries - 1:
                    return None
                    
            except requests.exceptions.ConnectionError as e:
                print(f'❌ Connection Error for {url} (attempt {attempt + 1}): {str(e)}')
                if attempt == max_retries - 1:
                    return None
                    
            except Exception as e:
                print(f'❌ Error making request to {url} (attempt {attempt + 1}): {str(e)}')
                if attempt == max_retries - 1:
                    return None
        
        return None

    def get_player_data(self) -> Optional[Dict[str, Any]]:
        """Get dan cache player data dari halaman"""
        if self._player_data:
            return self._player_data

        print("🔍 Fetching player data dari IQiyi...")
        response = self._request('get', self.url)
        if not response:
            print("❌ Failed to get response from IQiyi")
            return None

        # Check if we got a valid HTML response
        if not response.text or len(response.text) < 100:
            print("❌ Response too short or empty")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        script_tag = soup.find('script', {'id': '__NEXT_DATA__'})

        if not script_tag:
            print("❌ Tidak menemukan __NEXT_DATA__ script tag")
            # Try alternative script tag patterns
            alt_script = soup.find('script', string=re.compile(r'"cachePlayList"'))
            if alt_script:
                print("🔄 Found alternative script with cachePlayList")
                script_tag = alt_script
            else:
                print("❌ No alternative script found either")
                return None

        try:
            if script_tag.string:
                json_data = script_tag.string.strip()
            else:
                json_data = script_tag.get_text().strip()
                
            if not json_data:
                print("❌ Script tag is empty")
                return None
                
            self._player_data = json.loads(json_data)
            print("✅ Player data berhasil dimuat")
            return self._player_data
            
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON data: {e}")
            print(f"JSON preview: {json_data[:200]}...")
            return None
        except Exception as e:
            print(f"❌ Unexpected error getting player data: {e}")
            return None

    def dash(self) -> Optional[str]:
        """Extract DASH query dari player data"""
        data = self.get_player_data()
        if not data:
            return None

        try:
            log = data['props']['initialProps']['pageProps']['prePlayerData']['ssrlog']
            url_pattern = r'http://intel-cache\.video\.qiyi\.domain/dash\?([^\s]+)'
            urls = re.findall(url_pattern, log)

            if urls:
                return urls[0]
            return None

        except Exception as e:
            print(f"❌ Error extracting DASH query: {e}")
            return None

    def get_m3u8(self) -> Optional[str]:
        """Extract M3U8 content dari DASH API"""
        dash_query = self.dash()
        if not dash_query:
            print("❌ Tidak dapat menemukan DASH query")
            return None

        url = f'https://cache.video.iqiyi.com/dash?{dash_query}'
        response = self._request('get', url)

        if response:
            try:
                # Check if response is HTML instead of JSON
                if response.text.strip().startswith('<'):
                    print("❌ DASH API returned HTML instead of JSON - likely blocked or rate limited")
                    return None
                    
                data = response.json()
                if data.get('code') == 'A00000':
                    video = data['data']['program']['video']
                    for item in video:
                        if 'm3u8' in item:
                            print("✅ M3U8 content berhasil diekstrak")
                            return item['m3u8']
                else:
                    print(f"❌ DASH API error: {data.get('msg', 'Unknown error')}")
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON response from DASH API: {e}")
                print(f"Response content preview: {response.text[:200]}...")
            except Exception as e:
                print(f"❌ Error parsing DASH response: {e}")
        return None

    def get_dash_url(self) -> Optional[str]:
        """Get DASH URL lengkap"""
        dash_query = self.dash()
        if dash_query:
            return f'https://cache.video.iqiyi.com/dash?{dash_query}'
        return None

    def extract_episode_info(self) -> Optional[EpisodeData]:
        """Extract informasi episode dari URL"""
        print(f"🎬 Extracting episode info dari: {self.url}")
        
        # Get basic page info
        response = self._request('get', self.url)
        if not response:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title dari meta tags atau page title
        title = None
        meta_title = soup.find('meta', property='og:title')
        if meta_title:
            title = meta_title.get('content', '')
        else:
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text().strip()

        # Extract episode number dari title atau URL
        episode_number = None
        if title:
            # Cari pattern episode number
            episode_match = re.search(r'(?:episode|ep|第)\s*(\d+)', title.lower())
            if episode_match:
                episode_number = int(episode_match.group(1))

        # Extract thumbnail dari meta tags
        thumbnail = None
        meta_image = soup.find('meta', property='og:image')
        if meta_image:
            thumbnail = meta_image.get('content', '')

        # Extract description
        description = None
        meta_desc = soup.find('meta', property='og:description')
        if meta_desc:
            description = meta_desc.get('content', '')

        # Get DASH URL dan M3U8
        dash_url = self.get_dash_url()
        m3u8_url = None
        is_valid = False

        if dash_url:
            m3u8_content = self.get_m3u8()
            if m3u8_content and len(m3u8_content) > 100:
                m3u8_url = m3u8_content
                is_valid = True
                print("✅ Episode data valid dengan M3U8 content")
            else:
                print("❌ Tidak dapat mengextract M3U8 content")

        return EpisodeData(
            title=title or "Unknown Episode",
            episode_number=episode_number,
            url=self.url,
            dash_url=dash_url,
            m3u8_url=m3u8_url,
            thumbnail=thumbnail,
            description=description,
            is_valid=is_valid
        )

    def get_all_episodes(self, max_episodes: int = None) -> List[EpisodeData]:
        """Extract semua episode dari playlist IQiyi dengan rate limiting"""
        import time
        
        print("🎬 Extracting semua episode dari playlist...")
        data = self.get_player_data()
        if not data:
            print("❌ Cannot get player data - playlist extraction failed")
            return []

        episodes = []
        try:
            # Try to access the episode data with better error handling
            props = data.get('props', {})
            initial_state = props.get('initialState', {})
            play = initial_state.get('play', {})
            cache_playlist = play.get('cachePlayList', {})
            episode_data = cache_playlist.get('1', [])
            
            if not episode_data:
                print("❌ No episode data found in cachePlayList")
                # Try alternative data structure
                initial_props = props.get('initialProps', {})
                page_props = initial_props.get('pageProps', {})
                pre_player_data = page_props.get('prePlayerData', {})
                
                if pre_player_data:
                    print("🔄 Trying alternative data structure...")
                    # Look for alternative episode data structure
                    return []
                else:
                    print("❌ No alternative episode data found")
                    return []
            
            total_episodes = len(episode_data)
            print(f"📺 Ditemukan {total_episodes} episode")
            
            # Limit episodes untuk mencegah timeout jika diperlukan
            if max_episodes is None:
                process_count = total_episodes
                print(f"🎯 Processing SEMUA {total_episodes} episode")
            else:
                process_count = min(total_episodes, max_episodes)
                if total_episodes > max_episodes:
                    print(f"⚠️ Membatasi processing ke {max_episodes} episode pertama untuk mencegah timeout")

            for i, episode in enumerate(episode_data[:process_count], 1):
                episode_title = episode.get('subTitle', f'Episode {i}')
                
                # Build episode URL
                album_url = episode.get('albumPlayUrl', '')
                if album_url.startswith('//'):
                    full_url = f"https:{album_url}"
                elif album_url.startswith('/'):
                    full_url = f"https://www.iq.com{album_url}"
                else:
                    full_url = album_url

                # Add delay between requests untuk mencegah rate limiting
                if i > 1:
                    time.sleep(1.0)  # Increased delay to 1 second for better stability
                
                print(f"🎬 Processing episode {i}/{process_count}: {episode_title}")
                
                try:
                    # Extract DASH URL untuk episode ini
                    episode_scraper = IQiyiScraper(full_url)
                    episode_info = episode_scraper.extract_episode_info()
                    
                    if episode_info:
                        episode_info.episode_number = i
                        episode_info.title = episode_title
                        episodes.append(episode_info)
                        
                        if episode_info.is_valid:
                            print(f"✅ Episode {i}: {episode_title} - Valid")
                        else:
                            print(f"❌ Episode {i}: {episode_title} - Invalid")
                    else:
                        print(f"❌ Episode {i}: {episode_title} - Failed to extract")
                        
                except Exception as ep_error:
                    print(f"❌ Episode {i}: {episode_title} - Error: {ep_error}")
                    continue

            print(f"✅ Berhasil extract {len(episodes)} episode dari {process_count} yang diproses")
            return episodes

        except KeyError as e:
            print(f"❌ Key error - struktur data berubah: {e}")
            print("🔍 Available keys in data structure:")
            try:
                if 'props' in data:
                    print(f"  props keys: {list(data['props'].keys())}")
                    if 'initialState' in data['props']:
                        print(f"  initialState keys: {list(data['props']['initialState'].keys())}")
                    if 'initialProps' in data['props']:
                        print(f"  initialProps keys: {list(data['props']['initialProps'].keys())}")
            except:
                pass
            return []
        except Exception as e:
            print(f"❌ Error extracting episodes: {e}")
            return []

def scrape_iqiyi_episode(url: str) -> dict:
    """
    Function utama untuk scraping episode IQiyi
    Return: dict dengan episode data
    """
    try:
        scraper = IQiyiScraper(url)
        episode_data = scraper.extract_episode_info()
        
        if episode_data:
            return {
                'success': True,
                'data': {
                    'title': episode_data.title,
                    'episode_number': episode_data.episode_number,
                    'url': episode_data.url,
                    'dash_url': episode_data.dash_url,
                    'm3u8_content': episode_data.m3u8_url,
                    'thumbnail_url': episode_data.thumbnail,
                    'description': episode_data.description,
                    'is_valid': episode_data.is_valid
                }
            }
        else:
            return {
                'success': False,
                'error': 'Tidak dapat extract episode data'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def scrape_iqiyi_playlist(url: str, max_episodes: int = None) -> dict:
    """
    Function untuk scraping playlist IQiyi dengan batasan episode untuk mencegah timeout
    Return: dict dengan episode data
    """
    try:
        scraper = IQiyiScraper(url)
        episodes_data = scraper.get_all_episodes(max_episodes=max_episodes)
        
        if episodes_data:
            episodes_list = []
            for episode in episodes_data:
                episodes_list.append({
                    'title': episode.title,
                    'episode_number': episode.episode_number,
                    'url': episode.url,
                    'dash_url': episode.dash_url,
                    'm3u8_content': episode.m3u8_url,
                    'thumbnail_url': episode.thumbnail,
                    'description': episode.description,
                    'is_valid': episode.is_valid
                })
            
            return {
                'success': True,
                'total_episodes': len(episodes_list),
                'valid_episodes': len([ep for ep in episodes_list if ep['is_valid']]),
                'episodes': episodes_list,
                'message': f'Berhasil extract {len(episodes_list)} episode' + (f' (dibatasi {max_episodes} untuk mencegah timeout)' if max_episodes else ' dari seluruh playlist')
            }
        else:
            return {
                'success': False,
                'error': 'Tidak dapat extract episode dari playlist'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Error scraping playlist: {str(e)}'
        }

if __name__ == "__main__":
    # Test scraper
    test_url = 'https://www.iq.com/play/super-cube-episode-1-11eihk07dr8?lang=en_us'
    print("🧪 Testing IQiyi Scraper...")
    
    result = scrape_iqiyi_episode(test_url)
    print(f"📊 Result: {result}")