#!/usr/bin/env python3
"""
Test script to get studio information directly from AniList GraphQL API
"""

import requests
import json

def test_anilist_graphql_studio():
    """Test getting studio information from AniList GraphQL API"""
    
    # GraphQL query to get anime with studio information
    query = """
    query ($search: String) {
        Media(search: $search, type: ANIME) {
            id
            title {
                romaji
                english
            }
            studios(isMain: true) {
                nodes {
                    name
                    id
                }
            }
            format
            status
            episodes
            averageScore
            genres
            startDate {
                year
            }
        }
    }
    """
    
    test_anime = [
        'No Game No Life',
        'Demon Slayer',
        'Attack on Titan',
        'Naruto',
        'Jujutsu Kaisen',
        'Death Note',
        'My Hero Academia',
        'One Piece',
        'Solo Leveling'
    ]
    
    url = 'https://graphql.anilist.co'
    
    print("🎯 Testing AniList GraphQL Studio Information")
    print("=" * 70)
    
    for anime_title in test_anime:
        try:
            variables = {'search': anime_title}
            response = requests.post(url, json={'query': query, 'variables': variables})
            
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data and data['data']['Media']:
                    media = data['data']['Media']
                    
                    title = media['title']['english'] or media['title']['romaji']
                    studios = media.get('studios', {}).get('nodes', [])
                    
                    print(f"\n📺 {anime_title}")
                    print(f"   Title: {title}")
                    
                    if studios:
                        studio_names = [studio['name'] for studio in studios]
                        print(f"   Studio(s): {', '.join(studio_names)}")
                    else:
                        print("   Studio(s): NOT FOUND")
                    
                    print(f"   Score: {media.get('averageScore', 'N/A')}")
                    print(f"   Episodes: {media.get('episodes', 'N/A')}")
                    
                else:
                    print(f"\n📺 {anime_title}")
                    print("   ERROR: No media found")
                    
            else:
                print(f"\n📺 {anime_title}")
                print(f"   ERROR: API request failed - {response.status_code}")
                
        except Exception as e:
            print(f"\n📺 {anime_title}")
            print(f"   ERROR: {str(e)}")
    
    print("\n" + "=" * 70)
    print("Testing complete!")

if __name__ == "__main__":
    test_anilist_graphql_studio()