"""
VIP Download API endpoints for AniFlix
Handles video, subtitle, and audio downloads exclusively for VIP users
"""
from flask import Blueprint, request, jsonify, abort
from flask_login import login_required, current_user
from app import db
from models import VipDownload, Episode, Content
import logging

# Create blueprint for VIP download functionality
vip_downloads_bp = Blueprint('vip_downloads', __name__)

@vip_downloads_bp.route('/api/track-download', methods=['POST'])
@login_required
def track_download():
    """Track VIP download activity for analytics and abuse prevention"""
    
    # Verify VIP status
    if not current_user.is_vip():
        logging.warning(f"Non-VIP user {current_user.id} attempted download")
        return jsonify({
            'error': 'VIP subscription required',
            'message': 'Download functionality is exclusive to VIP members'
        }), 403
    
    try:
        data = request.get_json()
        episode_id = data.get('episode_id')
        download_type = data.get('download_type')  # video, subtitle, audio
        server_type = data.get('server_type', 'unknown')
        language = data.get('language')
        
        # Validate required fields
        if not episode_id or not download_type:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Verify episode exists
        episode = Episode.query.get(episode_id)
        if not episode:
            return jsonify({'error': 'Episode not found'}), 404
        
        # Get client information
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        user_agent = request.headers.get('User-Agent', '')
        
        # Create download record
        download_record = VipDownload(
            user_id=current_user.id,
            episode_id=episode_id,
            download_type=download_type,
            server_type=server_type,
            language=language,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.session.add(download_record)
        db.session.commit()
        
        logging.info(f"VIP download tracked: User {current_user.id}, Episode {episode_id}, Type {download_type}")
        
        return jsonify({
            'success': True,
            'message': 'Download tracked successfully',
            'download_id': download_record.id
        })
        
    except Exception as e:
        logging.error(f"Error tracking download: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@vip_downloads_bp.route('/api/download-stats', methods=['GET'])
@login_required
def get_download_stats():
    """Get VIP download statistics for current user"""
    
    if not current_user.is_vip():
        return jsonify({'error': 'VIP subscription required'}), 403
    
    try:
        # Get user's download history
        downloads = VipDownload.query.filter_by(user_id=current_user.id).all()
        
        stats = {
            'total_downloads': len(downloads),
            'video_downloads': len([d for d in downloads if d.download_type == 'video']),
            'subtitle_downloads': len([d for d in downloads if d.download_type == 'subtitle']),
            'audio_downloads': len([d for d in downloads if d.download_type == 'audio']),
            'recent_downloads': []
        }
        
        # Get recent downloads (last 10)
        recent = VipDownload.query.filter_by(user_id=current_user.id)\
                                  .order_by(VipDownload.download_timestamp.desc())\
                                  .limit(10).all()
        
        for download in recent:
            episode = Episode.query.get(download.episode_id)
            content = Content.query.get(episode.content_id) if episode else None
            
            stats['recent_downloads'].append({
                'id': download.id,
                'episode_title': episode.title if episode else 'Unknown',
                'content_title': content.title if content else 'Unknown',
                'download_type': download.download_type,
                'server_type': download.server_type,
                'language': download.language,
                'timestamp': download.download_timestamp.isoformat()
            })
        
        return jsonify(stats)
        
    except Exception as e:
        logging.error(f"Error getting download stats: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500