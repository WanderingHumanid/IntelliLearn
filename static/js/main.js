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

// Add event listeners when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
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
    
    if (chatForm && chatInput && chatMessages) {
        chatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const message = chatInput.value.trim();
            if (!message) return;
            
            // Add user message to chat
            const userMessageEl = document.createElement('div');
            userMessageEl.className = 'message user';
            userMessageEl.textContent = message;
            chatMessages.appendChild(userMessageEl);
            
            // Clear input
            chatInput.value = '';
            
            // Scroll to bottom
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            // Prepare AI response container
            const aiMessageEl = document.createElement('div');
            aiMessageEl.className = 'message ai';
            chatMessages.appendChild(aiMessageEl);
            
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
                
                function processText(result) {
                    if (result.done) return;
                    
                    const text = decoder.decode(result.value, { stream: true });
                    buffer += text;
                    
                    // Process markdown in the buffer
                    aiMessageEl.innerHTML = formatMarkdown(buffer);
                    
                    // Scroll to bottom
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                    
                    // Continue reading
                    return reader.read().then(processText);
                }
                
                return reader.read().then(processText);
            })
            .catch(error => {
                console.error('Error:', error);
                aiMessageEl.textContent = 'Sorry, there was an error processing your request.';
            });
        });
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
                    
                    if (oIndex === correctIndex) {
                        this.classList.add('correct');
                        showToast('Correct!', 'success');
                    } else {
                        this.classList.add('incorrect');
                        allOptions[correctIndex].classList.add('correct');
                        showToast('Incorrect!', 'error');
                    }
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
}); 