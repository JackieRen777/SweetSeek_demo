// SweetSeek - Main Page JavaScript

let systemReady = false;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeSystem();
    setupEventListeners();
});

// Initialize system
async function initializeSystem() {
    showLoading('Initializing system...');
    
    try {
        const response = await fetch('/api/init', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            systemReady = true;
            console.log('[Success] System initialized');
        } else {
            console.error('[Failed] System initialization failed');
        }
    } catch (error) {
        console.error('Initialization error:', error);
    } finally {
        hideLoading();
    }
}

// Setup event listeners
function setupEventListeners() {
    const sendBtn = document.getElementById('sendBtn');
    const questionInput = document.getElementById('questionInput');
    const newChatBtn = document.getElementById('newChatBtn');
    
    if (sendBtn) {
        sendBtn.addEventListener('click', handleSendQuestion);
    }
    
    if (questionInput) {
        questionInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendQuestion();
            }
        });
    }
    
    if (newChatBtn) {
        newChatBtn.addEventListener('click', handleNewChat);
    }
    
    // Example questions click
    const exampleQuestions = document.querySelectorAll('.example-questions li');
    exampleQuestions.forEach(item => {
        item.addEventListener('click', () => {
            const question = item.textContent;
            document.getElementById('questionInput').value = question;
            handleSendQuestion();
        });
    });
}

// Handle send question
async function handleSendQuestion() {
    const questionInput = document.getElementById('questionInput');
    const question = questionInput.value.trim();
    
    if (!question) {
        alert('Please enter a question');
        return;
    }
    
    if (!systemReady) {
        alert('System is initializing, please wait...');
        return;
    }
    
    // Clear input
    questionInput.value = '';
    
    // Hide welcome message
    const welcomeMessage = document.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.style.display = 'none';
    }
    
    // Add user message
    addMessage('user', question);
    
    // Show loading
    showLoading('Processing your question...');
    
    try {
        const response = await fetch('/api/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Add assistant message
            addMessage('assistant', data.answer);
            
            // Display references
            displayReferences(data.references || []);
        } else {
            addMessage('assistant', `Error: ${data.error}`);
        }
    } catch (error) {
        console.error('Query error:', error);
        addMessage('assistant', 'Sorry, an error occurred. Please try again.');
    } finally {
        hideLoading();
    }
}

// Add message to chat
function addMessage(role, content) {
    const chatMessages = document.getElementById('chatMessages');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${role}`;
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    
    if (role === 'user') {
        messageContent.textContent = content;
    } else {
        // Format assistant message
        messageContent.innerHTML = formatMessage(content);
    }
    
    messageDiv.appendChild(messageContent);
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Format message content
function formatMessage(text) {
    // Convert markdown-style formatting
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    text = text.replace(/\n/g, '<br>');
    return text;
}

// Display references
function displayReferences(references) {
    const referencesList = document.getElementById('referencesList');
    const refCount = document.getElementById('refCount');
    
    if (references.length === 0) {
        referencesList.innerHTML = `
            <div class="no-references">
                <p>No references found</p>
            </div>
        `;
        refCount.textContent = '0 references';
        return;
    }
    
    refCount.textContent = `${references.length} reference${references.length > 1 ? 's' : ''}`;
    
    referencesList.innerHTML = references.map((ref, index) => `
        <div class="reference-item">
            <h4>${ref.filename || 'Unknown Document'}</h4>
            <p>${ref.content || ref.text || 'No content available'}</p>
            ${ref.score ? `<div class="result-score">Relevance: ${(ref.score * 100).toFixed(1)}%</div>` : ''}
        </div>
    `).join('');
}

// Handle new chat
function handleNewChat() {
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.innerHTML = `
        <div class="welcome-message">
            <div class="welcome-icon"></div>
            <h3>Welcome to SweetSeek!</h3>
            <p>Ask me anything about sweetness-related topics:</p>
            <ul class="example-questions">
                <li>What are the main types of natural sweeteners?</li>
                <li>How do sweet taste receptors work?</li>
                <li>What are the health impacts of artificial sweeteners?</li>
            </ul>
        </div>
    `;
    
    // Clear references
    const referencesList = document.getElementById('referencesList');
    referencesList.innerHTML = `
        <div class="no-references">
            <p>References will be here when you ask a question</p>
        </div>
    `;
    
    document.getElementById('refCount').textContent = '0 references';
    
    // Re-setup example questions
    setupEventListeners();
}

// Show loading overlay
function showLoading(message = 'Processing...') {
    const overlay = document.getElementById('loadingOverlay');
    const text = overlay.querySelector('p');
    if (text) {
        text.textContent = message;
    }
    overlay.style.display = 'flex';
}

// Hide loading overlay
function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = 'none';
}
