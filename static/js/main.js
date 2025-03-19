document.addEventListener('DOMContentLoaded', function() {
    // Initialize socket connection for chat
    if (document.getElementById('chat-container')) {
        initializeChat();
    }
    
    // Add animation to achievement notifications
    const achievementAlert = document.getElementById('achievement-alert');
    if (achievementAlert) {
        setTimeout(() => {
            achievementAlert.classList.add('show');
            setTimeout(() => {
                achievementAlert.classList.remove('show');
            }, 5000);
        }, 1000);
    }
    
    // Add smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });
});

// Chat functionality
function initializeChat() {
    const socket = io();
    const messageForm = document.getElementById('message-form');
    const userInput = document.getElementById('user-input');
    const chatContainer = document.getElementById('chat-container');
    const chatId = chatContainer.getAttribute('data-chat-id');
    
    messageForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const message = userInput.value.trim();
        
        if (message) {
            // Add user message to UI
            addMessageToUI('user', message);
            
            // Clear input
            userInput.value = '';
            
            // Send message to server
            socket.emit('send_message', {
                chat_id: chatId,
                message: message
            });
        }
    });
    
    // Handle incoming message chunks
    socket.on('start_ai_response', function(data) {
        // Create a placeholder for the AI message
        const messageElement = document.createElement('div');
        messageElement.className = 'message ai-message';
        messageElement.id = `message-${data.message_id}`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageElement.appendChild(messageContent);
        
        chatContainer.appendChild(messageElement);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    });
    
    socket.on('ai_response_chunk', function(data) {
        const latestMessage = document.querySelector('.ai-message:last-child .message-content');
        latestMessage.textContent += data.text + ' ';
        chatContainer.scrollTop = chatContainer.scrollHeight;
    });
    
    socket.on('ai_response_complete', function() {
        // Add any finishing touches
        chatContainer.scrollTop = chatContainer.scrollHeight;
    });
    
    socket.on('achievement_earned', function(data) {
        showAchievementNotification(data.name, data.description, data.points);
    });
    
    socket.on('error', function(data) {
        console.error('Socket error:', data.message);
        showErrorMessage(data.message);
    });
}

function addMessageToUI(role, content) {
    const chatContainer = document.getElementById('chat-container');
    
    const messageElement = document.createElement('div');
    messageElement.className = `message ${role}-message`;
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.textContent = content;
    
    messageElement.appendChild(messageContent);
    chatContainer.appendChild(messageElement);
    
    // Scroll to bottom
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function showAchievementNotification(name, description, points) {
    const notification = document.createElement('div');
    notification.className = 'achievement-notification';
    notification.innerHTML = `
        <div class="achievement-icon">🏆</div>
        <div class="achievement-details">
            <h4>${name}</h4>
            <p>${description}</p>
            <p class="achievement-points">+${points} points</p>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Show notification
    setTimeout(() => {
        notification.classList.add('show');
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 5000);
    }, 100);
}

function showErrorMessage(message) {
    const notification = document.createElement('div');
    notification.className = 'error-notification';
    notification.innerHTML = `
        <div class="error-icon">❌</div>
        <div class="error-message">${message}</div>
    `;
    
    document.body.appendChild(notification);
    
    // Show notification
    setTimeout(() => {
        notification.classList.add('show');
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 5000);
    }, 100);
} 