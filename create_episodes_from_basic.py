#!/usr/bin/env python3
"""
Script to directly add episodes to database using basic scraping results
"""
from app import app, db
from models import Content, Episode
from simple_episode_scraper import scrape_basic_episodes

def create_episodes_directly():
    """Create episodes directly from basic scraping"""
    with app.app_context():
        # Find or create Super Cube content
        content = Content.query.filter_by(title='Super Cube').first()
        if not content:
            print("❌ Super Cube content not found in database")
            return
        
        print(f"✅ Found content: {content.title} (ID: {content.id})")
        
        # Clear existing episodes
        existing_count = Episode.query.filter_by(content_id=content.id).count()
        print(f"📊 Found {existing_count} existing episodes")
        
        # Scrape using basic method
        playlist_url = "https://www.iq.com/play/super-cube-115bxuuq7eo?lang=en_us"
        result = scrape_basic_episodes(playlist_url, max_episodes=22)  # Try to get all 22
        
        if not result.get('success'):
            print(f"❌ Basic scraping failed: {result.get('error')}")
            return
        
        episodes_data = result['episodes']
        print(f"✅ Scraped {len(episodes_data)} episodes")
        
        # Create episodes
        created_count = 0
        for ep_data in episodes_data:
            episode_number = ep_data['episode_number']
            
            # Check if episode already exists
            existing_episode = Episode.query.filter_by(
                content_id=content.id,
                episode_number=episode_number
            ).first()
            
            if existing_episode:
                print(f"⚠️  Episode {episode_number} already exists, skipping")
                continue
            
            # Create new episode
            new_episode = Episode(
                content_id=content.id,
                episode_number=episode_number,
                title=ep_data['title'],
                m3u8_url=None,  # Basic scraping doesn't provide M3U8
                embed_url=ep_data['url'],  # Use the episode URL as embed
                dash_url=None,
                thumbnail_url=None
            )
            
            db.session.add(new_episode)
            created_count += 1
            print(f"✅ Created Episode {episode_number}: {ep_data['title']}")
        
        try:
            db.session.commit()
            print(f"\n🎉 SUCCESS: Created {created_count} new episodes!")
            print(f"📊 Total episodes for Super Cube: {Episode.query.filter_by(content_id=content.id).count()}")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Database error: {str(e)}")

if __name__ == "__main__":
    create_episodes_directly()