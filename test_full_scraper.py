#!/usr/bin/env python3
"""
Test scraper untuk mengambil SEMUA episode dari playlist IQiyi
"""

from iqiyi_scraper import IQiyiScraper, EpisodeData
from typing import List
import time

def scrape_full_playlist(url: str) -> dict:
    """
    Function untuk scraping SELURUH playlist IQiyi tanpa batasan
    Return: dict dengan semua episode data
    """
    try:
        scraper = IQiyiScraper(url)
        print("🎬 Extracting SELURUH episode dari playlist...")
        data = scraper.get_player_data()
        if not data:
            return {'success': False, 'error': 'Cannot get player data'}

        episodes = []
        try:
            episode_data = data['props']['initialState']['play']['cachePlayList']['1']
            total_episodes = len(episode_data)
            print(f"📺 Total ditemukan {total_episodes} episode - akan diproses SEMUA")

            for i, episode in enumerate(episode_data, 1):
                episode_title = episode.get('subTitle', f'Episode {i}')
                
                # Build episode URL
                album_url = episode.get('albumPlayUrl', '')
                if album_url.startswith('//'):
                    full_url = f"https:{album_url}"
                elif album_url.startswith('/'):
                    full_url = f"https://www.iq.com{album_url}"
                else:
                    full_url = album_url

                print(f"🎬 Processing episode {i}/{total_episodes}: {episode_title}")
                
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

                # Small delay between episodes
                if i < total_episodes:
                    time.sleep(0.3)

            episodes_list = []
            for episode in episodes:
                episodes_list.append({
                    'title': episode.title,
                    'episode_number': episode.episode_number,
                    'url': episode.url,
                    'dash_url': episode.dash_url,
                    'm3u8_content': episode.m3u8_url[:100] + '...' if episode.m3u8_url else None,  # Truncate for display
                    'thumbnail_url': episode.thumbnail,
                    'description': episode.description,
                    'is_valid': episode.is_valid
                })
            
            return {
                'success': True,
                'total_episodes': len(episodes_list),
                'valid_episodes': len([ep for ep in episodes_list if ep['is_valid']]),
                'episodes': episodes_list,
                'message': f'Berhasil extract {len(episodes_list)} episode dari {total_episodes} total episode'
            }

        except Exception as e:
            print(f"❌ Error extracting episodes: {e}")
            return {'success': False, 'error': str(e)}
            
    except Exception as e:
        return {'success': False, 'error': f'Error scraping playlist: {str(e)}'}

if __name__ == "__main__":
    url = "https://www.iq.com/play/super-cube-115bxuuq7eo?lang=en_us"
    print(f"Testing full scraper on: {url}")
    
    result = scrape_full_playlist(url)
    
    print(f"\n🎯 HASIL FINAL:")
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"Total episodes: {result['total_episodes']}")
        print(f"Valid episodes: {result['valid_episodes']}")
        print(f"Message: {result['message']}")
        
        print(f"\n📋 EPISODE LIST:")
        for ep in result['episodes'][:10]:  # Show first 10
            status = "✅" if ep['is_valid'] else "❌"
            print(f"  {status} Episode {ep['episode_number']}: {ep['title']}")
            
        if len(result['episodes']) > 10:
            print(f"  ... dan {len(result['episodes']) - 10} episode lainnya")
    else:
        print(f"Error: {result['error']}")