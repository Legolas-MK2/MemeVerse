const MEMES_PER_PAGE = 24;
const MAX_LOADED_MEMES = 50;

const state = {
    tags: [],
    selectedTags: new Map(),
    selectedMemes: new Set(),
    filterTagIds: new Set(),
    memes: [],
    hasMore: true,
    loadingCount: 0,
    showUntaggedOnly: false,
    viewerVisible: false,
    viewerIndex: -1,
    viewerCurrentId: null,
    currentViewerIndex: null,
    viewerNavigating: false,
    pageData: new Map(),
    pageOrder: [],
    memeMap: new Map(),
    highestIndexLoaded: -1,
    lowestIndexLoaded: null
};

const pageFetchCache = new Map();

const dom = {};

function initDomRefs() {
    dom.tagSearch = document.getElementById('tag-search');
    dom.tagSuggestions = document.getElementById('tag-suggestions');
    dom.userTagsList = document.getElementById('user-tags-list');
    dom.applyTagsBtn = document.getElementById('apply-tags-btn');
    dom.unselectTagsBtn = document.getElementById('unselect-tags-btn');
    dom.unselectMemesBtn = document.getElementById('unselect-memes-btn');
    dom.selectionSummary = document.getElementById('selection-summary');

    dom.memeTagSearch = document.getElementById('meme-tag-search');
    dom.memeTagSuggestions = document.getElementById('meme-tag-suggestions');
    dom.appliedFilters = document.getElementById('applied-filters-tags');
    dom.untaggedToggle = document.getElementById('untagged-toggle');

    dom.memesScroll = document.getElementById('liked-memes-container');
    dom.memesGrid = document.getElementById('liked-memes-grid');
    dom.loadingIndicator = document.getElementById('memes-loading-indicator');

    dom.viewer = document.getElementById('meme-viewer');
    dom.viewerMedia = document.getElementById('viewer-media-container');
    dom.viewerTags = document.getElementById('viewer-tags');
    dom.viewerClose = document.getElementById('viewer-close-btn');
    dom.viewerPrev = document.getElementById('viewer-prev-btn');
    dom.viewerNext = document.getElementById('viewer-next-btn');
    dom.viewerSelectBtn = document.getElementById('viewer-select-btn');
}

function bindEvents() {
    dom.tagSearch.addEventListener('input', handleTagSearchInput);
    dom.tagSearch.addEventListener('keydown', handleTagSearchKeydown);
    dom.memeTagSearch.addEventListener('input', handleMemeFilterSearch);
    dom.memeTagSearch.addEventListener('keydown', handleMemeFilterKeydown);

    dom.applyTagsBtn.addEventListener('click', applySelectedTagsToMemes);
    dom.unselectTagsBtn.addEventListener('click', clearTagSelection);
    dom.unselectMemesBtn.addEventListener('click', clearMemeSelection);

    dom.untaggedToggle.addEventListener('change', handleUntaggedToggle);
    dom.memesScroll.addEventListener('scroll', maybeLoadMoreMemes);

    dom.viewerClose.addEventListener('click', closeViewer);
    dom.viewerPrev.addEventListener('click', () => shiftViewer(-1));
    dom.viewerNext.addEventListener('click', () => shiftViewer(1));
    dom.viewerSelectBtn.addEventListener('click', toggleViewerSelection);

    document.addEventListener('click', handleDocumentClick);
    document.addEventListener('keydown', handleGlobalKeydown);
}

function beginLoading() {
    state.loadingCount += 1;
    dom.loadingIndicator.classList.remove('hidden');
}

function endLoading() {
    state.loadingCount = Math.max(0, state.loadingCount - 1);
    if (state.loadingCount === 0) {
        dom.loadingIndicator.classList.add('hidden');
    }
}

function computePageForIndex(index) {
    return Math.floor(index / MEMES_PER_PAGE) + 1;
}

async function fetchPageData(pageNumber) {
    if (pageFetchCache.has(pageNumber)) {
        return pageFetchCache.get(pageNumber);
    }

    const promise = (async () => {
        const response = await fetch(`/api/liked-memes?page=${pageNumber}&per_page=${MEMES_PER_PAGE}`);
        const data = await response.json();

        if (data.error === 'Not authenticated') {
            window.location.href = '/login';
            return { memes: [], hasMore: false };
        }

        const processedMemes = (data.memes || []).map((meme, idx) => ({
            ...meme,
            _page: pageNumber,
            _index: (pageNumber - 1) * MEMES_PER_PAGE + idx
        }));

        return { memes: processedMemes, hasMore: Boolean(data.hasMore) };
    })();

    pageFetchCache.set(pageNumber, promise);

    promise.finally(() => {
        pageFetchCache.delete(pageNumber);
    });

    return promise;
}

function rebuildMemeMap() {
    state.memeMap = new Map(state.memes.map((meme) => [Number(meme.id), meme]));
}

function rebuildMemesFromPages() {
    state.pageOrder.sort((a, b) => a - b);
    const nextMemes = [];

    state.pageOrder.forEach((pageNumber) => {
        const pageItems = state.pageData.get(pageNumber);
        if (pageItems && pageItems.length) {
            nextMemes.push(...pageItems);
        }
    });

    state.memes = nextMemes;
    rebuildMemeMap();
}

function renderMemesGrid() {
    const previousScrollTop = dom.memesScroll.scrollTop;
    dom.memesGrid.innerHTML = '';

    if (!state.memes.length) {
        const empty = document.createElement('div');
        empty.className = 'empty-state';
        empty.textContent = 'No liked memes yet.';
        dom.memesGrid.appendChild(empty);
        dom.memesScroll.scrollTop = previousScrollTop;
        return;
    }

    state.memes.forEach((meme) => {
        dom.memesGrid.appendChild(buildMemeCard(meme));
    });

    refreshFeather(dom.memesGrid);
    dom.memesScroll.scrollTop = previousScrollTop;
}

function removeMemeFromStructures(position) {
    const removed = position === 'start' ? state.memes.shift() : state.memes.pop();
    if (!removed) {
        return;
    }

    const pageItems = state.pageData.get(removed._page);
    if (pageItems) {
        const idx = pageItems.findIndex((item) => item.id === removed.id);
        if (idx !== -1) {
            pageItems.splice(idx, 1);
        }
        if (pageItems.length === 0) {
            state.pageData.delete(removed._page);
            state.pageOrder = state.pageOrder.filter((page) => page !== removed._page);
        }
    }

    state.selectedMemes.delete(Number(removed.id));
    state.memeMap.delete(Number(removed.id));

    if (state.viewerCurrentId === Number(removed.id)) {
        closeViewer();
    }
}

function enforceMemeLimit(preferredIndex) {
    if (state.memes.length <= MAX_LOADED_MEMES) {
        return;
    }

    const anchorIndex = typeof preferredIndex === 'number'
        ? preferredIndex
        : (state.currentViewerIndex ?? (state.memes[Math.floor(state.memes.length / 2)]?._index ?? 0));

    while (state.memes.length > MAX_LOADED_MEMES) {
        const first = state.memes[0];
        const last = state.memes[state.memes.length - 1];

        if (!first && !last) {
            break;
        }

        const distanceToFirst = first ? Math.abs(anchorIndex - first._index) : -Infinity;
        const distanceToLast = last ? Math.abs(last._index - anchorIndex) : -Infinity;

        if (distanceToFirst > distanceToLast) {
            removeMemeFromStructures('start');
        } else {
            removeMemeFromStructures('end');
        }
    }

    rebuildMemeMap();
}

function getCurrentFirstIndex() {
    return state.memes.length ? state.memes[0]._index : 0;
}

function getCurrentLastIndex() {
    return state.memes.length ? state.memes[state.memes.length - 1]._index : -1;
}

async function loadPage(pageNumber, { position = 'append', preferredIndex } = {}) {
    if (pageNumber < 1) {
        return false;
    }

    beginLoading();

    try {
        const { memes, hasMore } = await fetchPageData(pageNumber);

        if (!memes.length) {
            if (position === 'append') {
                state.hasMore = false;
            }
            return false;
        }

        state.pageData.set(pageNumber, memes.slice());
        if (!state.pageOrder.includes(pageNumber)) {
            state.pageOrder.push(pageNumber);
        }

        rebuildMemesFromPages();

        const pageMinIndex = memes[0]._index;
        const pageMaxIndex = memes[memes.length - 1]._index;
        state.lowestIndexLoaded = state.lowestIndexLoaded === null
            ? pageMinIndex
            : Math.min(state.lowestIndexLoaded, pageMinIndex);
        state.highestIndexLoaded = Math.max(state.highestIndexLoaded, pageMaxIndex);

        enforceMemeLimit(preferredIndex);
        renderMemesGrid();
        applyFiltersToMemes();
        updateApplyButtonState();
        updateSelectionSummary();

        state.hasMore = hasMore;
        return true;
    } catch (error) {
        console.error(`Error loading page ${pageNumber}:`, error);
        return false;
    } finally {
        endLoading();
    }
}

async function loadOlderMemes({ anchorIndex } = {}) {
    const lastIndex = getCurrentLastIndex();
    if (!state.hasMore && lastIndex >= state.highestIndexLoaded) {
        return false;
    }

    const targetIndex = lastIndex + 1;
    const pageNumber = computePageForIndex(targetIndex);
    const preferred = typeof anchorIndex === 'number' ? anchorIndex : targetIndex;
    return loadPage(pageNumber, { position: 'append', preferredIndex: preferred });
}

async function loadNewerMemes({ anchorIndex } = {}) {
    const firstIndex = getCurrentFirstIndex();
    if (firstIndex <= 0 && state.lowestIndexLoaded === 0) {
        return false;
    }

    const targetIndex = firstIndex - 1;
    if (targetIndex < 0) {
        return false;
    }
    const pageNumber = computePageForIndex(targetIndex);
    const preferred = typeof anchorIndex === 'number' ? anchorIndex : targetIndex;
    return loadPage(pageNumber, { position: 'prepend', preferredIndex: preferred });
}

async function ensureIndexAvailable(targetIndex) {
    if (targetIndex < 0) {
        return false;
    }

    if (state.memes.some((meme) => meme._index === targetIndex)) {
        return true;
    }

    const pageNumber = computePageForIndex(targetIndex);
    const position = targetIndex >= getCurrentLastIndex() ? 'append' : 'prepend';
    const loaded = await loadPage(pageNumber, { position, preferredIndex: targetIndex });
    return loaded && state.memes.some((meme) => meme._index === targetIndex);
}

async function resetMemes() {
    state.pageData = new Map();
    state.pageOrder = [];
    state.memes = [];
    state.memeMap = new Map();
    state.selectedMemes.clear();
    state.hasMore = true;
    state.highestIndexLoaded = -1;
    state.lowestIndexLoaded = null;
    state.viewerVisible = false;
    state.viewerIndex = -1;
    state.viewerCurrentId = null;
    state.currentViewerIndex = null;
    state.viewerNavigating = false;

    dom.memesGrid.innerHTML = '';

    const loaded = await loadPage(1, { position: 'append', preferredIndex: 0 });

    if (!loaded && !state.memes.length) {
        renderMemesGrid();
    }
}

function handleDocumentClick(event) {
    if (!dom.tagSearch.contains(event.target) && !dom.tagSuggestions.contains(event.target)) {
        hideSuggestions(dom.tagSuggestions);
    }

    if (!dom.memeTagSearch.contains(event.target) && !dom.memeTagSuggestions.contains(event.target)) {
        hideSuggestions(dom.memeTagSuggestions);
    }
}

function handleGlobalKeydown(event) {
    if (state.viewerVisible) {
        if (event.key === 'Escape') {
            closeViewer();
        } else if (event.key === 'ArrowLeft') {
            event.preventDefault();
            shiftViewer(-1);
        } else if (event.key === 'ArrowRight') {
            event.preventDefault();
            shiftViewer(1);
        }
    }
}

function hideSuggestions(container) {
    container.classList.add('hidden');
    container.innerHTML = '';
}

function escapeHtml(str) {
    return str.replace(/[&<>'"]/g, (char) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    })[char]);
}

async function loadInitialData() {
    await loadUserTags();
    await resetMemes();
    updateSelectionSummary();
}

async function loadUserTags() {
    try {
        const response = await fetch('/api/tags');
        const data = await response.json();

        if (data.status === 'success') {
            state.tags = data.tags;
            renderUserTags();
        } else if (data.status === 'error' && data.message === 'Not logged in') {
            window.location.href = '/login';
        }
    } catch (error) {
        console.error('Error loading tags:', error);
    }
}

function renderUserTags() {
    const container = dom.userTagsList;
    container.innerHTML = '';

    if (!state.tags.length) {
        const empty = document.createElement('div');
        empty.className = 'empty-state';
        empty.textContent = 'No tags yet. Start by creating one above.';
        container.appendChild(empty);
        return;
    }

    state.tags
        .sort((a, b) => a.name.localeCompare(b.name))
        .forEach((tag) => {
            const tagElement = document.createElement('div');
            tagElement.className = 'tag-item';
            tagElement.dataset.tagId = tag.id;
            tagElement.innerHTML = `
                <span class="tag-badge" style="background:${tag.color};">${escapeHtml(tag.name)}</span>
                <button class="remove-tag-btn" type="button" aria-label="Delete tag">
                    <i data-feather="trash-2"></i>
                </button>
            `;

            tagElement.addEventListener('click', (event) => {
                if (event.target.closest('.remove-tag-btn')) {
                    event.stopPropagation();
                    deleteTag(tag.id);
                    return;
                }
                toggleTagSelection(tag);
            });

            container.appendChild(tagElement);
        });

    refreshFeather(container);
    syncSelectedTagHighlight();
}

function toggleTagSelection(tag) {
    if (state.selectedTags.has(tag.id)) {
        state.selectedTags.delete(tag.id);
    } else {
        state.selectedTags.set(tag.id, tag);
    }

    syncSelectedTagHighlight();
    updateApplyButtonState();
    updateSelectionSummary();
}

function syncSelectedTagHighlight() {
    dom.userTagsList.querySelectorAll('.tag-item').forEach((element) => {
        const tagId = Number(element.dataset.tagId);
        element.classList.toggle('selected', state.selectedTags.has(tagId));
    });
}

function clearTagSelection() {
    state.selectedTags.clear();
    syncSelectedTagHighlight();
    updateApplyButtonState();
    updateSelectionSummary();
}

async function deleteTag(tagId) {
    if (!confirm('Delete this tag for all memes?')) {
        return;
    }

    try {
        const response = await fetch(`/api/tags/${tagId}`, { method: 'DELETE' });
        const data = await response.json();

        if (data.status === 'success') {
            state.selectedTags.delete(Number(tagId));
            state.filterTagIds.delete(Number(tagId));
            state.tags = state.tags.filter((tag) => tag.id !== Number(tagId));
            renderUserTags();
            renderAppliedFilters();
            applyFiltersToMemes();
            updateApplyButtonState();
            updateSelectionSummary();
        } else if (data.status === 'error' && data.message === 'Not logged in') {
            window.location.href = '/login';
        } else {
            alert(data.message || 'Failed to delete tag.');
        }
    } catch (error) {
        console.error('Error deleting tag:', error);
        alert('Error deleting tag. Check console for details.');
    }
}

function handleTagSearchInput(event) {
    const term = event.target.value.trim();

    if (!term) {
        hideSuggestions(dom.tagSuggestions);
        return;
    }

    const lowerTerm = term.toLowerCase();
    dom.tagSuggestions.innerHTML = '';

    const createOption = document.createElement('div');
    createOption.className = 'create-tag-option';
    createOption.innerHTML = `Create tag "<strong>${escapeHtml(term)}</strong>"`;
    createOption.addEventListener('click', () => createTag(term));
    dom.tagSuggestions.appendChild(createOption);

    const matches = state.tags.filter((tag) => tag.name.toLowerCase().includes(lowerTerm)).slice(0, 6);
    matches.forEach((tag) => {
        const suggestion = document.createElement('div');
        suggestion.className = 'suggestion-item';
        suggestion.dataset.tagId = tag.id;
        suggestion.innerHTML = `
            <span class="tag-badge" style="background:${tag.color};">${escapeHtml(tag.name)}</span>
            <span class="suggestion-hint">Select</span>
        `;
        suggestion.addEventListener('click', () => {
            toggleTagSelection(tag);
            dom.tagSearch.value = '';
            hideSuggestions(dom.tagSuggestions);
        });
        dom.tagSuggestions.appendChild(suggestion);
    });

    dom.tagSuggestions.classList.remove('hidden');
}

function handleTagSearchKeydown(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        const value = dom.tagSearch.value.trim();
        if (value) {
            createTag(value);
        }
    } else if (event.key === 'Escape') {
        hideSuggestions(dom.tagSuggestions);
        dom.tagSearch.blur();
    }
}

async function createTag(name) {
    try {
        const response = await fetch('/api/tags', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, color: '#94a3b8' })
        });
        const data = await response.json();

        if (data.status === 'success') {
            dom.tagSearch.value = '';
            hideSuggestions(dom.tagSuggestions);
            state.tags.push(data.tag);
            renderUserTags();
            toggleTagSelection(data.tag);
        } else if (data.status === 'error' && data.message === 'Not logged in') {
            window.location.href = '/login';
        } else {
            alert(data.message || 'Unable to create tag.');
        }
    } catch (error) {
        console.error('Error creating tag:', error);
        alert('Error creating tag.');
    }
}

function handleMemeFilterSearch(event) {
    const term = event.target.value.trim();
    if (!term) {
        hideSuggestions(dom.memeTagSuggestions);
        return;
    }

    const lowerTerm = term.toLowerCase();
    dom.memeTagSuggestions.innerHTML = '';

    state.tags
        .filter((tag) => tag.name.toLowerCase().includes(lowerTerm))
        .slice(0, 8)
        .forEach((tag) => {
            const suggestion = document.createElement('div');
            suggestion.className = 'suggestion-item';
            suggestion.dataset.tagId = tag.id;
            suggestion.innerHTML = `
                <span class="tag-badge" style="background:${tag.color};">${escapeHtml(tag.name)}</span>
                <span class="suggestion-hint">Filter</span>
            `;
            suggestion.addEventListener('click', () => {
                addFilterTag(tag);
                dom.memeTagSearch.value = '';
                hideSuggestions(dom.memeTagSuggestions);
            });
            dom.memeTagSuggestions.appendChild(suggestion);
        });

    dom.memeTagSuggestions.classList.remove('hidden');
}

function handleMemeFilterKeydown(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        const value = dom.memeTagSearch.value.trim().toLowerCase();
        if (!value) return;
        const tag = state.tags.find((item) => item.name.toLowerCase() === value);
        if (tag) {
            addFilterTag(tag);
            dom.memeTagSearch.value = '';
            hideSuggestions(dom.memeTagSuggestions);
        }
    } else if (event.key === 'Escape') {
        hideSuggestions(dom.memeTagSuggestions);
        dom.memeTagSearch.blur();
    }
}

function addFilterTag(tag) {
    if (state.filterTagIds.has(tag.id)) {
        return;
    }
    state.filterTagIds.add(tag.id);
    renderAppliedFilters();
    applyFiltersToMemes();
}

function removeFilterTag(tagId) {
    state.filterTagIds.delete(tagId);
    renderAppliedFilters();
    applyFiltersToMemes();
}

function clearFilterTags() {
    state.filterTagIds.clear();
    renderAppliedFilters();
}

function renderAppliedFilters() {
    dom.appliedFilters.innerHTML = '';

    if (!state.filterTagIds.size) {
        const empty = document.createElement('div');
        empty.className = 'empty-state';
        empty.textContent = 'No tag filters applied';
        dom.appliedFilters.appendChild(empty);
        return;
    }

    state.tags
        .filter((tag) => state.filterTagIds.has(tag.id))
        .forEach((tag) => {
            const filter = document.createElement('div');
            filter.className = 'filter-tag';
            filter.dataset.tagId = tag.id;
            filter.innerHTML = `
                <span class="tag-badge" style="background:${tag.color};">${escapeHtml(tag.name)}</span>
                <button class="remove-tag-btn" type="button" aria-label="Remove filter">
                    <i data-feather="x"></i>
                </button>
            `;
            filter.querySelector('.remove-tag-btn').addEventListener('click', () => removeFilterTag(tag.id));
            dom.appliedFilters.appendChild(filter);
        });

    refreshFeather(dom.appliedFilters);
}

function handleUntaggedToggle(event) {
    state.showUntaggedOnly = event.target.checked;
    if (state.showUntaggedOnly && state.filterTagIds.size) {
        clearFilterTags();
    }
    applyFiltersToMemes();
}

function maybeLoadMoreMemes() {
    const { scrollTop, scrollHeight, clientHeight } = dom.memesScroll;
    if (scrollTop + clientHeight >= scrollHeight - 200) {
        loadOlderMemes({ anchorIndex: getCurrentLastIndex() + 1 });
    }
}

function buildMemeCard(meme) {
    const card = document.createElement('article');
    card.className = 'meme-item';
    card.dataset.memeId = meme.id;
    card.setAttribute('role', 'listitem');

    const thumbnail = document.createElement('div');
    thumbnail.className = 'meme-thumbnail';

    if (meme.media_type === 'video') {
        const video = document.createElement('video');
        video.src = meme.media_url;
        video.muted = true;
        video.loop = true;
        video.playsInline = true;
        video.autoplay = true;
        thumbnail.appendChild(video);
    } else {
        const img = document.createElement('img');
        img.src = meme.media_url;
        img.alt = 'Meme preview';
        thumbnail.appendChild(img);
    }

    const typeIndicator = document.createElement('div');
    typeIndicator.className = 'media-type-indicator';
    typeIndicator.innerHTML = `<i data-feather="${meme.media_type === 'video' ? 'video' : 'image'}"></i>`;
    thumbnail.appendChild(typeIndicator);

    const controls = document.createElement('div');
    controls.className = 'meme-controls';

    const viewBtn = document.createElement('button');
    viewBtn.type = 'button';
    viewBtn.className = 'view-button';
    viewBtn.innerHTML = `<i data-feather="maximize-2"></i> View`;
    viewBtn.addEventListener('click', (event) => {
        event.stopPropagation();
        openViewerForMeme(meme.id);
    });

    const selectBtn = document.createElement('button');
    selectBtn.type = 'button';
    selectBtn.className = 'select-toggle';
    selectBtn.innerHTML = '<i data-feather="check"></i>';
    selectBtn.addEventListener('click', (event) => {
        event.stopPropagation();
        toggleMemeSelection(meme.id);
    });

    controls.appendChild(viewBtn);
    controls.appendChild(selectBtn);
    thumbnail.appendChild(controls);

    card.appendChild(thumbnail);

    const meta = document.createElement('div');
    meta.className = 'meme-meta';

    const tagTray = document.createElement('div');
    tagTray.className = 'tag-pill-tray';

    if (meme.tags && meme.tags.length) {
        meme.tags.forEach((tag) => {
            const pill = document.createElement('span');
            pill.className = 'meme-tag-pill';
            pill.style.background = `${tag.color}1A`;
            pill.textContent = tag.name;
            tagTray.appendChild(pill);
        });
    } else {
        const empty = document.createElement('span');
        empty.className = 'empty-state';
        empty.textContent = 'No tags yet';
        tagTray.appendChild(empty);
    }

    meta.appendChild(tagTray);
    card.appendChild(meta);

    card.addEventListener('click', () => toggleMemeSelection(meme.id));

    updateMemeCardSelection(card, meme.id);

    return card;
}

function updateMemeCardSelection(card, memeId) {
    const isSelected = state.selectedMemes.has(Number(memeId));
    card.classList.toggle('selected', isSelected);
}

function toggleMemeSelection(memeId) {
    const id = Number(memeId);
    if (state.selectedMemes.has(id)) {
        state.selectedMemes.delete(id);
    } else {
        state.selectedMemes.add(id);
    }

    const card = dom.memesGrid.querySelector(`.meme-item[data-meme-id="${id}"]`);
    if (card) {
        updateMemeCardSelection(card, id);
    }

    updateApplyButtonState();
    updateSelectionSummary();
}

function clearMemeSelection() {
    state.selectedMemes.clear();
    dom.memesGrid.querySelectorAll('.meme-item.selected').forEach((card) => card.classList.remove('selected'));
    updateApplyButtonState();
    updateSelectionSummary();
}

function updateApplyButtonState() {
    dom.applyTagsBtn.disabled = !(state.selectedTags.size && state.selectedMemes.size);
}

function updateSelectionSummary() {
    const tagCount = state.selectedTags.size;
    const memeCount = state.selectedMemes.size;

    if (!tagCount && !memeCount) {
        dom.selectionSummary.textContent = '';
        return;
    }

    const tagLabel = `${tagCount} tag${tagCount === 1 ? '' : 's'}`;
    const memeLabel = `${memeCount} meme${memeCount === 1 ? '' : 's'}`;
    dom.selectionSummary.textContent = `${tagLabel} selected · ${memeLabel} selected`;
}

function applyFiltersToMemes() {
    const activeFilters = Array.from(state.filterTagIds).map(String);
    dom.memesGrid.querySelectorAll('.meme-item').forEach((card) => {
        const memeId = Number(card.dataset.memeId);
        const meme = state.memeMap.get(memeId);
        if (!meme) {
            card.classList.remove('hidden');
            return;
        }

        const tags = meme.tags || [];
        let visible = true;

        if (activeFilters.length) {
            const memeTagIds = tags.map((tag) => String(tag.id));
            visible = activeFilters.every((filterId) => memeTagIds.includes(filterId));
        }

        if (visible && state.showUntaggedOnly) {
            visible = tags.length === 0;
        }

        card.classList.toggle('hidden', !visible);
    });
}

async function applySelectedTagsToMemes() {
    if (!state.selectedTags.size || !state.selectedMemes.size) {
        return;
    }

    const tagIds = Array.from(state.selectedTags.keys());

    const promises = Array.from(state.selectedMemes).map(async (memeId) => {
        try {
            const response = await fetch(`/api/memes/${memeId}/tags`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tag_ids: tagIds })
            });
            const data = await response.json();
            if (data.status === 'success') {
                const meme = state.memeMap.get(memeId);
                if (meme) {
                    meme.tags = mergeTagsForMeme(meme.tags || [], tagIds);
                }
            }
            return data;
        } catch (error) {
            console.error(`Error tagging meme ${memeId}`, error);
            return { status: 'error', message: error.message };
        }
    });

    try {
        const results = await Promise.all(promises);
        const allGood = results.every((result) => result.status === 'success');

        if (allGood) {
            clearTagSelection();
            clearMemeSelection();
            refreshAllMemeTagDisplays();
            alert('Tags applied successfully.');
        } else {
            alert('Some memes could not be tagged. Check console for details.');
        }
    } catch (error) {
        console.error('Error applying tags:', error);
        alert('Error applying tags.');
    }
}

function mergeTagsForMeme(existingTags, newTagIds) {
    const allTags = [...existingTags];
    newTagIds.forEach((tagId) => {
        if (!allTags.some((tag) => tag.id === tagId)) {
            const sourceTag = state.tags.find((tag) => tag.id === tagId);
            if (sourceTag) {
                allTags.push(sourceTag);
            }
        }
    });
    return allTags;
}

function refreshAllMemeTagDisplays() {
    dom.memesGrid.querySelectorAll('.meme-item').forEach((card) => {
        const memeId = Number(card.dataset.memeId);
        const meme = state.memeMap.get(memeId);
        if (!meme) return;

        const tray = card.querySelector('.tag-pill-tray');
        tray.innerHTML = '';
        if (meme.tags && meme.tags.length) {
            meme.tags.forEach((tag) => {
                const pill = document.createElement('span');
                pill.className = 'meme-tag-pill';
                pill.style.background = `${tag.color}1A`;
                pill.textContent = tag.name;
                tray.appendChild(pill);
            });
        } else {
            const empty = document.createElement('span');
            empty.className = 'empty-state';
            empty.textContent = 'No tags yet';
            tray.appendChild(empty);
        }
    });
}

function openViewerForMeme(memeId) {
    const visibleMemes = getVisibleMemes();
    const index = visibleMemes.findIndex((meme) => meme.id === Number(memeId));
    if (index === -1) {
        return;
    }

    state.viewerIndex = index;
    state.viewerVisible = true;
    renderViewer(visibleMemes[index]);

    dom.viewer.classList.remove('hidden');
    dom.viewer.setAttribute('aria-hidden', 'false');
    dom.viewerClose.focus({ preventScroll: true });
}

function getVisibleMemes() {
    const activeFilters = Array.from(state.filterTagIds);
    return state.memes.filter((meme) => {
        const tags = meme.tags || [];

        if (state.showUntaggedOnly && tags.length) {
            return false;
        }

        if (activeFilters.length) {
            const memeTagIds = tags.map((tag) => tag.id);
            return activeFilters.every((id) => memeTagIds.includes(id));
        }

        return true;
    });
}

function renderViewer(meme) {
    if (!meme) {
        closeViewer();
        return;
    }

    stopViewerMedia();
    dom.viewerMedia.innerHTML = '';

    state.viewerCurrentId = Number(meme.id);
    if (typeof meme._index === 'number') {
        state.currentViewerIndex = meme._index;
    }

    if (meme.media_type === 'video') {
        const video = document.createElement('video');
        video.src = meme.media_url;
        video.controls = true;
        video.autoplay = true;
        video.playsInline = true;
        video.loop = true;
        dom.viewerMedia.appendChild(video);
    } else {
        const img = document.createElement('img');
        img.src = meme.media_url;
        img.alt = 'Meme full view';
        dom.viewerMedia.appendChild(img);
    }

    dom.viewerTags.innerHTML = '';
    if (meme.tags && meme.tags.length) {
        meme.tags.forEach((tag) => {
            const pill = document.createElement('span');
            pill.className = 'viewer-tag-pill';
            pill.style.background = `${tag.color}33`;
            pill.textContent = tag.name;
            dom.viewerTags.appendChild(pill);
        });
    } else {
        const empty = document.createElement('div');
        empty.className = 'empty-state';
        empty.textContent = 'No tags assigned to this meme yet.';
        dom.viewerTags.appendChild(empty);
    }

    const visibleMemes = getVisibleMemes();
    const indexInVisible = visibleMemes.findIndex((item) => item.id === meme.id);
    if (indexInVisible === -1) {
        closeViewer();
        return;
    }

    state.viewerIndex = indexInVisible;

    const atStart = indexInVisible <= 0;
    const canLoadNewer = getCurrentFirstIndex() > 0 || (state.lowestIndexLoaded !== null && state.lowestIndexLoaded > 0);
    dom.viewerPrev.disabled = atStart && !canLoadNewer;

    const atEnd = indexInVisible >= visibleMemes.length - 1;
    const canLoadOlder = state.hasMore || getCurrentLastIndex() < state.highestIndexLoaded;
    dom.viewerNext.disabled = atEnd && !canLoadOlder;

    refreshFeather(dom.viewer);
    syncViewerSelectionState(meme.id);
}

async function shiftViewer(delta) {
    if (!state.viewerVisible) {
        return;
    }

    if (state.viewerNavigating) {
        return;
    }

    state.viewerNavigating = true;

    let visibleMemes = getVisibleMemes();
    if (!visibleMemes.length) {
        closeViewer();
        state.viewerNavigating = false;
        return;
    }

    let newIndex = state.viewerIndex + delta;

    if (delta < 0) {
        while (newIndex < 0) {
            const loaded = await loadNewerMemes({ anchorIndex: (state.currentViewerIndex ?? getCurrentFirstIndex()) - 1 });
            if (!loaded) {
                state.viewerNavigating = false;
                return;
            }
            visibleMemes = getVisibleMemes();
            const currentIndex = visibleMemes.findIndex((item) => Number(item.id) === state.viewerCurrentId);
            if (currentIndex === -1) {
                closeViewer();
                state.viewerNavigating = false;
                return;
            }
            newIndex = currentIndex + delta;
        }
    } else if (delta > 0) {
        while (newIndex >= visibleMemes.length) {
            const loaded = await loadOlderMemes({ anchorIndex: (state.currentViewerIndex ?? getCurrentLastIndex()) + 1 });
            if (!loaded) {
                state.viewerNavigating = false;
                return;
            }
            visibleMemes = getVisibleMemes();
            const currentIndex = visibleMemes.findIndex((item) => Number(item.id) === state.viewerCurrentId);
            if (currentIndex === -1) {
                closeViewer();
                state.viewerNavigating = false;
                return;
            }
            newIndex = currentIndex + delta;
        }
    }

    if (newIndex < 0 || newIndex >= visibleMemes.length) {
        state.viewerNavigating = false;
        return;
    }

    const targetMeme = visibleMemes[newIndex];
    state.viewerIndex = newIndex;
    renderViewer(targetMeme);
    state.viewerNavigating = false;
}

function closeViewer() {
    state.viewerVisible = false;
    state.viewerIndex = -1;
    state.viewerCurrentId = null;
    state.currentViewerIndex = null;
    state.viewerNavigating = false;
    stopViewerMedia();
    dom.viewer.classList.add('hidden');
    dom.viewer.setAttribute('aria-hidden', 'true');
}

function syncViewerSelectionState(memeId) {
    const id = Number(memeId);
    if (state.selectedMemes.has(id)) {
        dom.viewerSelectBtn.textContent = 'Remove from selection';
    } else {
        dom.viewerSelectBtn.textContent = 'Select for tagging';
    }
}

function toggleViewerSelection() {
    if (state.viewerIndex === -1) {
        return;
    }
    const visibleMemes = getVisibleMemes();
    const meme = visibleMemes[state.viewerIndex];
    if (!meme) {
        return;
    }
    toggleMemeSelection(meme.id);
    syncViewerSelectionState(meme.id);
}

function refreshFeather(context = document) {
    if (window.feather && typeof window.feather.replace === 'function') {
        window.feather.replace({ element: context });
    }
}

function stopViewerMedia() {
    const video = dom.viewerMedia.querySelector('video');
    if (video) {
        video.pause();
        video.removeAttribute('src');
        video.load();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initDomRefs();
    bindEvents();
    renderAppliedFilters();
    loadInitialData();
    refreshFeather(document);
});
