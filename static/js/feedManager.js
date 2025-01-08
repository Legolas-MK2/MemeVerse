export class FeedManager {
    constructor(videoManager) {
        this.videoManager = videoManager;
        this.currentPage = 1;
        this.loading = false;
        this.hasMore = true;
        this.preloadThreshold = 8; // Start loading when within 8 items of the end
        this.feedContainer = document.getElementById('feed');
        
        if (!this.feedContainer) {
            throw new Error('Feed container not found');
        }

        // Initialize observers for tracking visible items
        this.setupVisibilityObserver();
        this.setupEventListeners();
        
        // Initial check for preloading
        this.checkForPreload();
    }

    setupVisibilityObserver() {
        // Create observer to track which items are visible
        this.visibilityObserver = new IntersectionObserver(
            (entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        // Update currently visible item
                        const visibleItem = entry.target;
                        this.checkForPreload(visibleItem);
                    }
                });
            },
            {
                root: this.feedContainer,
                threshold: 0.5 // Item is considered visible when 50% visible
            }
        );

        // Observe all initial items
        this.feedContainer.querySelectorAll('.feed-item').forEach(item => {
            this.visibilityObserver.observe(item);
        });
    }

    setupEventListeners() {
        // Handle double-tap likes
        this.feedContainer.addEventListener('click', (e) => {
            const feedItem = e.target.closest('.feed-item');
            if (feedItem) {
                const now = Date.now();
                if (now - this.lastTap < 300) { // Double tap detected
                    this.handleLike(feedItem.dataset.id);
                }
                this.lastTap = now;
            }
        });
    }

    async checkForPreload(visibleItem) {
        if (this.loading || !this.hasMore) return;

        const items = Array.from(this.feedContainer.querySelectorAll('.feed-item'));
        const currentIndex = visibleItem ? items.indexOf(visibleItem) : 0;
        const remainingItems = items.length - currentIndex;

        // Start loading more when user is within threshold of the end
        if (remainingItems <= this.preloadThreshold) {
            await this.loadMoreItems();
        }
    }

    async loadMoreItems() {
        try {
            this.loading = true;
            
            const response = await fetch(`/api/feed?page=${this.currentPage + 1}`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const data = await response.json();
            
            if (data.items?.length > 0) {
                await this.appendItems(data.items);
                this.currentPage++;
                this.hasMore = data.hasMore;
                
                // Initialize videos in new content
                this.videoManager.observeVideos();
            } else {
                this.hasMore = false;
            }
        } catch (error) {
            console.error('Error loading more items:', error);
        } finally {
            this.loading = false;
        }
    }

    async appendItems(items) {
        const fragment = document.createDocumentFragment();
        
        items.forEach(item => {
            const feedItem = document.createElement('div');
            feedItem.className = 'feed-item';
            feedItem.dataset.id = item.id;
            
            feedItem.innerHTML = `
                <div class="media-container">
                    <div class="feed-item-buttons">
                        <button class="action-button mute-button" onclick="feedManager.toggleMute()">
                            <i data-feather="volume-x"></i>
                        </button>
                        <button class="action-button like-button" onclick="feedManager.handleLike('${item.id}')">
                            <svg class="heart-icon" viewBox="0 0 24 24">
                                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                            </svg>
                        </button>
                        <div class="item-info">
                            <span class="username">${item.username}</span>
                            <span class="likes-count" id="likes-${item.id}">${item.likes || 0} likes</span>
                        </div>
                    </div>
                    ${item.type === 'video' 
                        ? `<video src="/media/${item.id}"
                               class="media-element"
                               loop muted playsinline
                               onclick="feedManager.videoManager.togglePlay(this)"></video>`
                        : `<img src="/media/${item.id}"
                               class="media-element"
                               alt="Posted by ${item.username}"
                               loading="lazy">`}
                </div>
            `;
            
            // Observe the new item for visibility
            this.visibilityObserver.observe(feedItem);
            fragment.appendChild(feedItem);
        });

        this.feedContainer.appendChild(fragment);
        
        // Replace Feather icons in new content
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }

    async handleLike(itemId) {
        try {
            const response = await fetch(`/api/like/${itemId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            const likeButton = document.querySelector(`.feed-item[data-id="${itemId}"] .like-button`);
            const likesCount = document.getElementById(`likes-${itemId}`);
            
            if (likeButton) {
                likeButton.classList.toggle('liked', data.action === 'liked');
                if (data.action === 'liked') {
                    this.createLikeAnimation(likeButton);
                }
            }
            
            if (likesCount) {
                likesCount.textContent = `${data.likes} likes`;
            }
        } catch (error) {
            console.error('Error handling like:', error);
        }
    }

    createLikeAnimation(likeButton) {
        const animation = document.createElement('div');
        animation.className = 'like-animation';
        animation.innerHTML = `
            <svg viewBox="0 0 24 24" fill="red" stroke="red" stroke-width="2">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
            </svg>
        `;
        
        const rect = likeButton.getBoundingClientRect();
        animation.style.left = `${rect.left + rect.width / 2}px`;
        animation.style.top = `${rect.top + rect.height / 2}px`;
        
        document.body.appendChild(animation);
        animation.addEventListener('animationend', () => animation.remove());
    }

    toggleMute() {
        this.videoManager?.toggleGlobalMute();
    }
}