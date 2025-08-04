from datetime import datetime, timedelta
from app import db
from flask_login import UserMixin
from sqlalchemy.sql import func

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    subscription_type = db.Column(db.String(20), default='free')  # free, vip_monthly, vip_3month, vip_yearly
    subscription_expires = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    watch_history = db.relationship('WatchHistory', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def is_vip(self):
        return (self.subscription_type in ['vip_monthly', 'vip_3month', 'vip_yearly'] and 
                self.subscription_expires and self.subscription_expires > datetime.utcnow())
    
    def can_watch_full_episode(self, episode_number):
        if self.is_vip():
            return True
        return episode_number <= 5
    
    def get_max_watch_time(self, episode_number):
        """Returns max watch time in minutes for an episode"""
        if self.is_vip() or episode_number <= 5:
            return None  # No limit
        return 10  # 10 minutes for free users on episodes 6+
    
    def is_admin_user(self):
        """Check if user is admin based on email"""
        return (self.email.endswith('@admin.aniflix.com') or 
                'admin' in self.email.lower() or 
                self.email.startswith('admin@'))
    
    def is_admin(self):
        """Alias for is_admin_user for template compatibility"""
        return self.is_admin_user()

class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    character_overview = db.Column(db.Text)  # Character descriptions and overview
    genre = db.Column(db.String(100))
    year = db.Column(db.Integer)
    rating = db.Column(db.Float, default=0.0)
    content_type = db.Column(db.String(20), default='anime')  # anime, donghua, movie
    thumbnail_url = db.Column(db.String(500))
    trailer_url = db.Column(db.String(500))
    total_episodes = db.Column(db.Integer)  # Total number of episodes
    studio = db.Column(db.String(200))  # Animation studio
    status = db.Column(db.String(20), default='unknown')  # complete, ongoing, unknown
    is_featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    episodes = db.relationship('Episode', backref='content', lazy=True, cascade='all, delete-orphan')
    watch_history = db.relationship('WatchHistory', backref='content', lazy=True, cascade='all, delete-orphan')

class Episode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    episode_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    duration = db.Column(db.Integer)  # Duration in minutes
    video_url = db.Column(db.String(500))  # Legacy field for compatibility
    thumbnail_url = db.Column(db.String(500))  # Episode thumbnail
    
    # Multiple streaming servers
    server_m3u8_url = db.Column(db.Text)  # M3U8 streaming content (can be very long)
    server_embed_url = db.Column(db.String(500))  # Embed iframe URL
    iqiyi_play_url = db.Column(db.String(500))  # iQiyi play URL (https://www.iq.com/play/...)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    watch_history = db.relationship('WatchHistory', backref='episode', lazy=True, cascade='all, delete-orphan')

class WatchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    episode_id = db.Column(db.Integer, db.ForeignKey('episode.id'), nullable=False)
    watch_time = db.Column(db.Integer, default=0)  # Watch time in seconds
    completed = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='on-going')  # on-going, completed
    last_watched = db.Column(db.DateTime, default=datetime.utcnow)

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stripe_session_id = db.Column(db.String(200))
    subscription_type = db.Column(db.String(20))  # vip_monthly, vip_3month, vip_yearly
    amount = db.Column(db.Float)
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='subscriptions')

class VipDownload(db.Model):
    """Track VIP-exclusive downloads for analytics and abuse prevention"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    episode_id = db.Column(db.Integer, db.ForeignKey('episode.id'), nullable=False)
    download_type = db.Column(db.String(20), nullable=False)  # video, subtitle, audio
    server_type = db.Column(db.String(20))  # m3u8, embed, iqiyi, direct
    language = db.Column(db.String(10))  # For subtitle downloads
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    download_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='vip_downloads')
    episode = db.relationship('Episode', backref='vip_downloads')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # None for global notifications
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='info')  # info, success, warning, error, episode, content
    is_read = db.Column(db.Boolean, default=False)
    is_global = db.Column(db.Boolean, default=False)  # Global notifications for all users
    action_url = db.Column(db.String(500))  # Optional URL for notification action
    icon = db.Column(db.String(100), default='bell')  # Font Awesome icon class
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)
    
    user = db.relationship('User', backref='notifications')
    read_by = db.relationship('NotificationRead', backref='notification', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'type': self.type,
            'is_read': self.is_read,
            'is_global': self.is_global,
            'action_url': self.action_url,
            'icon': self.icon,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None
        }

class NotificationRead(db.Model):
    """Track which notifications have been read by which users"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notification_id = db.Column(db.Integer, db.ForeignKey('notification.id'), nullable=False)
    read_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Composite unique constraint to prevent duplicate reads
    __table_args__ = (db.UniqueConstraint('user_id', 'notification_id'),)
    
    user = db.relationship('User', backref='notification_reads')
    
    def __init__(self, user_id, notification_id):
        self.user_id = user_id
        self.notification_id = notification_id


class SystemSettings(db.Model):
    """System-wide settings for the application"""
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False)
    setting_value = db.Column(db.Text)
    setting_type = db.Column(db.String(20), default='text')  # text, boolean, url, file
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SystemSettings {self.setting_key}: {self.setting_value}>'
    
    @staticmethod
    def get_setting(key, default=None):
        """Get a system setting value"""
        setting = SystemSettings.query.filter_by(setting_key=key).first()
        return setting.setting_value if setting else default
    
    @staticmethod
    def set_setting(key, value, setting_type='text', description=None):
        """Set a system setting value"""
        setting = SystemSettings.query.filter_by(setting_key=key).first()
        if setting:
            setting.setting_value = value
            setting.setting_type = setting_type
            if description:
                setting.description = description
            setting.updated_at = datetime.utcnow()
        else:
            setting = SystemSettings()
            setting.setting_key = key
            setting.setting_value = value
            setting.setting_type = setting_type
            setting.description = description
            db.session.add(setting)
        db.session.commit()
        return setting
