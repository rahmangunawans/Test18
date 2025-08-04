// Manual-only notification system
class NotificationManager {
    constructor() {
        this.notifications = [];
        this.unreadCount = 0;
        this.notificationContainer = null;
        this.notificationBell = null;
        this.notificationBadge = null;
        this.lastRefreshTime = null;
        
        this.init();
    }
    
    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupUI());
        } else {
            this.setupUI();
        }
        
        // Load notifications only once on page load
        this.loadNotifications();
        console.log('Notification system initialized - manual refresh only');
    }
    
    setupUI() {
        // Get existing notification bell from template
        this.notificationBell = document.getElementById('notification-bell');
        this.notificationBadge = document.getElementById('notification-badge');
        
        // Create notification container
        this.createNotificationContainer();
        
        // Setup event listeners
        this.setupEventListeners();
    }
    
    createNotificationContainer() {
        // Create notification dropdown container
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.className = 'fixed top-16 right-4 w-96 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 z-50 hidden max-h-96 overflow-hidden';
        container.innerHTML = `
            <div class="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Notifikasi</h3>
                <div class="flex items-center space-x-2">
                    <button id="refresh-notifications" class="text-sm text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors" title="Refresh notifikasi">
                        <i class="fas fa-sync-alt"></i>
                    </button>
                    <button id="mark-all-read" class="text-sm text-blue-600 dark:text-blue-400 hover:underline">
                        Tandai semua dibaca
                    </button>
                </div>
            </div>
            <div id="notifications-list" class="max-h-80 overflow-y-auto">
                <div class="p-4 text-center text-gray-500 dark:text-gray-400">
                    <i class="fas fa-bell-slash text-2xl mb-2"></i>
                    <p>Tidak ada notifikasi</p>
                </div>
            </div>
        `;
        
        document.body.appendChild(container);
        this.notificationContainer = container;
    }
    
    setupEventListeners() {
        // Toggle notification dropdown
        if (this.notificationBell) {
            this.notificationBell.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleNotificationDropdown();
            });
        }
        
        // Mark all as read
        const markAllReadBtn = document.getElementById('mark-all-read');
        if (markAllReadBtn) {
            markAllReadBtn.addEventListener('click', () => {
                this.markAllAsRead();
            });
        }
        
        // Manual refresh notifications
        const refreshBtn = document.getElementById('refresh-notifications');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.manualRefreshNotifications();
            });
        }
        
        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (this.notificationContainer && !this.notificationContainer.contains(e.target)) {
                this.notificationContainer.classList.add('hidden');
            }
        });
        
        // Keyboard shortcut for notifications (Ctrl/Cmd + Shift + N)
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'N') {
                e.preventDefault();
                this.toggleNotificationDropdown();
            }
        });
        
        // Keyboard shortcut for refresh (Ctrl/Cmd + Shift + R when notification panel is open)
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'R') {
                if (!this.notificationContainer.classList.contains('hidden')) {
                    e.preventDefault();
                    this.manualRefreshNotifications();
                }
            }
        });
    }
    
    setupManualRefresh() {
        // No automatic polling - only manual refresh
        console.log('Manual refresh system ready');
    }
    
    async loadNotifications() {
        try {
            const response = await fetch('/api/notifications');
            if (!response.ok) {
                if (response.status === 302) {
                    // User not logged in, skip notifications
                    return;
                }
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.notifications = data.notifications || [];
                this.unreadCount = data.unread_count || 0;
                this.lastRefreshTime = new Date();
                this.updateUI();
                console.log(`Loaded ${this.notifications.length} notifications, ${this.unreadCount} unread`);
            }
        } catch (error) {
            console.error('Failed to load notifications:', error);
            this.notifications = [];
            this.unreadCount = 0;
            this.updateUI();
        }
    }
    
    async manualRefreshNotifications() {
        const refreshBtn = document.getElementById('refresh-notifications');
        if (!refreshBtn) return;
        
        // Show loading animation
        const originalIcon = refreshBtn.innerHTML;
        refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        refreshBtn.disabled = true;
        
        try {
            const oldNotifications = [...this.notifications];
            const oldUnreadCount = this.unreadCount;
            
            // Reload notifications
            await this.loadNotifications();
            
            // Check for changes
            const newNotificationCount = this.notifications.length - oldNotifications.length;
            const unreadChange = this.unreadCount - oldUnreadCount;
            
            if (newNotificationCount > 0) {
                this.showNotificationToast({
                    title: 'Notifikasi Baru',
                    message: `${newNotificationCount} notifikasi baru ditemukan`,
                    type: 'success',
                    icon: 'bell'
                });
            } else if (unreadChange !== 0) {
                this.showNotificationToast({
                    title: 'Diperbarui',
                    message: 'Status notifikasi telah diperbarui',
                    type: 'info',
                    icon: 'sync-alt'
                });
            } else {
                this.showNotificationToast({
                    title: 'Tidak Ada Perubahan',
                    message: 'Tidak ada notifikasi baru',
                    type: 'info',
                    icon: 'check'
                });
            }
            
        } catch (error) {
            console.error('Failed to refresh notifications:', error);
            this.showNotificationToast({
                title: 'Error',
                message: 'Gagal memuat notifikasi terbaru',
                type: 'error',
                icon: 'exclamation-triangle'
            });
        } finally {
            // Restore button
            setTimeout(() => {
                if (refreshBtn) {
                    refreshBtn.innerHTML = originalIcon;
                    refreshBtn.disabled = false;
                }
            }, 500);
        }
    }
    
    // No addNotification function needed - only manual refresh
    
    updateUI() {
        this.updateNotificationBadge();
        this.updateNotificationList();
    }
    
    updateNotificationBadge() {
        if (this.notificationBadge) {
            if (this.unreadCount > 0) {
                this.notificationBadge.textContent = this.unreadCount > 99 ? '99+' : this.unreadCount.toString();
                this.notificationBadge.classList.remove('hidden');
                
                // Add pulse animation for new notifications
                this.notificationBell.classList.add('animate-pulse');
                setTimeout(() => {
                    this.notificationBell.classList.remove('animate-pulse');
                }, 2000);
            } else {
                this.notificationBadge.classList.add('hidden');
            }
        }
    }
    
    updateNotificationList() {
        const notificationsList = document.getElementById('notifications-list');
        if (!notificationsList) return;
        
        if (this.notifications.length === 0) {
            notificationsList.innerHTML = `
                <div class="p-4 text-center text-gray-500 dark:text-gray-400">
                    <i class="fas fa-bell-slash text-2xl mb-2"></i>
                    <p>Tidak ada notifikasi</p>
                </div>
            `;
            return;
        }
        
        notificationsList.innerHTML = this.notifications.map(notification => 
            this.createNotificationHTML(notification)
        ).join('');
        
        // Add event listeners to notification items
        notificationsList.querySelectorAll('[data-notification-id]').forEach(item => {
            item.addEventListener('click', () => {
                const notificationId = parseInt(item.dataset.notificationId);
                this.handleNotificationClick(notificationId);
            });
        });
    }
    
    createNotificationHTML(notification) {
        const createdTime = this.getTimeAgo(notification.created_at);
        const isUnread = !notification.is_read;
        const typeClass = this.getNotificationTypeClass(notification.type);
        
        // Show read time if notification has been read
        let timeInfo = `Dibuat ${createdTime}`;
        if (notification.is_read && notification.read_at) {
            const readTime = this.getTimeAgo(notification.read_at);
            timeInfo += ` • Dibaca ${readTime}`;
        }
        
        return `
            <div class="notification-item p-3 border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors duration-150 ${isUnread ? 'bg-blue-50 dark:bg-blue-900/20' : 'bg-gray-50 dark:bg-gray-700/50'}"
                 data-notification-id="${notification.id}">
                <div class="flex items-start space-x-3">
                    <div class="flex-shrink-0">
                        <i class="fas fa-${notification.icon} ${typeClass} text-lg"></i>
                    </div>
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center justify-between">
                            <p class="text-sm font-medium text-gray-900 dark:text-white truncate">
                                ${notification.title}
                            </p>
                            ${isUnread ? '<div class="w-2 h-2 bg-blue-500 rounded-full flex-shrink-0" title="Belum dibaca"></div>' : '<div class="w-2 h-2 bg-gray-400 rounded-full flex-shrink-0" title="Sudah dibaca"></div>'}
                        </div>
                        <p class="text-sm text-gray-600 dark:text-gray-300 mt-1 line-clamp-2">
                            ${notification.message}
                        </p>
                        <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">
                            ${timeInfo}
                        </p>
                    </div>
                </div>
            </div>
        `;
    }
    
    getNotificationTypeClass(type) {
        const typeClasses = {
            'info': 'text-blue-500',
            'success': 'text-green-500',
            'warning': 'text-yellow-500',
            'error': 'text-red-500',
            'episode': 'text-purple-500',
            'content': 'text-indigo-500'
        };
        return typeClasses[type] || 'text-gray-500';
    }
    
    getTimeAgo(dateString) {
        if (!dateString) return '';
        
        try {
            // Parse the date from database (ISO format)
            const date = new Date(dateString);
            const now = new Date();
            
            // Check if date is valid
            if (isNaN(date.getTime())) {
                console.warn('Invalid date string:', dateString);
                return 'Waktu tidak valid';
            }
            
            const diffInSeconds = Math.floor((now - date) / 1000);
            
            if (diffInSeconds < 0) return 'Di masa depan'; // Handle future dates
            if (diffInSeconds < 60) return 'Baru saja';
            if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} menit yang lalu`;
            if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} jam yang lalu`;
            if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)} hari yang lalu`;
            
            return date.toLocaleDateString('id-ID');
        } catch (error) {
            console.error('Error parsing date:', error, dateString);
            return 'Waktu tidak valid';
        }
    }
    
    toggleNotificationDropdown() {
        if (this.notificationContainer) {
            this.notificationContainer.classList.toggle('hidden');
        }
    }
    
    async handleNotificationClick(notificationId) {
        // Mark as read
        await this.markNotificationAsRead(notificationId);
        
        // Find the notification
        const notification = this.notifications.find(n => n.id === notificationId);
        if (notification && notification.action_url) {
            // Navigate to the action URL
            window.location.href = notification.action_url;
        }
    }
    
    async markNotificationAsRead(notificationId) {
        try {
            const response = await fetch(`/api/notifications/mark_read/${notificationId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                // Update local state
                const notification = this.notifications.find(n => n.id === notificationId);
                if (notification && !notification.is_read) {
                    notification.is_read = true;
                    notification.read_at = new Date().toISOString(); // Set read_at timestamp
                    this.unreadCount = Math.max(0, this.unreadCount - 1);
                    this.updateUI();
                }
            }
        } catch (error) {
            console.error('Failed to mark notification as read:', error);
        }
    }
    
    async markAllAsRead() {
        try {
            const response = await fetch('/api/notifications/mark_all_read', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                // Update local state
                const currentTime = new Date().toISOString();
                this.notifications.forEach(notification => {
                    if (!notification.is_read) {
                        notification.is_read = true;
                        notification.read_at = currentTime; // Set read_at timestamp
                    }
                });
                this.unreadCount = 0;
                this.updateUI();
                
                // Show success feedback
                this.showNotificationToast({
                    title: 'Berhasil',
                    message: 'Semua notifikasi telah ditandai sebagai dibaca',
                    type: 'success',
                    icon: 'check-circle'
                });
            } else {
                throw new Error('Failed to mark all as read');
            }
        } catch (error) {
            console.error('Failed to mark all notifications as read:', error);
            this.showNotificationToast({
                title: 'Error',
                message: 'Gagal menandai semua notifikasi sebagai dibaca',
                type: 'error',
                icon: 'exclamation-circle'
            });
        }
    }
    
    showNotificationToast(notification) {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = 'fixed top-20 right-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-4 max-w-sm z-50 transform translate-x-full transition-transform duration-300';
        
        const typeClass = this.getNotificationTypeClass(notification.type);
        
        toast.innerHTML = `
            <div class="flex items-start space-x-3">
                <div class="flex-shrink-0">
                    <i class="fas fa-${notification.icon} ${typeClass} text-lg"></i>
                </div>
                <div class="flex-1">
                    <h4 class="text-sm font-medium text-gray-900 dark:text-white">
                        ${notification.title}
                    </h4>
                    <p class="text-sm text-gray-600 dark:text-gray-300 mt-1">
                        ${notification.message}
                    </p>
                </div>
                <button class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        // Add close functionality
        const closeBtn = toast.querySelector('button');
        closeBtn.addEventListener('click', () => {
            this.removeToast(toast);
        });
        
        // Add click to view functionality
        toast.addEventListener('click', (e) => {
            if (e.target === closeBtn || closeBtn.contains(e.target)) return;
            
            if (notification.action_url) {
                window.location.href = notification.action_url;
            }
            this.removeToast(toast);
        });
        
        document.body.appendChild(toast);
        
        // Animate in
        setTimeout(() => {
            toast.classList.remove('translate-x-full');
        }, 100);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            this.removeToast(toast);
        }, 5000);
    }
    
    removeToast(toast) {
        toast.classList.add('translate-x-full');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }
}

// Initialize notification manager when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if user is logged in
    if (document.querySelector('nav')) {
        window.notificationManager = new NotificationManager();
    }
});

// Global functions for triggering notifications (for testing/admin use)
function testNotification() {
    if (window.notificationManager) {
        window.notificationManager.showNotificationToast({
            id: Date.now(),
            title: 'Test Notification',
            message: 'This is a test notification to check the system.',
            type: 'info',
            icon: 'bell',
            action_url: null
        });
    }
}

function createTestNotification(title, message, type = 'info') {
    fetch('/api/notifications', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            title: title,
            message: message,
            type: type
        })
    });
}