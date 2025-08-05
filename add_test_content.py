#!/usr/bin/env python3
"""
Add test content for testing video players
"""
import os
import sys
sys.path.append('.')

from app import app, db
from models import Content, Episode

def add_test_content():
    with app.app_context():
        print("Creating test content...")
        
        # Check if content already exists
        existing = Content.query.first()
        if existing:
            print(f"Content already exists: {existing.title}")
            return existing.id
        
        # Create test anime content
        test_content = Content(
            title="Attack on Titan",
            description="Humanity fights for survival against giant humanoid Titans that have brought civilization to the brink of extinction.",
            type="anime",
            status="completed",
            total_episodes=25,
            release_year=2013,
            genres="Action, Drama, Fantasy",
            rating=9.0,
            studio="Studio Pierrot",
            thumbnail_url="https://cdn.myanimelist.net/images/anime/10/47347.jpg",
            banner_url="https://cdn.myanimelist.net/images/anime/10/47347l.jpg",
            is_featured=True,
            is_vip_exclusive=False
        )
        
        db.session.add(test_content)
        db.session.flush()  # Get the ID
        
        # Create test episode
        test_episode = Episode(
            content_id=test_content.id,
            episode_number=1,
            title="To You, in 2000 Years: The Fall of Shiganshina, Part 1",
            description="The Colossal Titan appears and breaches the wall of Shiganshina District, letting other Titans invade the town.",
            duration="24:00",
            
            # Different server URLs for testing
            server_m3u8_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",  # Test M3U8 URL
            server_embed_url="https://www.mp4upload.com/embed-jky4645xkzgk.html",  # Embed URL  
            video_url="https://pomf2.lain.la/f/4gstlbwq.mp4",  # Direct MP4 URL
            iqiyi_play_url="https://www.iq.com/play/1bk9ic4jjh8",  # iQiyi URL
            
            thumbnail_url="https://cdn.myanimelist.net/images/anime/10/47347.jpg",
            is_available=True
        )
        
        db.session.add(test_episode)
        db.session.commit()
        
        print(f"✅ Test content created successfully:")
        print(f"   Content ID: {test_content.id}")
        print(f"   Episode ID: {test_episode.id}")
        print(f"   Watch URL: /watch/{test_content.id}/{test_episode.episode_number}")
        
        return test_content.id

if __name__ == "__main__":
    content_id = add_test_content()
    print(f"\n🎬 You can now test the video players at: /watch/{content_id}/1")