#!/usr/bin/env python3
"""
Test script to check AniList API studio information
"""

from AnilistPython import Anilist
import json

def test_anilist_studio_info():
    """Test getting studio information from AniList API"""
    
    anilist = Anilist()
    
    test_anime = [
        'no game no life',
        'demon slayer',
        'attack on titan',
        'naruto',
        'jujutsu kaisen',
        'death note',
        'my hero academia',
        'one piece',
        'solo leveling'
    ]
    
    print("🎯 Testing AniList Studio Information")
    print("=" * 60)
    
    for anime_title in test_anime:
        try:
            print(f"\n📺 Testing: {anime_title}")
            anime_info = anilist.get_anime(anime_title)
            
            if anime_info:
                print(f"   Title: {anime_info.get('name_romaji', 'N/A')}")
                
                # Check all possible studio fields
                studio_fields = ['studio', 'studios', 'animation_studio', 'production_studio']
                found_studio = False
                
                for field in studio_fields:
                    if field in anime_info and anime_info[field]:
                        print(f"   Studio ({field}): {anime_info[field]}")
                        found_studio = True
                
                if not found_studio:
                    print("   Studio: NOT FOUND")
                
                # Print all available fields to see what's available
                print(f"   Available fields: {list(anime_info.keys())}")
                
                # Check if there's any field containing 'studio'
                studio_related = [k for k in anime_info.keys() if 'studio' in k.lower()]
                if studio_related:
                    print(f"   Studio-related fields: {studio_related}")
                
            else:
                print("   ERROR: No anime info found")
                
        except Exception as e:
            print(f"   ERROR: {str(e)}")
    
    print("\n" + "=" * 60)
    print("Testing complete!")

if __name__ == "__main__":
    test_anilist_studio_info()