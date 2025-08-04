#!/usr/bin/env python3
"""
Script to extract all 22 episodes dari Super Cube playlist
Menggunakan teknik advanced scraping untuk mendapatkan semua episode
"""
import requests
import re
import json
from bs4 import BeautifulSoup
from app import app, db
from models import Content, Episode

def get_all_super_cube_episodes():
    """Extract all 22 episodes using advanced techniques"""
    print("🔍 Extracting ALL Super Cube episodes...")
    
    # Multiple URLs to try
    urls_to_try = [
        "https://www.iq.com/play/super-cube-115bxuuq7eo?lang=en_us",
        "https://www.iq.com/album/super-cube-2023-115bxuuq7eo",
        "https://www.iq.com/play/super-cube-115bxuuq7eo"
    ]
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    })
    
    all_episodes = []
    
    for url in urls_to_try:
        try:
            print(f"🌐 Trying URL: {url}")
            response = session.get(url, timeout=30)
            content = response.text
            print(f"📄 Page size: {len(content)} characters")
            
            # Method 1: Look for episode links in various formats
            patterns = [
                r'href="([^"]*super-cube[^"]*episode[^"]*)"',
                r'href="([^"]*play/super-cube[^"]*)"',
                r'"url":"([^"]*super-cube[^"]*)"',
                r'data-link="([^"]*super-cube[^"]*)"'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if 'episode' in match.lower() or 'super-cube' in match.lower():
                        all_episodes.append(match)
            
            # Method 2: Look for JSON data containing episodes
            json_patterns = [
                r'"episodes":\s*(\[.*?\])',
                r'"playlist":\s*(\[.*?\])',
                r'"videoList":\s*(\[.*?\])'
            ]
            
            for pattern in json_patterns:
                json_matches = re.findall(pattern, content, re.DOTALL)
                for json_match in json_matches:
                    try:
                        episodes_data = json.loads(json_match)
                        for ep in episodes_data:
                            if isinstance(ep, dict) and 'url' in ep:
                                all_episodes.append(ep['url'])
                    except:
                        continue
            
            # Method 3: BeautifulSoup parsing
            try:
                soup = BeautifulSoup(content, 'html.parser')
                
                # Look for episode links
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if 'super-cube' in href and 'episode' in href:
                        all_episodes.append(href)
                
                # Look for data attributes
                for elem in soup.find_all(attrs={'data-episode': True}):
                    all_episodes.append(elem.get('data-episode', ''))
                    
            except Exception as e:
                print(f"⚠️ BeautifulSoup parsing failed: {e}")
            
        except Exception as e:
            print(f"❌ Error with {url}: {e}")
            continue
    
    # Clean and deduplicate episodes
    clean_episodes = []
    seen_urls = set()
    
    for ep_url in all_episodes:
        if not ep_url or ep_url in seen_urls:
            continue
            
        # Clean URL
        if ep_url.startswith('//'):
            ep_url = 'https:' + ep_url
        elif ep_url.startswith('/'):
            ep_url = 'https://www.iq.com' + ep_url
        
        if 'iq.com' in ep_url and 'super-cube' in ep_url:
            seen_urls.add(ep_url)
            clean_episodes.append(ep_url)
    
    print(f"🎯 Found {len(clean_episodes)} unique episode URLs")
    
    # Extract episode numbers and titles
    final_episodes = []
    for i, url in enumerate(clean_episodes, 1):
        # Try to extract episode number from URL
        episode_match = re.search(r'episode[_-]?(\d+)', url, re.IGNORECASE)
        if episode_match:
            episode_num = int(episode_match.group(1))
        else:
            episode_num = i
        
        # Generate title
        title = f"Super Cube Episode {episode_num}"
        if '第' in url:
            title = f"超能立方：超凡篇 第{episode_num}集"
        
        final_episodes.append({
            'episode_number': episode_num,
            'title': title,
            'url': url,
            'method': 'advanced_extraction'
        })
    
    # Sort by episode number
    final_episodes.sort(key=lambda x: x['episode_number'])
    
    return final_episodes

def save_episodes_to_database(episodes_data):
    """Save episodes to database"""
    with app.app_context():
        content = Content.query.filter_by(title='Super Cube').first()
        if not content:
            print("❌ Super Cube content not found")
            return
        
        created_count = 0
        for ep_data in episodes_data:
            episode_number = ep_data['episode_number']
            
            existing = Episode.query.filter_by(
                content_id=content.id,
                episode_number=episode_number
            ).first()
            
            if existing:
                print(f"⚠️ Episode {episode_number} exists, updating...")
                existing.embed_url = ep_data['url']
                existing.title = ep_data['title']
            else:
                new_episode = Episode(
                    content_id=content.id,
                    episode_number=episode_number,
                    title=ep_data['title'],
                    embed_url=ep_data['url'],
                    m3u8_url=None,
                    dash_url=None,
                    thumbnail_url=None
                )
                db.session.add(new_episode)
                created_count += 1
                print(f"✅ Created Episode {episode_number}: {ep_data['title']}")
        
        try:
            db.session.commit()
            total_count = Episode.query.filter_by(content_id=content.id).count()
            print(f"\n🎉 SUCCESS! Total episodes: {total_count}")
            print(f"📊 Created: {created_count} new episodes")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Database error: {e}")

if __name__ == "__main__":
    episodes = get_all_super_cube_episodes()
    
    print(f"\n📋 FOUND {len(episodes)} EPISODES:")
    for ep in episodes[:5]:  # Show first 5
        print(f"  Episode {ep['episode_number']}: {ep['title']}")
    
    if len(episodes) > 5:
        print(f"  ... and {len(episodes) - 5} more episodes")
    
    if episodes:
        save_episodes_to_database(episodes)
    else:
        print("❌ No episodes found")