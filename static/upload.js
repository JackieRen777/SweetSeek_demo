// SweetSeek - Upload Page JavaScript

let currentCategory = 'papers';

document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadDocuments();
});

function setupEventListeners() {
    const uploadBtn = document.getElementById('uploadBtn');
    const refreshBtn = document.getElementById('refreshBtn');
    const fileInput = document.getElementById('fileInput');
    const tabBtns = document.querySelectorAll('.tab-btn');
    
    if (uploadBtn) {
        uploadBtn.addEventListener('click', handleUpload);
    }
    
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadDocuments);
    }
    
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            const files = e.target.files;
            if (files.length > 0) {
                uploadBtn.innerHTML = `<span>Upload ${files.length} file${files.length > 1 ? 's' : ''}</span>`;
            } else {
                uploadBtn.innerHTML = '<span>Upload Files</span>';
            }
        });
    }
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const category = e.target.dataset.category;
            switchCategory(category);
        });
    });
}

async function handleUpload() {
    const fileInput = document.getElementById('fileInput');
    const categorySelect = document.getElementById('categorySelect');
    const files = fileInput.files;
    
    if (files.length === 0) {
        alert('Please select files to upload');
        return;
    }
    
    const formData = new FormData();
    for (let file of files) {
        formData.append('files', file);
    }
    formData.append('category', categorySelect.value);
    
    showProgress(true);
    showLoading('Uploading and processing files...');
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`${data.message}`);
            fileInput.value = '';
            document.getElementById('uploadBtn').innerHTML = '<span>Upload Files</span>';
            loadDocuments();
        } else {
            alert(`Upload failed: ${data.error}`);
        }
    } catch (error) {
        console.error('Upload error:', error);
        alert(`Upload error: ${error.message}`);
    } finally {
        showProgress(false);
        hideLoading();
    }
}

async function loadDocuments() {
    const container = document.getElementById('documentsContainer');
    container.innerHTML = '<div class="loading-state">Loading...</div>';
    
    try {
        const response = await fetch('/api/documents');
        const data = await response.json();
        
        if (data.success) {
            displayDocuments(data.documents);
        } else {
            container.innerHTML = '<div class="error-message">Failed to load documents</div>';
        }
    } catch (error) {
        console.error('Load error:', error);
        container.innerHTML = '<div class="error-message">Network error</div>';
    }
}

function displayDocuments(documents) {
    const container = document.getElementById('documentsContainer');
    const categoryDocs = documents[currentCategory] || [];
    
    if (categoryDocs.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon"></div>
                <h3>No ${currentCategory === 'papers' ? 'Papers' : 'Datasets'}</h3>
                <p>Upload files using the form above</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = categoryDocs.map(doc => `
        <div class="document-item animate-slide-in">
            <div class="doc-info">
                <h4>${doc.filename}</h4>
                <p>Size: ${formatFileSize(doc.size)} | Modified: ${formatDate(doc.modified)}</p>
            </div>
            <div class="doc-actions">
                <button class="btn-danger" onclick="deleteDocument('${doc.filename}')">
                    Delete
                </button>
            </div>
        </div>
    `).join('');
}

function switchCategory(category) {
    currentCategory = category;
    
    // Update tab styles
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-category="${category}"]`).classList.add('active');
    
    // Reload documents
    loadDocuments();
}

async function deleteDocument(filename) {
    if (!confirm(`Are you sure you want to delete "${filename}"?\n\nThe index will be rebuilt after deletion.`)) {
        return;
    }
    
    showLoading('Deleting...');
    
    try {
        const response = await fetch(`/api/documents/${currentCategory}/${filename}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('Deleted successfully');
            loadDocuments();
        } else {
            alert(`Delete failed: ${data.error}`);
        }
    } catch (error) {
        console.error('Delete error:', error);
        alert(`Delete error: ${error.message}`);
    } finally {
        hideLoading();
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function showProgress(show) {
    const progress = document.getElementById('uploadProgress');
    if (progress) {
        progress.style.display = show ? 'block' : 'none';
    }
}

function showLoading(message = 'Processing...') {
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
