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
            displayResults(data.results || [], query);
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

function displayResults(results, query) {
    const resultsHeader = document.getElementById('resultsHeader');
    const resultCount = document.getElementById('resultCount');
    const searchResults = document.getElementById('searchResults');
    
    if (results.length === 0) {
        resultsHeader.style.display = 'none';
        searchResults.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon"></div>
                <h3>No Results Found</h3>
                <p>Try different keywords or check your spelling</p>
            </div>
        `;
        return;
    }
    
    resultsHeader.style.display = 'flex';
    resultCount.textContent = `${results.length} result${results.length > 1 ? 's' : ''} for "${query}"`;
    
    searchResults.innerHTML = results.map((result, index) => `
        <div class="result-item animate-slide-in" style="animation-delay: ${index * 0.1}s">
            <h4>${result.title || result.filename || 'Untitled Document'}</h4>
            <p>${result.content || result.text || 'No content available'}</p>
            <div class="result-meta">
                ${result.score ? `<span class="result-score">Relevance: ${(result.score * 100).toFixed(1)}%</span>` : ''}
                ${result.metadata && result.metadata.file_name ? `<span>Source: ${result.metadata.file_name}</span>` : ''}
            </div>
        </div>
    `).join('');
}

function showError(message) {
    const searchResults = document.getElementById('searchResults');
    searchResults.innerHTML = `
        <div class="empty-state">
            <div class="empty-icon">❌</div>
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
