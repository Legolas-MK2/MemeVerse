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
     
     // Apply navbar positioning if settings exist
     const savedPositions = localStorage.getItem('navbarPositions');
     if (savedPositions) {
         try {
             const positions = JSON.parse(savedPositions);
             const navbar = document.getElementById('main-navbar');
             
             // Remove all positioning classes
             navbar.classList.remove('nav-left', 'nav-right', 'nav-top', 'nav-bottom');
             
             // Apply positioning based on device type
             const isMobile = window.matchMedia("(max-width: 768px)").matches;
             if (isMobile) {
                 // For mobile, use mobile setting
                 navbar.classList.add(`nav-${positions.mobile}`);
             } else {
                 // For desktop, use PC setting
                 navbar.classList.add(`nav-${positions.pc}`);
             }
         } catch (e) {
             console.error('Error applying saved positions:', e);
         }
     } else {
         // Apply default positioning based on database defaults
         const navbar = document.getElementById('main-navbar');
         navbar.classList.remove('nav-left', 'nav-right', 'nav-top', 'nav-bottom');
         
         // Check if we're on a mobile device
         const isMobile = window.matchMedia("(max-width: 768px)").matches;
         if (isMobile) {
             // For mobile, use default mobile setting
             navbar.classList.add('nav-bottom');
         } else {
             // For desktop, use default PC setting
             navbar.classList.add('nav-left');
         }
     }
     
     console.log("Initialization complete.");
}


// Start initialization
initializeApp();

// Function to open media in an overlay (used in profile page)
function openMediaOverlay(meme) {
    // Create overlay element
    const overlay = document.createElement('div');
    overlay.className = 'media-overlay';
    overlay.id = 'media-overlay';
    
    // Create overlay content
    let overlayContent;
    if (meme.media_type === 'video') {
        overlayContent = `
            <div class="overlay-content">
                <video src="/media/${meme.id}" 
                       controls autoplay 
                       disablePictureInPicture
                       controlsList="nodownload"></video>
            </div>
        `;
    } else {
        overlayContent = `
            <div class="overlay-content">
                <img src="/media/${meme.id}" alt="Liked meme">
            </div>
        `;
    }
    
    // Add unlike button for authenticated users
    const unlikeButton = `
        <button class="overlay-unlike-button" data-meme-id="${meme.id}">
            <i data-feather="heart"></i> Unlike
        </button>
    `;
    
    overlay.innerHTML = `
        <div class="overlay-close">×</div>
        ${overlayContent}
        ${unlikeButton}
    `;
    
    // Add close functionality
    overlay.querySelector('.overlay-close').addEventListener('click', () => {
        document.body.removeChild(overlay);
    });
    
    // Add unlike functionality
    overlay.querySelector('.overlay-unlike-button').addEventListener('click', async (e) => {
        e.stopPropagation();
        const memeId = e.target.closest('.overlay-unlike-button').dataset.memeId;
        try {
            const response = await fetch(`/api/like/${memeId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (response.ok) {
                // Remove the meme from the grid
                const memeElements = document.querySelectorAll(`.meme-media-container[data-media-id="${memeId}"]`);
                memeElements.forEach(el => {
                    el.closest('.meme-item').remove();
                });
                
                // Close overlay
                document.body.removeChild(overlay);
            } else {
                console.error('Failed to unlike meme');
            }
        } catch (error) {
            console.error('Error unliking meme:', error);
        }
    });
    
    // Close when clicking outside content
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            document.body.removeChild(overlay);
        }
    });
    
    // Add to document
    document.body.appendChild(overlay);
    
    // Initialize feather icons
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
}
