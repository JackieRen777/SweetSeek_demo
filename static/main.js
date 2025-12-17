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
    
    // Show typing indicator
    showTypingIndicator();
    
    try {
        const response = await fetch('/api/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question })
        });
        
        const data = await response.json();
        
        // Hide typing indicator
        hideTypingIndicator();
        
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
        hideTypingIndicator();
        addMessage('assistant', 'Sorry, an error occurred. Please try again.');
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
        <div class="reference-item-compact" data-ref-id="${ref.ref_id || `ref_${index + 1}`}">
            <div class="ref-identifier" 
                 onmouseenter="showRefTooltip(event, ${index})"
                 onmouseleave="hideRefTooltip()"
                 onclick="event.stopPropagation()">
                ${ref.ref_id || `ref_${index + 1}`}: ${ref.journal || 'Unknown'} ${ref.year || 'N/A'}
            </div>
        </div>
    `).join('');
    
    // 在body中添加tooltip（避免被容器裁剪）
    references.forEach((ref, index) => {
        const existingTooltip = document.getElementById(`tooltip-${index}`);
        if (existingTooltip) {
            existingTooltip.remove();
        }
        
        const tooltip = document.createElement('div');
        tooltip.className = 'ref-tooltip';
        tooltip.id = `tooltip-${index}`;
        tooltip.style.display = 'none';
        tooltip.innerHTML = `
            <div class="tooltip-content">
                <h4>${ref.title || ref.filename || 'Unknown Title'}</h4>
                <p><strong>Authors:</strong> ${formatAuthors(ref.authors || [])}</p>
                <p><strong>Year:</strong> ${ref.year || 'N/A'}</p>
                <p><strong>DOI:</strong> 
                    ${ref.doi && ref.doi !== 'Not Available' 
                        ? `<a href="https://doi.org/${ref.doi}" target="_blank" rel="noopener">${ref.doi}</a>`
                        : 'Not Available'}
                </p>
            </div>
        `;
        document.body.appendChild(tooltip);
    });
}

// Format authors list
function formatAuthors(authors) {
    if (!authors || authors.length === 0) return 'Unknown';
    if (authors.length <= 3) return authors.join(', ');
    return authors.slice(0, 3).join(', ') + ' et al.';
}

// 全局变量用于管理tooltip
let currentTooltip = null;
let tooltipTimeout = null;
let isMouseOverTooltip = false;

// Show reference tooltip
function showRefTooltip(event, index) {
    // 清除之前的隐藏定时器
    if (tooltipTimeout) {
        clearTimeout(tooltipTimeout);
        tooltipTimeout = null;
    }
    
    // 隐藏其他tooltip
    document.querySelectorAll('.ref-tooltip').forEach(t => {
        if (t.id !== `tooltip-${index}`) {
            t.style.display = 'none';
            t.style.opacity = '0';
        }
    });
    
    const tooltip = document.getElementById(`tooltip-${index}`);
    if (tooltip) {
        const target = event.currentTarget;
        const rect = target.getBoundingClientRect();
        
        // 先显示tooltip以获取其高度
        tooltip.style.display = 'block';
        tooltip.style.opacity = '0';
        
        // 等待一帧以确保tooltip已渲染
        requestAnimationFrame(() => {
            const tooltipHeight = tooltip.offsetHeight;
            const tooltipWidth = tooltip.offsetWidth;
            
            // 计算tooltip位置（在引用标识符上方）
            let left = rect.left;
            let top = rect.top - tooltipHeight - 10;
            
            // 确保tooltip不会超出屏幕左侧
            if (left < 10) {
                left = 10;
            }
            
            // 确保tooltip不会超出屏幕右侧
            if (left + tooltipWidth > window.innerWidth - 10) {
                left = window.innerWidth - tooltipWidth - 10;
            }
            
            // 如果上方空间不够，显示在下方
            if (top < 10) {
                top = rect.bottom + 10;
            }
            
            tooltip.style.left = left + 'px';
            tooltip.style.top = top + 'px';
            
            // 淡入显示
            setTimeout(() => {
                tooltip.style.opacity = '1';
            }, 10);
        });
        
        currentTooltip = tooltip;
        
        // 添加tooltip的鼠标事件监听
        tooltip.onmouseenter = () => {
            isMouseOverTooltip = true;
            if (tooltipTimeout) {
                clearTimeout(tooltipTimeout);
                tooltipTimeout = null;
            }
        };
        
        tooltip.onmouseleave = () => {
            isMouseOverTooltip = false;
            hideRefTooltip();
        };
    }
}

// Hide reference tooltip
function hideRefTooltip() {
    // 延迟隐藏，给用户时间阅读或移动到tooltip上
    tooltipTimeout = setTimeout(() => {
        // 如果鼠标在tooltip上，不隐藏
        if (isMouseOverTooltip) {
            return;
        }
        
        document.querySelectorAll('.ref-tooltip').forEach(tooltip => {
            tooltip.style.opacity = '0';
            setTimeout(() => {
                tooltip.style.display = 'none';
            }, 200);
        });
        currentTooltip = null;
    }, 125); // 125ms延迟
}

// Handle new chat
function handleNewChat() {
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.innerHTML = `
        <div class="welcome-message">
            <div class="welcome-icon"></div>
            <h3>Welcome to SweetSeek!</h3>
            <p>Ask me anything about food science and nutrition:</p>
            <ul class="example-questions">
                <li>What are the main types of natural sweeteners?</li>
                <li>How do sweet taste receptors work?</li>
                <li>What are the health impacts of artificial sweeteners?</li>
                <li>Compare the nutritional profiles of different sugars</li>
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

// Show typing indicator
function showTypingIndicator() {
    const chatMessages = document.getElementById('chatMessages');
    
    const typingDiv = document.createElement('div');
    typingDiv.className = 'typing-indicator';
    typingDiv.id = 'typingIndicator';
    
    const typingDots = document.createElement('div');
    typingDots.className = 'typing-dots';
    typingDots.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;
    
    typingDiv.appendChild(typingDots);
    chatMessages.appendChild(typingDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Hide typing indicator
function hideTypingIndicator() {
    const typingIndicator = document.getElementById('typingIndicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Show loading overlay (for system initialization)
function showLoading(message = 'Processing...') {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        const text = overlay.querySelector('p');
        if (text) {
            text.textContent = message;
        }
        overlay.style.display = 'flex';
    }
}

// Hide loading overlay
function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}
