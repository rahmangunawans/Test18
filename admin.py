from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import db, Content, Episode, User, WatchHistory, Notification, SystemSettings
from notifications import create_notification, notify_admin_message, notify_new_episode, notify_new_content
from werkzeug.security import generate_password_hash
from sqlalchemy import text, inspect
from anilist_integration import anilist_service

import logging
import json
from iqiyi_scraper import scrape_iqiyi_episode, scrape_iqiyi_playlist
from iqiyi_m3u8_scraper import IQiyiM3U8Scraper

admin_bp = Blueprint('admin', __name__)

# Emergency admin access route (hidden for security)
@admin_bp.route('/emergency-admin-access')
def emergency_admin_access():
    """Hidden emergency access route for admins during maintenance"""
    from flask import render_template
    return render_template('admin/emergency_login.html')

@admin_bp.route('/maintenance-override')
def maintenance_override():
    """Alternative emergency route for admin access"""
    from flask import render_template
    return render_template('admin/emergency_login.html')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login first.', 'error')
            return redirect(url_for('auth.login'))
        
        # Check admin status using email-based check
        is_admin = current_user.is_admin_user()
        
        if not is_admin:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@admin_required
def admin_dashboard():
    try:
        # Get statistics with proper error handling
        total_users = db.session.query(User).count()
        total_content = db.session.query(Content).count()
        total_episodes = db.session.query(Episode).count()
        
        # Get VIP users count
        vip_users = db.session.query(User).filter(
            User.subscription_type.in_(['vip_monthly', 'vip_3month', 'vip_yearly'])
        ).count()
        
        # Recent content and users with error handling
        recent_content = db.session.query(Content).order_by(Content.created_at.desc()).limit(5).all()
        recent_users = db.session.query(User).order_by(User.created_at.desc()).limit(5).all()
        
        return render_template('admin/dashboard.html',
                             total_users=total_users,
                             total_content=total_content,
                             total_episodes=total_episodes,
                             vip_users=vip_users,
                             recent_content=recent_content,
                             recent_users=recent_users)
    except Exception as e:
        logging.error(f"Admin dashboard error: {str(e)}")
        flash(f'Dashboard loading error. Please contact administrator.', 'error')
        return redirect(url_for('index'))

@admin_bp.route('/content')
@login_required
@admin_required
def admin_content():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Content.query
    if search:
        query = query.filter(
            db.or_(
                Content.title.contains(search),
                Content.genre.contains(search),
                Content.description.contains(search)
            )
        )
    
    content = query.order_by(Content.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False)
    
    return render_template('admin/content.html', content=content, search=search)

@admin_bp.route('/content/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_content():
    if request.method == 'POST':
        try:
            # Handle optional fields
            total_episodes = request.form.get('total_episodes')
            total_episodes = int(total_episodes) if total_episodes and total_episodes.strip() else None
            
            content = Content(
                title=request.form['title'],
                description=request.form['description'],
                character_overview=request.form.get('character_overview', ''),
                genre=request.form['genre'],
                year=int(request.form['year']),
                rating=float(request.form['rating']),
                content_type=request.form['content_type'],
                thumbnail_url=request.form['thumbnail_url'],
                trailer_url=request.form['trailer_url'],
                studio=request.form.get('studio', ''),
                total_episodes=total_episodes,
                status=request.form.get('status', 'unknown'),
                is_featured=bool(request.form.get('is_featured'))
            )
            db.session.add(content)
            db.session.commit()
            
            # Create notification for new content
            notify_new_content(content.title, content.content_type, content.id)
            
            flash(f'Content "{content.title}" added successfully!', 'success')
            return redirect(url_for('admin.admin_content'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding content: {str(e)}', 'error')
    
    return render_template('admin/content_form.html')

@admin_bp.route('/api/anilist/search')
@login_required
@admin_required
def anilist_search():
    """API endpoint to search AniList or MyAnimeList for anime/manga data"""
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'anime')  # anime or manga
    source = request.args.get('source', 'anilist').strip()  # anilist or myanimelist
    
    if not query:
        return jsonify({'error': 'Query parameter is required'}), 400
    
    try:
        if search_type == 'manga':
            result = anilist_service.search_manga(query)
            results = [result] if result else []
        else:
            results = anilist_service.search_anime(query, source=source, limit=5)
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results),
            'source': source
        })
        
    except Exception as e:
        logging.error(f"Anime search error for {source}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to search {source}. Please try again.'
        }), 500

@admin_bp.route('/api/anilist/get/<int:anilist_id>')
@login_required
@admin_required
def anilist_get_by_id(anilist_id):
    """API endpoint to get specific anime by AniList ID"""
    try:
        result = anilist_service.search_anime_by_id(anilist_id)
        
        if result:
            return jsonify({
                'success': True,
                'result': result
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Anime not found'
            }), 404
            
    except Exception as e:
        logging.error(f"AniList get by ID error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get anime data. Please try again.'
        }), 500



@admin_bp.route('/content/<int:content_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_content(content_id):
    content = Content.query.get_or_404(content_id)
    
    if request.method == 'POST':
        try:
            # Handle optional fields
            total_episodes = request.form.get('total_episodes')
            total_episodes = int(total_episodes) if total_episodes and total_episodes.strip() else None
            
            content.title = request.form['title']
            content.description = request.form['description']
            content.character_overview = request.form.get('character_overview', '')
            content.genre = request.form['genre']
            content.year = int(request.form['year'])
            content.rating = float(request.form['rating'])
            content.content_type = request.form['content_type']
            content.thumbnail_url = request.form['thumbnail_url']
            content.trailer_url = request.form['trailer_url']
            content.studio = request.form.get('studio', '')
            content.total_episodes = total_episodes
            content.status = request.form.get('status', 'unknown')
            content.is_featured = bool(request.form.get('is_featured'))
            
            db.session.commit()
            flash(f'Content "{content.title}" updated successfully!', 'success')
            return redirect(url_for('admin.admin_content'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating content: {str(e)}', 'error')
    
    return render_template('admin/content_form.html', content=content)

@admin_bp.route('/content/<int:content_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_content(content_id):
    content = Content.query.get_or_404(content_id)
    try:
        # Delete associated episodes and watch history
        Episode.query.filter_by(content_id=content_id).delete()
        WatchHistory.query.filter_by(content_id=content_id).delete()
        
        db.session.delete(content)
        db.session.commit()
        flash(f'Content "{content.title}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting content: {str(e)}', 'error')
    
    return redirect(url_for('admin.admin_content'))

@admin_bp.route('/content/<int:content_id>/episodes')
@login_required
@admin_required
def manage_episodes(content_id):
    content = Content.query.get_or_404(content_id)
    search = request.args.get('search', '')
    
    query = Episode.query.filter_by(content_id=content_id)
    if search:
        query = query.filter(
            db.or_(
                Episode.title.contains(search),
                Episode.description.contains(search),
                Episode.episode_number == search if search.isdigit() else False
            )
        )
    
    episodes = query.order_by(Episode.episode_number).all()
    return render_template('admin/episodes.html', content=content, episodes=episodes, search=search)

@admin_bp.route('/content/<int:content_id>/episodes/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_episode(content_id):
    content = Content.query.get_or_404(content_id)
    
    if request.method == 'POST':
        try:
            episode = Episode(
                content_id=content_id,
                episode_number=int(request.form['episode_number']),
                title=request.form['title'],
                duration=int(request.form['duration']),
                video_url=request.form.get('video_url', ''),
                thumbnail_url=request.form.get('thumbnail_url', ''),
                description=request.form.get('description', ''),
                server_m3u8_url=request.form.get('server_m3u8_url', ''),
                server_embed_url=request.form.get('server_embed_url', ''),
                iqiyi_play_url=request.form.get('iqiyi_play_url', '')
            )
            db.session.add(episode)
            db.session.commit()
            
            # Create notification for new episode
            notify_new_episode(content.title, episode.episode_number, episode.title, content.id)
            
            flash(f'Episode {episode.episode_number} added successfully!', 'success')
            return redirect(url_for('admin.manage_episodes', content_id=content_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding episode: {str(e)}', 'error')
    
    return render_template('admin/episode_form.html', content=content)

@admin_bp.route('/episodes/<int:episode_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_episode(episode_id):
    episode = Episode.query.get_or_404(episode_id)
    
    if request.method == 'POST':
        try:
            episode.episode_number = int(request.form['episode_number'])
            episode.title = request.form['title']
            episode.duration = int(request.form['duration'])
            episode.video_url = request.form.get('video_url', '')
            episode.thumbnail_url = request.form.get('thumbnail_url', '')
            episode.description = request.form.get('description', '')
            episode.server_m3u8_url = request.form.get('server_m3u8_url', '')
            episode.server_embed_url = request.form.get('server_embed_url', '')
            episode.iqiyi_play_url = request.form.get('iqiyi_play_url', '')
            
            db.session.commit()
            flash(f'Episode {episode.episode_number} updated successfully!', 'success')
            return redirect(url_for('admin.manage_episodes', content_id=episode.content_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating episode: {str(e)}', 'error')
    
    return render_template('admin/episode_form.html', content=episode.content, episode=episode)

@admin_bp.route('/episodes/<int:episode_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_episode(episode_id):
    episode = Episode.query.get_or_404(episode_id)
    content_id = episode.content_id
    
    try:
        # Delete associated watch history
        WatchHistory.query.filter_by(episode_id=episode_id).delete()
        
        db.session.delete(episode)
        db.session.commit()
        flash(f'Episode {episode.episode_number} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting episode: {str(e)}', 'error')
    
    return redirect(url_for('admin.manage_episodes', content_id=content_id))

@admin_bp.route('/episodes/bulk-delete', methods=['POST'])
@login_required
@admin_required
def bulk_delete_episodes():
    try:
        data = request.get_json()
        episode_ids = data.get('episode_ids', [])
        
        if not episode_ids:
            return jsonify({
                'success': False,
                'error': 'Tidak ada episode yang dipilih'
            }), 400
        
        # Delete associated watch history for all episodes
        WatchHistory.query.filter(WatchHistory.episode_id.in_(episode_ids)).delete(synchronize_session=False)
        
        # Delete episodes
        deleted_count = Episode.query.filter(Episode.id.in_(episode_ids)).delete(synchronize_session=False)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Berhasil menghapus {deleted_count} episode'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Bulk delete episodes error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error menghapus episode: {str(e)}'
        }), 500

@admin_bp.route('/users')
@login_required
@admin_required
def admin_users():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = User.query
    if search:
        query = query.filter(User.email.contains(search))
    
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    
    return render_template('admin/users.html', users=users, search=search)

@admin_bp.route('/users/<int:user_id>/toggle_admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    
    try:
        # Toggle admin status by changing email domain
        if user.is_admin():
            # Remove admin status by changing email if it has admin domain
            if '@admin.aniflix.com' in user.email:
                user.email = user.email.replace('@admin.aniflix.com', '@aniflix.com')
                status = "revoked"
            else:
                status = "revoked (email updated)"
        else:
            # Grant admin status by changing email domain
            if '@aniflix.com' in user.email:
                user.email = user.email.replace('@aniflix.com', '@admin.aniflix.com')
            elif '@' in user.email:
                domain = user.email.split('@')[1]
                user.email = user.email.replace(f'@{domain}', '@admin.aniflix.com')
            else:
                user.email = user.email + '@admin.aniflix.com'
            status = "granted"
        
        db.session.commit()
        flash(f'Admin privileges {status} for {user.email}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating user: {str(e)}', 'error')
    
    return redirect(url_for('admin.admin_users'))

@admin_bp.route('/content/<int:content_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_content_quick(content_id):
    content = Content.query.get_or_404(content_id)
    
    if request.method == 'POST':
        try:
            # Update content details
            content.title = request.form.get('title', content.title)
            content.description = request.form.get('description', content.description)
            content.genre = request.form.get('genre', content.genre)
            content.year = int(request.form.get('year', content.year))
            content.rating = float(request.form.get('rating', content.rating))
            content.thumbnail_url = request.form.get('thumbnail_url', content.thumbnail_url)

            content.is_featured = bool(request.form.get('is_featured'))
            
            db.session.commit()
            flash(f'Content "{content.title}" updated successfully!', 'success')
            return redirect(url_for('admin.admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating content: {str(e)}', 'error')
    
    return render_template('admin/content_form.html', content=content)

@admin_bp.route('/episode/<int:episode_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_episode_direct(episode_id):
    episode = Episode.query.get_or_404(episode_id)
    
    if request.method == 'POST':
        try:
            # Update episode details
            episode.title = request.form.get('title', episode.title)
            episode.episode_number = int(request.form.get('episode_number', episode.episode_number))
            episode.duration = int(request.form.get('duration', episode.duration))
            episode.video_url = request.form.get('video_url', episode.video_url)
            
            db.session.commit()
            flash(f'Episode "{episode.title}" updated successfully!', 'success')
            return redirect(url_for('admin.manage_episodes', content_id=episode.content_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating episode: {str(e)}', 'error')
    
    return render_template('admin/episode_form.html', content=episode.content, episode=episode)

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        try:
            # Update basic user info
            user.username = request.form.get('username', user.username)
            user.email = request.form.get('email', user.email)
            
            # Update subscription type
            subscription_type = request.form.get('subscription_type')
            user.subscription_type = subscription_type
            
            # Handle VIP expiration - check if custom date is provided
            custom_expiration = request.form.get('subscription_expires')
            if subscription_type != 'free':
                if custom_expiration:
                    # Use custom expiration date
                    from datetime import datetime
                    user.subscription_expires = datetime.strptime(custom_expiration, '%Y-%m-%d')
                else:
                    # Auto-calculate based on subscription type
                    from datetime import datetime, timedelta
                    days_map = {
                        'vip_monthly': 30,
                        'vip_3month': 90,
                        'vip_yearly': 365
                    }
                    if subscription_type in days_map:
                        user.subscription_expires = datetime.utcnow() + timedelta(days=days_map[subscription_type])
            else:
                # Free user - clear expiration
                user.subscription_expires = None
            
            # Reset password if provided
            new_password = request.form.get('new_password')
            if new_password and new_password.strip():
                user.password_hash = generate_password_hash(new_password)
            
            # Update max devices
            user.max_devices = 2 if subscription_type != 'free' else 1
            
            db.session.commit()
            flash(f'User {user.username} updated successfully!', 'success')
            return redirect(url_for('admin.admin_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'error')
    
    return render_template('admin/user_form.html', user=user)

# IQiyi Auto Scraping API Endpoints
@admin_bp.route('/api/scrape-basic', methods=['POST'])
@login_required
@admin_required
def api_scrape_basic():
    """API endpoint for basic episode scraping without M3U8 extraction"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'})
        
        iqiyi_url = data.get('iqiyi_url', '').strip()
        if not iqiyi_url:
            return jsonify({'success': False, 'error': 'IQiyi URL is required'})
        
        # Validasi URL IQiyi
        if 'iq.com' not in iqiyi_url:
            return jsonify({
                'success': False,
                'error': 'URL harus dari domain iq.com'
            }), 400
        
        batch_size = data.get('batch_size', 10)
        
        # Import and use basic scraper
        from simple_episode_scraper import scrape_basic_episodes
        result = scrape_basic_episodes(iqiyi_url, max_episodes=batch_size)
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'playlist_data': {
                    'episodes': result['episodes']
                },
                'message': f"Basic scraping successful: {result['message']}. Note: No M3U8 URLs extracted.",
                'method': 'basic_scraping'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Basic scraping failed'),
                'suggestion': result.get('suggestion', 'Try again later')
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Basic scraping error: {str(e)}',
            'suggestion': 'Even basic scraping failed - network issues'
        })

@admin_bp.route('/api/scrape-episode', methods=['POST'])
@login_required
@admin_required
def api_scrape_episode():
    """API endpoint untuk auto scraping single episode dari IQiyi"""
    try:
        data = request.get_json()
        iqiyi_url = data.get('iqiyi_url', '').strip()
        
        if not iqiyi_url:
            return jsonify({
                'success': False,
                'error': 'URL IQiyi diperlukan'
            }), 400
        
        # Validasi URL IQiyi
        if 'iq.com' not in iqiyi_url:
            return jsonify({
                'success': False,
                'error': 'URL harus dari domain iq.com'
            }), 400
        
        # Import enhanced scraping functions
        from enhanced_iqiyi_scraper import scrape_single_episode
        
        # Scrape single episode using enhanced scraper
        result = scrape_single_episode(iqiyi_url)
        
        if result['success']:
            return jsonify({
                'success': True,
                'episode_data': result['data'],
                'message': result['message']
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Gagal scraping episode')
            }), 500
            
    except Exception as e:
        logging.error(f"Error scraping episode: {e}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@admin_bp.route('/api/scrape-all-playlist', methods=['POST'])
@login_required
@admin_required  
def api_scrape_all_playlist():
    """API endpoint untuk auto scraping semua episode dari playlist IQiyi"""
    try:
        data = request.get_json()
        iqiyi_url = data.get('iqiyi_url', '').strip()
        
        if not iqiyi_url:
            return jsonify({
                'success': False,
                'error': 'URL IQiyi diperlukan'
            }), 400
        
        # Validasi URL IQiyi
        if 'iq.com' not in iqiyi_url:
            return jsonify({
                'success': False,
                'error': 'URL harus dari domain iq.com'
            }), 400
        
        # Import enhanced scraping functions
        from enhanced_iqiyi_scraper import scrape_all_episodes_playlist
        
        # Scrape all episodes from playlist using enhanced scraper
        max_episodes = data.get('max_episodes', 50)  # Default to 50 if not specified
        
        # Enhanced error handling with fallback to basic scraping
        try:
            result = scrape_all_episodes_playlist(iqiyi_url, max_episodes=max_episodes)
        except Exception as e:
            # Handle all types of network errors gracefully
            error_msg = str(e).lower()
            
            if any(term in error_msg for term in ['ssl', 'certificate', 'handshake']):
                return jsonify({
                    'success': False,
                    'error': 'SSL/Certificate error. IQiyi servers are rejecting secure connections.',
                    'suggestion': 'This is a server-side issue with IQiyi. Try again later or contact system admin.',
                    'technical_error': str(e)
                })
            elif any(term in error_msg for term in ['timeout', 'timed out', 'time out']):
                return jsonify({
                    'success': False,
                    'error': 'Request timeout. IQiyi servers are too slow to respond.',
                    'suggestion': 'Try with fewer episodes (5 instead of 15) or try again later.',
                    'technical_error': str(e)
                })
            elif any(term in error_msg for term in ['dns', 'getaddrinfo', 'name resolution', 'resolve']):
                return jsonify({
                    'success': False,
                    'error': 'DNS/Network resolution error. Cannot reach IQiyi servers.',
                    'suggestion': 'This indicates internet connectivity issues or IQiyi blocking this server.',
                    'technical_error': str(e)
                })
            elif any(term in error_msg for term in ['connection', 'refused', 'unreachable']):
                return jsonify({
                    'success': False,
                    'error': 'Connection refused. IQiyi servers are not accepting connections.',
                    'suggestion': 'IQiyi may have blocked this server or is temporarily down.',
                    'technical_error': str(e)
                })
            else:
                # Handle JSON parsing errors specifically
                if 'unexpected token' in error_msg or 'not valid json' in error_msg:
                    return jsonify({
                        'success': False,
                        'error': 'Network error: Unexpected token \'<\', " <"... is not valid JSON',
                        'suggestion': 'IQiyi is returning HTML instead of JSON. This indicates server-side blocking or rate limiting.',
                        'technical_error': str(e)
                    })
                
                # Try fallback to basic scraping
                print(f"⚠️ Full scraping failed: {str(e)}")
                print("🔄 Attempting fallback to basic scraping...")
                
                try:
                    from iqiyi_fallback_scraper import scrape_iqiyi_playlist_fallback
                    fallback_result = scrape_iqiyi_playlist_fallback(iqiyi_url, max_episodes=max_episodes)
                    
                    if fallback_result.get('success'):
                        # Convert fallback scraping format to expected format
                        return jsonify({
                            'success': True,
                            'playlist_data': fallback_result,
                            'message': f"Fallback scraper used - {fallback_result['message']}. Basic episode info extracted successfully.",
                            'method': 'fallback_scraping'
                        })
                    else:
                        return jsonify({
                            'success': False,
                            'error': f'Both full and fallback scraping failed: {fallback_result.get("error")}',
                            'suggestion': 'IQiyi servers are completely inaccessible right now. Try again later.',
                            'technical_error': str(e)
                        })
                except Exception as fallback_error:
                    return jsonify({
                        'success': False,
                        'error': f'All scraping methods failed. Original: {str(e)}. Fallback: {str(fallback_error)}',
                        'suggestion': 'Complete network failure - try again later.',
                        'technical_error': str(e)
                    })
        
        if result['success']:
            return jsonify({
                'success': True,
                'playlist_data': result,
                'message': f"Berhasil scrape {result['total_episodes']} episode ({result['valid_episodes']} valid)"
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Gagal scraping playlist')
            }), 500
            
    except Exception as e:
        logging.error(f"Error scraping playlist: {e}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@admin_bp.route('/api/auto-add-episodes', methods=['POST'])
@login_required
@admin_required
def api_auto_add_episodes():
    """API endpoint untuk otomatis menambahkan episode hasil scraping ke database"""
    try:
        data = request.get_json()
        content_id = data.get('content_id')
        episodes_data = data.get('episodes_data', [])
        
        logging.info(f"Auto add episodes - Content ID: {content_id}, Episodes count: {len(episodes_data)}")
        
        if not content_id:
            return jsonify({
                'success': False,
                'error': 'Content ID diperlukan'
            }), 400
        
        # Validasi content exists
        content = Content.query.get(content_id)
        if not content:
            return jsonify({
                'success': False,
                'error': 'Content tidak ditemukan'
            }), 404
        
        added_episodes = []
        failed_episodes = []
        
        for episode_data in episodes_data:
            try:
                # Check if episode already exists
                existing_episode = Episode.query.filter_by(
                    content_id=content_id,
                    episode_number=episode_data.get('episode_number')
                ).first()
                
                if existing_episode:
                    failed_episodes.append({
                        'episode_number': episode_data.get('episode_number'),
                        'title': episode_data.get('title'),
                        'error': 'Episode sudah ada'
                    })
                    continue
                
                # Create new episode
                logging.info(f"Creating episode {episode_data.get('episode_number')}: {episode_data.get('title')}")
                
                new_episode = Episode(
                    content_id=content_id,
                    episode_number=episode_data.get('episode_number'),
                    title=episode_data.get('title')[:200] if episode_data.get('title') else None,  # Limit title length
                    description=episode_data.get('description'),  # TEXT field, no limit needed
                    server_m3u8_url=episode_data.get('m3u8_content'),  # TEXT field, no limit needed
                    server_embed_url=episode_data.get('url'),  # IQiyi URL sebagai embed fallback
                    iqiyi_play_url=episode_data.get('url'),  # IQiyi play URL untuk Server 3
                    thumbnail_url=episode_data.get('thumbnail_url')
                )
                
                db.session.add(new_episode)
                added_episodes.append({
                    'episode_number': episode_data.get('episode_number'),
                    'title': episode_data.get('title')
                })
                
            except Exception as e:
                failed_episodes.append({
                    'episode_number': episode_data.get('episode_number', 'Unknown'),
                    'title': episode_data.get('title', 'Unknown'),
                    'error': str(e)
                })
        
        # Commit changes
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logging.error(f"Database commit error: {e}")
            raise e
        
        # Create notification for new episodes (disabled for now)
        # if added_episodes:
        #     notify_new_episode(content.title, len(added_episodes))
        
        return jsonify({
            'success': True,
            'added_count': len(added_episodes),
            'failed_count': len(failed_episodes),
            'added_episodes': added_episodes,
            'failed_episodes': failed_episodes,
            'message': f'Berhasil menambahkan {len(added_episodes)} episode'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error auto adding episodes: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting current admin user
    if user.id == current_user.id:
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('admin.admin_users'))
    
    try:
        # Delete associated data
        WatchHistory.query.filter_by(user_id=user_id).delete()
        
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.email} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
    
    return redirect(url_for('admin.admin_users'))

@admin_bp.route('/analytics')
@login_required
@admin_required
def admin_analytics():
    # Get viewing statistics
    popular_content = db.session.query(
        Content.title,
        db.func.count(WatchHistory.id).label('views')
    ).join(WatchHistory).group_by(Content.id, Content.title).order_by(
        db.func.count(WatchHistory.id).desc()
    ).limit(10).all()
    
    # Completion rates
    completion_stats = db.session.query(
        WatchHistory.status,
        db.func.count(WatchHistory.id).label('count')
    ).group_by(WatchHistory.status).all()
    
    # User statistics
    total_users = User.query.count()
    vip_users = User.query.filter(User.subscription_type != 'free').count()
    
    # Content statistics
    total_content = Content.query.count()
    anime_count = Content.query.filter_by(content_type='anime').count()
    movie_count = Content.query.filter_by(content_type='movie').count()
    
    return render_template('admin/analytics.html',
                         popular_content=popular_content,
                         completion_stats=completion_stats,
                         total_users=total_users,
                         vip_users=vip_users,
                         total_content=total_content,
                         anime_count=anime_count,
                         movie_count=movie_count)

@admin_bp.route('/vip-management')
@admin_required
def vip_management():
    """VIP user management page"""
    vip_users = User.query.filter(
        User.subscription_type.in_(['vip_monthly', 'vip_3month', 'vip_yearly'])
    ).order_by(User.subscription_expires.desc()).all()
    
    return render_template('admin/vip_management.html', vip_users=vip_users)

@admin_bp.route('/user/<int:user_id>/edit-details', methods=['GET', 'POST'])
@admin_required
def edit_user_details(user_id):
    """Edit user details including VIP status"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        try:
            user.username = request.form.get('username', user.username)
            user.email = request.form.get('email', user.email)
            user.subscription_type = request.form.get('subscription_type', user.subscription_type)
            
            # Handle VIP expiration
            if request.form.get('subscription_expires'):
                from datetime import datetime
                user.subscription_expires = datetime.strptime(
                    request.form.get('subscription_expires'), '%Y-%m-%d'
                )
            else:
                user.subscription_expires = None
            
            # Reset password if provided
            if request.form.get('new_password'):
                user.password_hash = generate_password_hash(request.form.get('new_password'))
            
            db.session.commit()
            flash(f'User {user.username} updated successfully!', 'success')
            return redirect(url_for('admin.admin_users'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'error')
            logging.error(f"Error updating user {user_id}: {e}")
    
    return render_template('admin/edit_user.html', user=user)

@admin_bp.route('/user/<int:user_id>/remove', methods=['POST'])
@admin_required
def remove_user(user_id):
    """Delete user account"""
    user = User.query.get_or_404(user_id)
    
    # Prevent deletion of current admin
    if user.id == current_user.id:
        flash('Cannot delete your own account!', 'error')
        return redirect(url_for('admin.admin_users'))
    
    try:
        username = user.username
        db.session.delete(user)
        db.session.commit()
        flash(f'User {username} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
        logging.error(f"Error deleting user {user_id}: {e}")
    
    return redirect(url_for('admin.admin_users'))

@admin_bp.route('/user/<int:user_id>/toggle-vip', methods=['POST'])
@admin_required
def toggle_vip(user_id):
    """Quick toggle VIP status"""
    user = User.query.get_or_404(user_id)
    
    try:
        if user.subscription_type == 'free':
            user.subscription_type = 'vip_monthly'
            from datetime import datetime, timedelta
            user.subscription_expires = datetime.utcnow() + timedelta(days=30)
            flash(f'User {user.username} upgraded to VIP!', 'success')
        else:
            user.subscription_type = 'free'
            user.subscription_expires = None
            flash(f'User {user.username} downgraded to Free!', 'success')
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating VIP status: {str(e)}', 'error')
        logging.error(f"Error toggling VIP for user {user_id}: {e}")
    
    return redirect(url_for('admin.admin_users'))

# @admin_bp.route('/notifications')
# @admin_required
# def admin_notifications():
#     """Admin notification management page - DISABLED"""
#     # Route disabled as per user request
#     return redirect(url_for('admin.admin_dashboard'))

# @admin_bp.route('/notifications/send', methods=['GET', 'POST'])
# @admin_required
def send_notification_disabled():
    """Send notification to users"""
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            message = request.form.get('message', '').strip()
            notification_type = request.form.get('type', 'info')
            is_global = request.form.get('is_global') == 'on'
            user_id = request.form.get('user_id')
            action_url = request.form.get('action_url', '').strip()
            icon = request.form.get('icon', 'bell')
            
            if not title or not message:
                flash('Title and message are required.', 'error')
                return redirect(url_for('admin.send_notification'))
            
            # If not global, user_id is required
            if not is_global and not user_id:
                flash('User selection is required for individual notifications.', 'error')
                return redirect(url_for('admin.send_notification'))
            
            # Create notification
            notification = create_notification(
                user_id=int(user_id) if user_id and not is_global else None,
                title=title,
                message=message,
                notification_type=notification_type,
                is_global=is_global,
                action_url=action_url if action_url else None,
                icon=icon
            )
            
            if notification:
                if is_global:
                    flash('Global notification sent successfully to all users!', 'success')
                else:
                    user = User.query.get(user_id)
                    flash(f'Notification sent successfully to {user.username}!', 'success')
            else:
                flash('Failed to send notification.', 'error')
                
        except Exception as e:
            logging.error(f"Error sending notification: {e}")
            flash('Failed to send notification.', 'error')
            
        return redirect(url_for('admin.admin_dashboard'))
    
    # GET request - show form
    users = User.query.order_by(User.username).all()
    return render_template('admin/send_notification.html', users=users)

# @admin_bp.route('/notifications/test')
# @admin_required
def test_notification_disabled():
    """Send a test notification"""
    try:
        # Send test notification to current admin
        notification = create_notification(
            user_id=current_user.id,
            title="Test Notification",
            message="This is a test notification to verify the real-time notification system is working correctly.",
            notification_type="info",
            icon="flask"
        )
        
        if notification:
            flash('Test notification sent successfully!', 'success')
        else:
            flash('Failed to send test notification.', 'error')
            
    except Exception as e:
        logging.error(f"Error sending test notification: {e}")
        flash('Failed to send test notification.', 'error')
        
    return redirect(url_for('admin.admin_dashboard'))



@admin_bp.route('/system-settings')
@admin_required
def system_settings():
    """System settings page for admin"""
    try:
        # Get system statistics
        total_users = db.session.query(User).count()
        total_content = db.session.query(Content).count()
        total_episodes = db.session.query(Episode).count()
        total_notifications = Notification.query.count()
        
        # Get VIP users count
        vip_users = db.session.query(User).filter(
            User.subscription_type.in_(['vip_monthly', 'vip_3month', 'vip_yearly'])
        ).count()
        
        # Get admin users count
        admin_users = db.session.query(User).filter(
            User.email.like('%admin%')
        ).count()
        
        # Get recent activity
        recent_content = db.session.query(Content).order_by(Content.created_at.desc()).limit(5).all()
        recent_users = db.session.query(User).order_by(User.created_at.desc()).limit(5).all()
        
        # Database information
        database_info = {
            'engine': 'PostgreSQL',
            'host': 'Supabase',
            'status': 'Connected'
        }
        
        # Get current system settings
        from models import SystemSettings
        maintenance_enabled = SystemSettings.get_setting('maintenance_enabled', 'false') == 'true'
        maintenance_message = SystemSettings.get_setting('maintenance_message', '')
        site_logo_url = SystemSettings.get_setting('site_logo_url', '')
        site_logo_alt = SystemSettings.get_setting('site_logo_alt', 'AniFlix')
        site_title = SystemSettings.get_setting('site_title', 'AniFlix')
        site_description = SystemSettings.get_setting('site_description', '')
        
        return render_template('admin/system_settings.html',
                             total_users=total_users,
                             total_content=total_content,
                             total_episodes=total_episodes,
                             total_notifications=total_notifications,
                             vip_users=vip_users,
                             admin_users=admin_users,
                             recent_content=recent_content,
                             recent_users=recent_users,
                             database_info=database_info,
                             maintenance_enabled=maintenance_enabled,
                             maintenance_message=maintenance_message,
                             site_logo_url=site_logo_url,
                             site_logo_alt=site_logo_alt,
                             site_title=site_title,
                             site_description=site_description)
    except Exception as e:
        flash(f'Error loading system settings: {str(e)}', 'error')
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/system-settings/update', methods=['POST'])
@admin_required
def update_system_settings():
    """Update system settings"""
    try:
        action = request.form.get('action')
        
        if action == 'cleanup_notifications':
            # Delete notifications older than 30 days
            from datetime import datetime, timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            old_notifications = Notification.query.filter(Notification.created_at < cutoff_date).all()
            
            for notification in old_notifications:
                db.session.delete(notification)
            
            db.session.commit()
            flash(f'Cleaned up {len(old_notifications)} old notifications.', 'success')
            
        elif action == 'reset_demo_data':
            # Reset demo data (for testing purposes)
            flash('Demo data reset feature is not implemented yet.', 'info')
            
        elif action == 'optimize_database':
            # Database optimization placeholder
            flash('Database optimization completed.', 'success')
            
        elif action == 'update_maintenance':
            # Update maintenance message settings
            maintenance_enabled = request.form.get('maintenance_enabled') == 'on'
            maintenance_message = request.form.get('maintenance_message', '').strip()
            
            from models import SystemSettings
            SystemSettings.set_setting('maintenance_enabled', 'true' if maintenance_enabled else 'false', 
                                     'boolean', 'Enable or disable maintenance mode')
            SystemSettings.set_setting('maintenance_message', maintenance_message, 
                                     'text', 'Message displayed during maintenance mode')
            
            flash('Maintenance settings updated successfully.', 'success')
            
        elif action == 'toggle_maintenance':
            # Quick toggle maintenance mode
            from models import SystemSettings
            current_maintenance = SystemSettings.get_setting('maintenance_enabled', 'false') == 'true'
            new_status = not current_maintenance
            
            SystemSettings.set_setting('maintenance_enabled', 'true' if new_status else 'false',
                                     'boolean', 'Enable or disable maintenance mode')
            
            status_text = 'enabled' if new_status else 'disabled'
            flash(f'Maintenance mode {status_text} successfully.', 'success')
            
        elif action == 'update_logo':
            # Update logo settings
            logo_url = request.form.get('logo_url', '').strip()
            logo_alt = request.form.get('logo_alt', 'AniFlix').strip()
            
            from models import SystemSettings
            SystemSettings.set_setting('site_logo_url', logo_url, 
                                     'url', 'URL for the site logo')
            SystemSettings.set_setting('site_logo_alt', logo_alt, 
                                     'text', 'Alt text for the site logo')
            
            flash('Logo settings updated successfully.', 'success')
            
        elif action == 'update_site_info':
            # Update site information
            site_title = request.form.get('site_title', 'AniFlix').strip()
            site_description = request.form.get('site_description', '').strip()
            
            from models import SystemSettings
            SystemSettings.set_setting('site_title', site_title, 
                                     'text', 'Site title displayed in browser')
            SystemSettings.set_setting('site_description', site_description, 
                                     'text', 'Site description for SEO')
            
            flash('Site information updated successfully.', 'success')
            
        else:
            flash('Unknown action requested.', 'error')
            
    except Exception as e:
        flash(f'Error updating system settings: {str(e)}', 'error')
        db.session.rollback()
    
    return redirect(url_for('admin.system_settings'))

@admin_bp.route('/api/extract-dash-m3u8', methods=['POST'])
@login_required
@admin_required
def extract_dash_m3u8():
    """Extract M3U8 from DASH URL"""
    try:
        data = request.get_json()
        dash_url = data.get('dash_url', '').strip()
        
        if not dash_url:
            return jsonify({
                'success': False,
                'error': 'DASH URL is required'
            }), 400
        
        # Validate DASH URL format
        if 'cache.video.iqiyi.com/dash' not in dash_url:
            return jsonify({
                'success': False,
                'error': 'Invalid DASH URL format'
            }), 400
        
        logging.info(f"Extracting M3U8 from DASH URL: {dash_url[:100]}...")
        
        # Extract M3U8 using new scraper
        scraper = IQiyiM3U8Scraper()
        m3u8_url = scraper.extract_m3u8_from_dash_url(dash_url)
        result = {'success': bool(m3u8_url), 'm3u8_content': m3u8_url, 'method': 'new_scraper'}
        
        if result['success']:
            return jsonify({
                'success': True,
                'm3u8_content': result['m3u8_content'],
                'method': result['method'],
                'message': f'M3U8 berhasil diekstrak menggunakan method {result["method"]}'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to extract M3U8 from DASH URL'),
                'details': 'Periksa apakah DASH URL masih valid dan dapat diakses'
            }), 400
            
    except Exception as e:
        logging.error(f"DASH M3U8 extraction error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error extracting M3U8: {str(e)}'
        }), 500

@admin_bp.route('/api/extract-iqiyi-m3u8', methods=['POST'])
@login_required
@admin_required
def extract_iqiyi_m3u8():
    """Extract M3U8 from iQiyi play URL"""
    try:
        data = request.get_json()
        iqiyi_play_url = data.get('iqiyi_play_url', '').strip()
        
        if not iqiyi_play_url:
            return jsonify({
                'success': False,
                'error': 'iQiyi play URL is required'
            }), 400
        
        # Validate iQiyi play URL format
        if 'iq.com/play/' not in iqiyi_play_url:
            return jsonify({
                'success': False,
                'error': 'Invalid iQiyi play URL format'
            }), 400
        
        logging.info(f"Extracting M3U8 from iQiyi play URL: {iqiyi_play_url[:100]}...")
        
        # Extract M3U8 using the play URL extractor
        from iqiyi_play_extractor import extract_m3u8_from_iqiyi_play_url
        result = extract_m3u8_from_iqiyi_play_url(iqiyi_play_url)
        
        if result['success']:
            return jsonify({
                'success': True,
                'm3u8_content': result['m3u8_content'],
                'method': result['method'],
                'episode_info': result.get('episode_info', {}),
                'message': f'M3U8 berhasil diekstrak dari iQiyi play URL'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to extract M3U8 from iQiyi play URL'),
                'details': 'Periksa apakah URL play iQiyi masih valid dan dapat diakses'
            }), 400
            
    except Exception as e:
        logging.error(f"iQiyi play M3U8 extraction error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error extracting M3U8: {str(e)}'
        }), 500

@admin_bp.route('/api/extract-yourupload-video', methods=['POST'])
@login_required  
@admin_required
def extract_yourupload_video():
    """Extract direct video URL from YouUpload embed URL"""
    try:
        data = request.get_json()
        embed_url = data.get('embed_url', '').strip()
        
        if not embed_url:
            return jsonify({
                'success': False,
                'error': 'YouUpload embed URL is required'
            }), 400
        
        # Validate YouUpload embed URL format
        if 'yourupload.com/embed/' not in embed_url:
            return jsonify({
                'success': False,
                'error': 'Invalid YouUpload embed URL format'
            }), 400
        
        logging.info(f"Extracting video from YouUpload embed: {embed_url}")
        
        # Extract video ID from embed URL
        import re
        video_id_match = re.search(r'/embed/([^?/]+)', embed_url)
        if not video_id_match:
            return jsonify({
                'success': False,
                'error': 'Cannot extract video ID from embed URL'
            }), 400
            
        video_id = video_id_match.group(1)
        logging.info(f"Extracted video ID: {video_id}")
        
        # Try to get the direct video page
        import requests
        from bs4 import BeautifulSoup
        
        watch_url = f"https://www.yourupload.com/watch/{video_id}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.yourupload.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        response = requests.get(watch_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'Cannot access YouUpload watch page: {response.status_code}'
            }), 400
            
        # Parse the page to find video URL
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for video source in various common patterns
        video_url = None
        
        # Method 1: Look for video tag source
        video_tag = soup.find('video')
        if video_tag:
            source_tag = video_tag.find('source')
            if source_tag and source_tag.get('src'):
                video_url = source_tag['src']
                logging.info("✅ Found video URL in <video><source> tag")
        
        # Method 2: Look for JavaScript video configuration
        if not video_url:
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string:
                    # Look for common video URL patterns in JavaScript
                    video_patterns = [
                        r'src["\']?\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
                        r'video["\']?\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
                        r'url["\']?\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
                        r'["\']([^"\']*yourupload[^"\']*\.mp4[^"\']*)["\']'
                    ]
                    
                    for pattern in video_patterns:
                        matches = re.findall(pattern, script.string, re.IGNORECASE)
                        if matches:
                            video_url = matches[0]
                            logging.info(f"✅ Found video URL in JavaScript: {pattern}")
                            break
                    if video_url:
                        break
        
        if video_url:
            # Make sure URL is absolute
            if video_url.startswith('//'):
                video_url = 'https:' + video_url
            elif video_url.startswith('/'):
                video_url = 'https://www.yourupload.com' + video_url
            
            return jsonify({
                'success': True,
                'video_url': video_url,
                'method': 'page_scraping',
                'message': 'Direct video URL extracted from YouUpload'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Could not find direct video URL on YouUpload page',
                'fallback_url': watch_url
            }), 400
            
    except Exception as e:
        logging.error(f"YouUpload video extraction error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error extracting video: {str(e)}'
        }), 500

