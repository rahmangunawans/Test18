from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from app import db
from models import Notification, User, NotificationRead
from datetime import datetime, timedelta
import logging

notifications_bp = Blueprint('notifications', __name__)

# SocketIO instance will be initialized in app.py
socketio = None

def init_socketio(app, socketio_instance):
    """Initialize SocketIO with the app"""
    global socketio
    socketio = socketio_instance

def cleanup_old_notifications():
    """Delete notifications older than 5 days and their read records"""
    try:
        five_days_ago = datetime.utcnow() - timedelta(days=5)
        old_notifications = Notification.query.filter(
            Notification.created_at < five_days_ago
        ).all()
        
        if old_notifications:
            notification_ids = [notif.id for notif in old_notifications]
            
            # Delete associated NotificationRead records first
            old_read_records = NotificationRead.query.filter(
                NotificationRead.notification_id.in_(notification_ids)
            ).all()
            
            for read_record in old_read_records:
                db.session.delete(read_record)
            
            # Then delete the notifications
            for notification in old_notifications:
                db.session.delete(notification)
            
            db.session.commit()
            logging.info(f"Cleaned up {len(old_notifications)} old notifications and {len(old_read_records)} read records")
        
        # Also clean up orphaned read records (for notifications that no longer exist)
        orphaned_reads = NotificationRead.query.filter(
            ~NotificationRead.notification_id.in_(
                db.session.query(Notification.id).scalar_subquery()
            )
        ).all()
        
        if orphaned_reads:
            for read_record in orphaned_reads:
                db.session.delete(read_record)
            db.session.commit()
            logging.info(f"Cleaned up {len(orphaned_reads)} orphaned read records")
        
        # Clean up very old read records (older than 30 days) to prevent database bloat
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        very_old_reads = NotificationRead.query.filter(
            NotificationRead.read_at < thirty_days_ago
        ).all()
        
        if very_old_reads:
            for read_record in very_old_reads:
                db.session.delete(read_record)
            db.session.commit()
            logging.info(f"Cleaned up {len(very_old_reads)} very old read records")
            
    except Exception as e:
        logging.error(f"Failed to cleanup old notifications: {e}")
        db.session.rollback()

@notifications_bp.route('/notifications')
@login_required
def get_notifications():
    """Get user notifications via API"""
    try:
        # Clean up old notifications first
        cleanup_old_notifications()
        
        # Get user-specific notifications
        user_notifications = Notification.query.filter_by(
            user_id=current_user.id
        ).order_by(Notification.created_at.desc()).limit(20).all()
        
        # Get read notification IDs for current user
        read_notification_ids = db.session.query(NotificationRead.notification_id).filter_by(
            user_id=current_user.id
        ).scalar_subquery()
        
        # Get global notifications that user hasn't read yet
        global_notifications = Notification.query.filter_by(
            is_global=True,
            user_id=None
        ).filter(
            ~Notification.id.in_(read_notification_ids)
        ).order_by(Notification.created_at.desc()).limit(10).all()
        
        # Combine and sort notifications
        all_notifications = user_notifications + global_notifications
        all_notifications.sort(key=lambda x: x.created_at, reverse=True)
        
        # Build response with proper read status
        notifications_data = []
        unread_count = 0
        
        for notif in all_notifications[:20]:
            notif_dict = notif.to_dict()
            
            # Check if this notification has been read by the current user
            if notif.is_global:
                # For global notifications, check the NotificationRead table
                read_record = NotificationRead.query.filter_by(
                    user_id=current_user.id,
                    notification_id=notif.id
                ).first()
                notif_dict['is_read'] = read_record is not None
                if read_record:
                    notif_dict['read_at'] = read_record.read_at.isoformat()
                else:
                    notif_dict['read_at'] = None
                    unread_count += 1
            else:
                # For user-specific notifications, use the original is_read field
                if not notif.is_read:
                    unread_count += 1
                    
            notifications_data.append(notif_dict)
        
        return jsonify({
            'success': True,
            'notifications': notifications_data,
            'unread_count': unread_count
        })
    except Exception as e:
        logging.error(f"Error fetching notifications: {e}")
        return jsonify({'success': False, 'message': 'Failed to fetch notifications'})

@notifications_bp.route('/notifications/mark_read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    try:
        notification = Notification.query.get(notification_id)
        if not notification:
            return jsonify({'success': False, 'message': 'Notification not found'})
        
        # Check if user owns this notification or it's a global notification
        if notification.user_id != current_user.id and not notification.is_global:
            return jsonify({'success': False, 'message': 'Access denied'})
        
        if notification.is_global:
            # For global notifications, create a read record
            existing_read = NotificationRead.query.filter_by(
                user_id=current_user.id,
                notification_id=notification_id
            ).first()
            
            if not existing_read:
                read_record = NotificationRead(
                    user_id=current_user.id,
                    notification_id=notification_id
                )
                db.session.add(read_record)
        else:
            # For user-specific notifications, update the original record
            notification.is_read = True
            notification.read_at = datetime.utcnow()
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Error marking notification as read: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to mark notification as read'})

@notifications_bp.route('/notifications/mark_all_read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all user notifications as read"""
    try:
        current_time = datetime.utcnow()
        
        # Mark user-specific notifications as read
        user_notifications = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).all()
        
        for notif in user_notifications:
            notif.is_read = True
            notif.read_at = current_time
        
        # Get all global notifications that user hasn't read yet
        read_notification_ids = db.session.query(NotificationRead.notification_id).filter_by(
            user_id=current_user.id
        ).scalar_subquery()
        
        global_notifications = Notification.query.filter_by(
            is_global=True,
            user_id=None
        ).filter(
            ~Notification.id.in_(read_notification_ids)
        ).all()
        
        # Mark global notifications as read for this user
        for notif in global_notifications:
            read_record = NotificationRead(
                user_id=current_user.id,
                notification_id=notif.id
            )
            db.session.add(read_record)
        
        db.session.commit()
        logging.info(f"Marked {len(user_notifications)} user notifications and {len(global_notifications)} global notifications as read for user {current_user.id}")
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Error marking all notifications as read: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to mark notifications as read'})

@notifications_bp.route('/notifications/delete/<int:notification_id>', methods=['DELETE'])
@login_required
def delete_notification(notification_id):
    """Delete a notification"""
    try:
        notification = Notification.query.get(notification_id)
        if not notification:
            return jsonify({'success': False, 'message': 'Notification not found'})
        
        # Check if user owns this notification or it's a global notification
        if notification.user_id != current_user.id and not notification.is_global:
            return jsonify({'success': False, 'message': 'Access denied'})
        
        if notification.is_global:
            # For global notifications, just mark as read so they don't show up again
            existing_read = NotificationRead.query.filter_by(
                user_id=current_user.id,
                notification_id=notification_id
            ).first()
            
            if not existing_read:
                read_record = NotificationRead(
                    user_id=current_user.id,
                    notification_id=notification_id
                )
                db.session.add(read_record)
        else:
            # For user-specific notifications, delete completely
            db.session.delete(notification)
        
        db.session.commit()
        logging.info(f"Notification {notification_id} deleted by user {current_user.id}")
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Error deleting notification: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to delete notification'})

@notifications_bp.route('/notifications/delete_all', methods=['DELETE'])
@login_required
def delete_all_notifications():
    """Delete all notifications for user"""
    try:
        # Delete user-specific notifications
        user_notifications = Notification.query.filter_by(user_id=current_user.id).all()
        for notif in user_notifications:
            db.session.delete(notif)
        
        # For global notifications, mark them as read so they don't show up again
        read_notification_ids = db.session.query(NotificationRead.notification_id).filter_by(
            user_id=current_user.id
        ).scalar_subquery()
        
        global_notifications = Notification.query.filter_by(
            is_global=True,
            user_id=None
        ).filter(
            ~Notification.id.in_(read_notification_ids)
        ).all()
        
        for notif in global_notifications:
            read_record = NotificationRead(
                user_id=current_user.id,
                notification_id=notif.id
            )
            db.session.add(read_record)
        
        db.session.commit()
        logging.info(f"All notifications deleted for user {current_user.id}")
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Error deleting all notifications: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to delete all notifications'})

def create_notification(user_id=None, title="", message="", notification_type="info", 
                       is_global=False, action_url=None, icon="bell"):
    """Create a new notification"""
    try:
        from models import Notification
        from app import db
        
        logging.info(f"Creating notification: {title} - Global: {is_global}")
        
        notification = Notification()
        notification.user_id = user_id
        notification.title = title
        notification.message = message
        notification.type = notification_type
        notification.is_global = is_global
        notification.action_url = action_url
        notification.icon = icon
        
        db.session.add(notification)
        db.session.commit()
        
        logging.info(f"Notification created successfully with ID: {notification.id}")
        
        return notification
    except Exception as e:
        logging.error(f"Error creating notification: {e}")
        import traceback
        logging.error(f"Full traceback: {traceback.format_exc()}")
        db.session.rollback()
        return None

def notify_new_episode(content_title, episode_number, episode_title, content_id):
    """Create notification for new episode"""
    create_notification(
        title="Episode Baru Tersedia!",
        message=f"Episode {episode_number} dari {content_title} - {episode_title} sudah dapat ditonton",
        notification_type="episode",
        is_global=True,
        action_url=f"/anime/{content_id}",
        icon="play-circle"
    )

def notify_new_content(content_title, content_type, content_id):
    """Create notification for new content"""
    type_text = "Anime" if content_type == "anime" else "Film"
    create_notification(
        title=f"{type_text} Baru Ditambahkan!",
        message=f"{content_title} telah ditambahkan ke platform",
        notification_type="content",
        is_global=True,
        action_url=f"/anime/{content_id}",
        icon="plus-circle"
    )

def notify_subscription_success(user_id, subscription_type):
    """Create notification for successful subscription"""
    type_text = {
        'vip_monthly': 'VIP Bulanan',
        'vip_3month': 'VIP 3 Bulan',
        'vip_yearly': 'VIP Tahunan'
    }.get(subscription_type, 'VIP')
    
    create_notification(
        user_id=user_id,
        title="Berlangganan Berhasil!",
        message=f"Selamat! Anda sekarang adalah member {type_text}. Nikmati semua konten premium!",
        notification_type="success",
        action_url="/dashboard",
        icon="crown"
    )

def notify_admin_message(user_id, title, message):
    """Create notification from admin to user"""
    create_notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type="info",
        icon="user-shield"
    )

# SocketIO Event Handlers
def setup_socketio_events(socketio_instance):
    """Setup SocketIO event handlers"""
    global socketio
    socketio = socketio_instance
    
    @socketio.on('connect')
    def handle_connect():
        if current_user.is_authenticated:
            join_room(f'user_{current_user.id}')
            logging.info(f'User {current_user.username} connected to notifications')
    
    @socketio.on('disconnect')
    def handle_disconnect():
        if current_user.is_authenticated:
            leave_room(f'user_{current_user.id}')
            logging.info(f'User {current_user.username} disconnected from notifications')
    
    @socketio.on('join_notifications')
    def handle_join_notifications():
        if current_user.is_authenticated:
            join_room(f'user_{current_user.id}')
            emit('notification_status', {'status': 'connected'})
    
    @socketio.on('mark_notification_read')
    def handle_mark_read(data):
        if current_user.is_authenticated:
            notification_id = data.get('notification_id')
            if notification_id:
                try:
                    notification = Notification.query.get(notification_id)
                    if notification and (notification.user_id == current_user.id or notification.is_global):
                        notification.is_read = True
                        notification.read_at = datetime.utcnow()
                        db.session.commit()
                        emit('notification_marked_read', {'notification_id': notification_id})
                except Exception as e:
                    logging.error(f"Error marking notification as read via SocketIO: {e}")
                    db.session.rollback()