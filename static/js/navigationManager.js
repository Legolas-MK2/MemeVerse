export class NavigationManager {
    constructor() {
        this.touchStart = null;
        this.SWIPE_THRESHOLD = 50;
        this.setupEventListeners();
    }

    setupEventListeners() {
        document.addEventListener('touchstart', (e) => {
            this.touchStart = e.touches[0].clientX;
        });

        document.addEventListener('touchend', (e) => {
            if (!this.touchStart) return;

            const touchEnd = e.changedTouches[0].clientX;
            const diff = this.touchStart - touchEnd;

            if (Math.abs(diff) > this.SWIPE_THRESHOLD) {
                const buttons = document.querySelectorAll('.nav-button');
                const activeIndex = Array.from(buttons).findIndex(
                    button => button.classList.contains('active')
                );

                if (diff > 0 && activeIndex < buttons.length - 1) {
                    this.setActiveTab(buttons[activeIndex + 1].querySelector('span').textContent);
                } else if (diff < 0 && activeIndex > 0) {
                    this.setActiveTab(buttons[activeIndex - 1].querySelector('span').textContent);
                }
            }

            this.touchStart = null;
        });
    }

    setActiveTab(tab) {
        const buttons = document.querySelectorAll('.nav-button');
        buttons.forEach(button => {
            if (button.querySelector('span').textContent === tab) {
                button.classList.add('active');
            } else {
                button.classList.remove('active');
            }
        });
    }
}
