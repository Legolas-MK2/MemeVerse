import { VideoManager } from './videoManager.js';
import { FeedManager } from './feedManager.js';
import { NavigationManager } from './navigationManager.js';

// Make feedManager globally accessible
window.feedManager = null;

function initializeManagers() {
    try {
        // Clean up any existing instances
        if (window.feedManager) {
            window.feedManager.cleanup();
        }

        // Initialize managers
        const videoManager = new VideoManager();
        window.feedManager = new FeedManager(videoManager);
        const navigationManager = new NavigationManager();

        // Initial video setup
        videoManager.observeVideos();
        
        // Initialize Feather icons
        if (typeof feather !== 'undefined') {
            feather.replace();
        }

    } catch (error) {
        console.error('Initialization error:', error);
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeManagers);
} else {
    initializeManagers();
}