/**
 * Professional Video Player with Subtitle Support
 * Supports M3U8, MP4, and Embed streaming with SRT/VTT/XML subtitles
 */

class ProfessionalVideoPlayer {
    constructor() {
        this.player = null;
        this.currentServer = null;
        this.currentHls = null;
        this.availableSubtitles = [];
        this.currentSubtitle = null;
        this.init();
    }

    init() {
        console.log('🎬 Initializing Professional Video Player...');
        this.setupVideoPlayer();
        this.setupEventListeners();
        this.loadInitialServer();
    }

    setupVideoPlayer() {
        // Initialize Video.js player with professional options
        const videoElement = document.getElementById('video-player');
        if (!videoElement) {
            console.error('Video element not found');
            return;
        }

        this.player = videojs('video-player', {
            controls: true,
            fluid: true,
            responsive: true,
            playbackRates: [0.5, 0.75, 1, 1.25, 1.5, 2],
            html5: {
                vhs: {
                    overrideNative: true
                },
                nativeVideoTracks: false,
                nativeAudioTracks: false,
                nativeTextTracks: false
            },
            plugins: {
                hotkeys: {
                    volumeStep: 0.1,
                    seekStep: 5,
                    enableModifiersForNumbers: false
                }
            }
        });

        // Professional player ready event
        this.player.ready(() => {
            console.log('✅ Professional Video Player Ready');
            this.setupSubtitleSupport();
            this.customizePlayerUI();
        });

        // Track player events
        this.player.on('loadstart', () => console.log('Video loading started'));
        this.player.on('canplay', () => console.log('Video can start playing'));
        this.player.on('error', (e) => this.handleVideoError(e));
        this.player.on('timeupdate', () => this.updateWatchProgress());
    }

    setupSubtitleSupport() {
        // Setup subtitle parsing and rendering
        this.player.on('loadedmetadata', () => {
            this.parseAvailableSubtitles();
        });
    }

    customizePlayerUI() {
        // Add professional styling classes
        this.player.addClass('professional-player');
        
        // Add custom subtitle button to control bar
        const SubtitleButton = videojs.extend(videojs.Button, {
            constructor: function() {
                videojs.Button.apply(this, arguments);
                this.addClass('vjs-subtitle-button');
            },
            buildCSSClass: function() {
                return 'vjs-subtitle-button vjs-control vjs-button';
            },
            createEl: function() {
                const button = videojs.Button.prototype.createEl.call(this, 'button');
                button.innerHTML = '<i class="fas fa-closed-captioning"></i>';
                button.title = 'Subtitles';
                return button;
            },
            handleClick: function() {
                window.professionalPlayer.toggleSubtitleMenu();
            }
        });

        videojs.registerComponent('SubtitleButton', SubtitleButton);
        this.player.getChild('controlBar').addChild('SubtitleButton', {}, 7);
    }

    setupEventListeners() {
        // Subtitle menu toggle
        document.getElementById('subtitle-btn')?.addEventListener('click', () => {
            this.toggleSubtitleMenu();
        });

        // Quality menu toggle  
        document.getElementById('quality-btn')?.addEventListener('click', () => {
            this.toggleQualityMenu();
        });

        // Click outside to close menus
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.subtitle-menu') && !e.target.closest('#subtitle-btn')) {
                this.hideSubtitleMenu();
            }
            if (!e.target.closest('.quality-menu') && !e.target.closest('#quality-btn')) {
                this.hideQualityMenu();
            }
        });
    }

    loadInitialServer() {
        // Load first available server automatically
        const servers = window.availableServers || [];
        if (servers.length > 0) {
            console.log('Loading first server:', servers[0]);
            this.switchServer(servers[0].type, servers[0].url);
        }
    }

    async switchServer(serverType, serverUrl) {
        console.log(`🔄 Switching to ${serverType} server:`, serverUrl);
        
        this.currentServer = { type: serverType, url: serverUrl };
        this.updateServerButtons(serverType);

        try {
            switch (serverType) {
                case 'm3u8':
                    await this.loadM3U8Stream(serverUrl);
                    break;
                case 'direct':
                    await this.loadDirectVideo(serverUrl);
                    break;
                case 'embed':
                    this.loadEmbedPlayer(serverUrl);
                    break;
                case 'iqiyi':
                    await this.loadIQiyiStream(serverUrl);
                    break;
                default:
                    throw new Error('Unknown server type');
            }
        } catch (error) {
            console.error(`Error switching to ${serverType}:`, error);
            this.showNotification(`Failed to load ${serverType} server`, 'error');
        }
    }

    async loadM3U8Stream(url) {
        this.showVideoPlayer();
        
        if (this.player.tech().hls) {
            this.player.src({
                src: url,
                type: 'application/x-mpegURL'
            });
        } else {
            // Fallback for browsers without HLS support
            this.player.src({
                src: url,
                type: 'application/x-mpegURL'
            });
        }
        
        this.showNotification('M3U8 stream loaded', 'success');
    }

    async loadDirectVideo(url) {
        this.showVideoPlayer();
        
        this.player.src({
            src: url,
            type: 'video/mp4'
        });
        
        this.showNotification('Direct video loaded', 'success');
    }

    loadEmbedPlayer(url) {
        console.log('🔄 Loading Server 2 - Embed iframe');
        this.hideVideoPlayer();
        
        const embedContainer = document.getElementById('embed-container');
        const embedPlayer = document.getElementById('embed-player');
        
        console.log('📺 Embed elements found:', {
            container: !!embedContainer,
            player: !!embedPlayer,
            url: url
        });
        
        if (embedContainer && embedPlayer) {
            embedPlayer.src = url;
            embedContainer.classList.remove('hidden');
            console.log('✅ Server 2 embed iframe created and injected');
            this.showNotification('Embed player loaded', 'success');
            
            // Add load event listener
            embedPlayer.onload = () => {
                console.log('✅ Server 2 embed iframe loaded successfully');
            };
            
            embedPlayer.onerror = (error) => {
                console.error('❌ Server 2 embed iframe failed to load:', error);
                this.showNotification('Embed player failed to load', 'error');
            };
        } else {
            console.error('❌ Embed container or player not found');
            this.showNotification('Embed container not found', 'error');
        }
    }

    async loadIQiyiStream(playUrl) {
        this.showVideoPlayer();
        this.showNotification('Extracting M3U8 from iQiyi...', 'info');
        
        try {
            const response = await fetch('/api/extract-iqiyi-m3u8', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    iqiyi_play_url: playUrl
                })
            });

            const data = await response.json();
            
            if (data.success && data.m3u8_content) {
                console.log('✅ M3U8 extracted successfully, content length:', data.m3u8_content.length);
                
                // Create blob URL for M3U8 content
                const blob = new Blob([data.m3u8_content], { 
                    type: 'application/vnd.apple.mpegurl' 
                });
                const blobUrl = URL.createObjectURL(blob);
                console.log('Created M3U8 blob URL:', blobUrl);
                
                // Load the M3U8 stream
                await this.loadM3U8Stream(blobUrl);
                this.showNotification('iQiyi stream ready!', 'success');
            } else {
                throw new Error(data.error || 'Failed to extract M3U8');
            }
        } catch (error) {
            console.error('❌ Failed to extract M3U8:', error);
            this.showIQiyiError(error.message);
        }
    }

    showIQiyiError(errorMessage) {
        // Show professional error modal for iQiyi
        const errorHtml = `
            <div class="text-center text-white p-8">
                <div class="mb-6">
                    <div class="inline-flex items-center justify-center w-20 h-20 rounded-full bg-red-500/20 mb-4">
                        <i class="fas fa-exclamation-triangle text-3xl text-red-400"></i>
                    </div>
                    <h3 class="text-2xl font-bold mb-2">iQiyi Server Error</h3>
                    <p class="text-lg text-gray-300 mb-4">${errorMessage}</p>
                </div>
                <div class="bg-gray-700 p-4 rounded-lg mb-6 text-left">
                    <p class="text-sm text-gray-300 mb-2">Troubleshooting:</p>
                    <ul class="text-xs text-gray-400 space-y-1">
                        <li>• iQiyi requires valid authentication/signature</li>
                        <li>• DASH URLs expire after a few minutes</li>
                        <li>• Try other servers (M3U8, Embed) instead</li>
                        <li>• Admin needs to refresh episode URLs</li>
                    </ul>
                    <p class="text-xs text-yellow-400 mt-2">
                        💡 Server 3 successfully extracts episode ID but needs fresh DASH URL
                    </p>
                </div>
                <div class="flex gap-4 justify-center">
                    <button onclick="window.professionalPlayer.switchServer('m3u8', window.availableServers.find(s => s.type === 'm3u8')?.url)" 
                            class="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors">
                        Use Server 1 (M3U8)
                    </button>
                    <button onclick="window.professionalPlayer.switchServer('iqiyi', '${this.currentServer?.url}')" 
                            class="px-6 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg transition-colors">
                        Try Again
                    </button>
                </div>
            </div>
        `;
        
        // Show in video container temporarily
        this.showCustomMessage(errorHtml);
    }

    showCustomMessage(html) {
        const videoContainer = document.getElementById('video-container');
        const messageDiv = document.createElement('div');
        messageDiv.id = 'custom-message';
        messageDiv.className = 'absolute inset-0 flex items-center justify-center bg-black/80 backdrop-blur-sm z-50';
        messageDiv.innerHTML = html;
        
        // Remove existing message
        const existing = document.getElementById('custom-message');
        if (existing) existing.remove();
        
        videoContainer.appendChild(messageDiv);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.remove();
            }
        }, 10000);
    }

    showVideoPlayer() {
        document.getElementById('video-player')?.classList.remove('hidden');
        document.getElementById('embed-container')?.classList.add('hidden');
    }

    hideVideoPlayer() {
        document.getElementById('video-player')?.classList.add('hidden');
        // Also hide embed container when showing video player
        document.getElementById('embed-container')?.classList.add('hidden');
    }

    updateServerButtons(activeType) {
        document.querySelectorAll('.server-btn').forEach(btn => {
            btn.classList.remove('bg-red-600', 'bg-blue-600', 'bg-orange-600', 'bg-slate-600');
            btn.classList.add('bg-gray-600');
        });
        
        const activeBtn = document.getElementById(`server-${activeType}`);
        if (activeBtn) {
            activeBtn.classList.remove('bg-gray-600');
            if (activeType === 'm3u8') activeBtn.classList.add('bg-red-600');
            else if (activeType === 'embed') activeBtn.classList.add('bg-blue-600');
            else if (activeType === 'iqiyi') activeBtn.classList.add('bg-orange-600');
            else if (activeType === 'direct') activeBtn.classList.add('bg-slate-600');
        }
    }

    toggleSubtitleMenu() {
        const menu = document.getElementById('subtitle-menu');
        menu?.classList.toggle('active');
    }

    hideSubtitleMenu() {
        document.getElementById('subtitle-menu')?.classList.remove('active');
    }

    toggleQualityMenu() {
        const menu = document.getElementById('quality-menu');
        menu?.classList.toggle('active');
    }

    hideQualityMenu() {
        document.getElementById('quality-menu')?.classList.remove('active');
    }

    parseAvailableSubtitles() {
        // Parse subtitle information from episode data
        if (window.episodeSubtitles && window.episodeSubtitles.length > 0) {
            this.availableSubtitles = window.episodeSubtitles;
            this.updateSubtitleMenu();
        }
    }

    updateSubtitleMenu() {
        const optionsContainer = document.getElementById('subtitle-options');
        if (!optionsContainer) return;

        // Clear existing options except "Off"
        const offOption = optionsContainer.querySelector('[data-lang="off"]');
        optionsContainer.innerHTML = '';
        if (offOption) optionsContainer.appendChild(offOption);

        // Add available subtitles
        this.availableSubtitles.forEach(subtitle => {
            const option = document.createElement('div');
            option.className = 'subtitle-option';
            option.dataset.lang = subtitle.language_code || subtitle.language;
            option.dataset.url = subtitle.url;
            option.dataset.type = subtitle.subtitle_type;
            option.textContent = `${subtitle.language} (${subtitle.subtitle_type.toUpperCase()})`;
            option.onclick = () => this.selectSubtitle(subtitle);
            optionsContainer.appendChild(option);
        });
    }

    async selectSubtitle(subtitle) {
        if (!subtitle) {
            // Turn off subtitles
            this.player.textTracks().tracks_.forEach(track => {
                track.mode = 'disabled';
            });
            this.currentSubtitle = null;
            this.updateSubtitleMenuSelection('off');
            return;
        }

        try {
            // Load and parse subtitle file
            const subtitleContent = await this.loadSubtitleFile(subtitle.url);
            const parsedSubtitle = this.parseSubtitleContent(subtitleContent, subtitle.subtitle_type);
            
            // Add subtitle track to player
            this.addSubtitleTrack(parsedSubtitle, subtitle);
            this.currentSubtitle = subtitle;
            this.updateSubtitleMenuSelection(subtitle.language_code || subtitle.language);
            
            this.showNotification(`Subtitle loaded: ${subtitle.language}`, 'success');
        } catch (error) {
            console.error('Failed to load subtitle:', error);
            this.showNotification('Failed to load subtitle', 'error');
        }
    }

    async loadSubtitleFile(url) {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Failed to fetch subtitle: ${response.status}`);
        }
        return await response.text();
    }

    parseSubtitleContent(content, type) {
        switch (type.toLowerCase()) {
            case 'srt':
                return this.parseSRT(content);
            case 'vtt':
                return this.parseVTT(content);
            case 'xml':
                return this.parseXML(content);
            default:
                throw new Error(`Unsupported subtitle type: ${type}`);
        }
    }

    parseSRT(content) {
        const lines = content.split('\n');
        const cues = [];
        let currentCue = null;

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            
            if (/^\d+$/.test(line)) {
                currentCue = { index: parseInt(line) };
            } else if (line.includes('-->')) {
                const times = line.split('-->');
                currentCue.startTime = this.parseTimeString(times[0].trim());
                currentCue.endTime = this.parseTimeString(times[1].trim());
                currentCue.text = '';
            } else if (line && currentCue && 'startTime' in currentCue) {
                currentCue.text += (currentCue.text ? '\n' : '') + line;
            } else if (!line && currentCue) {
                cues.push(currentCue);
                currentCue = null;
            }
        }
        
        if (currentCue) cues.push(currentCue);
        return cues;
    }

    parseVTT(content) {
        // Basic VTT parsing - could be enhanced for more features
        return this.parseSRT(content.replace(/^WEBVTT\n\n/, ''));
    }

    parseXML(content) {
        // Basic XML subtitle parsing
        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(content, 'text/xml');
        const cues = [];
        
        // This is a simplified parser - real implementation would depend on XML format
        const subtitles = xmlDoc.getElementsByTagName('subtitle');
        for (let i = 0; i < subtitles.length; i++) {
            const subtitle = subtitles[i];
            cues.push({
                startTime: parseFloat(subtitle.getAttribute('start') || 0),
                endTime: parseFloat(subtitle.getAttribute('end') || 0),
                text: subtitle.textContent || ''
            });
        }
        
        return cues;
    }

    parseTimeString(timeStr) {
        const parts = timeStr.replace(',', '.').split(':');
        const hours = parseFloat(parts[0] || 0);
        const minutes = parseFloat(parts[1] || 0);
        const seconds = parseFloat(parts[2] || 0);
        return hours * 3600 + minutes * 60 + seconds;
    }

    addSubtitleTrack(cues, subtitle) {
        // Remove existing subtitle tracks
        const existingTracks = this.player.textTracks();
        for (let i = existingTracks.length - 1; i >= 0; i--) {
            if (existingTracks[i].kind === 'subtitles') {
                this.player.removeTextTrack(existingTracks[i]);
            }
        }

        // Add new subtitle track
        const track = this.player.addTextTrack('subtitles', subtitle.language, subtitle.language_code || 'en');
        track.mode = 'showing';

        // Add cues to track
        cues.forEach(cue => {
            track.addCue(new VTTCue(cue.startTime, cue.endTime, cue.text));
        });
    }

    updateSubtitleMenuSelection(selectedLang) {
        document.querySelectorAll('.subtitle-option').forEach(option => {
            option.classList.remove('active');
            if (option.dataset.lang === selectedLang) {
                option.classList.add('active');
            }
        });
    }

    updateWatchProgress() {
        if (!this.player || this.player.paused()) return;

        const currentTime = this.player.currentTime();
        const duration = this.player.duration();
        
        if (duration && currentTime > 0) {
            const progressData = {
                watch_time: currentTime,
                total_duration: duration,
                completed: Math.min(100, (currentTime / duration) * 100)
            };

            // Throttle progress updates to every 5 seconds
            if (!this.lastProgressUpdate || Date.now() - this.lastProgressUpdate > 5000) {
                this.sendProgressUpdate(progressData);
                this.lastProgressUpdate = Date.now();
            }
        }
    }

    async sendProgressUpdate(progressData) {
        try {
            const response = await fetch('/api/update-watch-progress', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    episode_id: window.currentEpisodeId,
                    ...progressData
                })
            });

            if (!response.ok) {
                throw new Error('Failed to update progress');
            }
        } catch (error) {
            console.error('Failed to update watch progress:', error.message);
        }
    }

    handleVideoError(error) {
        console.error('Video player error:', error);
        const errorMsg = this.player.error()?.message || 'Unknown playback error';
        this.showNotification(`Playback error: ${errorMsg}`, 'error');
    }

    showNotification(message, type = 'info') {
        // Show professional notification
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 z-50 px-6 py-4 rounded-lg shadow-lg transform translate-x-full transition-transform duration-300`;
        
        switch (type) {
            case 'success':
                notification.classList.add('bg-green-600', 'text-white');
                break;
            case 'error':
                notification.classList.add('bg-red-600', 'text-white');
                break;
            case 'warning':
                notification.classList.add('bg-yellow-600', 'text-white');
                break;
            default:
                notification.classList.add('bg-blue-600', 'text-white');
        }
        
        notification.textContent = message;
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.classList.remove('translate-x-full');
        }, 100);
        
        // Auto-remove
        setTimeout(() => {
            notification.classList.add('translate-x-full');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        }, 3000);
    }
}

// Initialize professional player when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.professionalPlayer = new ProfessionalVideoPlayer();
});

// Global functions for backward compatibility
function switchServer(type, url) {
    window.professionalPlayer?.switchServer(type, url);
}

function showNotification(message, type) {
    window.professionalPlayer?.showNotification(message, type);
}