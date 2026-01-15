// SweetSeek - Search Page JavaScript

document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
});

function setupEventListeners() {
    const searchBtn = document.getElementById('searchBtn');
    const searchInput = document.getElementById('searchInput');
    
    if (searchBtn) {
        searchBtn.addEventListener('click', handleSearch);
    }
    
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleSearch();
            }
        });
    }
}

async function handleSearch() {
    const searchInput = document.getElementById('searchInput');
    const query = searchInput.value.trim();
    
    if (!query) {
        alert('Please enter search keywords');
        return;
    }
    
    showLoading('Searching literature...');
    
    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayResults(data.results || [], query, data.expanded_terms || []);
        } else {
            showError(data.error || 'Search failed');
        }
    } catch (error) {
        console.error('Search error:', error);
        showError('Network error occurred');
    } finally {
        hideLoading();
    }
}

function displayResults(results, query, expandedTerms = []) {
    const searchResults = document.getElementById('searchResults');
    
    if (results.length === 0) {
        searchResults.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon"></div>
                <h3>No Results Found</h3>
                <p>Try different keywords or check your spelling</p>
            </div>
        `;
        return;
    }
    
    searchResults.innerHTML = results.map((result, index) => {
        const authors = result.authors && result.authors.length > 0 
            ? result.authors.slice(0, 3).join(', ') + (result.authors.length > 3 ? ' et al.' : '')
            : 'Unknown Authors';
        
        return `
            <div class="literature-card animate-slide-in" style="animation-delay: ${index * 0.05}s">
                <div class="lit-header">
                    <h4 class="lit-title">${result.title}</h4>
                    <span class="lit-year">${result.year}</span>
                </div>
                <div class="lit-authors">${authors}</div>
                <div class="lit-journal">${result.journal}</div>
                <div class="lit-footer">
                    <span class="lit-doi">${result.doi !== 'Not Available' ? 'DOI: ' + result.doi : ''}</span>
                    <span class="lit-filename">${result.filename}</span>
                </div>
            </div>
        `;
    }).join('');
}

function showError(message) {
    const searchResults = document.getElementById('searchResults');
    searchResults.innerHTML = `
        <div class="empty-state">
            <div class="empty-icon"></div>
            <h3>Error</h3>
            <p>${message}</p>
        </div>
    `;
}

function showLoading(message = 'Searching...') {
    const overlay = document.getElementById('loadingOverlay');
    const text = overlay.querySelector('p');
    if (text) {
        text.textContent = message;
    }
    overlay.style.display = 'flex';
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = 'none';
}
