import { VideoManager } from './videoManager.js';
import { FeedManager } from './feedManager.js';

// Make feedManager global only if necessary for debugging or onclick attributes
window.feedManager = null;
window.videoManager = null; // Make VideoManager instance accessible if needed globally

async function initializeApp() {
    try {
        // Wait for DOM to be fully loaded
        if (document.readyState !== 'loading') {
             console.log("DOM already loaded.");
             initManagers();
        } else {
             console.log("Waiting for DOMContentLoaded...");
             document.addEventListener('DOMContentLoaded', initManagers);
        }

    } catch (error) {
        console.error('Error initializing app:', error);
    }
}

function initManagers() {
     console.log("Initializing managers...");
     // Initialize managers
     window.videoManager = new VideoManager();

     // Only initialize FeedManager if we're on the feed page
     const feedContainer = document.getElementById('feed');
     if (feedContainer) {
         console.log("Feed container found, initializing FeedManager.");
         window.feedManager = new FeedManager(window.videoManager);
     } else {
         console.log("Feed container not found, FeedManager not initialized.");
     }

     // Initialize Feather icons if they exist
     if (typeof feather !== 'undefined') {
         feather.replace();
         console.log("Feather icons replaced.");
     }

     // Hide initial loader if it exists
     const initialLoader = document.getElementById('initial-loader');
     if (initialLoader) {
         initialLoader.style.display = 'none';
     }
     console.log("Initialization complete.");
}


// Start initialization
initializeApp();