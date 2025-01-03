export class FeedManager {
    constructor(videoManager) {
        this.videoManager = videoManager;
        this.currentPage = 1;
        this.loading = false;
        this.hasMore = true;
    }

    observeLastItem() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting && !this.loading && this.hasMore) {
                    this.loadMoreItems();
                }
            });
        }, {
            threshold: 0.5
        });

        const lastItem = document.querySelector('.feed-item:last-child');
        if (lastItem) {
            observer.observe(lastItem);
        }
    }

    async loadMoreItems() {
        try {
            this.loading = true;
            const response = await fetch(`/api/feed?page=${this.currentPage + 1}`);
            const data = await response.json();
            
            if (data.items && data.items.length > 0) {
                this.appendItems(data.items);
                this.currentPage++;
                this.hasMore = data.hasMore;
                this.videoManager.observeVideos();
                this.observeLastItem();
                // Add this line to reinitialize Feather icons
                feather.replace();
            } else {
                this.hasMore = false;
            }
        } catch (error) {
            console.error('Error loading more items:', error);
        } finally {
            this.loading = false;
        }
    }

    appendItems(items) {
        const feed = document.getElementById('feed');
        items.forEach(item => {
            const feedItem = this.createFeedItem(item);
            feed.appendChild(feedItem);
        });
    }

    createFeedItem(item) {
        const div = document.createElement('div');
        div.className = 'feed-item';
        div.dataset.id = item.id;

        div.innerHTML = `
            <div class="media-container" ondblclick="handleDoubleTap(event, '${item.id}')">
                <div class="feed-item-buttons">
                    <div class="mute-button" onclick="toggleMute()">
                        <i data-feather="volume-x"></i>
                    </div>
                    <div class="like-button" onclick="handleLike('${item.id}')">
                        <i data-feather="heart"></i>
                    </div>
                </div>
                ${item.type === 'video' 
                    ? `<video src="${item.media_url}" 
                        alt="Video content" 
                        loop muted playsinline autoplay 
                        onclick="togglePlay(this)"></video>`
                    : `<img src="${item.media_url}" 
                        alt="Content by ${item.username}" 
                        loading="lazy">`}
            </div>
        `;

        // Initialize Feather icons for this item
        feather.replace({}, div);
        
        // Return the element
        return div;
    }

    handleDoubleTap(event, itemId) {
        // Add like animation
        const heart = document.createElement('div');
        heart.className = 'like-animation';
        heart.innerHTML = `<i data-feather="heart" style="width: 80px; height: 80px; color: white;"></i>`;
        heart.style.left = event.clientX + 'px';
        heart.style.top = event.clientY + 'px';
        document.body.appendChild(heart);
        feather.replace();

        // Remove after animation
        heart.addEventListener('animationend', () => {
            heart.remove();
        });

        // Get the actual item ID from the event target
        const feedItem = event.target.closest('.feed-item');
        const actualItemId = feedItem?.dataset?.id || itemId;

        // Toggle like with the correct item ID
        this.toggleLike(actualItemId);
    }

    async toggleLike(itemId) {
        try {
            const response = await fetch(`/api/like/${itemId}`, {
                method: 'POST'
            });
            const data = await response.json();
            console.log('Like toggled:', data);
        } catch (error) {
            console.error('Error toggling like:', error);
        }
    }
}
