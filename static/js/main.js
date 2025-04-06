// Utility functions for IntelliLearn platform

// Format timestamp to readable date
function formatTimestamp(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
}

// Format markdown text to HTML
function formatMarkdown(text) {
    return marked.parse(text);
}

// Toast notification
function showToast(message, type = 'info') {
    // Create toast element if it doesn't exist
    let toast = document.getElementById('toast');
    
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        document.body.appendChild(toast);
        
        // Add styles
        toast.style.position = 'fixed';
        toast.style.bottom = '20px';
        toast.style.right = '20px';
        toast.style.padding = '12px 20px';
        toast.style.borderRadius = '12px';
        toast.style.zIndex = '9999';
        toast.style.minWidth = '250px';
        toast.style.backdropFilter = 'blur(8px)';
        toast.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.2)';
        toast.style.transition = 'all 0.3s ease';
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
    }
    
    // Set color based on type
    if (type === 'success') {
        toast.style.backgroundColor = 'rgba(76, 175, 80, 0.8)';
    } else if (type === 'error') {
        toast.style.backgroundColor = 'rgba(244, 67, 54, 0.8)';
    } else if (type === 'warning') {
        toast.style.backgroundColor = 'rgba(255, 152, 0, 0.8)';
    } else {
        toast.style.backgroundColor = 'rgba(33, 150, 243, 0.8)';
    }
    
    // Set message and show
    toast.textContent = message;
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';
    
    // Hide after 3 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
    }, 3000);
}

// Show points earned notification
function showPointsEarned(points, reason = '') {
    // Create points toast if it doesn't exist
    let pointsToast = document.getElementById('points-toast');
    
    if (!pointsToast) {
        pointsToast = document.createElement('div');
        pointsToast.id = 'points-toast';
        document.body.appendChild(pointsToast);
        
        // Add styles
        pointsToast.style.position = 'fixed';
        pointsToast.style.top = '20px';
        pointsToast.style.right = '20px';
        pointsToast.style.padding = '12px 20px';
        pointsToast.style.borderRadius = '12px';
        pointsToast.style.zIndex = '9999';
        pointsToast.style.backgroundColor = 'rgba(124, 77, 255, 0.9)';
        pointsToast.style.color = 'white';
        pointsToast.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.3)';
        pointsToast.style.transition = 'all 0.3s ease';
        pointsToast.style.opacity = '0';
        pointsToast.style.transform = 'translateY(-20px)';
        pointsToast.style.fontWeight = 'bold';
        pointsToast.style.textAlign = 'center';
    }
    
    // Set message and show
    const reasonText = reason ? ` for ${reason}` : '';
    pointsToast.innerHTML = `<i class="fas fa-star"></i> +${points} points${reasonText}!`;
    pointsToast.style.opacity = '1';
    pointsToast.style.transform = 'translateY(0)';
    
    // Hide after 3 seconds
    setTimeout(() => {
        pointsToast.style.opacity = '0';
        pointsToast.style.transform = 'translateY(-20px)';
    }, 3000);
}

// Function to update user stats in the UI
function updateUserStats(points, level) {
    // Update points display if it exists
    const pointsElement = document.querySelector('.user-points');
    if (pointsElement) {
        pointsElement.textContent = `${points} pts`;
    }
    
    // Update level display if it exists
    const levelElement = document.querySelector('.user-level');
    if (levelElement) {
        levelElement.textContent = `Lvl ${level}`;
    }
}

// Add event listeners when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Highlight flash messages
    highlightFlashMessages();
    
    // User profile link in sidebar
    const userInfoLink = document.querySelector('.user-info-link');
    if (userInfoLink) {
        userInfoLink.addEventListener('click', function(e) {
            // Add visual feedback when clicked
            const userAvatar = this.querySelector('.user-avatar');
            if (userAvatar) {
                userAvatar.style.transform = 'scale(0.9)';
                setTimeout(() => {
                    userAvatar.style.transform = 'scale(1)';
                }, 150);
            }
        });
    }
    
    // Mobile responsive menu toggle
    const menuToggle = document.querySelector('.menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('active');
        });
    }
    
    // AI Chat page
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const newConversationBtn = document.getElementById('new-conversation');
    const uploadButton = document.getElementById('upload-button');
    const fileUploadInput = document.getElementById('file-upload');
    const filePreviewContainer = document.getElementById('file-preview-container');
    const filePreviewElement = document.getElementById('file-preview');
    const fileNameElement = document.getElementById('file-name');
    const cancelUploadButton = document.getElementById('cancel-upload');
    const loadingOverlay = document.getElementById('loading-overlay');
    const ocrMethodToggle = document.getElementById('ocr-method-toggle');
    const ocrMethodLabel = document.getElementById('ocr-method-label');
    const conversationItems = document.querySelectorAll('.conversation-item');
    
    // Set OCR method label based on toggle
    if (ocrMethodToggle && ocrMethodLabel) {
        ocrMethodToggle.addEventListener('change', function() {
            ocrMethodLabel.textContent = this.checked ? 'TR-OCR' : 'Tesseract';
        });
    }
    
    // Load conversation history
    if (conversationItems) {
        conversationItems.forEach(item => {
            item.addEventListener('click', function(e) {
                e.preventDefault();
                
                const conversationId = this.getAttribute('data-conversation-id');
                if (!conversationId) return;
                
                // Show loading indicator
                if (loadingOverlay) {
                    loadingOverlay.style.display = 'flex';
                }
                
                // Load conversation
                fetch(`/api/load-conversation/${conversationId}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            // Clear current messages
                            chatMessages.innerHTML = '';
                            
                            // Add messages to chat
                            data.messages.forEach(message => {
                                const messageEl = document.createElement('div');
                                messageEl.className = `message ${message.is_user ? 'user' : 'ai'}`;
                                
                                // Create avatar div
                                const avatarDiv = document.createElement('div');
                                avatarDiv.className = 'message-avatar';
                                avatarDiv.innerHTML = message.is_user ? 
                                    '<i class="fas fa-user"></i>' : 
                                    '<i class="fas fa-robot"></i>';
                                
                                // Create content div
                                const contentDiv = document.createElement('div');
                                contentDiv.className = 'message-content';
                                
                                let content = '';
                                
                                // Add file attachments if present
                                if (message.has_file) {
                                    let fileAttachmentHTML = '';
                                    if (message.message_type === 'image') {
                                        const filename = message.file_path.split('/').pop();
                                        fileAttachmentHTML = `
                                            <div class="file-attachment">
                                                <div class="image-preview">
                                                    <img src="/uploads/${filename}" alt="${message.file_name || 'Uploaded image'}">
                                                </div>
                                            </div>
                                        `;
                                    } else {
                                        fileAttachmentHTML = `
                                            <div class="file-attachment">
                                                <div class="file-info">
                                                    <span class="file-icon"><i class="fas fa-file-alt"></i></span>
                                                    <span class="file-name">${message.file_name || 'Uploaded file'}</span>
                                                </div>
                                            </div>
                                        `;
                                    }
                                    content += fileAttachmentHTML;
                                }
                                
                                content += `<p>${formatMarkdown(message.content)}</p>`;
                                contentDiv.innerHTML = content;
                                
                                // Append avatar and content to message element
                                messageEl.appendChild(avatarDiv);
                                messageEl.appendChild(contentDiv);
                                
                                // Append message to chat
                                chatMessages.appendChild(messageEl);
                            });
                            
                            // Scroll to bottom
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                        } else {
                            showToast('Error loading conversation', 'error');
                        }
                        
                        // Hide loading indicator
                        if (loadingOverlay) {
                            loadingOverlay.style.display = 'none';
                        }
                    })
                    .catch(error => {
                        console.error('Error loading conversation:', error);
                        
                        // Hide loading indicator
                        if (loadingOverlay) {
                            loadingOverlay.style.display = 'none';
                        }
                        
                        showToast('Error loading conversation', 'error');
                    });
            });
        });
    }
    
    if (chatForm && chatInput && chatMessages) {
        // Auto-scroll to bottom of chat on page load
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        chatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const message = chatInput.value.trim();
            if (!message) return;
            
            // Add user message to chat
            const userMessageEl = document.createElement('div');
            userMessageEl.className = 'message user';
            
            // Create avatar div
            const userAvatarDiv = document.createElement('div');
            userAvatarDiv.className = 'message-avatar';
            userAvatarDiv.innerHTML = '<i class="fas fa-user"></i>';
            
            // Create content div
            const userContentDiv = document.createElement('div');
            userContentDiv.className = 'message-content';
            userContentDiv.innerHTML = `<p>${escapeHtml(message)}</p>`;
            
            // Append avatar and content to message element
            userMessageEl.appendChild(userAvatarDiv);
            userMessageEl.appendChild(userContentDiv);
            
            chatMessages.appendChild(userMessageEl);
            
            // Clear input
            chatInput.value = '';
            
            // Scroll to bottom
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            // Create AI message container
            const aiMessageEl = document.createElement('div');
            aiMessageEl.className = 'message ai';
            
            // Create avatar div
            const aiAvatarDiv = document.createElement('div');
            aiAvatarDiv.className = 'message-avatar';
            aiAvatarDiv.innerHTML = '<i class="fas fa-robot"></i>';
            
            // Create content div
            const aiContentDiv = document.createElement('div');
            aiContentDiv.className = 'message-content';
            
            // Append avatar and content to message element
            aiMessageEl.appendChild(aiAvatarDiv);
            aiMessageEl.appendChild(aiContentDiv);
            
            chatMessages.appendChild(aiMessageEl);
            
            // Show loading animation
            const typingIndicator = document.createElement('div');
            typingIndicator.className = 'typing';
            for (let i = 0; i < 3; i++) {
                const dot = document.createElement('div');
                dot.className = 'typing-dot';
                typingIndicator.appendChild(dot);
            }
            aiContentDiv.appendChild(typingIndicator);
            
            // Stream response from server
            fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: message })
            })
            .then(response => {
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                
                // Remove typing indicator
                aiContentDiv.innerHTML = '';
                
                function processText(result) {
                    if (result.done) return;
                    
                    const text = decoder.decode(result.value, { stream: true });
                    buffer += text;
                    
                    // Process markdown in the buffer
                    aiContentDiv.innerHTML = `<p>${formatMarkdown(buffer)}</p>`;
                    
                    // Scroll to bottom
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                    
                    // Continue reading
                    return reader.read().then(processText);
                }
                
                return reader.read().then(processText);
            })
            .catch(error => {
                console.error('Error:', error);
                aiContentDiv.innerHTML = '<p>Sorry, there was an error processing your request.</p>';
            });
        });
    }
    
    // File upload functionality
    if (uploadButton && fileUploadInput) {
        // File upload button click
        uploadButton.addEventListener('click', function() {
            fileUploadInput.click();
        });
        
        // File selection
        fileUploadInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const file = this.files[0];
                
                // Show file preview
                filePreviewContainer.style.display = 'block';
                fileNameElement.textContent = file.name;
                
                // Check if it's an image file
                if (file.type.startsWith('image/')) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        filePreviewElement.innerHTML = `<img src="${e.target.result}" alt="${file.name}">`;
                    };
                    reader.readAsDataURL(file);
                } else {
                    // Show generic file icon
                    filePreviewElement.innerHTML = '<i class="fas fa-file-alt"></i>';
                }
            }
        });
        
        // Cancel upload button
        if (cancelUploadButton) {
            cancelUploadButton.addEventListener('click', function() {
                // Hide preview and reset file input
                filePreviewContainer.style.display = 'none';
                fileUploadInput.value = '';
            });
        }
        
        // Upload file to server
        if (filePreviewContainer) {
            filePreviewContainer.addEventListener('click', function(e) {
                // If the click is on the cancel button, don't proceed
                if (e.target.closest('#cancel-upload')) return;
                
                if (fileUploadInput.files && fileUploadInput.files[0]) {
                    // Get selected OCR method
                    const ocrMethod = ocrMethodToggle && ocrMethodToggle.checked ? 'tr' : 'tesseract';
                    
                    // Show loading overlay
                    if (loadingOverlay) {
                        loadingOverlay.style.display = 'flex';
                    }
                    
                    // Create form data for file upload
                    const formData = new FormData();
                    formData.append('file', fileUploadInput.files[0]);
                    formData.append('ocr_method', ocrMethod);
                    
                    // Upload file to server
                    fetch('/api/upload-file', {
                        method: 'POST',
                        body: formData
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            // If points were awarded, show a notification and update UI
                            if (data.points) {
                                showPointsEarned(3, 'uploading a file');
                                updateUserStats(data.points, data.level);
                            }
                            
                            // Reset UI
                            fileUploadInput.value = '';
                            filePreviewContainer.style.display = 'none';
                            loadingOverlay.style.display = 'none';
                            
                            // Add user message with file to chat
                            const messageData = data.message;
                            const messageEl = document.createElement('div');
                            messageEl.className = 'message user';
                            
                            // Create avatar div
                            const avatarDiv = document.createElement('div');
                            avatarDiv.className = 'message-avatar';
                            avatarDiv.innerHTML = '<i class="fas fa-user"></i>';
                            
                            // Create content div
                            const contentDiv = document.createElement('div');
                            contentDiv.className = 'message-content';
                            
                            let content = '';
                            
                            // Add file attachment HTML
                            if (messageData.has_file) {
                                if (messageData.message_type === 'image') {
                                    const filename = messageData.file_path.split('/').pop();
                                    content += `
                                        <div class="file-attachment">
                                            <div class="image-preview">
                                                <img src="/uploads/${filename}" alt="${messageData.file_name || 'Uploaded image'}">
                                            </div>
                                        </div>
                                    `;
                                } else {
                                    content += `
                                        <div class="file-attachment">
                                            <div class="file-info">
                                                <span class="file-icon"><i class="fas fa-file-alt"></i></span>
                                                <span class="file-name">${messageData.file_name || 'Uploaded file'}</span>
                                            </div>
                                        </div>
                                    `;
                                }
                            }
                            
                            content += `<p>${messageData.content}</p>`;
                            contentDiv.innerHTML = content;
                            
                            // Append avatar and content to message element
                            messageEl.appendChild(avatarDiv);
                            messageEl.appendChild(contentDiv);
                            
                            chatMessages.appendChild(messageEl);
                            
                            // Scroll to bottom
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                            
                            // Create typing indicator
                            showTypingIndicator();
                            
                            // Get AI response
                            getAIResponse();
                        } else {
                            showToast(data.error || 'Error uploading file', 'error');
                            loadingOverlay.style.display = 'none';
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        loadingOverlay.style.display = 'none';
                        showToast('Error uploading file', 'error');
                    });
                }
            });
        }
    }
    
    // New conversation button
    if (newConversationBtn) {
        newConversationBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            fetch('/api/new-conversation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Clear chat messages
                    chatMessages.innerHTML = '';
                    
                    // Create welcome message with proper structure
                    const messageEl = document.createElement('div');
                    messageEl.className = 'message ai';
                    
                    // Create avatar div
                    const avatarDiv = document.createElement('div');
                    avatarDiv.className = 'message-avatar';
                    avatarDiv.innerHTML = '<i class="fas fa-robot"></i>';
                    
                    // Create content div
                    const contentDiv = document.createElement('div');
                    contentDiv.className = 'message-content';
                    contentDiv.innerHTML = '<p>Hello, I\'m your personal AI learning assistant. How can I help you with your studies today?</p>';
                    
                    // Append avatar and content to message element
                    messageEl.appendChild(avatarDiv);
                    messageEl.appendChild(contentDiv);
                    chatMessages.appendChild(messageEl);
                    
                    // Scroll to bottom
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }
            })
            .catch(error => {
                console.error('Error starting new conversation:', error);
                showToast('Error starting new conversation', 'error');
            });
        });
    }
    
    // Helper function to escape HTML
    function escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
    
    // Format markdown to HTML
    function formatMarkdown(text) {
        // Very basic markdown conversion
        // Bold
        text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Italic
        text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
        // Code block
        text = text.replace(/```(.*?)```/gs, '<pre><code>$1</code></pre>');
        // Inline code
        text = text.replace(/`(.*?)`/g, '<code>$1</code>');
        // Links
        text = text.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank">$1</a>');
        // Headers
        text = text.replace(/^# (.*?)$/gm, '<h1>$1</h1>');
        text = text.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
        text = text.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
        // Unordered lists
        text = text.replace(/^\* (.*?)$/gm, '<li>$1</li>');
        text = text.replace(/(<li>.*?<\/li>)/gs, '<ul>$1</ul>');
        // Line breaks
        text = text.replace(/\n/g, '<br>');
        
        return text;
    }
    
    // Roadmap creator
    const roadmapForm = document.getElementById('roadmap-form');
    const roadmapTopic = document.getElementById('roadmap-topic');
    const roadmapResult = document.getElementById('roadmap-result');
    const loadingIndicator = document.getElementById('loading-indicator');
    
    if (roadmapForm && roadmapTopic && roadmapResult) {
        roadmapForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const topic = roadmapTopic.value.trim();
            if (!topic) {
                showToast('Please enter a topic for your roadmap', 'error');
                return;
            }
            
            // Show loading indicator
            if (loadingIndicator) {
                loadingIndicator.style.display = 'flex';
            }
            
            // Clear previous results
            roadmapResult.innerHTML = '';
            
            // Show a message to user
            roadmapResult.innerHTML = '<div class="loading-message">Creating your roadmap. This may take up to a minute...</div>';
            
            // Generate roadmap from server
            fetch('/api/create-roadmap', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ topic: topic })
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || 'Failed to create roadmap');
                    });
                }
                return response.json();
            })
            .then(data => {
                // Hide loading indicator
                if (loadingIndicator) {
                    loadingIndicator.style.display = 'none';
                }
                
                if (data.error) {
                    showToast(data.error, 'error');
                    roadmapResult.innerHTML = '<div class="error-message">Error: ' + data.error + '</div>';
                    return;
                }
                
                // Show success message
                showToast('Roadmap created successfully!', 'success');
                
                // Redirect to roadmap view
                window.location.href = `/roadmap/${data.roadmap.id}`;
            })
            .catch(error => {
                console.error('Error:', error);
                if (loadingIndicator) {
                    loadingIndicator.style.display = 'none';
                }
                showToast(error.message || 'Error creating roadmap', 'error');
                roadmapResult.innerHTML = '<div class="error-message">Error: ' + (error.message || 'Failed to create roadmap') + '</div>';
            });
        });
    }
    
    // Roadmap view page - Mark topic as complete
    const completeButtons = document.querySelectorAll('.complete-topic');
    
    if (completeButtons.length > 0) {
        completeButtons.forEach(button => {
            button.addEventListener('click', function() {
                const roadmapId = this.getAttribute('data-roadmap');
                const topicName = this.getAttribute('data-topic');
                
                fetch('/api/complete-topic', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ 
                        roadmap_id: roadmapId,
                        topic_name: topicName
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        showToast(data.error, 'error');
                        return;
                    }
                    
                    // Update UI
                    const topicEl = button.closest('.topic-card');
                    if (topicEl) {
                        topicEl.classList.add('completed');
                        button.innerHTML = '<i class="fas fa-check"></i> Completed';
                        button.disabled = true;
                    }
                    
                    // Update stats
                    const pointsEl = document.querySelector('.stat-points');
                    const levelEl = document.querySelector('.stat-level');
                    const streakEl = document.querySelector('.stat-streak');
                    
                    if (pointsEl) pointsEl.textContent = data.points;
                    if (levelEl) levelEl.textContent = data.level;
                    if (streakEl) streakEl.textContent = data.streak;
                    
                    showToast('Topic completed! +10 points', 'success');
                    
                    // If user leveled up
                    if (data.level > parseInt(levelEl.getAttribute('data-prev-level'))) {
                        showToast(`Congratulations! You reached level ${data.level}!`, 'success');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showToast('Error updating progress', 'error');
                });
            });
        });
    }
    
    // Forum post form
    const forumPostForm = document.getElementById('forum-post-form');
    const forumPosts = document.getElementById('forum-posts');
    
    if (forumPostForm && forumPosts) {
        forumPostForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const titleInput = document.getElementById('post-title');
            const contentInput = document.getElementById('post-content');
            
            const title = titleInput.value.trim();
            const content = contentInput.value.trim();
            
            if (!title || !content) {
                showToast('Please fill all fields', 'warning');
                return;
            }
            
            fetch('/api/forum-post', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    title: title,
                    content: content
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showToast(data.error, 'error');
                    return;
                }
                
                // Clear form
                titleInput.value = '';
                contentInput.value = '';
                
                // Refresh posts (or you could just append the new post to the DOM)
                window.location.reload();
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Error creating post', 'error');
            });
        });
    }
    
    // Comment form
    const commentForms = document.querySelectorAll('.comment-form');
    
    if (commentForms.length > 0) {
        commentForms.forEach(form => {
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const postId = this.getAttribute('data-post-id');
                const contentInput = this.querySelector('.comment-input');
                const content = contentInput.value.trim();
                
                if (!content) return;
                
                fetch('/api/forum-comment', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ 
                        post_id: postId,
                        content: content
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        showToast(data.error, 'error');
                        return;
                    }
                    
                    // Clear input
                    contentInput.value = '';
                    
                    // Refresh page to show new comment
                    window.location.reload();
                })
                .catch(error => {
                    console.error('Error:', error);
                    showToast('Error posting comment', 'error');
                });
            });
        });
    }
    
    // Quiz generator
    const quizForm = document.getElementById('quiz-form');
    const quizTopic = document.getElementById('quiz-topic');
    const quizContainer = document.getElementById('quiz-container');
    
    if (quizForm && quizTopic && quizContainer) {
        quizForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const topic = quizTopic.value.trim();
            if (!topic) return;
            
            // Show loading
            quizContainer.innerHTML = '<div class="loading">Generating quiz...</div>';
            
            fetch('/api/generate-quiz', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ topic: topic })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    quizContainer.innerHTML = `<p class="error">${data.error}</p>`;
                    return;
                }
                
                // Render quiz
                renderQuiz(data.quiz, quizContainer);
            })
            .catch(error => {
                console.error('Error:', error);
                quizContainer.innerHTML = '<p class="error">Error generating quiz</p>';
            });
        });
    }
    
    // Function to render quiz
    function renderQuiz(quiz, container) {
        container.innerHTML = '';
        
        if (!quiz || !quiz.questions || quiz.questions.length === 0) {
            container.innerHTML = '<p>No questions available</p>';
            return;
        }
        
        const quizEl = document.createElement('div');
        quizEl.className = 'quiz';
        
        quiz.questions.forEach((q, qIndex) => {
            const questionCard = document.createElement('div');
            questionCard.className = 'question-card';
            
            // Question number
            const questionNumber = document.createElement('div');
            questionNumber.className = 'question-number';
            questionNumber.textContent = `Question ${qIndex + 1}`;
            
            // Question text
            const questionText = document.createElement('div');
            questionText.className = 'question-text';
            questionText.textContent = q.question;
            
            // Options
            const optionsList = document.createElement('ul');
            optionsList.className = 'options-list';
            
            q.options.forEach((option, oIndex) => {
                const optionItem = document.createElement('li');
                optionItem.className = 'option-item';
                optionItem.textContent = option;
                optionItem.setAttribute('data-index', oIndex);
                optionItem.setAttribute('data-question', qIndex);
                
                optionItem.addEventListener('click', function() {
                    // Get all options for this question
                    const allOptions = optionsList.querySelectorAll('.option-item');
                    
                    // Remove selected class from all options
                    allOptions.forEach(opt => {
                        opt.classList.remove('selected');
                        opt.classList.remove('correct');
                        opt.classList.remove('incorrect');
                    });
                    
                    // Add selected class to clicked option
                    this.classList.add('selected');
                    
                    // Check if answer is correct
                    const correctIndex = q.correct_index;
                    const isCorrect = oIndex === correctIndex;
                    
                    if (isCorrect) {
                        this.classList.add('correct');
                    } else {
                        this.classList.add('incorrect');
                        allOptions[correctIndex].classList.add('correct');
                    }
                    
                    // Submit answer to get points
                    fetch('/api/submit-quiz-answer', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ correct: isCorrect })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            // Update points display if it exists
                            const pointsElement = document.querySelector('.user-points');
                            if (pointsElement) {
                                pointsElement.textContent = `${data.points} pts`;
                            }
                            
                            // Update level display if it exists
                            const levelElement = document.querySelector('.user-level');
                            if (levelElement) {
                                levelElement.textContent = `Lvl ${data.level}`;
                            }
                            
                            // Show points earned notification
                            const pointsEarned = isCorrect ? 5 : 1;
                            const reason = isCorrect ? 'correct answer' : 'trying';
                            showPointsEarned(pointsEarned, reason);
                            
                            // Show success message
                            showToast(data.message, isCorrect ? 'success' : 'warning');
                        }
                    })
                    .catch(error => {
                        console.error('Error submitting answer:', error);
                    });
                });
                
                optionsList.appendChild(optionItem);
            });
            
            // Append elements to question card
            questionCard.appendChild(questionNumber);
            questionCard.appendChild(questionText);
            questionCard.appendChild(optionsList);
            
            // Append question card to quiz
            quizEl.appendChild(questionCard);
        });
        
        container.appendChild(quizEl);
    }
    
    // Highlight flash messages for better visibility
    function highlightFlashMessages() {
        const flashMessages = document.querySelectorAll('.flash-message');
        if (flashMessages.length > 0) {
            flashMessages.forEach(msg => {
                // Add animation effect
                msg.style.animation = 'flash-highlight 2s ease';
                
                // Add event listener to close the message
                const closeBtn = document.createElement('span');
                closeBtn.innerHTML = '&times;';
                closeBtn.className = 'flash-close';
                closeBtn.addEventListener('click', () => {
                    msg.style.opacity = '0';
                    setTimeout(() => {
                        msg.remove();
                    }, 300);
                });
                
                msg.appendChild(closeBtn);
                
                // Auto-hide after 5 seconds
                setTimeout(() => {
                    msg.style.opacity = '0';
                    setTimeout(() => {
                        msg.remove();
                    }, 300);
                }, 5000);
            });
        }
    }

    // Function to show typing indicator
    function showTypingIndicator() {
        // Create AI message with typing indicator
        const messageEl = document.createElement('div');
        messageEl.className = 'message ai';
        messageEl.id = 'ai-typing-message';
        
        // Create avatar div
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.innerHTML = '<i class="fas fa-robot"></i>';
        
        // Create content div
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Add typing indicator
        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'typing';
        typingIndicator.innerHTML = `
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        `;
        
        contentDiv.appendChild(typingIndicator);
        
        // Append avatar and content to message element
        messageEl.appendChild(avatarDiv);
        messageEl.appendChild(contentDiv);
        
        chatMessages.appendChild(messageEl);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return { messageEl, contentDiv };
    }

    // Function to get AI response
    function getAIResponse() {
        const messageInput = document.getElementById('message-input');
        const message = messageInput.value.trim();
        const messageText = message || 'Please analyze the uploaded file.';
        const existingTypingMessage = document.getElementById('ai-typing-message');
        let aiMessageEl, aiContentDiv;
        
        if (existingTypingMessage) {
            aiMessageEl = existingTypingMessage;
            aiContentDiv = existingTypingMessage.querySelector('.message-content');
        }
        
        // Use fetch to get AI response
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                message: messageText,
                conversation_id: conversationId || null
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';
            
            // Remove typing indicator
            const typingIndicator = aiContentDiv.querySelector('.typing');
            if (typingIndicator) {
                typingIndicator.remove();
            }
            
            aiContentDiv.innerHTML = '';
            
            function processText(result) {
                if (result.done) return;
                
                const text = decoder.decode(result.value, { stream: true });
                buffer += text;
                
                // Process markdown in the buffer
                aiContentDiv.innerHTML = `<p>${formatMarkdown(buffer)}</p>`;
                
                // Scroll to bottom
                chatMessages.scrollTop = chatMessages.scrollHeight;
                
                // Continue reading
                return reader.read().then(processText);
            }
            
            return reader.read().then(processText);
        })
        .catch(error => {
            console.error('Error:', error);
            aiContentDiv.innerHTML = '<p>Sorry, there was an error processing your request.</p>';
        });
    }
}); 