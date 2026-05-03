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
        const mediaContainer = video.closest('.media-container');
        const wrapper = video.closest('.video-wrapper');
        const progressIndicator = mediaContainer?.querySelector('.progress-indicator');
        const progressContainer = mediaContainer?.querySelector('.progress-container');
        const progressBar = mediaContainer?.querySelector('.progress-bar');

        if (!progressIndicator || !progressContainer || !progressBar || !wrapper) return;

        let thumb = progressBar.querySelector('.progress-thumb');
        if (!thumb) {
            thumb = document.createElement('div');
            thumb.className = 'progress-thumb';
            progressBar.appendChild(thumb);
        }

        let isDragging = false;
        let resumeAfterDrag = false;

        const setPercent = (percent) => {
            progressIndicator.style.width = `${percent}%`;
            thumb.style.left = `${percent}%`;
        };

        const percentFromClientX = (clientX) => {
            const rect = progressContainer.getBoundingClientRect();
            const ratio = (clientX - rect.left) / rect.width;
            return Math.max(0, Math.min(1, ratio));
        };

        video.addEventListener('timeupdate', () => {
            if (isDragging || !video.duration) return;
            setPercent((video.currentTime / video.duration) * 100);
        });

        video.addEventListener('ended', () => {
            if (!isDragging) setPercent(0);
        });

        // Show the thumb when the cursor is near the bar (YouTube-style hot zone),
        // since the bar itself is only a few pixels tall.
        const PROXIMITY_PX = 32;
        wrapper.addEventListener('mousemove', (e) => {
            if (isDragging) return;
            const rect = progressContainer.getBoundingClientRect();
            const dy = Math.abs(e.clientY - (rect.top + rect.height / 2));
            progressContainer.classList.toggle('is-near', dy <= PROXIMITY_PX);
        });
        wrapper.addEventListener('mouseleave', () => {
            if (!isDragging) progressContainer.classList.remove('is-near');
        });

        const beginDrag = (clientX) => {
            isDragging = true;
            resumeAfterDrag = !video.paused;
            if (resumeAfterDrag) video.pause();
            progressContainer.classList.add('dragging');
            const ratio = percentFromClientX(clientX);
            setPercent(ratio * 100);
            if (video.duration) video.currentTime = ratio * video.duration;
        };

        const moveDrag = (clientX) => {
            const ratio = percentFromClientX(clientX);
            setPercent(ratio * 100);
            if (video.duration) video.currentTime = ratio * video.duration;
        };

        const endDrag = () => {
            if (!isDragging) return;
            isDragging = false;
            progressContainer.classList.remove('dragging');
            progressContainer.classList.remove('is-near');
            if (resumeAfterDrag) video.play().catch(() => {});
        };

        const onMouseMove = (e) => moveDrag(e.clientX);
        const onMouseUp = () => {
            endDrag();
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        };
        progressContainer.addEventListener('mousedown', (e) => {
            e.preventDefault();
            e.stopPropagation();
            beginDrag(e.clientX);
            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
        // Swallow the trailing click so it doesn't reach the double-tap-like handler.
        progressContainer.addEventListener('click', (e) => e.stopPropagation());

        const onTouchMove = (e) => {
            if (!e.touches[0]) return;
            e.preventDefault();
            moveDrag(e.touches[0].clientX);
        };
        const onTouchEnd = () => {
            endDrag();
            document.removeEventListener('touchmove', onTouchMove);
            document.removeEventListener('touchend', onTouchEnd);
            document.removeEventListener('touchcancel', onTouchEnd);
        };
        progressContainer.addEventListener('touchstart', (e) => {
            if (!e.touches[0]) return;
            e.preventDefault();
            e.stopPropagation();
            beginDrag(e.touches[0].clientX);
            document.addEventListener('touchmove', onTouchMove, { passive: false });
            document.addEventListener('touchend', onTouchEnd);
            document.addEventListener('touchcancel', onTouchEnd);
        }, { passive: false });
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
