#!/usr/bin/env python3
"""
Script to analyze popular anime studios from AniList API
to help determine which studios are most important to include in our database
"""

import requests
import json
import logging
from collections import Counter
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO)

def get_popular_anime_with_studios():
    """Get popular anime from AniList with their studio information"""
    
    # GraphQL query to get popular anime with studio information
    query = """
    query ($page: Int, $perPage: Int) {
        Page(page: $page, perPage: $perPage) {
            media(type: ANIME, sort: POPULARITY_DESC, status: FINISHED) {
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
                popularity
                averageScore
                genres
                startDate {
                    year
                }
            }
        }
    }
    """
    
    url = 'https://graphql.anilist.co'
    
    all_studios = []
    studio_anime_count = Counter()
    studio_details = {}
    
    # Get multiple pages of popular anime
    for page in range(1, 6):  # Get top 250 popular anime (50 per page)
        variables = {
            'page': page,
            'perPage': 50
        }
        
        try:
            response = requests.post(url, json={'query': query, 'variables': variables})
            data = response.json()
            
            if 'data' in data and 'Page' in data['data']:
                media_list = data['data']['Page']['media']
                
                for anime in media_list:
                    title = anime['title']['english'] or anime['title']['romaji']
                    studios = anime.get('studios', {}).get('nodes', [])
                    
                    for studio in studios:
                        studio_name = studio['name']
                        studio_anime_count[studio_name] += 1
                        
                        if studio_name not in studio_details:
                            studio_details[studio_name] = {
                                'name': studio_name,
                                'id': studio['id'],
                                'anime_count': 0,
                                'popular_anime': [],
                                'avg_score': 0,
                                'total_score': 0,
                                'scored_anime': 0
                            }
                        
                        studio_details[studio_name]['anime_count'] += 1
                        studio_details[studio_name]['popular_anime'].append({
                            'title': title,
                            'popularity': anime['popularity'],
                            'score': anime['averageScore'],
                            'year': anime['startDate']['year'] if anime['startDate'] else None
                        })
                        
                        if anime['averageScore']:
                            studio_details[studio_name]['total_score'] += anime['averageScore']
                            studio_details[studio_name]['scored_anime'] += 1
            
            print(f"Processed page {page}")
            
        except Exception as e:
            logging.error(f"Error fetching page {page}: {str(e)}")
            continue
    
    # Calculate average scores
    for studio_name in studio_details:
        if studio_details[studio_name]['scored_anime'] > 0:
            studio_details[studio_name]['avg_score'] = round(
                studio_details[studio_name]['total_score'] / studio_details[studio_name]['scored_anime'], 1
            )
    
    return studio_anime_count, studio_details

def analyze_studios():
    """Analyze and rank anime studios by importance"""
    
    print("🎯 Menganalisis studio anime populer dari AniList API...")
    studio_counts, studio_details = get_popular_anime_with_studios()
    
    # Filter studios with at least 2 popular anime
    important_studios = {k: v for k, v in studio_details.items() if v['anime_count'] >= 2}
    
    # Sort by anime count and average score
    sorted_studios = sorted(
        important_studios.items(),
        key=lambda x: (x[1]['anime_count'], x[1]['avg_score']),
        reverse=True
    )
    
    print("\n" + "="*80)
    print("📊 STUDIO ANIME PALING PENTING BERDASARKAN ANILIST API")
    print("="*80)
    
    print(f"\n{'Rank':<4} {'Studio Name':<25} {'Anime Count':<12} {'Avg Score':<10} {'Popular Titles'}")
    print("-" * 90)
    
    top_studios = []
    
    for i, (studio_name, details) in enumerate(sorted_studios[:30], 1):
        popular_titles = [anime['title'] for anime in details['popular_anime'][:3]]
        titles_str = ", ".join(popular_titles)
        if len(titles_str) > 40:
            titles_str = titles_str[:37] + "..."
        
        print(f"{i:<4} {studio_name:<25} {details['anime_count']:<12} {details['avg_score']:<10} {titles_str}")
        
        top_studios.append({
            'rank': i,
            'name': studio_name,
            'anime_count': details['anime_count'],
            'avg_score': details['avg_score'],
            'popular_anime': details['popular_anime'][:5],
            'anilist_id': details['id']
        })
    
    # Generate studio categories
    print("\n" + "="*80)
    print("🏆 KATEGORI STUDIO BERDASARKAN POPULARITAS")
    print("="*80)
    
    tier_s = [s for s in top_studios if s['anime_count'] >= 8]
    tier_a = [s for s in top_studios if 5 <= s['anime_count'] < 8]
    tier_b = [s for s in top_studios if 3 <= s['anime_count'] < 5]
    tier_c = [s for s in top_studios if s['anime_count'] == 2]
    
    print(f"\n🥇 TIER S - Super Studio (8+ anime populer): {len(tier_s)} studio")
    for studio in tier_s[:10]:
        print(f"   • {studio['name']} ({studio['anime_count']} anime, score: {studio['avg_score']})")
    
    print(f"\n🥈 TIER A - Top Studio (5-7 anime populer): {len(tier_a)} studio")
    for studio in tier_a[:10]:
        print(f"   • {studio['name']} ({studio['anime_count']} anime, score: {studio['avg_score']})")
    
    print(f"\n🥉 TIER B - Notable Studio (3-4 anime populer): {len(tier_b)} studio")
    for studio in tier_b[:10]:
        print(f"   • {studio['name']} ({studio['anime_count']} anime, score: {studio['avg_score']})")
    
    # Create studio database mapping
    studio_mapping = {}
    for studio in top_studios:
        studio_mapping[studio['name']] = {
            'tier': 'S' if studio['anime_count'] >= 8 else 'A' if studio['anime_count'] >= 5 else 'B' if studio['anime_count'] >= 3 else 'C',
            'anime_count': studio['anime_count'],
            'avg_score': studio['avg_score'],
            'popular_titles': [anime['title'] for anime in studio['popular_anime']]
        }
    
    # Save results to JSON
    with open('studio_analysis_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'analysis_date': '2025-07-30',
            'total_studios_analyzed': len(studio_details),
            'important_studios': len(important_studios),
            'studio_mapping': studio_mapping,
            'tier_breakdown': {
                'tier_s': len(tier_s),
                'tier_a': len(tier_a), 
                'tier_b': len(tier_b),
                'tier_c': len(tier_c)
            }
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Hasil analisis disimpan ke 'studio_analysis_results.json'")
    
    return studio_mapping

if __name__ == "__main__":
    analyze_studios()