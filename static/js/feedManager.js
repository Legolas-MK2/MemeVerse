export class FeedManager {
    constructor(videoManager) {
        this.videoManager = videoManager;
        this.loading = false;
        // this.hasMore = true; // Backend still sends this, but frontend logic is primary
        this.feedContainer = document.getElementById('feed');
        this.renderedItemIds = new Set(); // Track IDs currently in the DOM

        // --- New State Variables ---
        this.cachedMemes = []; // Array to hold meme data not yet fully visible
        this.currentItemIndex = -1; // Index of the highest feed item scrolled past/into view
        this.lastTap = 0; // For double-tap like

        if (!this.feedContainer) {
            console.error('Feed container not found');
            return; // Stop initialization if container is missing
        }

        this.setupVisibilityObserver();
        this.setupEventListeners();

        // Trigger initial load immediately
        console.log("FeedManager initialized. Triggering initial load.");
        this.loadItemsBasedOnCache(); // Start loading the first batch
    }

    // --- New Function: Determine Request Size ---
    getRequestCount() {
        const cacheSize = this.cachedMemes.length;
        console.log(`Current cache size: ${cacheSize}`);
        if (cacheSize >= 24) return 0;
        if (cacheSize >= 21) return 1;
        if (cacheSize >= 16) return 4;
        if (cacheSize >= 8) return 10; // Max request size
        if (cacheSize >= 3) return 4;
        // if (cacheSize < 3)
        return 1; // Includes initial load (cacheSize == 0)
    }

    // --- New Function: Load items based on cache state ---
    async loadItemsBasedOnCache() {
        if (this.loading) {
            console.log("Already loading, skipping request.");
            return;
        }

        const requestCount = this.getRequestCount();
        console.log(`Calculated request count: ${requestCount}`);

        if (requestCount <= 0) {
            console.log("Cache full or sufficient, not requesting more items.");
            return;
        }

        this.loading = true;
        // Optional: Show a loading indicator
        console.log(`Requesting ${requestCount} new items...`);

        try {
            const response = await fetch(`/api/feed?count=${requestCount}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log(`Received ${data.items?.length || 0} items.`);

            if (data.items && data.items.length > 0) {
                // Add received items to the internal cache
                this.cachedMemes.push(...data.items);
                console.log(`Cache size after adding: ${this.cachedMemes.length}`);

                // Trigger rendering of items if needed (e.g., if feed is empty or near end)
                this.renderMoreItemsFromCache();
            } else {
                console.log("Received no items or empty array.");
                // Potentially handle end-of-feed scenario if backend 'hasMore' was false
            }

        } catch (error) {
            console.error('Error loading items:', error);
            // Optional: Show error message to user
        } finally {
            this.loading = false;
            // Optional: Hide loading indicator

            // Check again immediately in case the cache is still too low after the request
            // (e.g., if user scrolled very fast during the request)
            // Be careful not to cause infinite loops if requests fail or return 0 items.
             if (this.getRequestCount() > 0 && this.cachedMemes.length < 8) { // Add a condition like minimum cache needed
                 setTimeout(() => this.loadItemsBasedOnCache(), 500); // Add a small delay
             }
        }
    }

    // --- New Function: Render items from cache to DOM ---
    renderMoreItemsFromCache() {
        const itemsToRender = [];
        const maxItemsToRender = 5; // Render a few items at a time from cache

        // Take items from the front of the cache
        while(this.cachedMemes.length > 0 && itemsToRender.length < maxItemsToRender) {
             const item = this.cachedMemes.shift(); // Get item from the beginning of the cache array
             // Avoid re-rendering the same item if logic somehow allows it
             if (!this.renderedItemIds.has(item.id)) {
                itemsToRender.push(item);
                this.renderedItemIds.add(item.id);
             }
        }

        if (itemsToRender.length > 0) {
            console.log(`Rendering ${itemsToRender.length} items from cache. Cache size now: ${this.cachedMemes.length}`);
            this.appendItemsToDOM(itemsToRender);
            // Make sure video manager observes newly added videos
             this.videoManager.observeVideos();
        } else {
             console.log("No items to render from cache right now.");
        }
    }


    // Renamed from appendItems - this now *only* handles DOM manipulation
    appendItemsToDOM(items) {
        const fragment = document.createDocumentFragment();

        items.forEach(item => {
            const feedItem = document.createElement('div');
            feedItem.className = 'feed-item';
            feedItem.dataset.id = item.id;
            feedItem.dataset.mediaType = item.media_type; // Store type for observer

            // Use the existing template structure (ensure it matches your feeditem.html or adjust)
            feedItem.innerHTML = `
                <div class="media-container">
                    <div class="feed-item-buttons">
                        ${item.media_type === 'video' ? `
                        <button class="action-button mute-button">
                             <i data-feather="volume-x"></i>
                        </button>
                        ` : ''}
                        <button class="action-button like-button">
                            <svg class="heart-icon" viewBox="0 0 24 24">
                                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                            </svg>
                        </button>
                        <div class="item-info">
                            <span class="username">${item.username}</span>
                            <span class="likes-count" id="likes-${item.id}">${this.formatLikes(item.likes)} likes</span>
                         </div>
                    </div>
                    ${item.media_type === 'video'
                        ? `<video src="${item.media_url}"
                                class="media-element"
                                loop muted playsinline></video>` /* Removed autoplay - let observer handle */
                        : `<img src="${item.media_url}"
                                class="media-element"
                                alt="Posted by ${item.username}"
                                loading="lazy">`}
                </div>
            `;

            // Add event listeners directly here if preferred over onclick attributes
            const likeButton = feedItem.querySelector('.like-button');
            if (likeButton) {
                likeButton.addEventListener('click', () => this.handleLike(item.id));
            }
             const muteButton = feedItem.querySelector('.mute-button');
             if (muteButton) {
                 muteButton.addEventListener('click', () => this.videoManager.toggleGlobalMute());
             }
            const mediaElement = feedItem.querySelector('.media-element');
             if (mediaElement && item.media_type === 'video') {
                 mediaElement.addEventListener('click', () => this.videoManager.togglePlay(mediaElement));
             }


            fragment.appendChild(feedItem);
            this.visibilityObserver.observe(feedItem); // Observe the new item
        });

        this.feedContainer.appendChild(fragment);

        if (typeof feather !== 'undefined') {
            feather.replace(); // Update icons
        }
    }

     formatLikes(value) {
        if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
        if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
        return value.toString();
     }

    // --- Modify Observer Logic ---
    setupVisibilityObserver() {
        this.visibilityObserver = new IntersectionObserver(
            (entries) => {
                entries.forEach(entry => {
                    const feedItem = entry.target;
                    const items = Array.from(this.feedContainer.querySelectorAll('.feed-item'));
                    const itemIndex = items.indexOf(feedItem);

                    if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
                         // Item is significantly visible
                         console.log(`Item ${feedItem.dataset.id} intersecting at index ${itemIndex}`);
                         this.currentItemIndex = Math.max(this.currentItemIndex, itemIndex); // Track highest index seen

                        // Render more from cache if we are near the end of rendered items
                         if (items.length - itemIndex < 3 && this.cachedMemes.length > 0) {
                             console.log("Near end of rendered items, rendering more from cache.");
                             this.renderMoreItemsFromCache();
                         }

                         // Check if we need to load more into the cache based on cache size
                         if (!this.loading && this.getRequestCount() > 0) {
                             console.log("Cache low, loading more items based on cache.");
                             this.loadItemsBasedOnCache();
                         }

                    } else if (!entry.isIntersecting) {
                         // Item is no longer intersecting
                         // We don't strictly need to track cache decrement here,
                         // as the cache represents items *fetched but not yet rendered/scrolled past*.
                         // The trigger to fetch more is the cache size itself dropping.
                         // However, if an item scrolls *off screen*, we might want to remove it from DOM eventually
                         // to save memory (advanced optimization).
                          // If it scrolled off the *top*
                         if (entry.boundingClientRect.top < 0) {
                              // Optionally: Mark item as "seen" or potentially remove from DOM if far enough back
                             // console.log(`Item ${feedItem.dataset.id} scrolled off top`);
                         }
                    }
                });
            },
            {
                root: null, // Use viewport as root
                threshold: 0.5 // Trigger when 50% visible
            }
        );

        // Observe any initially rendered items (should be none now)
        // this.feedContainer.querySelectorAll('.feed-item').forEach(item => {
        //     this.visibilityObserver.observe(item);
        // });
    }

    setupEventListeners() {
        // --- Double Tap Like ---
        // Use a more robust double-tap detection on the container
        this.feedContainer.addEventListener('click', (e) => {
            // Check if the click is on the media container itself or the media element
            const mediaContainer = e.target.closest('.media-container');
             const feedItem = e.target.closest('.feed-item');

             // Prevent double-tap if clicking on buttons
             if (e.target.closest('.action-button')) {
                 return;
             }

            if (mediaContainer && feedItem) {
                const now = Date.now();
                // Use a data attribute on the item to store last tap time
                const lastTapTime = parseInt(feedItem.dataset.lastTap || '0');

                if (now - lastTapTime < 300) { // 300ms threshold for double tap
                    console.log(`Double tap detected on item ${feedItem.dataset.id}`);
                    this.handleLike(feedItem.dataset.id);
                    // Reset last tap time to prevent triple taps counting as double
                    feedItem.dataset.lastTap = '0';
                } else {
                    feedItem.dataset.lastTap = now.toString();
                }
            }
        });

        // --- Optional: Debounced scroll listener if needed for other things ---
        // window.addEventListener('scroll', debounce(this.handleScroll.bind(this), 100));
    }

    // handleScroll() { // Example if using scroll listener
    //     // Check scroll position, maybe trigger loading if observer fails?
    // }

    async handleLike(itemId) {
        const feedItem = this.feedContainer.querySelector(`.feed-item[data-id="${itemId}"]`);
        if (!feedItem) return;

        const likeButton = feedItem.querySelector('.like-button');
        const likesCountSpan = feedItem.querySelector('.likes-count'); // Corrected selector

        // Immediately toggle UI for responsiveness
        const isCurrentlyLiked = likeButton.classList.contains('liked');
        likeButton.classList.toggle('liked');
         if (!isCurrentlyLiked) { // If it wasn't liked before, show animation
              this.createLikeAnimation(likeButton);
         }

         // Basic like count update (backend should return the true count)
         let currentLikes = parseInt(likesCountSpan.textContent.replace(/,/g, '').split(' ')[0]) || 0;
         // Note: This simple increment/decrement can be wrong if multiple users interact.
         // It's better to update with the value returned from the server.
         // likesCountSpan.textContent = `${this.formatLikes(isCurrentlyLiked ? currentLikes - 1 : currentLikes + 1)} likes`;


        try {
            const response = await fetch(`/api/like/${itemId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!response.ok) {
                 console.error(`Like request failed: ${response.status}`);
                 // Revert UI on failure
                 likeButton.classList.toggle('liked', isCurrentlyLiked); // Revert to original state
                // Optionally revert like count span too, or show error
                 return;
             }

            const data = await response.json();

            if (data.status === 'success') {
                console.log(`Item ${itemId} action: ${data.action}`);
                // Update UI based on definitive server response (especially if count is returned)
                 likeButton.classList.toggle('liked', data.action === 'liked');
                 // If backend returns the new count:
                 // if (data.new_like_count !== undefined && likesCountSpan) {
                 //    likesCountSpan.textContent = `${this.formatLikes(data.new_like_count)} likes`;
                 // }
            } else {
                 console.error(`Like action failed: ${data.message}`);
                 // Revert UI on failure
                 likeButton.classList.toggle('liked', isCurrentlyLiked); // Revert to original state
            }

        } catch (error) {
            console.error('Error handling like:', error);
            // Revert UI on network error
             likeButton.classList.toggle('liked', isCurrentlyLiked); // Revert to original state
        }
    }

    createLikeAnimation(likeButton) {
        const animation = document.createElement('div');
        animation.className = 'like-animation';
        // Ensure the SVG has correct styling or use an inline style
        animation.innerHTML = `
            <svg viewBox="0 0 24 24" style="width: 100%; height: 100%; fill: red; stroke: red; stroke-width: 1;">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
            </svg>
        `;

        // Position animation roughly over the media container center or like button
        const feedItem = likeButton.closest('.feed-item');
        const mediaContainer = feedItem?.querySelector('.media-container');
        if(mediaContainer) {
             const rect = mediaContainer.getBoundingClientRect();
             // Position in the center of the media container
             animation.style.position = 'fixed'; // Use fixed to position relative to viewport
             animation.style.left = `${rect.left + rect.width / 2 - 25}px`; // Adjust for animation size (50px/2)
             animation.style.top = `${rect.top + rect.height / 2 - 25}px`; // Adjust for animation size (50px/2)
             animation.style.width = '50px';
             animation.style.height = '50px';
             animation.style.zIndex = '2001'; // Ensure it's above content

            document.body.appendChild(animation);
            animation.addEventListener('animationend', () => animation.remove());
        }
    }

    // toggleMute method is no longer needed here, handled by VideoManager instance
    // toggleMute() {
    //     this.videoManager?.toggleGlobalMute();
    // }
}

// Helper for debouncing scroll events if needed
// function debounce(func, wait) {
//     let timeout;
//     return function executedFunction(...args) {
//         const later = () => {
//             clearTimeout(timeout);
//             func(...args);
//         };
//         clearTimeout(timeout);
//         timeout = setTimeout(later, wait);
//     };
// }

// Ensure VideoManager is initialized and passed correctly in main.js
// window.feedManager = new FeedManager(videoManagerInstance);