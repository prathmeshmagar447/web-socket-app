// Web Socket Chat Client JavaScript
class ChatClient {
    constructor() {
        this.socket = null;
        this.currentRoom = null;
        this.currentUser = null;
        this.typingTimeout = null;
        
        this.initializeElements();
        this.initializeSocket();
        this.bindEvents();
        this.loadRooms();
        this.loadUserData();
        this.requestNotificationPermission();
    }
    
    loadUserData() {
        const userData = document.getElementById('userData');
        if (userData) {
            this.currentUser = {
                id: userData.dataset.userId,
                username: userData.dataset.username
            };
        }
    }
    
    initializeElements() {
        // UI Elements
        this.messagesContainer = document.getElementById('messagesContainer');
        this.messageInput = document.getElementById('messageText');
        this.sendBtn = document.getElementById('sendBtn');
        this.roomsList = document.getElementById('roomsList');
        this.onlineUsers = document.getElementById('onlineUsers');
        this.chatTitle = document.getElementById('chatTitle');
        this.chatDescription = document.getElementById('chatDescription');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.typingText = document.getElementById('typingText');
        this.messageInputContainer = document.getElementById('messageInput');
        
        // Buttons
        this.logoutBtn = document.getElementById('logoutBtn');
        this.createRoomBtn = document.getElementById('createRoomBtn');
        this.roomInfoBtn = document.getElementById('roomInfoBtn');
        this.emojiBtn = document.getElementById('emojiBtn');
        this.fileBtn = document.getElementById('fileBtn');
        
        // Modals
        this.createRoomModal = document.getElementById('createRoomModal');
        this.joinRoomModal = document.getElementById('joinRoomModal');
        
        // Forms
        this.createRoomForm = document.getElementById('createRoomForm');
        this.joinRoomForm = document.getElementById('joinRoomForm');
    }
    
    initializeSocket() {
        this.socket = io();
        
        // Connection events
        this.socket.on('connect', () => {
            console.log('Connected to server');
            this.showNotification('Connected to server', 'success');
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.showNotification('Disconnected from server', 'error');
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('Connection error:', error);
            this.showNotification('Failed to connect to server', 'error');
        });
        
        // Message events
        this.socket.on('new_message', (data) => {
            this.handleNewMessage(data);
        });
        
        this.socket.on('new_private_message', (data) => {
            this.handleNewPrivateMessage(data);
        });
        
        this.socket.on('message_error', (data) => {
            this.showNotification(data.message, 'error');
        });
        
        // Room events
        this.socket.on('room_joined', (data) => {
            if (data.success) {
                this.showNotification('Successfully joined room', 'success');
                this.closeModal();
            } else {
                this.showNotification(data.message, 'error');
            }
        });
        
        this.socket.on('user_joined', (data) => {
            this.handleUserJoined(data);
        });
        
        this.socket.on('user_left', (data) => {
            this.handleUserLeft(data);
        });
        
        // Typing events
        this.socket.on('user_typing', (data) => {
            this.handleTypingIndicator(data);
        });
    }
    
    bindEvents() {
        // Message sending
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            } else {
                this.handleTyping();
            }
        });
        
        // Typing indicator
        this.messageInput.addEventListener('input', () => this.handleTyping());
        this.messageInput.addEventListener('blur', () => this.stopTyping());
        
        // Logout
        this.logoutBtn.addEventListener('click', () => this.logout());
        
        // Room creation
        this.createRoomBtn.addEventListener('click', () => this.showCreateRoomModal());
        this.createRoomForm.addEventListener('submit', (e) => this.handleCreateRoom(e));
        
        // Join room form
        this.joinRoomForm.addEventListener('submit', (e) => this.handleJoinRoom(e));
        
        // Modal events
        this.bindModalEvents();
        
        // File upload (placeholder)
        this.fileBtn.addEventListener('click', () => this.handleFileUpload());
        
        // Emoji (placeholder)
        this.emojiBtn.addEventListener('click', () => this.handleEmojiPicker());
    }
    
    bindModalEvents() {
        // Close modal events
        document.querySelectorAll('.modal-close, .modal-cancel').forEach(btn => {
            btn.addEventListener('click', () => this.closeModal());
        });
        
        // Click outside modal to close
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModal();
                }
            });
        });
    }
    
    async loadRooms() {
        try {
            const response = await fetch('/api/rooms');
            const data = await response.json();
            
            if (data.success) {
                this.displayRooms(data.rooms);
            } else {
                this.showNotification('Failed to load rooms', 'error');
            }
        } catch (error) {
            console.error('Error loading rooms:', error);
            this.showNotification('Failed to load rooms', 'error');
        }
    }
    
    displayRooms(rooms) {
        this.roomsList.innerHTML = '';
        
        if (rooms.length === 0) {
            this.roomsList.innerHTML = '<div class=\"empty-state\">No rooms available. Create one!</div>';
            return;
        }
        
        rooms.forEach(room => {
            const roomElement = this.createRoomElement(room);
            this.roomsList.appendChild(roomElement);
        });
    }
    
    createRoomElement(room) {
        const roomDiv = document.createElement('div');
        roomDiv.className = 'room-item';
        roomDiv.dataset.roomId = room.id;
        
        const isPrivate = room.is_private;
        const hasPassword = room.password_hash !== null;
        
        let icon = '<i class=\"fas fa-users\"></i>';
        if (isPrivate) {
            icon = '<i class=\"fas fa-lock\"></i>';
        } else if (hasPassword) {
            icon = '<i class=\"fas fa-key\"></i>';
        }
        
        roomDiv.innerHTML = `
            <div class=\"room-icon\">${icon}</div>
            <div class=\"room-info\">
                <div class=\"room-name\">${this.escapeHtml(room.name)}</div>
                ${room.description ? `<div class=\"room-description\">${this.escapeHtml(room.description)}</div>` : ''}
            </div>
        `;
        
        roomDiv.addEventListener('click', () => this.joinRoom(room));
        
        return roomDiv;
    }
    
    async joinRoom(room) {
        // Check if room requires password and we don't have it
        if (room.password_hash && !this.currentRoom) {
            this.showJoinRoomModal(room);
            return;
        }
        
        // Leave current room if any
        if (this.currentRoom) {
            this.socket.emit('leave_room', { room_id: this.currentRoom.id });
        }
        
        // Join new room
        this.socket.emit('join_room', { 
            room_id: room.id,
            password: room.password || null
        });
        
        // Update UI
        this.currentRoom = room;
        this.updateChatHeader(room);
        this.clearMessages();
        this.showMessageInput();
        this.updateActiveRoom(room.id);
        
        // Load room messages
        this.loadRoomMessages(room.id);
    }
    
    updateChatHeader(room) {
        this.chatTitle.textContent = room.name;
        this.chatDescription.textContent = room.description || '';
        this.roomInfoBtn.style.display = 'block';
    }
    
    updateActiveRoom(roomId) {
        document.querySelectorAll('.room-item').forEach(item => {
            item.classList.remove('active');
        });
        
        const activeRoom = document.querySelector(`[data-room-id=\"${roomId}\"]`);
        if (activeRoom) {
            activeRoom.classList.add('active');
        }
    }
    
    clearMessages() {
        this.messagesContainer.innerHTML = '';
    }
    
    showMessageInput() {
        this.messageInputContainer.style.display = 'block';
    }
    
    async loadRoomMessages(roomId) {
        try {
            const response = await fetch(`/api/rooms/${roomId}/messages`);
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.displayMessages(data.messages);
                }
            }
        } catch (error) {
            console.error('Error loading messages:', error);
        }
    }
    
    displayMessages(messages) {
        messages.forEach(message => {
            this.appendMessage(message);
        });
        this.scrollToBottom();
    }
    
    sendMessage() {
        const content = this.messageInput.value.trim();
        if (!content || !this.currentRoom) return;
        
        this.socket.emit('send_message', {
            room_id: this.currentRoom.id,
            content: content,
            reply_to_id: null // TODO: Handle replies
        });
        
        this.messageInput.value = '';
        this.stopTyping();
    }
    
    handleNewMessage(data) {
        if (data.room_id === this.currentRoom?.id) {
            this.appendMessage(data);
            this.scrollToBottom();
        }
        
        // Show notification if not in current room
        if (data.room_id !== this.currentRoom?.id) {
            this.showNotification(`New message in ${data.room_name || 'a room'}`, 'info');
        }
    }
    
    handleNewPrivateMessage(data) {
        console.log('New private message:', data);
        // TODO: Handle private messages
        this.showNotification(`Private message from ${data.sender_username}`, 'info');
    }
    
    appendMessage(message) {
        const messageElement = this.createMessageElement(message);
        this.messagesContainer.appendChild(messageElement);
    }
    
    createMessageElement(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message';
        
        // Check if message is from current user
        if (message.sender_id === this.getCurrentUserId()) {
            messageDiv.classList.add('own');
        }
        
        const avatar = this.createAvatar(message.sender_username || message.sender_id);
        const timestamp = this.formatTimestamp(message.timestamp);
        
        messageDiv.innerHTML = `
            <div class=\"message-avatar\">${avatar}</div>
            <div class=\"message-content\">
                <div class=\"message-header\">
                    <span class=\"message-author\">${this.escapeHtml(message.sender_username || 'Unknown')}</span>
                    <span class=\"message-time\">${timestamp}</span>
                </div>
                <div class=\"message-text\">${this.escapeHtml(message.content)}</div>
            </div>
        `;
        
        return messageDiv;
    }
    
    createAvatar(username) {
        if (!username) return '?';
        return username.charAt(0).toUpperCase();
    }
    
    formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diffInHours = (now - date) / (1000 * 60 * 60);
        
        if (diffInHours < 24) {
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } else {
            return date.toLocaleDateString();
        }
    }
    
    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
    
    handleTyping() {
        if (!this.currentRoom) return;
        
        // Send typing start
        this.socket.emit('typing_start', { room_id: this.currentRoom.id });
        
        // Clear existing timeout
        if (this.typingTimeout) {
            clearTimeout(this.typingTimeout);
        }
        
        // Set timeout to stop typing
        this.typingTimeout = setTimeout(() => {
            this.stopTyping();
        }, 3000);
    }
    
    stopTyping() {
        if (this.typingTimeout) {
            clearTimeout(this.typingTimeout);
            this.typingTimeout = null;
        }
        
        if (this.currentRoom) {
            this.socket.emit('typing_stop', { room_id: this.currentRoom.id });
        }
    }
    
    handleTypingIndicator(data) {
        if (data.room_id !== this.currentRoom?.id) return;
        
        if (data.typing) {
            this.typingText.textContent = `${data.username} is typing...`;
            this.typingIndicator.style.display = 'block';
        } else {
            this.typingIndicator.style.display = 'none';
        }
    }
    
    handleUserJoined(data) {
        if (data.room_id === this.currentRoom?.id) {
            this.showSystemMessage(`${data.username} joined the room`);
        }
    }
    
    handleUserLeft(data) {
        if (data.room_id === this.currentRoom?.id) {
            this.showSystemMessage(`${data.username} left the room`);
        }
    }
    
    showSystemMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message system';
        messageDiv.innerHTML = `
            <div class=\"message-content\">
                <div class=\"message-text\">${this.escapeHtml(message)}</div>
            </div>
        `;
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    showCreateRoomModal() {
        this.createRoomModal.style.display = 'flex';
        document.getElementById('roomName').focus();
    }
    
    showJoinRoomModal(room) {
        this.joinRoomModal.style.display = 'flex';
        this.joinRoomModal.dataset.roomId = room.id;
        document.getElementById('joinRoomPassword').focus();
    }
    
    closeModal() {
        this.createRoomModal.style.display = 'none';
        this.joinRoomModal.style.display = 'none';
        
        // Reset forms
        this.createRoomForm.reset();
        this.joinRoomForm.reset();
    }
    
    async handleCreateRoom(e) {
        e.preventDefault();
        
        const formData = new FormData(this.createRoomForm);
        const roomData = {
            name: document.getElementById('roomName').value,
            description: document.getElementById('roomDescription').value,
            password: document.getElementById('roomPassword').value || null,
            is_private: document.getElementById('isPrivate').checked
        };
        
        try {
            const response = await fetch('/api/rooms', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(roomData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Room created successfully!', 'success');
                this.closeModal();
                this.loadRooms(); // Refresh room list
                
                // Auto-join the new room
                const newRoom = {
                    id: data.room_id,
                    name: data.room_name,
                    description: roomData.description,
                    password: roomData.password
                };
                setTimeout(() => this.joinRoom(newRoom), 500);
            } else {
                this.showNotification(data.message, 'error');
            }
        } catch (error) {
            console.error('Error creating room:', error);
            this.showNotification('Failed to create room', 'error');
        }
    }
    
    handleJoinRoom(e) {
        e.preventDefault();
        
        const roomId = this.joinRoomModal.dataset.roomId;
        const password = document.getElementById('joinRoomPassword').value;
        
        // Find the room data
        const roomElement = document.querySelector(`[data-room-id=\"${roomId}\"]`);
        if (!roomElement) return;
        
        // Create room object with password
        const room = {
            id: parseInt(roomId),
            name: roomElement.querySelector('.room-name').textContent,
            description: roomElement.querySelector('.room-description')?.textContent || '',
            password: password
        };
        
        this.joinRoom(room);
    }
    
    handleFileUpload() {
        // TODO: Implement file upload
        this.showNotification('File upload feature coming soon!', 'info');
    }
    
    handleEmojiPicker() {
        // TODO: Implement emoji picker
        this.showNotification('Emoji picker coming soon!', 'info');
    }
    
    async logout() {
        try {
            const response = await fetch('/api/auth/logout', {
                method: 'POST'
            });
            
            if (response.ok) {
                window.location.href = '/login';
            } else {
                this.showNotification('Failed to logout', 'error');
            }
        } catch (error) {
            console.error('Logout error:', error);
            this.showNotification('Failed to logout', 'error');
        }
    }

    requestNotificationPermission() {
        if ('Notification' in window) {
            if (Notification.permission !== 'granted' && Notification.permission !== 'denied') {
                Notification.requestPermission().then(permission => {
                    if (permission === 'granted') {
                        this.showNotification('Notifications enabled!', 'success');
                    }
                });
            }
        }
    }
    
    showNotification(message, type = 'info', options = {}) {
        const { body = '', icon = '/static/images/logo.png', tag = 'default' } = options;

        if ('Notification' in window && Notification.permission === 'granted') {
            const notification = new Notification(message, { body, icon, tag });
            notification.onclick = () => {
                window.focus();
            };
        } else {
            // Fallback to the old notification system
            const notification = document.createElement('div');
            notification.className = `notification ${type}`;
            notification.innerHTML = `
                <span>${this.escapeHtml(message)}</span>
                <button class="notification-close">&times;</button>
            `;

            const container = this.getNotificationContainer();
            container.appendChild(notification);

            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 5000);

            notification.querySelector('.notification-close').addEventListener('click', () => {
                notification.remove();
            });
        }
    }
    
    getNotificationContainer() {
        let container = document.getElementById('notifications');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notifications';
            container.className = 'notifications-container';
            document.body.appendChild(container);
        }
        return container;
    }
    
    getCurrentUserId() {
        return this.currentUser ? parseInt(this.currentUser.id) : null;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// CSS for notifications (inject into page)
const notificationStyles = `
    .notifications-container {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 2000;
        pointer-events: none;
    }
    
    .notification {
        display: flex;
        align-items: center;
        justify-content: space-between;
        min-width: 300px;
        padding: 12px 16px;
        margin-bottom: 10px;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        pointer-events: auto;
        animation: slideInRight 0.3s ease-out;
    }
    
    .notification.success {
        background-color: #00b894;
    }
    
    .notification.error {
        background-color: #e74c3c;
    }
    
    .notification.info {
        background-color: #6c5ce7;
    }
    
    .notification-close {
        background: none;
        border: none;
        color: white;
        font-size: 18px;
        cursor: pointer;
        margin-left: 10px;
        padding: 0;
        opacity: 0.8;
    }
    
    .notification-close:hover {
        opacity: 1;
    }
    
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    .empty-state {
        text-align: center;
        color: var(--text-muted);
        padding: 2rem;
        font-style: italic;
    }
`;

// Inject notification styles
const styleSheet = document.createElement('style');
styleSheet.textContent = notificationStyles;
document.head.appendChild(styleSheet);

// Initialize chat when page loads
document.addEventListener('DOMContentLoaded', () => {
    const chatClient = new ChatClient();
});