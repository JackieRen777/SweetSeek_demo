// SweetSeek - Management Page JavaScript

const ADMIN_PASSWORD = 'admin123'; // Change this in production
let isLoggedIn = false;

document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    checkLoginStatus();
});

function setupEventListeners() {
    const loginBtn = document.getElementById('loginBtn');
    const logoutBtn = document.getElementById('logoutBtn');
    const uploadForm = document.getElementById('uploadForm');
    const refreshBtn = document.getElementById('refreshBtn');
    const adminPassword = document.getElementById('adminPassword');
    
    if (loginBtn) {
        loginBtn.addEventListener('click', handleLogin);
    }
    
    if (adminPassword) {
        adminPassword.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                handleLogin();
            }
        });
    }
    
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
    
    if (uploadForm) {
        uploadForm.addEventListener('submit', handleUpload);
    }
    
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadDocuments);
    }
}

function checkLoginStatus() {
    isLoggedIn = sessionStorage.getItem('adminLoggedIn') === 'true';
    
    if (isLoggedIn) {
        showManagementSection();
        loadDocuments();
    }
}

function handleLogin() {
    const passwordInput = document.getElementById('adminPassword');
    const password = passwordInput.value;
    const loginError = document.getElementById('loginError');
    
    if (password === ADMIN_PASSWORD) {
        isLoggedIn = true;
        sessionStorage.setItem('adminLoggedIn', 'true');
        showManagementSection();
        loadDocuments();
        loginError.style.display = 'none';
    } else {
        loginError.textContent = 'Incorrect password';
        loginError.style.display = 'block';
    }
}

function handleLogout() {
    isLoggedIn = false;
    sessionStorage.removeItem('adminLoggedIn');
    document.getElementById('loginSection').style.display = 'block';
    document.getElementById('managementSection').style.display = 'none';
    document.getElementById('adminPassword').value = '';
}

function showManagementSection() {
    document.getElementById('loginSection').style.display = 'none';
    document.getElementById('managementSection').style.display = 'block';
}

async function handleUpload(e) {
    e.preventDefault();
    
    const pdfFile = document.getElementById('pdfFile').files[0];
    const paperTitle = document.getElementById('paperTitle').value;
    const paperAuthors = document.getElementById('paperAuthors').value;
    const paperYear = document.getElementById('paperYear').value;
    const paperJournal = document.getElementById('paperJournal').value;
    
    if (!pdfFile) {
        showStatus('Please select a PDF file', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('files', pdfFile);
    formData.append('category', 'papers');
    formData.append('title', paperTitle);
    formData.append('authors', paperAuthors);
    formData.append('year', paperYear);
    formData.append('journal', paperJournal);
    
    showLoading('Uploading and processing document...');
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            showStatus('Document uploaded successfully!', 'success');
            document.getElementById('uploadForm').reset();
            loadDocuments();
        } else {
            showStatus(`Upload failed: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showStatus('Network error occurred', 'error');
    } finally {
        hideLoading();
    }
}

async function loadDocuments() {
    const documentsList = document.getElementById('documentsList');
    documentsList.innerHTML = '<div class="loading-state">Loading documents...</div>';
    
    try {
        const response = await fetch('/api/documents');
        const data = await response.json();
        
        if (data.success) {
            displayDocuments(data.documents);
        } else {
            documentsList.innerHTML = '<div class="error-message">Failed to load documents</div>';
        }
    } catch (error) {
        console.error('Load error:', error);
        documentsList.innerHTML = '<div class="error-message">Network error</div>';
    }
}

function displayDocuments(documents) {
    const documentsList = document.getElementById('documentsList');
    const allDocs = [...(documents.papers || []), ...(documents.datasets || [])];
    
    if (allDocs.length === 0) {
        documentsList.innerHTML = `
            <div class="empty-state">
                <p>No documents uploaded yet</p>
            </div>
        `;
        return;
    }
    
    documentsList.innerHTML = allDocs.map(doc => `
        <div class="document-item">
            <div class="doc-info">
                <h4>${doc.filename}</h4>
                <p>Size: ${formatFileSize(doc.size)} | Modified: ${formatDate(doc.modified)}</p>
            </div>
            <div class="doc-actions">
                <button class="btn-danger" onclick="deleteDocument('${doc.filename}', 'papers')">
                    Delete
                </button>
            </div>
        </div>
    `).join('');
}

async function deleteDocument(filename, category) {
    if (!confirm(`Are you sure you want to delete "${filename}"?\n\nThe index will be rebuilt after deletion.`)) {
        return;
    }
    
    showLoading('Deleting document...');
    
    try {
        const response = await fetch(`/api/documents/${category}/${filename}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showStatus('Document deleted successfully', 'success');
            loadDocuments();
        } else {
            showStatus(`Delete failed: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Delete error:', error);
        showStatus('Network error occurred', 'error');
    } finally {
        hideLoading();
    }
}

function showStatus(message, type) {
    const uploadStatus = document.getElementById('uploadStatus');
    uploadStatus.textContent = message;
    uploadStatus.className = `status-message ${type}`;
    uploadStatus.style.display = 'block';
    
    setTimeout(() => {
        uploadStatus.style.display = 'none';
    }, 5000);
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

function showLoading(message = 'Processing...') {
    const overlay = document.getElementById('loadingOverlay');
    const text = document.getElementById('loadingText');
    if (text) {
        text.textContent = message;
    }
    overlay.style.display = 'flex';
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = 'none';
}
