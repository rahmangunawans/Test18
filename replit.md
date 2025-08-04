# AniFlix - Anime and Movie Streaming Platform

## Overview
AniFlix is a premium anime and movie streaming platform designed to offer a Netflix-like experience for anime content. It supports user authentication, subscription management (free and VIP tiers), video streaming, and comprehensive admin controls. The platform aims to provide a robust and enjoyable content consumption experience with features like content restrictions based on subscription status.

## User Preferences
Preferred communication style: Simple, everyday language.
Database preference: Always use Supabase PostgreSQL database exclusively - no fallback mechanisms.
Code cleanliness: Remove redundant maintenance and setup scripts to keep codebase clean.
Auto Scrape Enhancement: Enhanced auto scrape functionality in admin interface to include thumbnail and duration extraction from IQiyi episodes. The scraper now extracts episode thumbnails and duration data directly from the playlist metadata for improved content management. Fixed duration display format from "1260 min" to proper "21:00" format using template filter. Enhanced description extraction to prioritize detailed album descriptions over simple episode titles (August 4, 2025).

## System Architecture

### Backend
- **Framework**: Flask with SQLAlchemy ORM.
- **Database**: PostgreSQL (exclusively Supabase).
- **Authentication**: Flask-Login for session-based user authentication. Admin users are identified by specific email patterns.
- **Payment Processing**: Stripe integration for subscription management.

### Frontend
- **Templating**: Jinja2 for responsive web pages.
- **Styling**: Tailwind CSS for modern UI and responsive design.
- **JavaScript**: Vanilla JS for interactivity and Plyr.io for video playback.
- **UI/UX**: Focus on a clean, modern, and responsive interface with consistent styling, animations, and visual feedback. Two-level navigation (App Header and Horizontal Navigation Bar) with optimized spacing and mobile responsiveness.

### Key Features
- **User Management**: Registration, login, role-based access control (user/admin), session management.
- **Subscription System**: Free tier (limited access) and multiple VIP tiers with Stripe for payments and content access restrictions.
- **Content Management**: Support for anime series, movies, and donghua with episode organization, genre categorization, and filtering. Admin interface for CRUD operations on content and users.
- **Video Streaming**: Plyr.io player with HLS.js support for M3U8 streams, progress tracking, resume functionality, quality controls, and speed settings. Supports M3U8, Embed, and IQiyi streaming servers. VIP-exclusive download functionality is available.
- **Admin Panel**: Dashboard for statistics, user management, content/episode management, system settings, and maintenance controls.
- **Data Integration**: AniList and MyAnimeList API integration for automated content population (title, description, genres, studio, episodes, status, ratings, thumbnails, character overview, trailer URLs). IQiyi scraping for episode URLs and subtitles.

## External Dependencies

- **Stripe**: For subscription payment processing and webhook handling.
- **Supabase PostgreSQL**: Exclusive primary database with SSL connection.
- **Tailwind CSS**: Via CDN for styling.
- **Font Awesome**: Icon library.
- **Google Fonts**: Poppins font family.
- **Plyr.io**: Modern video player library with extensive customization and features.
- **HLS.js**: For M3U8 streaming support with Plyr.io video player.
- **AniList API**: For automated anime/donghua content data fetching.
- **Jikan API (MyAnimeList)**: Alternative data source for content fetching.
- **YouTube (web scraping)**: For automatic trailer URL detection.
- **IQiyi**: For specific M3U8 and subtitle extraction via a dedicated scraper.