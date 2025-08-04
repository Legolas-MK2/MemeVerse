export class FeedManager {
    constructor(videoManager) {
        this.videoManager = videoManager;
        this.loading = false;
        this.feedContainer = document.getElementById('feed');
        this.renderedItems = new Map(); // Track rendered items by ID
        this.itemCounter = 0; // Track total items loaded
        this.visibleItems = new Set(); // Track currently visible items
        
        // Performance optimization: limit DOM items
        this.maxDomItems = 20;
        this.loadThreshold = 5; // Load more when this many items from bottom are visible
        
        if (!this.feedContainer) {
            console.error('Feed container not found');
            return;
        }

        this.setupVisibilityObserver();
        this.setupEventListeners();
        
        // Trigger initial load
        console.log("FeedManager initialized. Loading first item.");
        this.loadNextItem();
    }

    // Load a single item (for the first item)
    async loadNextItem() {
        if (this.loading) return;
        
        this.loading = true;
        try {
            const response = await fetch('/api/feed?count=1');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            if (data.items && data.items.length > 0) {
                this.appendItemsToDOM([data.items[0]]);
                this.videoManager.observeVideos();
            }
        } catch (error) {
            console.error('Error loading item:', error);
        } finally {
            this.loading = false;
        }
    }
    
    // Load multiple items (for subsequent loads)
    async loadBatchItems(count = 5) {
        if (this.loading) return;
        
        this.loading = true;
        try {
            const response = await fetch(`/api/feed?count=${count}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            if (data.items && data.items.length > 0) {
                this.appendItemsToDOM(data.items);
                this.videoManager.observeVideos();
            }
        } catch (error) {
            console.error('Error loading batch items:', error);
        } finally {
            this.loading = false;
        }
    }

    // Append items to DOM with performance optimization
    appendItemsToDOM(items) {
        const fragment = document.createDocumentFragment();
        const newElements = [];
        
        items.forEach(item => {
            // Skip if already rendered
            if (this.renderedItems.has(item.id)) return;
            
            const feedItem = document.createElement('div');
            feedItem.className = 'feed-item';
            feedItem.dataset.id = item.id;
            feedItem.dataset.mediaType = item.media_type;
            
            feedItem.innerHTML = `
                <div class="media-container">
                    <div class="feed-item-buttons">
                        ${item.media_type === 'video' ? `
                        <button class="action-button mute-button">
                             <i data-feather="volume-x"></i>
                        </button>
                        ` : ''}
                        <button class="action-button like-button ${item.liked ? 'liked' : ''}">
                            <svg class="heart-icon" viewBox="0 0 24 24">
                                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                            </svg>
                        </button>
                    </div>
                    ${item.media_type === 'video'
                        ? `<div class="video-wrapper">
                               <video src="${item.media_url}"
                                      class="media-element"
                                      loop muted playsinline></video>
                               <div class="progress-container">
                                   <div class="progress-bar">
                                       <div class="progress-indicator"></div>
                                   </div>
                               </div>
                           </div>`
                        : `<img src="${item.media_url}"
                                class="media-element"
                                alt="Meme image"
                                loading="lazy">`}
</div>
            `;
            
            // Add event listeners
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
                // Initialize progress tracking for the video
                this.initializeVideoWithProgress(mediaElement);
            }
            
            fragment.appendChild(feedItem);
            newElements.push(feedItem);
            
            // Track in our map
            this.renderedItems.set(item.id, {
                element: feedItem,
                timestamp: Date.now(),
                position: this.itemCounter++
            });
            
            // Observe the new item
            this.visibilityObserver.observe(feedItem);
        });
        
        this.feedContainer.appendChild(fragment);
        
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
        
        // Clean up old items if we have too many
        this.cleanupOldItems();
        
        return newElements;
    }
    
    // Remove old items from DOM to maintain performance
    cleanupOldItems() {
        if (this.renderedItems.size <= this.maxDomItems) return;
        
        // Convert map to array and sort by position (oldest first)
        const itemsArray = Array.from(this.renderedItems.entries())
            .sort((a, b) => a[1].position - b[1].position);
        
        // Calculate how many items to remove
        const itemsToRemove = this.renderedItems.size - this.maxDomItems;
        
        // Remove oldest items that are not currently visible
        let removedCount = 0;
        for (let i = 0; i < itemsArray.length && removedCount < itemsToRemove; i++) {
            const [itemId, itemData] = itemsArray[i];
            // Don't remove items that are currently visible
            if (!this.visibleItems.has(itemId)) {
                if (itemData.element && itemData.element.parentNode) {
                    itemData.element.parentNode.removeChild(itemData.element);
                    this.renderedItems.delete(itemId);
                    removedCount++;
                }
            }
        }
        
        console.log(`Cleaned up ${removedCount} old items from DOM`);
    }

    setupVisibilityObserver() {
        this.visibilityObserver = new IntersectionObserver(
            (entries) => {
                entries.forEach(entry => {
                    const feedItem = entry.target;
                    const itemId = feedItem.dataset.id;
                    
                    if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
                        // Item is visible
                        this.visibleItems.add(itemId);
                        console.log(`Item ${itemId} is visible`);
                        
                        // Check if this is the last item in the feed
                        const itemsArray = Array.from(this.renderedItems.entries());
                        const lastItem = itemsArray[itemsArray.length - 1];
                        
                        if (lastItem && lastItem[0] === itemId) {
                            // If we're at the last item, load more items
                            console.log("Reached last item, loading more items");
                            
                            // Load next item or batch depending on current state
                            if (this.renderedItems.size === 1) {
                                // After first item, load a batch
                                this.loadBatchItems(5);
                            } else if (this.renderedItems.size % 10 === 0) {
                                // Every 10 items, load a larger batch
                                this.loadBatchItems(10);
                            } else if (this.renderedItems.size % 3 === 0) {
                                // Every 3 items, load a small batch
                                this.loadBatchItems(3);
                            }
                        }
                    } else {
                        // Item is no longer visible
                        this.visibleItems.delete(itemId);
                    }
                });
            },
            {
                root: null,
                threshold: 0.5
            }
        );
    }

    setupEventListeners() {
        // Double tap like functionality
        this.feedContainer.addEventListener('click', (e) => {
            const mediaContainer = e.target.closest('.media-container');
            const feedItem = e.target.closest('.feed-item');
            
            // Prevent double-tap if clicking on buttons
            if (e.target.closest('.action-button')) {
                return;
            }
            
            if (mediaContainer && feedItem) {
                const now = Date.now();
                const lastTapTime = parseInt(feedItem.dataset.lastTap || '0');
                
                if (now - lastTapTime < 300) {
                    console.log(`Double tap detected on item ${feedItem.dataset.id}`);
                    this.handleLike(feedItem.dataset.id);
                    feedItem.dataset.lastTap = '0';
                } else {
                    feedItem.dataset.lastTap = now.toString();
                }
            }
        });
        
        // Scroll to load more items at the end
        window.addEventListener('scroll', () => {
            // Check if we're near the bottom of the page
            if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 1000) {
                // Load more items if we're not already loading
                if (!this.loading && this.renderedItems.size > 1) {
                    console.log("Near bottom of page, loading more items");
                    this.loadBatchItems(5);
                }
            }
        });
    }

    async handleLike(itemId) {
        const feedItem = this.feedContainer.querySelector(`.feed-item[data-id="${itemId}"]`);
        if (!feedItem) return;
        
        const likeButton = feedItem.querySelector('.like-button');
        const likesCountSpan = feedItem.querySelector('.likes-count');
        
        // Immediately toggle UI for responsiveness
        const isCurrentlyLiked = likeButton.classList.contains('liked');
        likeButton.classList.toggle('liked');
        
        if (!isCurrentlyLiked) {
            this.createLikeAnimation(likeButton);
        }
        
        try {
            const response = await fetch(`/api/like/${itemId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (!response.ok) {
                console.error(`Like request failed: ${response.status}`);
                likeButton.classList.toggle('liked', isCurrentlyLiked);
                return;
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                console.log(`Item ${itemId} action: ${data.action}`);
                likeButton.classList.toggle('liked', data.action === 'liked');
            } else {
                console.error(`Like action failed: ${data.message}`);
                likeButton.classList.toggle('liked', isCurrentlyLiked);
            }
        } catch (error) {
            console.error('Error handling like:', error);
            likeButton.classList.toggle('liked', isCurrentlyLiked);
        }
    }

    createLikeAnimation(likeButton) {
        const animation = document.createElement('div');
        animation.className = 'like-animation';
        animation.innerHTML = `
            <svg viewBox="0 0 24 24" style="width: 100%; height: 100%; fill: red; stroke: red; stroke-width: 1;">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
            </svg>
        `;
        
        const feedItem = likeButton.closest('.feed-item');
        const mediaContainer = feedItem?.querySelector('.media-container');
        if(mediaContainer) {
            const rect = mediaContainer.getBoundingClientRect();
            animation.style.position = 'fixed';
            animation.style.left = `${rect.left + rect.width / 2 - 25}px`;
            animation.style.top = `${rect.top + rect.height / 2 - 25}px`;
            animation.style.width = '50px';
            animation.style.height = '50px';
            animation.style.zIndex = '2001';
            
            document.body.appendChild(animation);
            animation.addEventListener('animationend', () => animation.remove());
        }
    }

    formatLikes(value) {
        if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
        if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
        return value.toString();
    }
    
    initializeVideoWithProgress(videoElement) {
        // Find the progress indicator for this video
        const mediaContainer = videoElement.closest('.media-container');
        const progressIndicator = mediaContainer?.querySelector('.progress-indicator');
        
        if (!progressIndicator) return;
        
        // Update progress as video plays
        videoElement.addEventListener('timeupdate', () => {
            const progress = (videoElement.currentTime / videoElement.duration) * 100;
            progressIndicator.style.width = `${progress}%`;
        });
        
        // Reset progress when video ends (for non-looping videos)
        videoElement.addEventListener('ended', () => {
            progressIndicator.style.width = '0%';
        });
    }
}
