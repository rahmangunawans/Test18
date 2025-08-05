/**
 * Stable Video Player System
 * Prevents conflicts between different server types
 */

class StableVideoPlayer {
    constructor() {
        this.currentPlayer = null;
        this.currentHls = null;
        this.currentServerType = null;
        this.isInitialized = false;
    }

    // Complete cleanup of all player instances
    async cleanup() {
        console.log('🧹 Cleaning up all player instances...');
        
        // Destroy Plyr player
        if (this.currentPlayer) {
            try {
                this.currentPlayer.destroy();
            } catch (e) {
                console.log('Plyr cleanup warning:', e);
            }
            this.currentPlayer = null;
        }

        // Destroy HLS instance
        if (this.currentHls) {
            try {
                this.currentHls.destroy();
            } catch (e) {
                console.log('HLS cleanup warning:', e);
            }
            this.currentHls = null;
        }

        // Clear window references
        window.player = null;
        window.hls = null;
        
        this.currentServerType = null;
        
        // Small delay to ensure cleanup is complete
        await new Promise(resolve => setTimeout(resolve, 100));
        console.log('✅ Cleanup completed');
    }

    // Load M3U8 server
    async loadM3U8Server(m3u8Url) {
        console.log('🔄 Loading M3U8 Server:', m3u8Url);
        await this.cleanup();
        
        const video = document.getElementById('video-player');
        const embedContainer = document.getElementById('embed-container');
        
        // Hide embed, show video
        if (embedContainer) {
            embedContainer.style.display = 'none';
            embedContainer.classList.add('hidden');
        }
        if (video) video.style.display = 'block';

        if (Hls.isSupported()) {
            this.currentHls = new Hls({
                debug: false,
                enableWorker: true,
                lowLatencyMode: true
            });
            
            this.currentHls.loadSource(m3u8Url);
            this.currentHls.attachMedia(video);
            
            this.currentHls.on(Hls.Events.MANIFEST_PARSED, () => {
                console.log('✅ M3U8 manifest loaded');
            });
            
            this.currentHls.on(Hls.Events.ERROR, (event, data) => {
                console.error('❌ HLS Error:', data);
                if (data.fatal) {
                    this.currentHls.startLoad();
                }
            });
        } else {
            video.src = m3u8Url;
        }

        this.currentPlayer = new Plyr(video, {
            controls: ['play-large', 'play', 'progress', 'current-time', 'duration', 'mute', 'volume', 'settings', 'fullscreen'],
            settings: ['speed'],
            speed: { selected: 1, options: [0.5, 0.75, 1, 1.25, 1.5, 2] }
        });
        
        window.player = this.currentPlayer;
        window.hls = this.currentHls;
        this.currentServerType = 'm3u8';
        
        this.updateButtonStyles('m3u8');
        console.log('✅ M3U8 server loaded');
    }

    // Load embed server
    async loadEmbedServer(embedUrl) {
        console.log('🔄 Loading Embed Server:', embedUrl);
        await this.cleanup();
        
        const video = document.getElementById('video-player');
        const embedContainer = document.getElementById('embed-container');
        const embedPlayer = document.getElementById('embed-player');
        
        // Hide video, show embed
        if (video) video.style.display = 'none';
        
        if (embedContainer && embedPlayer) {
            embedPlayer.src = embedUrl;
            embedContainer.classList.remove('hidden');
            embedContainer.style.display = 'block';
        }
        
        this.currentServerType = 'embed';
        this.updateButtonStyles('embed');
        console.log('✅ Embed server loaded');
    }

    // Load direct video server
    async loadDirectServer(directUrl) {
        console.log('🔄 Loading Direct Video Server:', directUrl);
        await this.cleanup();
        
        const video = document.getElementById('video-player');
        const embedContainer = document.getElementById('embed-container');
        
        // Hide embed, show video
        if (embedContainer) {
            embedContainer.style.display = 'none';
            embedContainer.classList.add('hidden');
        }
        if (video) {
            video.style.display = 'block';
            video.src = directUrl;
            video.crossOrigin = null;
            video.load();
        }

        this.currentPlayer = new Plyr(video, {
            controls: ['play-large', 'play', 'progress', 'current-time', 'duration', 'mute', 'volume', 'settings', 'fullscreen'],
            settings: ['quality', 'speed'],
            quality: { default: 720, options: [1080, 720, 480, 360] },
            speed: { selected: 1, options: [0.5, 0.75, 1, 1.25, 1.5, 2] }
        });
        
        window.player = this.currentPlayer;
        this.currentServerType = 'direct';
        
        this.updateButtonStyles('direct');
        console.log('✅ Direct video server loaded');
    }

    // Load iQiyi server with extraction
    async loadIqiyiServer(iqiyiUrl) {
        console.log('🔄 Loading iQiyi Server:', iqiyiUrl);
        await this.cleanup();
        
        try {
            const response = await fetch('/admin/api/extract-iqiyi-m3u8', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ iqiyi_play_url: iqiyiUrl })
            });
            
            const result = await response.json();
            
            if (result.success && result.m3u8_content) {
                const blob = new Blob([result.m3u8_content], { type: 'application/vnd.apple.mpegurl' });
                const videoUrl = URL.createObjectURL(blob);
                
                const video = document.getElementById('video-player');
                const embedContainer = document.getElementById('embed-container');
                
                // Hide embed, show video
                if (embedContainer) {
                    embedContainer.style.display = 'none';
                    embedContainer.classList.add('hidden');
                }
                if (video) {
                    video.style.display = 'block';
                    video.src = videoUrl;
                    video.crossOrigin = null;
                    video.load();
                }

                this.currentPlayer = new Plyr(video, {
                    controls: ['play-large', 'play', 'progress', 'current-time', 'duration', 'mute', 'volume', 'settings', 'fullscreen'],
                    settings: ['quality', 'speed'],
                    quality: { default: 720, options: [1080, 720, 480, 360] },
                    speed: { selected: 1, options: [0.5, 0.75, 1, 1.25, 1.5, 2] }
                });
                
                window.player = this.currentPlayer;
                this.currentServerType = 'iqiyi';
                
                this.updateButtonStyles('iqiyi');
                console.log('✅ iQiyi server loaded successfully');
            } else {
                throw new Error('Failed to extract M3U8');
            }
        } catch (error) {
            console.error('❌ iQiyi extraction failed:', error);
            // Fallback to iframe
            await this.loadEmbedServer(iqiyiUrl);
        }
    }

    // Update button styles
    updateButtonStyles(activeType) {
        document.querySelectorAll('.server-btn').forEach(btn => {
            btn.classList.remove('bg-green-600', 'bg-blue-600', 'bg-orange-600', 'bg-slate-600');
            btn.classList.add('bg-slate-600');
        });
        
        const colorMap = {
            'm3u8': 'bg-green-600',
            'embed': 'bg-blue-600', 
            'iqiyi': 'bg-orange-600',
            'direct': 'bg-green-600'
        };
        
        const activeBtn = document.getElementById(`server-${activeType}`);
        if (activeBtn && colorMap[activeType]) {
            activeBtn.classList.remove('bg-slate-600');
            activeBtn.classList.add(colorMap[activeType]);
        }
    }

    // Initialize empty player
    async initializeEmpty() {
        if (this.isInitialized) return;
        
        const video = document.getElementById('video-player');
        if (video) {
            this.currentPlayer = new Plyr(video, {
                controls: ['play-large', 'play', 'progress', 'current-time', 'duration', 'mute', 'volume', 'settings', 'fullscreen']
            });
            window.player = this.currentPlayer;
            this.isInitialized = true;
            console.log('✅ Empty player initialized');
        }
    }
}

// Create global instance
window.stablePlayer = new StableVideoPlayer();

// Global functions for template compatibility
function loadM3U8Server(url) { window.stablePlayer.loadM3U8Server(url); }
function loadEmbedServer(url) { window.stablePlayer.loadEmbedServer(url); }
function loadDirectServer(url) { window.stablePlayer.loadDirectServer(url); }
function loadIqiyiServer(url) { window.stablePlayer.loadIqiyiServer(url); }

// Initialize when DOM loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎬 Stable Video Player System Ready');
    window.stablePlayer.initializeEmpty();
});