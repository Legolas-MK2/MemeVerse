import { VideoManager } from './videoManager.js';
import { FeedManager } from './feedManager.js';

window.feedManager = null;

async function initializeApp() {
    try {
        // Wait for DOM to be fully loaded
        if (document.readyState !== 'complete') {
            await new Promise(resolve => {
                document.addEventListener('DOMContentLoaded', resolve);
            });
        }

        // Initialize managers
        const videoManager = new VideoManager();
        
        // Only initialize FeedManager if we're on the feed page
        const feedContainer = document.getElementById('feed');
        if (feedContainer) {
            window.feedManager = new FeedManager(videoManager);
        }
        
        // Initialize Feather icons
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    } catch (error) {
        console.error('Error initializing app:', error);
    }
}

// Start initialization
initializeApp();