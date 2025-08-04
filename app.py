import os
import logging
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user
# from flask_socketio import SocketIO  # Disabled due to Gunicorn compatibility issues
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv



# Load environment variables
load_dotenv()

# Load Supabase password from .env if exists
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        for line in f:
            if line.startswith('SUPABASE_PASSWORD='):
                os.environ['SUPABASE_PASSWORD'] = line.split('=', 1)[1].strip()

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
# socketio disabled for stability

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET") or "dev-secret-key-for-replit-migration"
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for development
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database - Use Supabase exclusively as requested
supabase_password = os.environ.get("SUPABASE_PASSWORD") or "24AuDjUfMpFFIljP"
supabase_project_ref = os.environ.get("SUPABASE_PROJECT_REF") or "heotmyzuxabzfobirhnm"  # Correct project ID from user

# Build Supabase connection URL (try different connection formats)
supabase_url_pooler = f"postgresql://postgres.{supabase_project_ref}:{supabase_password}@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
supabase_url_direct = f"postgresql://postgres:{supabase_password}@db.{supabase_project_ref}.supabase.co:5432/postgres"

# Priority: Use Supabase database first, fallback to Replit DATABASE_URL if needed
database_url = os.environ.get("DATABASE_URL")
supabase_connected = False

# Use Supabase database exclusively as requested
app.config["SQLALCHEMY_DATABASE_URI"] = supabase_url_pooler
logging.info(f"Using Supabase PostgreSQL database: {supabase_project_ref}")
logging.info(f"Connection: postgres.{supabase_project_ref}@aws-0-ap-southeast-1.pooler.supabase.com:6543")

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
    "pool_timeout": 20,
    "pool_size": 3,
    "max_overflow": 5,
    "connect_args": {
        "sslmode": "require",
        "connect_timeout": 10
    }
}

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
# socketio.init_app(app)  # Disabled for stability
login_manager.login_view = 'auth.login'  # type: ignore
login_manager.login_message = 'Please log in to access this page.'

# Add template filter for duration formatting
@app.template_filter('format_duration')
def format_duration(seconds):
    """Convert seconds to MM:SS format for display"""
    if not seconds or seconds == 0:
        return 'N/A'
    
    try:
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{remaining_seconds:02d}"
        else:
            return f"{minutes:02d}:{remaining_seconds:02d}"
    except (ValueError, TypeError):
        return 'N/A'

# Add custom Jinja2 filters
@app.template_filter('from_json')
def from_json_filter(value):
    """Parse JSON string to Python object"""
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Register blueprints
from auth import auth_bp
from content import content_bp
from subscription import subscription_bp
from admin import admin_bp
from notifications import notifications_bp

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(content_bp)
app.register_blueprint(subscription_bp, url_prefix='/subscription')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(notifications_bp, url_prefix='/api')

# Add API endpoint for M3U8 extraction (accessible from video player)
@app.route('/api/extract-iqiyi-m3u8', methods=['POST'])
def extract_iqiyi_m3u8():
    """Public endpoint for extracting M3U8 from iQiyi play URL"""
    try:
        import logging
        
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
                'message': 'M3U8 berhasil diekstrak dari iQiyi play URL'
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

# Emergency admin access routes (must be after blueprints)
@app.route('/emergency-admin-access')
def emergency_admin_access():
    """Emergency admin access during maintenance"""
    from flask import redirect, url_for
    return redirect(url_for('auth.login'))

@app.route('/maintenance-override')
def maintenance_override():
    """Direct maintenance override for admins"""
    from flask import redirect, url_for
    return redirect(url_for('admin.system_settings'))

# Socket.IO disabled for stability - using fast polling instead

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()
    
    # Create sample content if database is empty (commented out for schema update)
    pass

from flask import render_template, redirect, url_for, abort
from flask_login import current_user

# Real-time System Settings Context Processor
@app.context_processor
def inject_system_settings():
    """Inject system settings into all templates for real-time updates"""
    try:
        from models import SystemSettings
        settings = {
            'maintenance_enabled': SystemSettings.get_setting('maintenance_enabled', 'false') == 'true',
            'maintenance_message': SystemSettings.get_setting('maintenance_message', ''),
            'site_logo_url': SystemSettings.get_setting('site_logo_url', ''),
            'site_logo_alt': SystemSettings.get_setting('site_logo_alt', 'AniFlix'),
            'site_title': SystemSettings.get_setting('site_title', 'AniFlix'),
            'site_description': SystemSettings.get_setting('site_description', '')
        }
        return {'system_settings': settings}
    except:
        return {'system_settings': {'maintenance_enabled': False}}

# Real-time Maintenance Mode Middleware
@app.before_request
def check_maintenance_mode():
    """Check maintenance mode on every request for real-time updates"""
    try:
        from models import SystemSettings
        from flask import request
        
        # Skip maintenance check for admin and maintenance-related routes
        admin_routes = ['admin.', 'auth.login', 'auth.logout', 'static', 'notifications.']
        maintenance_routes = ['/admin', '/login', '/logout', '/static', '/notifications']
        
        # Secret admin bypass URL for security
        secret_admin_paths = ['/admin/emergency-admin-access', '/admin/maintenance-override', '/emergency-admin-access', '/maintenance-override']
        
        # Check if current route should bypass maintenance
        if any(request.endpoint and request.endpoint.startswith(route) for route in admin_routes):
            return
        if any(request.path.startswith(route) for route in maintenance_routes):
            return
        if any(request.path.startswith(route) for route in secret_admin_paths):
            return
        
        # Admin bypass parameter removed for security reasons
        
        # Check if maintenance mode is enabled (controllable via System Settings)
        try:
            maintenance_enabled = SystemSettings.get_setting('maintenance_enabled', 'false') == 'true'
        except:
            maintenance_enabled = False  # Default to disabled if no setting found
        
        if maintenance_enabled:
            # Check if user is admin first (most important check)
            if current_user.is_authenticated and hasattr(current_user, 'is_admin') and current_user.is_admin():
                return  # Allow admin to access during maintenance
            
            # Also check by email pattern for extra safety
            if current_user.is_authenticated and current_user.email:
                admin_patterns = ['@admin.aniflix.com', 'admin@', 'admin']
                if any(pattern in current_user.email.lower() for pattern in admin_patterns):
                    return  # Allow admin access
            
            # Show maintenance page for regular users
            maintenance_message = SystemSettings.get_setting('maintenance_message', 
                'AniFlix is currently under maintenance. Please check back later.')
            return render_template('maintenance.html', 
                                 maintenance_message=maintenance_message), 503
    except:
        pass  # Continue normally if there's any error

@app.route('/')
def index():
    from models import Content
    featured_content = Content.query.filter_by(is_featured=True).all()
    latest_content = Content.query.order_by(Content.created_at.desc()).limit(8).all()
    popular_content = Content.query.order_by(Content.rating.desc()).limit(8).all()
    
    # Get featured donghua (Chinese anime) - using specific IDs for now
    featured_donghua = Content.query.filter(Content.id.in_([1,2,3])).all()
    
    return render_template('index.html', 
                         featured_content=featured_content, 
                         latest_content=latest_content, 
                         popular_content=popular_content,
                         featured_donghua=featured_donghua)

@app.route('/dashboard')
@login_required
def dashboard():
    # Get user's watch history for dashboard
    from models import WatchHistory, Content, Episode
    from sqlalchemy import func
    
    # Get ongoing episodes (not completed)
    ongoing_episodes = WatchHistory.query.filter_by(
        user_id=current_user.id, 
        completed=False
    ).order_by(WatchHistory.last_watched.desc()).limit(6).all()
    
    # Get recent watch history
    recent_history = WatchHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(WatchHistory.last_watched.desc()).limit(10).all()
    
    # Calculate statistics
    total_watched = WatchHistory.query.filter_by(user_id=current_user.id).count()
    
    completed_count = WatchHistory.query.filter_by(
        user_id=current_user.id, 
        completed=True
    ).count()
    
    # Calculate total watch time in hours
    watch_time_result = db.session.query(
        func.sum(WatchHistory.watch_time)
    ).filter_by(user_id=current_user.id).scalar()
    
    watch_hours = round((watch_time_result / 3600) if watch_time_result else 0, 1)
    
    return render_template('dashboard.html', 
                         ongoing_episodes=ongoing_episodes,
                         recent_history=recent_history,
                         total_watched=total_watched,
                         completed_count=completed_count,
                         watch_hours=watch_hours)

@app.route('/dashboard/search')
@login_required
def dashboard_search():
    from models import Content, Episode, WatchHistory
    from sqlalchemy import or_, desc, asc
    
    search_query = request.args.get('search', '').strip()
    genre_filter = request.args.get('genre', '').strip()
    status_filter = request.args.get('status', '').strip()
    sort_filter = request.args.get('sort', 'recent').strip()
    
    # Base query
    query = Content.query
    
    # Apply search filter
    if search_query:
        query = query.filter(
            or_(
                Content.title.ilike(f'%{search_query}%'),
                Content.description.ilike(f'%{search_query}%'),
                Content.genre.ilike(f'%{search_query}%')
            )
        )
    
    # Apply genre filter
    if genre_filter:
        query = query.filter(Content.genre.ilike(f'%{genre_filter}%'))
    
    # Get content
    content_list = query.all()
    
    # Process results with watch history
    results = []
    for content in content_list:
        # Get user's watch history for this content
        watch_history = WatchHistory.query.filter_by(
            user_id=current_user.id,
            content_id=content.id
        ).order_by(WatchHistory.last_watched.desc()).first()
        
        # Apply status filter
        if status_filter:
            if status_filter == 'ongoing' and (not watch_history or watch_history.completed):
                continue
            elif status_filter == 'completed' and (not watch_history or not watch_history.completed):
                continue
            elif status_filter == 'not-started' and watch_history:
                continue
        
        # Calculate progress
        progress = 0
        current_episode = 1
        if watch_history:
            current_episode = watch_history.episode.episode_number
            if watch_history.episode.duration:
                progress = (watch_history.watch_time / (watch_history.episode.duration * 60)) * 100
            else:
                progress = 100 if watch_history.completed else 50
        
        results.append({
            'id': content.id,
            'title': content.title,
            'genre': content.genre,
            'year': content.year,
            'thumbnail_url': content.thumbnail_url,
            'progress': progress,
            'current_episode': current_episode,
            'last_watched': watch_history.last_watched if watch_history else None,
            'completed': watch_history.completed if watch_history else False
        })
    
    # Apply sorting
    if sort_filter == 'recent':
        results.sort(key=lambda x: x['last_watched'] or datetime.min, reverse=True)
    elif sort_filter == 'rating':
        # Sort by content rating
        content_dict = {c.id: c for c in content_list}
        results.sort(key=lambda x: content_dict[x['id']].rating or 0, reverse=True)
    elif sort_filter == 'title':
        results.sort(key=lambda x: x['title'])
    elif sort_filter == 'year':
        results.sort(key=lambda x: x['year'] or 0, reverse=True)
    elif sort_filter == 'progress':
        results.sort(key=lambda x: x['progress'], reverse=True)
    
    return jsonify({'results': results[:20]})  # Limit to 20 results

@app.route('/api/watchlist/toggle/<int:anime_id>', methods=['POST'])
@login_required
def toggle_watchlist(anime_id):
    """Toggle anime in user's watchlist (placeholder for future feature)"""
    # This is a placeholder for watchlist functionality
    # You can implement actual watchlist logic here
    return jsonify({
        'success': True,
        'message': 'Watchlist feature coming soon!'
    })

@app.route('/api/watch-history/update', methods=['POST'])
@login_required
def update_watch_history():
    """Update watch history status"""
    try:
        from models import WatchHistory, Episode
        data = request.get_json()
        episode_id = data.get('episode_id')
        status = data.get('status')
        
        if not episode_id or not status:
            return jsonify({'success': False, 'message': 'Missing required data'})
        
        # Find the watch history record
        history = WatchHistory.query.filter_by(
            user_id=current_user.id,
            episode_id=episode_id
        ).first()
        
        if not history:
            return jsonify({'success': False, 'message': 'Watch history not found'})
        
        # Update status
        if status == 'completed':
            history.completed = True
            history.status = 'completed'
            # Set watch time to full duration if episode has duration
            if history.episode.duration:
                history.watch_time = history.episode.duration * 60
        elif status == 'ongoing':
            history.completed = False
            history.status = 'on-going'
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Watch status updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating watch history: {e}")
        return jsonify({'success': False, 'message': 'Failed to update watch status'})

@app.route('/api/watch-history/remove', methods=['DELETE'])
@login_required
def remove_watch_history():
    """Remove episode from watch history"""
    try:
        from models import WatchHistory
        data = request.get_json()
        episode_id = data.get('episode_id')
        
        if not episode_id:
            return jsonify({'success': False, 'message': 'Missing episode ID'})
        
        # Find and delete the watch history record
        history = WatchHistory.query.filter_by(
            user_id=current_user.id,
            episode_id=episode_id
        ).first()
        
        if not history:
            return jsonify({'success': False, 'message': 'Watch history not found'})
        
        db.session.delete(history)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Removed from watch history successfully'})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error removing watch history: {e}")
        return jsonify({'success': False, 'message': 'Failed to remove from watch history'})

@app.route('/profile')
@login_required
def profile():
    """View user profile"""
    return render_template('profile.html')

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    from models import User
    from werkzeug.security import check_password_hash, generate_password_hash
    
    if request.method == 'POST':
        try:
            # Get form data
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            # Validation
            if not username or not email:
                return render_template('edit_profile.html', error='Username and email are required')
            
            # Check if username or email already exists (excluding current user)
            existing_user_username = User.query.filter(
                User.username == username, 
                User.id != current_user.id
            ).first()
            
            existing_user_email = User.query.filter(
                User.email == email, 
                User.id != current_user.id
            ).first()
            
            if existing_user_username:
                return render_template('edit_profile.html', error='Username already exists')
            
            if existing_user_email:
                return render_template('edit_profile.html', error='Email already exists')
            
            # Update basic info
            current_user.username = username
            current_user.email = email
            
            # Handle password change
            if new_password:
                if not current_password:
                    return render_template('edit_profile.html', error='Current password is required to change password')
                
                if not check_password_hash(current_user.password_hash, current_password):
                    return render_template('edit_profile.html', error='Current password is incorrect')
                
                if new_password != confirm_password:
                    return render_template('edit_profile.html', error='New passwords do not match')
                
                if len(new_password) < 6:
                    return render_template('edit_profile.html', error='Password must be at least 6 characters')
                
                current_user.password_hash = generate_password_hash(new_password)
            
            db.session.commit()
            return render_template('edit_profile.html', success='Profile updated successfully')
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error updating profile: {e}")
            return render_template('edit_profile.html', error='Failed to update profile')
    
    return render_template('edit_profile.html')



