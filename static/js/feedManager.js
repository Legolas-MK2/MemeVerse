export class FeedManager {
    constructor(videoManager) {
        // Basic state
        this.videoManager = videoManager;
        this.currentPage = 1;
        this.loading = false;
        this.hasMore = true;
        this.isInitialized = false;
        this.activeObserver = null;
        
        // Preloading configuration
        this.preloadThreshold = 5;
        this.preloadingInProgress = false;
        this.cachedNextItems = null;
        this.itemsPerPage = 15;
        
        // Debugging
        this.debug = true;
        this.logPrefix = '[FeedManager]';
        
        // Bind all methods
        this.handleIntersection = this.handleIntersection.bind(this);
        this.initialize = this.initialize.bind(this);
        this.observeLastItem = this.observeLastItem.bind(this);
        this.loadMoreItems = this.loadMoreItems.bind(this);
        this.handleLike = this.handleLike.bind(this);
        this.toggleMute = this.toggleMute.bind(this);
        this.preloadNextItems = this.preloadNextItems.bind(this);
        this.appendCachedItems = this.appendCachedItems.bind(this);
        
        this.preloadedPages = new Map(); // Cache für preloaded pages
        this.currentlyPreloading = new Set(); // Tracking von aktiven preload requests


        // Initialize after DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initialize());
        } else {
            this.initialize();
        }
    }

    log(...args) {
        if (this.debug) {
            const timestamp = new Date().toISOString();
            console.log(`[${timestamp}]${this.logPrefix}`, ...args);
        }
    }

    error(...args) {
        const timestamp = new Date().toISOString();
        console.error(`[${timestamp}]${this.logPrefix} ERROR:`, ...args);
    }

    time(label) {
        if (this.debug) {
            console.time(`${this.logPrefix} ${label}`);
        }
    }

    timeEnd(label) {
        if (this.debug) {
            console.timeEnd(`${this.logPrefix} ${label}`);
        }
    }

    initialize() {
        this.time('Initialize');
        if (this.isInitialized) {
            this.log('Already initialized');
            this.timeEnd('Initialize');
            return;
        }

        // Wait for initial feed items to be rendered
        setTimeout(() => {
            this.log('Initializing FeedManager with options:', {
                rootMargin: '100% 0px',
                threshold: 0.1
            });
            
            // Create new observer with optimized options
            this.activeObserver = new IntersectionObserver(this.handleIntersection, {
                root: null,
                rootMargin: '100% 0px',
                threshold: 0.1
            });

            this.isInitialized = true;
            this.observeLastItem();

            // Load initial items if feed is empty
            const feed = document.querySelector('#feed');
            if (feed && !feed.children.length) {
                this.loadMoreItems();
            }

            // Start preloading next batch
            if (this.hasMore) {
                this.preloadNextItems();
            }
        }, 100);
    }

    // Cleanup method to prevent memory leaks
    cleanup() {
        this.preloadedPages.clear();
        this.currentlyPreloading.clear();
        if (this.activeObserver) {
            this.activeObserver.disconnect();
        }
    }

    toggleMute() {
        if (this.videoManager) {
            this.videoManager.toggleGlobalMute();
        }
    }

    async handleIntersection(entries) {
        entries.forEach(async (entry) => {
            if (entry.isIntersecting) {
                const feedItems = document.querySelectorAll('.feed-item');
                const currentIndex = Array.from(feedItems).indexOf(entry.target);
                const remainingItems = feedItems.length - currentIndex;

                // Start preloading when approaching the end
                if (remainingItems <= this.preloadThreshold && !this.preloadingInProgress && this.hasMore) {
                    await this.preloadNextItems();
                }

                // Append preloaded items if we're at the last item
                if (remainingItems === 1 && this.cachedNextItems) {
                    await this.appendCachedItems();
                }
            }
        });
    }

    observeLastItem() {
        if (!this.isInitialized || !this.activeObserver) {
            this.log('Cannot observe: manager not initialized');
            return;
        }

        // Cleanup previous observations
        this.cleanup();
        
        const feed = document.querySelector('#feed');
        if (!feed) {
            this.log('Feed container not found');
            return;
        }

        const lastItem = feed.querySelector('.feed-item:last-child');
        if (lastItem) {
            this.log('Observing new last item:', lastItem.dataset.id);
            this.activeObserver.observe(lastItem);
        } else {
            this.log('No last item found to observe');
            // Try to load initial items if no items exist
            if (!this.loading && this.hasMore) {
                this.loadMoreItems();
            }
        }
    }

    async preloadNextPages(currentPage) {
        try {
            // Preload next 2 pages
            const pagesToPreload = [currentPage + 1, currentPage + 2];
            
            for (const page of pagesToPreload) {
                // Skip if already preloaded or currently preloading
                if (this.preloadedPages.has(page) || this.currentlyPreloading.has(page)) {
                    continue;
                }

                this.currentlyPreloading.add(page);
                
                const response = await fetch(`/api/feed?page=${page}`);
                const data = await response.json();
                
                if (data.items?.length > 0) {
                    this.preloadedPages.set(page, data);
                    this.log(`Preloaded page ${page}`);
                }
                
                this.currentlyPreloading.delete(page);
            }
        } catch (error) {
            this.error('Error preloading pages:', error);
        }
    }


    async preloadNextItems() {
        try {
            this.preloadingInProgress = true;
            this.log('Preloading next items for page:', this.currentPage + 1);
            
            const response = await fetch(`/api/feed?page=${this.currentPage + 1}`);
            const data = await response.json();
            
            if (data.items && data.items.length > 0) {
                this.cachedNextItems = data;
                this.log('Successfully cached next items:', data.items.length);
            }
        } catch (error) {
            this.error('Error preloading items:', error);
        } finally {
            this.preloadingInProgress = false;
        }
    }

    async appendCachedItems() {
        if (!this.cachedNextItems) return;

        this.time('Append Cached Items');
        try {
            await this.appendItems(this.cachedNextItems.items);
            this.currentPage++;
            this.hasMore = this.cachedNextItems.hasMore;
            this.cachedNextItems = null;

            // Start preloading the next batch immediately
            if (this.hasMore) {
                this.preloadNextItems();
            }

            // Initialize new videos and update observers
            this.videoManager.observeVideos();
            this.observeLastItem();
        } catch (error) {
            this.error('Error appending cached items:', error);
        }
        this.timeEnd('Append Cached Items');
    }

    async loadMoreItems() {
        if (this.loading || !this.hasMore) return;

        try {
            this.loading = true;
            const nextPage = this.currentPage + 1;

            // Check if we have preloaded data
            let data;
            if (this.preloadedPages.has(nextPage)) {
                data = this.preloadedPages.get(nextPage);
                this.preloadedPages.delete(nextPage);
                this.log(`Using preloaded data for page ${nextPage}`);
            } else {
                // Fall back to regular fetch if no preloaded data
                const response = await fetch(`/api/feed?page=${nextPage}`);
                data = await response.json();
            }

            if (data.items?.length > 0) {
                await this.appendItems(data.items);
                this.currentPage = nextPage;
                this.hasMore = data.hasMore;

                // Start preloading next pages
                this.preloadNextPages(this.currentPage);

                // Initialize new content
                this.videoManager.observeVideos();
                this.observeLastItem();
            }
        } catch (error) {
            this.error('Error loading items:', error);
        } finally {
            this.loading = false;
        }
    }



    async appendItems(items) {
        this.time('Append Items');
        const feed = document.getElementById('feed');
        if (!feed) {
            this.error('Feed container not found');
            this.timeEnd('Append Items');
            return;
        }
        
        this.log('Appending items:', {
            count: items.length,
            firstItemId: items[0]?.id,
            lastItemId: items[items.length - 1]?.id
        });

        const fragment = document.createDocumentFragment();
        items.forEach(item => {
            const feedItem = this.createFeedItem(item);
            fragment.appendChild(feedItem);
        });

        feed.appendChild(fragment);
        this.log('Items appended to feed');
        this.timeEnd('Append Items');
    }

    async handleLike(itemId) {
        const likeButton = document.querySelector(`.feed-item[data-id="${itemId}"] .like-button`);
        if (!likeButton) return;

        try {
            const response = await fetch(`/api/like/${itemId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                likeButton.classList.toggle('liked', result.action === 'liked');
                
                if (result.action === 'liked') {
                    this.createLikeAnimation(likeButton);
                }
            }
        } catch (error) {
            this.error('Error toggling like:', error);
        }
    }

    createLikeAnimation(likeButton) {
        const animation = document.createElement('div');
        animation.className = 'like-animation';
        animation.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 24 24" fill="red" stroke="red" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
            </svg>
        `;
        
        const rect = likeButton.getBoundingClientRect();
        const centerX = rect.left + (rect.width / 2);
        const centerY = rect.top + (rect.height / 2);
        animation.style.left = `${centerX}px`;
        animation.style.top = `${centerY}px`;
        document.body.appendChild(animation);
        
        animation.addEventListener('animationend', () => {
            animation.remove();
        });
    }

    createFeedItem(item) {
        this.time('Create Feed Item');
        const div = document.createElement('div');
        div.className = 'feed-item';
        div.dataset.id = item.id;
        
        div.innerHTML = `
            <div class="media-container" ondblclick="feedManager.handleDoubleTap(event, '${item.id}')">
                <div class="feed-item-buttons">
                    <div class="mute-button" onclick="feedManager.toggleMute()">
                        <i data-feather="volume-x"></i>
                    </div>
                    <div class="like-button" onclick="feedManager.handleLike('${item.id}')">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="heart-icon">
                            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                        </svg>
                    </div>
                </div>
                ${item.type === 'video' 
                    ? `<video src="${item.media_url}" 
                        alt="Video content" 
                        loop muted playsinline autoplay 
                        onclick="feedManager.videoManager.togglePlay(this)"></video>`
                    : `<img src="${item.media_url}" 
                        alt="Content by ${item.username}" 
                        loading="lazy">`}
            </div>
        `;

        this.timeEnd('Create Feed Item');
        return div;
    }

    handleDoubleTap(event, itemId) {
        const now = Date.now();
        const DOUBLE_TAP_DELAY = 300;
        
        if (this.lastTap && (now - this.lastTap) < DOUBLE_TAP_DELAY) {
            event.preventDefault();
            this.handleLike(itemId);
        }
        
        this.lastTap = now;
    }
}