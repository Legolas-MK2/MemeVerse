import { VideoManager } from './videoManager.js';
import { FeedManager } from './feedManager.js';
import { NavigationManager } from './navigationManager.js';

let videoManager;

document.addEventListener('DOMContentLoaded', () => {
    try {
        // Initialize managers first
        videoManager = new VideoManager();
        const feedManager = new FeedManager(videoManager);
        const navigationManager = new NavigationManager();

        // Initial setup
        videoManager.observeVideos();
        feedManager.observeLastItem();
        
        // Initialize Feather icons
        feather.replace();
        
        // Ensure icons are properly initialized in mute buttons
        document.querySelectorAll('.mute-button i').forEach(icon => {
            if (!icon.dataset.feather) {
                icon.dataset.feather = 'volume-x';
                feather.replace(icon);
            }
        });

        // Expose necessary functions to window for HTML event handlers
        window.togglePlay = (video) => videoManager.togglePlay(video);
        window.setActiveTab = (tab) => navigationManager.setActiveTab(tab);
        window.handleDoubleTap = (event, itemId) => feedManager.handleDoubleTap(event, itemId);
        window.toggleLike = (itemId) => feedManager.toggleLike(itemId);
        window.toggleMute = () => {
            if (!videoManager) {
                console.error('VideoManager not initialized');
                return;
            }
            videoManager.toggleGlobalMute();
        };

        // Update mute buttons immediately after initialization
        videoManager.updateMuteButtons();
    } catch (error) {
        console.error('Initialization error:', error);
    }
});
