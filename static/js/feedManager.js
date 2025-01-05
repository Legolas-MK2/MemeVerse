export class FeedManager {
    constructor(videoManager) {
        // Basic state
        this.videoManager = videoManager;
        this.currentPage = 1;
        this.loading = false;
        this.hasMore = true;
        this.isInitialized = false;
        this.activeObserver = null;
        
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
                rootMargin: '50px',
                threshold: 0.5
            });
            
            // Create new observer with more conservative options
            this.activeObserver = new IntersectionObserver(this.handleIntersection, {
                root: null,
                rootMargin: '50px',
                threshold: 0.5
            });

            this.isInitialized = true;
            this.observeLastItem();

            // Load initial items if feed is empty
            const feed = document.querySelector('#feed');
            if (feed && !feed.children.length) {
                this.loadMoreItems();
            }
        }, 100); // Small delay to ensure DOM is ready
    }

    cleanup() {
        this.log('Cleaning up observers');
        if (this.activeObserver) {
            this.activeObserver.disconnect();
        }
    }

    toggleMute() {
        if (this.videoManager) {
            this.videoManager.toggleGlobalMute();
        }
    }

    handleIntersection(entries) {
        this.time('Handle Intersection');
        entries.forEach(entry => {
            if (entry.isIntersecting && !this.loading && this.hasMore) {
                this.loadMoreItems();
            }
        });
        this.timeEnd('Handle Intersection');
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

    async loadMoreItems() {
        this.time('Load More Items');
        if (this.loading || !this.hasMore) {
            this.log('Skipping load: already loading or no more items');
            this.timeEnd('Load More Items');
            return;
        }

        try {
            this.loading = true;
            this.log('Loading page:', this.currentPage + 1, {
                currentPage: this.currentPage,
                hasMore: this.hasMore,
                loading: this.loading
            });

            const url = `/api/feed?page=${this.currentPage + 1}`;
            this.log('Fetching feed from:', url);
            const startTime = performance.now();
            const response = await fetch(url);
            const fetchTime = performance.now() - startTime;
            this.log('Fetch completed in:', fetchTime, 'ms');
            
            const data = await response.json();
            this.log('Received response:', {
                status: response.status,
                itemCount: data.items?.length || 0,
                hasMore: data.hasMore
            });
            
            if (data.items && data.items.length > 0) {
                this.log('Received items:', data.items.length);
                await this.appendItems(data.items);
                this.currentPage++;
                this.hasMore = data.hasMore;
                
                // Wait for DOM update
                await new Promise(resolve => requestAnimationFrame(resolve));
                
                this.videoManager.observeVideos();
                this.observeLastItem();
                
                // Initialize icons after everything else
                requestAnimationFrame(() => {
                    feather.replace();
                });
            } else {
                this.log('No more items received');
                this.hasMore = false;
            }
        } catch (error) {
            console.error(this.logPrefix, 'Error loading items:', error);
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
                
                // Only show animation when liking, not unliking
                if (result.action === 'liked') {
                    // Create like animation
                    const animation = document.createElement('div');
                    animation.className = 'like-animation';
                    animation.innerHTML = `
                        <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 24 24" fill="red" stroke="red" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                        </svg>
                    `;
                    
                    // Position and animate
                    const rect = likeButton.getBoundingClientRect();
                    const centerX = rect.left + (rect.width / 2);
                    const centerY = rect.top + (rect.height / 2);
                    animation.style.left = `${centerX}px`;
                    animation.style.top = `${centerY}px`;
                    document.body.appendChild(animation);
                    
                    // Clean up after animation
                    animation.addEventListener('animationend', () => {
                        animation.remove();
                    });
                }
            }
        } catch (error) {
            console.error('Error toggling like:', error);
        }
    }

    // In FeedManager.js, update the createFeedItem method:
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
}
