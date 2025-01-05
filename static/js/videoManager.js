export class VideoManager {
    constructor() {
        this.activeVideo = null;
        this.videoObserver = new IntersectionObserver(this.handleIntersection.bind(this), {
            threshold: [0.8]
        });
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
        const isMuted = videos[0]?.muted ?? true;
        
        // Initialize all videos with the same mute state
        videos.forEach(video => {
            video.muted = isMuted;
            this.videoObserver.unobserve(video);
            this.videoObserver.observe(video);
            
            // Add click handler for direct video mute toggle
            video.addEventListener('click', () => {
                video.muted = !video.muted;
                this.updateMuteButtons();
            });
        });

        // Initialize mute buttons
        this.updateMuteButtons();
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
                    feather.replace(icon);
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

        // Send mute state to backend
        try {
            await fetch('/api/mute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ is_muted: newMuteState })
            });
        } catch (error) {
            console.error('Error updating mute state:', error);
        }
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
