export class VideoManager {
    constructor() {
        this.activeVideo = null;
        this._initializedVideos = new WeakSet();
        this._userInteracted = false;
        this.videoObserver = new IntersectionObserver(this.handleIntersection.bind(this), {
            threshold: [0.8]
        });

        // After first user interaction, unmute all videos (browsers allow audio after interaction)
        const enableAudio = () => {
            this._userInteracted = true;
            const videos = document.querySelectorAll('video');
            videos.forEach(video => { video.muted = false; });
            this.updateMuteButtons();
            document.removeEventListener('click', enableAudio);
            document.removeEventListener('touchstart', enableAudio);
            document.removeEventListener('keydown', enableAudio);
        };
        document.addEventListener('click', enableAudio, { once: false });
        document.addEventListener('touchstart', enableAudio, { once: false });
        document.addEventListener('keydown', enableAudio, { once: false });
    }

    handleIntersection(entries) {
        entries.forEach((entry) => {
            const video = entry.target;
            
            if (entry.isIntersecting) {
                if (entry.intersectionRatio > 0.8) {
                    if (this.activeVideo && this.activeVideo !== video) {
                        this.activeVideo.pause();
                    }
                    
                    video.play().then(() => {
                        this.activeVideo = video;
                    }).catch((error) => {
                        console.error('Video playback failed:', error);
                        video.controls = true;
                    });
                }
            } else {
                video.pause();
                if (this.activeVideo === video) {
                    this.activeVideo = null;
                }
            }
        });
    }

    observeVideos() {
        const videos = document.querySelectorAll('video');
        const isMuted = this._userInteracted ? false : (videos[0]?.muted ?? true);

        // Initialize all videos with the same mute state
        videos.forEach(video => {
            video.muted = isMuted;
            this.videoObserver.unobserve(video);
            this.videoObserver.observe(video);

            // Skip if already initialized to prevent listener accumulation
            if (this._initializedVideos.has(video)) return;
            this._initializedVideos.add(video);

            // Add click handler for direct video mute toggle
            video.addEventListener('click', () => {
                video.muted = !video.muted;
                this.updateMuteButtons();
            });

            // Add progress tracking
            this.addProgressTracking(video);
        });

        // Initialize mute buttons
        this.updateMuteButtons();
    }

    addProgressTracking(video) {
        // Find the progress indicator for this video
        const mediaContainer = video.closest('.media-container');
        const progressIndicator = mediaContainer?.querySelector('.progress-indicator');
        const progressContainer = mediaContainer?.querySelector('.progress-container');
        
        if (!progressIndicator || !progressContainer) return;
        
        // Update progress as video plays
        video.addEventListener('timeupdate', () => {
            const progress = (video.currentTime / video.duration) * 100;
            progressIndicator.style.width = `${progress}%`;
        });
        
        // Reset progress when video ends (for non-looping videos)
        video.addEventListener('ended', () => {
            progressIndicator.style.width = '0%';
        });
        
        // Add click event listener for seeking
        progressContainer.addEventListener('click', (e) => {
            const rect = progressContainer.getBoundingClientRect();
            const pos = (e.clientX - rect.left) / rect.width;
            const seekTime = pos * video.duration;
            video.currentTime = seekTime;
        });
    }

    updateMuteButtons() {
        // Guard against recursive calls
        if (this._updatingMuteButtons) {
            return;
        }
        this._updatingMuteButtons = true;

        try {
            const videos = document.querySelectorAll('video');
            const isMuted = videos[0]?.muted ?? true;
            const muteButtons = document.querySelectorAll('.mute-button');
            
            muteButtons.forEach((muteButtonContainer, index) => {
                
                // Clean up any existing SVG elements
                muteButtonContainer.querySelectorAll('svg').forEach(svg => svg.remove());
                
                // Ensure icon element exists
                let icon = muteButtonContainer.querySelector('i');
                if (!icon) {
                    // Create icon if it doesn't exist
                    icon = document.createElement('i');
                    icon.className = 'feather';
                    muteButtonContainer.appendChild(icon);
                }

                const iconName = isMuted ? 'volume-x' : 'volume-2';
                const currentIcon = icon.dataset.feather;
                // Only update if the icon needs to change
                if (currentIcon !== iconName) {
                    icon.className = 'feather';
                    icon.dataset.feather = iconName;
                    icon.classList.add(`feather-${iconName}`);
                    if (typeof feather !== 'undefined') feather.replace(icon);
                }
            });
        } finally {
            this._updatingMuteButtons = false;
        }
    }

    async toggleGlobalMute(event) {
        const videos = document.querySelectorAll('video');
        const isMuted = videos[0]?.muted ?? true;
        const newMuteState = !isMuted;
        
        // Toggle mute state for all videos
        videos.forEach(video => {
            video.muted = newMuteState;
        });

        // Update all mute button icons
        this.updateMuteButtons();
    }

    togglePlay(video) {
        if (video.paused) {
            if (this.activeVideo && this.activeVideo !== video) {
                this.activeVideo.pause();
            }
            video.play().then(() => {
                this.activeVideo = video;
            }).catch(error => {
                console.error('Video playback failed:', error);
                video.controls = true;
            });
        } else {
            video.pause();
            if (this.activeVideo === video) {
                this.activeVideo = null;
            }
        }
    }
}
