"""
Anime Data Integration for AniFlix
Provides functions to search and retrieve anime/manga data from AniList and MyAnimeList APIs
"""

import AnilistPython
import logging
import requests
from typing import Dict, List, Optional, Any
import time

class AnimeDataService:
    def __init__(self):
        """Initialize both AniList and MyAnimeList clients"""
        # Initialize AniList
        try:
            self.anilist = AnilistPython.Anilist()
            logging.info("AniList integration initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize AniList integration: {str(e)}")
            self.anilist = None
        
        # MyAnimeList will use direct HTTP requests to v4 API
        self.mal_base_url = "https://api.jikan.moe/v4"
        logging.info("MyAnimeList (Jikan v4) integration initialized successfully")
    
    def search_anime(self, query: str, source: str = "anilist", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for anime on specified source and return formatted results
        
        Args:
            query: Search query string
            source: Data source ("anilist" or "myanimelist")
            limit: Maximum number of results to return
        
        Returns:
            List of dictionaries containing anime information
        """
        if source == "myanimelist":
            return self._search_myanimelist(query, limit)
        else:
            return self._search_anilist(query, limit)
    
    def _search_anilist(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search anime using AniList API"""
        if not self.anilist:
            return []
        
        try:
            results = []
            
            # Try multiple variations of the search query for better results
            search_variations = [
                query.strip(),
                query.strip().title(),
                query.strip().lower()
            ]
            
            # Remove duplicates while preserving order
            search_variations = list(dict.fromkeys(search_variations))
            
            for search_query in search_variations[:2]:  # Limit to first 2 variations
                try:
                    # Search anime by name
                    anime_data = self.anilist.get_anime(search_query, manual_select=False)
                    
                    if anime_data and isinstance(anime_data, dict):
                        # Format the result for our application
                        formatted_result = self._format_anilist_data(anime_data)
                        if formatted_result and formatted_result not in results:
                            results.append(formatted_result)
                            if len(results) >= limit:
                                break
                                
                except Exception as search_error:
                    logging.debug(f"AniList search variation '{search_query}' failed: {str(search_error)}")
                    continue
            
            return results
            
        except Exception as e:
            logging.error(f"Error searching anime on AniList '{query}': {str(e)}")
            return []
    
    def _search_myanimelist(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search anime using MyAnimeList (Jikan v4) API"""
        try:
            # Clean and prepare query
            if not query or not query.strip():
                logging.warning("Empty query provided to MyAnimeList search")
                return []
                
            clean_query = query.strip()
            
            # Make direct HTTP request to Jikan v4 API
            url = f"{self.mal_base_url}/anime"
            params = {
                'q': clean_query,
                'limit': min(limit, 25),  # API max is 25
                'order_by': 'popularity',
                'sort': 'desc'
            }
            
            headers = {
                'User-Agent': 'AniFlix/1.0 (contact@aniflix.com)'
            }
            
            logging.info(f"Searching MyAnimeList for: '{clean_query}' with params: {params}")
            
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            logging.info(f"MyAnimeList API response: {response.status_code}")
            
            if response.status_code == 429:  # Rate limited
                logging.warning("MyAnimeList API rate limited, waiting 2 seconds...")
                time.sleep(2)
                response = requests.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code != 200:
                logging.error(f"MyAnimeList API error: {response.status_code}, Response: {response.text[:200]}")
                return []
            
            search_results = response.json()
            
            if not search_results or 'data' not in search_results:
                logging.warning(f"No data found in MyAnimeList response for query: '{clean_query}'")
                return []
            
            data_results = search_results['data']
            logging.info(f"Found {len(data_results)} results from MyAnimeList")
            
            results = []
            for anime_data in data_results[:limit]:
                formatted_result = self._format_myanimelist_data(anime_data)
                if formatted_result:
                    results.append(formatted_result)
            
            logging.info(f"Successfully formatted {len(results)} MyAnimeList results")
            return results
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error searching MyAnimeList for '{query}': {str(e)}")
            return []
        except Exception as e:
            logging.error(f"Error searching anime on MyAnimeList '{query}': {str(e)}")
            return []
    
    def search_anime_by_id(self, anilist_id: int) -> Optional[Dict[str, Any]]:
        """
        Get anime by AniList ID
        
        Args:
            anilist_id: AniList anime ID
        
        Returns:
            Dictionary containing anime information or None
        """
        if not self.anilist:
            return None
        
        try:
            anime_data = self.anilist.get_anime_with_id(anilist_id)
            
            if not anime_data:
                return None
            
            return self._format_anilist_data(anime_data)
            
        except Exception as e:
            logging.error(f"Error getting anime with ID {anilist_id}: {str(e)}")
            return None
    
    def search_manga(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search for manga on AniList (can be used for manhwa/donghua source material)
        
        Args:
            query: Search query string
        
        Returns:
            Dictionary containing manga information or None
        """
        if not self.anilist:
            return None
        
        try:
            manga_data = self.anilist.get_manga(query, manual_select=False)
            
            if not manga_data:
                return None
            
            return self._format_manga_data(manga_data)
            
        except Exception as e:
            logging.error(f"Error searching manga '{query}': {str(e)}")
            return None
    
    def _format_anilist_data(self, anime_data: Any) -> Dict[str, Any]:
        """
        Format AniList anime data for our application
        
        Args:
            anime_data: Raw anime data from AniList (can be dict or other format)
        
        Returns:
            Formatted dictionary for our Content model
        """
        try:
            # Handle different data formats from AniList
            if isinstance(anime_data, str):
                logging.error(f"Received string data instead of dict: {anime_data}")
                return {}
            
            if not isinstance(anime_data, dict):
                logging.error(f"Unexpected data type: {type(anime_data)}")
                return {}
            
            # Determine content type based on format
            content_type = 'anime'  # Default
            anime_format = anime_data.get('format', '').lower()
            
            if 'movie' in anime_format or anime_format == 'film':
                content_type = 'movie'
            elif any(keyword in str(anime_data.get('name_english', '')).lower() or 
                    keyword in str(anime_data.get('name_romaji', '')).lower() 
                    for keyword in ['chinese', 'donghua']):
                content_type = 'donghua'
            
            # Get title (prefer English, fallback to Romaji)
            title = anime_data.get('name_english') or anime_data.get('name_romaji') or 'Unknown Title'
            
            # Format genres
            genres = anime_data.get('genres', [])
            genre_str = ', '.join(genres) if genres else ''
            
            # Get description and clean it
            description = anime_data.get('desc', '').replace('<br>', '\n').replace('<i>', '').replace('</i>', '').replace('<br><br>', '\n\n')
            # Remove extra whitespace and newlines
            description = ' '.join(description.split())
            if len(description) > 1000:
                description = description[:997] + '...'
            
            # Get episodes count (use airing_episodes field)
            episodes = anime_data.get('airing_episodes')
            total_episodes = episodes if episodes and episodes > 0 else None
            
            # Determine status from airing_status
            status = 'unknown'
            anilist_status = anime_data.get('airing_status', '').lower()
            if 'finished' in anilist_status or 'completed' in anilist_status:
                status = 'completed'
            elif 'releasing' in anilist_status or 'ongoing' in anilist_status or 'airing' in anilist_status:
                status = 'ongoing'
            
            # Get studio information from available data
            studio = ''
            # Try to extract studio from different possible fields
            if 'studios' in anime_data and anime_data['studios']:
                if isinstance(anime_data['studios'], list):
                    studio = anime_data['studios'][0] if anime_data['studios'] else ''
                else:
                    studio = str(anime_data['studios'])
            elif 'studio' in anime_data:
                studio = str(anime_data['studio']) if anime_data['studio'] else ''
            elif 'producer' in anime_data:
                studio = str(anime_data['producer']) if anime_data['producer'] else ''
            
            # If still no studio, try to get it from GraphQL API first, then fallback to mapping
            if not studio:
                studio = self._get_studio_from_graphql(title)
                if not studio:
                    studio = self._find_studio_info(title)
            
            # Get year from starting_time (format: "4/7/2013")
            year = None
            start_time = anime_data.get('starting_time', '')
            if start_time:
                try:
                    # Extract year from date string like "4/7/2013"
                    year_str = start_time.split('/')[-1]
                    year = int(year_str) if year_str.isdigit() else None
                except:
                    year = None
            
            # Get rating (convert from 0-100 to 0-10 scale)
            average_score = anime_data.get('average_score')
            rating = round(average_score / 10, 1) if average_score else None
            
            # Get cover image
            cover_image = anime_data.get('cover_image')
            thumbnail_url = cover_image if cover_image else ''
            
            # Try to find trailer URL
            trailer_url = self._find_trailer_url(title)
            
            # Try to get character information from AniList
            character_overview = self._get_character_overview_anilist(anime_data, title, content_type)

            return {
                'title': title,
                'description': description,
                'character_overview': character_overview,
                'genre': genre_str,
                'year': year,
                'rating': rating,
                'content_type': content_type,
                'thumbnail_url': thumbnail_url,
                'trailer_url': trailer_url,
                'studio': studio,
                'total_episodes': total_episodes,
                'status': status,
                'anilist_id': None,  # ID not provided in this API format
                'anilist_url': ''  # Cannot generate URL without ID
            }
        
        except Exception as e:
            logging.error(f"Error formatting anime data: {str(e)}")
            return {}
    
    def _find_trailer_url(self, title: str) -> str:
        """
        Try to find YouTube trailer URL for the anime using web scraping
        
        Args:
            title: Anime title
            
        Returns:
            YouTube embed URL or empty string if not found
        """
        try:
            import re
            import urllib.parse
            
            # Clean title for search
            search_title = title.replace(':', '').replace('-', ' ').strip()
            
            # Try to search for trailers using multiple approaches
            search_queries = [
                f"{search_title} trailer",
                f"{search_title} official trailer", 
                f"{search_title} anime trailer",
                f"{search_title} PV"
            ]
            
            for query in search_queries[:2]:  # Limit to first 2 queries
                try:
                    # Create YouTube search URL
                    encoded_query = urllib.parse.quote_plus(query)
                    search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
                    
                    # Use requests to get search results
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    
                    response = requests.get(search_url, headers=headers, timeout=5)
                    
                    if response.status_code == 200:
                        # Look for video IDs in the response
                        video_pattern = r'"videoId":"([a-zA-Z0-9_-]{11})"'
                        matches = re.findall(video_pattern, response.text)
                        
                        if matches:
                            # Return the first video as embed URL
                            video_id = matches[0]
                            return f"https://www.youtube.com/embed/{video_id}"
                            
                except Exception as search_error:
                    logging.debug(f"Trailer search failed for '{query}': {str(search_error)}")
                    continue
                    
            # If web scraping fails, provide a manual search URL that opens in new tab
            encoded_title = urllib.parse.quote_plus(f"{search_title} trailer")
            return f"https://www.youtube.com/results?search_query={encoded_title}"
            
        except Exception as e:
            logging.debug(f"Error finding trailer for '{title}': {str(e)}")
            return ''
    
    def _get_studio_from_graphql(self, title: str) -> str:
        """
        Get studio information directly from AniList GraphQL API
        
        Args:
            title: Anime title to search for
            
        Returns:
            Studio name or empty string if not found
        """
        try:
            import requests
            
            # GraphQL query to get anime with studio information
            query = """
            query ($search: String) {
                Media(search: $search, type: ANIME) {
                    studios(isMain: true) {
                        nodes {
                            name
                        }
                    }
                }
            }
            """
            
            url = 'https://graphql.anilist.co'
            variables = {'search': title}
            
            response = requests.post(url, json={'query': query, 'variables': variables}, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data and data['data']['Media']:
                    media = data['data']['Media']
                    studios = media.get('studios', {}).get('nodes', [])
                    
                    if studios:
                        studio_names = [studio['name'] for studio in studios]
                        studio_name = ', '.join(studio_names)
                        logging.info(f"Found studio from GraphQL for '{title}': {studio_name}")
                        return studio_name
            
            logging.info(f"No studio found from GraphQL for '{title}'")
            return ''
            
        except Exception as e:
            logging.error(f"Error getting studio from GraphQL for '{title}': {str(e)}")
            return ''
    
    def _find_studio_info(self, title: str) -> str:
        """
        Find studio information based on AniList API analysis data
        Uses real data from top anime studios by popularity and quality
        
        Args:
            title: Anime title
            
        Returns:
            Studio name or empty string if not found
        """
        try:
            # Studio database based on AniList API analysis - TIER S Studios (Most Important)
            studio_mappings = {
                # A-1 Pictures (21 popular anime) - Tier S
                'sword art online': 'A-1 Pictures',
                'your lie in april': 'A-1 Pictures',
                'erased': 'A-1 Pictures',
                'kaguya-sama': 'A-1 Pictures',
                'seven deadly sins': 'A-1 Pictures',
                'fairy tail': 'A-1 Pictures',
                
                # bones (20 popular anime) - Tier S
                'my hero academia': 'bones',
                'boku no hero academia': 'bones',
                'fullmetal alchemist': 'bones',
                'mob psycho 100': 'bones',
                'noragami': 'bones',
                'soul eater': 'bones',
                
                # MAPPA (16 popular anime) - Tier S
                'jujutsu kaisen': 'MAPPA',
                'attack on titan final season': 'MAPPA',
                'chainsaw man': 'MAPPA',
                'kakegurui': 'MAPPA',
                'yuri on ice': 'MAPPA',
                'vinland saga': 'MAPPA',
                
                # MADHOUSE (16 popular anime) - Tier S
                'death note': 'MADHOUSE',
                'hunter x hunter': 'MADHOUSE',
                'one punch man': 'MADHOUSE',
                'no game no life': 'MADHOUSE',
                'parasyte': 'MADHOUSE',
                'overlord': 'MADHOUSE',
                
                # J.C.STAFF (14 popular anime) - Tier S
                'toradora': 'J.C.STAFF',
                'one punch man season 2': 'J.C.STAFF',
                'food wars': 'J.C.STAFF',
                'danmachi': 'J.C.STAFF',
                'saiki k': 'J.C.STAFF',
                
                # Production I.G (12 popular anime) - Tier S
                'haikyuu': 'Production I.G',
                'psycho-pass': 'Production I.G',
                'kuroko no basket': 'Production I.G',
                'ghost in the shell': 'Production I.G',
                
                # WIT STUDIO (11 popular anime) - Tier S
                'attack on titan': 'WIT STUDIO',
                'shingeki no kyojin': 'WIT STUDIO',
                'spy x family': 'WIT STUDIO',
                'kabaneri': 'WIT STUDIO',
                
                # CloverWorks (11 popular anime) - Tier S
                'the promised neverland': 'CloverWorks',
                'rascal does not dream': 'CloverWorks',
                'horimiya': 'CloverWorks',
                
                # Kyoto Animation (10 popular anime) - Tier S
                'violet evergarden': 'Kyoto Animation',
                'a silent voice': 'Kyoto Animation',
                'hyouka': 'Kyoto Animation',
                'k-on': 'Kyoto Animation',
                'clannad': 'Kyoto Animation',
                
                # ufotable (9 popular anime) - Tier S
                'demon slayer': 'ufotable',
                'kimetsu no yaiba': 'ufotable',
                'fate zero': 'ufotable',
                'fate stay night': 'ufotable',
                
                # Studio Pierrot (9 popular anime) - Tier S
                'naruto': 'Studio Pierrot',
                'naruto shippuden': 'Studio Pierrot',
                'tokyo ghoul': 'Studio Pierrot',
                'bleach': 'Studio Pierrot',
                'black clover': 'Studio Pierrot',
                
                # WHITE FOX (8 popular anime) - Tier S
                'rezero': 'WHITE FOX',
                're:zero': 'WHITE FOX',
                'steins gate': 'WHITE FOX',
                'goblin slayer': 'WHITE FOX',
                
                # TIER A Studios (5-7 popular anime)
                'jojos bizarre adventure': 'David Production',
                'fire force': 'David Production',
                'assassination classroom': 'Lerche',
                'classroom of the elite': 'Lerche',
                'dr stone': 'TMS Entertainment',
                
                # TIER B Studios (3-4 popular anime)
                'code geass': 'Sunrise',
                'cowboy bebop': 'Sunrise',
                'spirited away': 'Studio Ghibli',
                'howls moving castle': 'Studio Ghibli',
                'princess mononoke': 'Studio Ghibli',
                'totoro': 'Studio Ghibli',
                'your name': 'CoMix Wave',
                'weathering with you': 'CoMix Wave',
                'oregairu': "Brain's Base",
                'evangelion': 'Gainax',
                'neon genesis evangelion': 'Gainax',
                'mushoku tensei': 'Studio Bind',
                'oshi no ko': 'Doga Kobo',
                'darling in the franxx': 'TRIGGER',
                'kill la kill': 'TRIGGER',
                
                # Additional major anime
                'one piece': 'Toei Animation',
                'dragon ball': 'Toei Animation',
                'dragon ball z': 'Toei Animation',
                'dragon ball super': 'Toei Animation',
                'sailor moon': 'Toei Animation',
                'pokemon': 'OLM',
                'komi': 'OLM',
            }
            
            # Search for studio match with improved accuracy
            title_lower = title.lower().strip()
            
            # Direct match first
            if title_lower in studio_mappings:
                logging.info(f"Direct studio match for '{title}': {studio_mappings[title_lower]}")
                return studio_mappings[title_lower]
            
            # Partial match
            for key, studio in studio_mappings.items():
                if key in title_lower or any(word in title_lower for word in key.split() if len(word) > 3):
                    logging.info(f"Partial studio match for '{title}': {studio}")
                    return studio
            
            logging.info(f"No studio mapping found for '{title}'")
            return ''  # No studio information found
            
        except Exception as e:
            logging.error(f"Error finding studio for '{title}': {str(e)}")
            return ''
    
    def _format_myanimelist_data(self, anime_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format MyAnimeList anime data for our application
        
        Args:
            anime_data: Raw anime data from MyAnimeList API
            
        Returns:
            Formatted dictionary for our Content model
        """
        try:
            # Get title (prefer English, fallback to original)
            title = anime_data.get('title_english') or anime_data.get('title') or 'Unknown Title'
            
            # Get content type
            content_type = 'anime'
            anime_type = anime_data.get('type', '').lower()
            if 'movie' in anime_type:
                content_type = 'movie'
            
            # Format genres
            genres = anime_data.get('genres', [])
            genre_list = [genre.get('name', '') for genre in genres if isinstance(genre, dict)]
            genre_str = ', '.join(genre_list) if genre_list else ''
            
            # Get description and clean it
            synopsis = anime_data.get('synopsis', '') or ''
            description = synopsis.replace('[Written by MAL Rewrite]', '').strip() if synopsis else ''
            if description and len(description) > 1000:
                description = description[:997] + '...'
            
            # Get episodes count
            episodes = anime_data.get('episodes')
            total_episodes = episodes if episodes and episodes > 0 else None
            
            # Determine status
            status = 'unknown'
            mal_status = anime_data.get('status', '').lower()
            if 'finished' in mal_status or 'completed' in mal_status:
                status = 'completed'
            elif 'airing' in mal_status or 'ongoing' in mal_status:
                status = 'ongoing'
            
            # Get studio information
            studios = anime_data.get('studios', [])
            studio_list = [studio.get('name', '') for studio in studios if isinstance(studio, dict)]
            studio = ', '.join(studio_list) if studio_list else ''
            
            # If no studio from API, try to get from mapping
            if not studio:
                studio = self._find_studio_info(title)
            
            # Get year from aired date
            year = None
            aired = anime_data.get('aired', {})
            if aired and 'from' in aired and aired['from']:
                try:
                    from datetime import datetime
                    aired_date = aired['from']
                    if isinstance(aired_date, str):
                        year = int(aired_date[:4])
                    elif isinstance(aired_date, dict) and 'year' in aired_date:
                        year = aired_date['year']
                except:
                    year = None
            
            # Get rating
            score = anime_data.get('score')
            rating = score if score else None
            
            # Get images
            images = anime_data.get('images', {})
            jpg_images = images.get('jpg', {}) if images else {}
            thumbnail_url = jpg_images.get('large_image_url') or jpg_images.get('image_url') or ''
            
            # Try to find trailer URL
            trailer_url = self._find_trailer_url(title)
            
            # Try to get character information from MyAnimeList
            character_overview = self._get_character_overview_mal(anime_data, title, content_type)

            return {
                'title': title,
                'description': description,
                'character_overview': character_overview,
                'genre': genre_str,
                'year': year,
                'rating': rating,
                'content_type': content_type,
                'thumbnail_url': thumbnail_url,
                'trailer_url': trailer_url,
                'studio': studio,
                'total_episodes': total_episodes,
                'status': status,
                'anilist_id': None,  # MyAnimeList doesn't provide AniList IDs
                'anilist_url': '',
                'mal_id': anime_data.get('mal_id'),
                'mal_url': anime_data.get('url', '')
            }
            
        except Exception as e:
            logging.error(f"Error formatting MyAnimeList data: {str(e)}")
            return {}
    
    def _format_manga_data(self, manga_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format AniList manga data (for donghua source material reference)
        
        Args:
            manga_data: Raw manga data from AniList
        
        Returns:
            Formatted dictionary with manga information
        """
        try:
            title = manga_data.get('name_english') or manga_data.get('name_romaji') or 'Unknown Title'
            
            genres = manga_data.get('genres', [])
            genre_str = ', '.join(genres) if genres else ''
            
            description = manga_data.get('desc', '').replace('<br>', '\n').replace('<i>', '').replace('</i>', '')
            if len(description) > 1000:
                description = description[:997] + '...'
            
            start_date = manga_data.get('starting_time', {})
            year = start_date.get('year') if start_date else None
            
            average_score = manga_data.get('average_score')
            rating = round(average_score / 10, 1) if average_score else None
            
            cover_image = manga_data.get('cover_image')
            thumbnail_url = cover_image if cover_image else ''
            
            return {
                'title': title,
                'description': description,
                'genre': genre_str,
                'year': year,
                'rating': rating,
                'thumbnail_url': thumbnail_url,
                'anilist_id': manga_data.get('id'),
                'anilist_url': f"https://anilist.co/manga/{manga_data.get('id')}" if manga_data.get('id') else ''
            }
        
        except Exception as e:
            logging.error(f"Error formatting manga data: {str(e)}")
            return {}

    def _get_character_overview_anilist(self, anime_data: Dict[str, Any], title: str, content_type: str) -> str:
        """
        Get character overview information from AniList data with detailed character profiles
        
        Args:
            anime_data: Raw anime data from AniList
            title: Anime title
            content_type: Type of content (anime, movie, donghua)
            
        Returns:
            Character overview string with detailed character information including photos, names, voice actors, and descriptions
        """
        try:
            characters_overview = []
            
            # AniList API might have character data in different formats
            if 'characters' in anime_data and anime_data['characters']:
                characters = anime_data['characters']
                if isinstance(characters, list):
                    for i, char in enumerate(characters[:4]):  # Limit to top 4 characters
                        if isinstance(char, dict):
                            char_name = char.get('name', {}).get('full', '') or char.get('name', '')
                            char_role = char.get('role', 'Main Character')
                            char_image = char.get('image', {}).get('large', '') if isinstance(char.get('image'), dict) else ''
                            
                            # Get voice actor information if available
                            voice_actor = 'Unknown Voice Actor'
                            if 'voice_actors' in char and char['voice_actors']:
                                va_data = char['voice_actors'][0] if isinstance(char['voice_actors'], list) else char['voice_actors']
                                if isinstance(va_data, dict):
                                    va_name = va_data.get('name', {}).get('full', '') if isinstance(va_data.get('name'), dict) else va_data.get('name', '')
                                    if va_name:
                                        voice_actor = va_name
                            
                            # Create character description based on role and available info
                            description = char.get('description', f"Karakter {char_role.lower()} dalam {title}")
                            if not description or len(description) < 10:
                                if char_role.lower() == 'main':
                                    description = f"Protagonis utama dalam cerita {title} dengan peran penting dalam alur cerita."
                                elif char_role.lower() == 'supporting':
                                    description = f"Karakter pendukung yang membantu mengembangkan cerita {title}."
                                else:
                                    description = f"Karakter penting dalam {title} yang berkontribusi pada perkembangan plot."
                            
                            if char_name:
                                character_info = f"""
**Karakter {i+1}:**
• Foto: {char_image if char_image else 'Tidak tersedia'}
• Nama Karakter: {char_name}
• Pengisi Suara: {voice_actor}
• Deskripsi: {description[:150]}{'...' if len(description) > 150 else ''}"""
                                characters_overview.append(character_info)
            
            # If we have character data, format it properly
            if characters_overview:
                return '\n'.join(characters_overview)
            
            # Fallback: try to extract character mentions from description and create basic profiles
            description = anime_data.get('desc', '')
            if description:
                character_mentions = self._extract_character_mentions(description)
                if character_mentions:
                    fallback_chars = []
                    for i, char_name in enumerate(character_mentions[:3]):
                        fallback_info = f"""
**Karakter {i+1}:**
• Foto: Tidak tersedia
• Nama Karakter: {char_name}
• Pengisi Suara: Akan diumumkan
• Deskripsi: Karakter penting dalam {title} yang berperan dalam pengembangan cerita."""
                        fallback_chars.append(fallback_info)
                    return '\n'.join(fallback_chars)
            
            # Final fallback with generic character template
            generic_overview = f"""
**Karakter Utama:**
• Foto: Akan ditambahkan
• Nama Karakter: Protagonis {title}
• Pengisi Suara: Akan diumumkan
• Deskripsi: Karakter utama yang menggerakkan alur cerita dalam {title}."""
            
            return generic_overview
                
        except Exception as e:
            logging.error(f"Error getting character overview for '{title}': {str(e)}")
            return f"Informasi karakter untuk {title} akan segera tersedia."
    
    def _get_character_overview_mal(self, anime_data: Dict[str, Any], title: str, content_type: str) -> str:
        """
        Get character overview information from MyAnimeList data with detailed character profiles
        
        Args:
            anime_data: Raw anime data from MyAnimeList
            title: Anime title
            content_type: Type of content (anime, movie, donghua)
            
        Returns:
            Character overview string with detailed character information including photos, names, voice actors, and descriptions
        """
        try:
            characters_overview = []
            
            # Try to get character data from MAL API response
            if 'characters' in anime_data and anime_data['characters']:
                characters = anime_data['characters']
                if isinstance(characters, list):
                    for i, char in enumerate(characters[:4]):  # Limit to top 4 characters
                        if isinstance(char, dict):
                            char_name = char.get('name', '')
                            char_role = char.get('role', 'Main Character')
                            char_image = char.get('images', {}).get('jpg', {}).get('image_url', '') if isinstance(char.get('images'), dict) else ''
                            
                            # Get voice actor information if available
                            voice_actor = 'Unknown Voice Actor'
                            if 'voice_actors' in char and char['voice_actors']:
                                va_data = char['voice_actors'][0] if isinstance(char['voice_actors'], list) else char['voice_actors']
                                if isinstance(va_data, dict):
                                    person = va_data.get('person', {})
                                    if isinstance(person, dict):
                                        va_name = person.get('name', '')
                                        if va_name:
                                            voice_actor = va_name
                            
                            # Create character description
                            description = f"Karakter {char_role.lower()} dalam {title}"
                            if char_role.lower() == 'main':
                                description = f"Protagonis utama dalam cerita {title} dengan peran penting dalam alur cerita."
                            elif char_role.lower() == 'supporting':
                                description = f"Karakter pendukung yang membantu mengembangkan cerita {title}."
                            else:
                                description = f"Karakter penting dalam {title} yang berkontribusi pada perkembangan plot."
                            
                            if char_name:
                                character_info = f"""
**Karakter {i+1}:**
• Foto: {char_image if char_image else 'Tidak tersedia'}
• Nama Karakter: {char_name}
• Pengisi Suara: {voice_actor}
• Deskripsi: {description}"""
                                characters_overview.append(character_info)
            
            # If we have character data, format it properly
            if characters_overview:
                return '\n'.join(characters_overview)
            
            # Try to extract from synopsis and create character profiles
            synopsis = anime_data.get('synopsis', '')
            if synopsis:
                character_mentions = self._extract_character_mentions(synopsis)
                if character_mentions:
                    fallback_chars = []
                    for i, char_name in enumerate(character_mentions[:3]):
                        fallback_info = f"""
**Karakter {i+1}:**
• Foto: Tidak tersedia
• Nama Karakter: {char_name}
• Pengisi Suara: Akan diumumkan
• Deskripsi: Karakter penting dalam {title} yang berperan dalam pengembangan cerita."""
                        fallback_chars.append(fallback_info)
                    return '\n'.join(fallback_chars)
            
            # Get genres to create genre-specific character descriptions
            genres = anime_data.get('genres', [])
            genre_names = [g.get('name', '') for g in genres if isinstance(g, dict)] if genres else []
            
            # Create genre-specific character template
            if any(genre in ['Action', 'Adventure', 'Shounen'] for genre in genre_names):
                character_desc = f"Karakter yang kuat dan berani menghadapi tantangan dalam petualangan {title}."
            elif any(genre in ['Romance', 'Drama', 'Slice of Life'] for genre in genre_names):
                character_desc = f"Karakter yang menghadapi masalah kehidupan sehari-hari dan hubungan personal dalam {title}."
            elif any(genre in ['Fantasy', 'Magic', 'Supernatural'] for genre in genre_names):
                character_desc = f"Karakter dengan kemampuan khusus dalam dunia fantasi {title}."
            else:
                character_desc = f"Karakter utama yang menggerakkan alur cerita dalam {title}."
            
            generic_overview = f"""
**Karakter Utama:**
• Foto: Akan ditambahkan
• Nama Karakter: Protagonis {title}
• Pengisi Suara: Akan diumumkan
• Deskripsi: {character_desc}"""
            
            return generic_overview
                
        except Exception as e:
            logging.error(f"Error getting MAL character overview for '{title}': {str(e)}")
            return f"Informasi karakter untuk {title} akan segera tersedia."
    
    def _extract_character_mentions(self, text: str) -> List[str]:
        """
        Extract potential character names from description text
        
        Args:
            text: Description text to analyze
            
        Returns:
            List of potential character names
        """
        try:
            import re
            
            # Remove HTML tags and clean text
            clean_text = re.sub(r'<[^>]+>', '', text)
            
            # Look for capitalized words that might be character names
            # This is a simple heuristic approach
            potential_names = []
            
            # Pattern for potential names (capitalized words, excluding common words)
            words = clean_text.split()
            skip_words = {'The', 'A', 'An', 'And', 'Or', 'But', 'In', 'On', 'At', 'To', 'For', 'Of', 'With', 'By', 'From', 'Up', 'About', 'Into', 'Through', 'During', 'Before', 'After', 'Above', 'Below', 'Between', 'Among', 'Since', 'Until', 'While', 'Because', 'Although', 'However', 'Therefore', 'Meanwhile', 'Furthermore', 'Moreover', 'Nevertheless'}
            
            for i, word in enumerate(words):
                # Clean word from punctuation
                clean_word = re.sub(r'[^\w]', '', word)
                
                # Check if it's a potential character name
                if (len(clean_word) >= 3 and 
                    clean_word[0].isupper() and 
                    clean_word not in skip_words and
                    not clean_word.isupper()):  # Avoid all-caps words
                    
                    # Check if next word is also capitalized (compound names like "Naruto Uzumaki")
                    if i + 1 < len(words):
                        next_word = re.sub(r'[^\w]', '', words[i + 1])
                        if (len(next_word) >= 2 and 
                            next_word[0].isupper() and 
                            next_word not in skip_words):
                            potential_names.append(f"{clean_word} {next_word}")
                            continue
                    
                    potential_names.append(clean_word)
            
            # Remove duplicates and return top candidates
            unique_names = list(dict.fromkeys(potential_names))  # Preserve order
            return unique_names[:5]  # Return top 5 potential names
            
        except Exception as e:
            logging.error(f"Error extracting character mentions: {str(e)}")
            return []

# Global instance
anime_data_service = AnimeDataService()

# Backward compatibility
anilist_service = anime_data_service