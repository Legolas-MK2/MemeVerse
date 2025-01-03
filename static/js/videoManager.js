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
        console.log('[DEBUG] Entering updateMuteButtons');
        // Guard against recursive calls
        if (this._updatingMuteButtons) {
            console.log('[DEBUG] Recursive call prevented');
            return;
        }
        this._updatingMuteButtons = true;

        try {
            const videos = document.querySelectorAll('video');
            const isMuted = videos[0]?.muted ?? true;
            console.log(`[DEBUG] Current mute state: ${isMuted ? 'muted' : 'unmuted'}`);
            
            const muteButtons = document.querySelectorAll('.mute-button');
            console.log(`[DEBUG] Found ${muteButtons.length} mute buttons`);
            
            muteButtons.forEach((muteButtonContainer, index) => {
                console.log(`[DEBUG] Processing button ${index + 1}`);
                
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
                console.log(`[DEBUG] Button ${index + 1} current icon: ${currentIcon}`);
                
                // Only update if the icon needs to change
                if (currentIcon !== iconName) {
                    console.log(`[DEBUG] Updating button ${index + 1} icon to ${iconName}`);
                    icon.className = 'feather';
                    icon.dataset.feather = iconName;
                    icon.classList.add(`feather-${iconName}`);
                    feather.replace(icon);
                    console.error('Mute button icon changed to:', iconName);
                } else {
                    console.log(`[DEBUG] Button ${index + 1} icon already correct`);
                }
            });
        } finally {
            this._updatingMuteButtons = false;
            console.log('[DEBUG] Exiting updateMuteButtons');
        }
    }

    async toggleGlobalMute(event) {
        console.error('[MUTE] Toggle initiated at:', new Date().toISOString());
        const videos = document.querySelectorAll('video');
        const isMuted = videos[0]?.muted ?? true;
        const newMuteState = !isMuted;
        
        // Toggle mute state for all videos
        videos.forEach(video => {
            video.muted = newMuteState;
        });

        // Update all mute button icons
        console.error('[MUTE] Calling updateMuteButtons');
        this.updateMuteButtons();

        // Send mute state to backend
        console.error(`[MUTE] State changed to: ${newMuteState ? 'muted' : 'unmuted'}`);
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
