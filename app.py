from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit
import requests
import json
import os
import sqlite3
import uuid
from datetime import datetime
import pytesseract
from PIL import Image
import io
import base64
import re
import time

app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Database setup
def setup_database():
    conn = sqlite3.connect('db/intelli_learn.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        points INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        streak INTEGER DEFAULT 0,
        last_login TEXT,
        created_at TEXT
    )
    ''')
    
    # AI Chats table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chats (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        title TEXT,
        created_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Chat Messages table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chat_messages (
        id TEXT PRIMARY KEY,
        chat_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TEXT,
        FOREIGN KEY (chat_id) REFERENCES chats (id)
    )
    ''')
    
    # Forum Categories table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS forum_categories (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT
    )
    ''')
    
    # Forum Topics table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS forum_topics (
        id TEXT PRIMARY KEY,
        category_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT,
        updated_at TEXT,
        views INTEGER DEFAULT 0,
        FOREIGN KEY (category_id) REFERENCES forum_categories (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Forum Replies table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS forum_replies (
        id TEXT PRIMARY KEY,
        topic_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT,
        updated_at TEXT,
        FOREIGN KEY (topic_id) REFERENCES forum_topics (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Achievements table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS achievements (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        points INTEGER DEFAULT 0,
        icon TEXT
    )
    ''')
    
    # User Achievements table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_achievements (
        user_id TEXT NOT NULL,
        achievement_id TEXT NOT NULL,
        earned_at TEXT,
        PRIMARY KEY (user_id, achievement_id),
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (achievement_id) REFERENCES achievements (id)
    )
    ''')
    
    # Insert default forum categories
    cursor.execute("INSERT OR IGNORE INTO forum_categories (id, name, description) VALUES (?, ?, ?)",
                  ('1', 'General Discussion', 'General topics related to learning and education'))
    cursor.execute("INSERT OR IGNORE INTO forum_categories (id, name, description) VALUES (?, ?, ?)",
                  ('2', 'AI Learning', 'Discussions about AI-assisted learning techniques'))
    cursor.execute("INSERT OR IGNORE INTO forum_categories (id, name, description) VALUES (?, ?, ?)",
                  ('3', 'Study Groups', 'Find and join study groups'))
    
    # Insert default achievements
    cursor.execute("INSERT OR IGNORE INTO achievements (id, name, description, points, icon) VALUES (?, ?, ?, ?, ?)",
                  ('1', 'First Chat', 'Started your first AI chat session', 10, 'chat-icon'))
    cursor.execute("INSERT OR IGNORE INTO achievements (id, name, description, points, icon) VALUES (?, ?, ?, ?, ?)",
                  ('2', 'Forum Novice', 'Made your first forum post', 20, 'forum-icon'))
    cursor.execute("INSERT OR IGNORE INTO achievements (id, name, description, points, icon) VALUES (?, ?, ?, ?, ?)",
                  ('3', '7-Day Streak', 'Logged in for 7 consecutive days', 50, 'streak-icon'))
    
    conn.commit()
    conn.close()

# Call database setup
setup_database()

# Helper function to get database connection
def get_db_connection():
    conn = sqlite3.connect('db/intelli_learn.db')
    conn.row_factory = sqlite3.Row
    return conn

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and user['password'] == password:  # In production, use proper password hashing
            session['user_id'] = user['id']
            session['username'] = user['username']
            
            # Update streak and last login
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn = get_db_connection()
            conn.execute('UPDATE users SET last_login = ?, streak = streak + 1 WHERE id = ?', 
                        (now, user['id']))
            conn.commit()
            conn.close()
            
            return redirect(url_for('dashboard'))
        
        return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        
        conn = get_db_connection()
        existing_user = conn.execute('SELECT * FROM users WHERE username = ? OR email = ?', 
                                   (username, email)).fetchone()
        
        if existing_user:
            conn.close()
            return render_template('register.html', error='Username or email already exists')
        
        user_id = str(uuid.uuid4())
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn.execute('INSERT INTO users (id, username, password, email, created_at, last_login) VALUES (?, ?, ?, ?, ?, ?)',
                    (user_id, username, password, email, now, now))
        conn.commit()
        conn.close()
        
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    chats = conn.execute('SELECT * FROM chats WHERE user_id = ? ORDER BY created_at DESC', 
                       (session['user_id'],)).fetchall()
    achievements = conn.execute('''
        SELECT a.* FROM achievements a
        JOIN user_achievements ua ON a.id = ua.achievement_id
        WHERE ua.user_id = ?
    ''', (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('dashboard.html', user=user, chats=chats, achievements=achievements)

@app.route('/ai-chat')
def ai_chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    chat_id = request.args.get('id')
    chat = None
    messages = []
    
    conn = get_db_connection()
    # Get all user chats for the sidebar
    chats = conn.execute('SELECT * FROM chats WHERE user_id = ? ORDER BY created_at DESC', 
                       (session['user_id'],)).fetchall()
    
    if chat_id:
        chat = conn.execute('SELECT * FROM chats WHERE id = ? AND user_id = ?', 
                          (chat_id, session['user_id'])).fetchone()
        
        if chat:
            messages = conn.execute('SELECT * FROM chat_messages WHERE chat_id = ? ORDER BY timestamp',
                                  (chat_id,)).fetchall()
    conn.close()
    
    return render_template('ai_chat.html', chat=chat, messages=messages, chats=chats)

@app.route('/api/chats/new', methods=['POST'])
def create_new_chat():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    chat_id = str(uuid.uuid4())
    
    # Get the initial message as title (or use default)
    initial_message = request.json.get('message', '')
    if initial_message:
        # Generate a summary title from the initial message
        title = generate_chat_title(initial_message)
    else:
        title = "New Chat"
        
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    conn = get_db_connection()
    conn.execute('INSERT INTO chats (id, user_id, title, created_at) VALUES (?, ?, ?, ?)',
                (chat_id, session['user_id'], title, now))
    conn.commit()
    conn.close()
    
    return jsonify({
        'chat_id': chat_id,
        'title': title,
        'created_at': now
    })

# Function to generate a chat title using the initial message
def generate_chat_title(message):
    try:
        # Try to generate a summary using the local AI model
        prompt = f"Summarize the following user message into a brief chat title (4-6 words max):\n\n{message}"
        
        response = requests.post(
            'http://localhost:11434/api/chat',
            json={
                'model': 'llama3.2',
                'messages': [{'role': 'user', 'content': prompt}],
                'stream': False
            }
        )
        
        if response.status_code == 200:
            title = response.json().get('message', {}).get('content', '')
            
            # Clean up and limit the title length
            title = title.strip().strip('"').replace('\n', ' ')
            title = re.sub(r'Chat Title: |Title: |Summary: ', '', title, flags=re.IGNORECASE)
            
            # Limit to 50 characters
            if len(title) > 50:
                title = title[:47] + "..."
                
            if title:
                return title
    
    except Exception as e:
        print(f"Error generating chat title: {str(e)}")
    
    # Fallback: use a truncated version of the message
    if len(message) > 50:
        return message[:47] + "..."
    return message

@app.route('/api/chats/<chat_id>/messages', methods=['GET'])
def get_chat_messages(chat_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    conn = get_db_connection()
    chat = conn.execute('SELECT * FROM chats WHERE id = ? AND user_id = ?',
                      (chat_id, session['user_id'])).fetchone()
    
    if not chat:
        conn.close()
        return jsonify({'error': 'Chat not found'}), 404
    
    messages = conn.execute('SELECT * FROM chat_messages WHERE chat_id = ? ORDER BY timestamp',
                          (chat_id,)).fetchall()
    conn.close()
    
    return jsonify({'messages': [dict(m) for m in messages]})

@socketio.on('send_message')
def handle_message(data):
    if 'user_id' not in session:
        emit('error', {'message': 'Not logged in'})
        return
    
    chat_id = data.get('chat_id', 'new')
    message = data.get('message')
    
    if not message:
        emit('error', {'message': 'Message cannot be empty'})
        return
    
    conn = get_db_connection()
    
    # Handle "new" chat_id or missing chat_id
    if chat_id == 'new' or chat_id == '':
        # Create a new chat
        chat_id = str(uuid.uuid4())
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Generate a title based on the user's first message
        title = generate_chat_title(message)
        
        conn.execute('INSERT INTO chats (id, user_id, title, created_at) VALUES (?, ?, ?, ?)',
                    (chat_id, session['user_id'], title, now))
        conn.commit()
        print(f"Created new chat with ID: {chat_id} and title: {title}")
        
        # Emit a chat_created event to update the UI
        emit('chat_created', {
            'chat_id': chat_id,
            'title': title,
            'created_at': now
        })
    else:
        # Verify chat belongs to user
        chat = conn.execute('SELECT * FROM chats WHERE id = ? AND user_id = ?', 
                         (chat_id, session['user_id'])).fetchone()
        if not chat:
            print(f"Invalid chat ID: {chat_id}")
            conn.close()
            emit('error', {'message': 'Invalid chat'})
            return
    
    # Save user message to database
    message_id = str(uuid.uuid4())
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    conn.execute('INSERT INTO chat_messages (id, chat_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)',
                (message_id, chat_id, 'user', message, now))
    conn.commit()
    print(f"Saved user message to database")
    
    # Send to Ollama API - using local Llama 3.2 model
    try:
        # Stream the response
        ai_message_id = str(uuid.uuid4())
        emit('start_ai_response', {'message_id': ai_message_id})
        
        try:
            print(f"Sending request to Ollama API")
            response = requests.post(
                'http://localhost:11434/api/chat',
                json={
                    'model': 'llama3.2',
                    'messages': [{'role': 'user', 'content': message}],
                    'stream': False
                }
            )
            
            if response.status_code == 200:
                ai_response = response.json().get('message', {}).get('content', '')
                print(f"Received AI response: {ai_response[:50]}...")
                
                # Save AI response to database
                conn.execute('INSERT INTO chat_messages (id, chat_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)',
                            (ai_message_id, chat_id, 'assistant', ai_response, now))
                conn.commit()
                
                # Award points for using AI chat
                conn.execute('UPDATE users SET points = points + 5 WHERE id = ?', (session['user_id'],))
                conn.commit()
                
                # Check if this is their first chat (for achievement)
                chat_count = conn.execute('SELECT COUNT(*) FROM chats WHERE user_id = ?', 
                                       (session['user_id'],)).fetchone()[0]
                
                if chat_count == 1:
                    # Award the "First Chat" achievement
                    conn.execute('''
                        INSERT OR IGNORE INTO user_achievements (user_id, achievement_id, earned_at) 
                        VALUES (?, ?, ?)
                    ''', (session['user_id'], '1', now))
                    conn.commit()
                    emit('achievement_earned', {
                        'name': 'First Chat',
                        'description': 'Started your first AI chat session',
                        'points': 10
                    })
                
                # Simulate streaming for better UX
                words = ai_response.split()
                chunk_size = 1  # Send one word at a time for smoother streaming
                for i in range(0, len(words), chunk_size):
                    chunk = ' '.join(words[i:i+chunk_size])
                    # Fix numbering patterns for Markdown compatibility
                    chunk = re.sub(r'(\d+)\. ', r'\1\. ', chunk)
                    emit('ai_response_chunk', {'text': chunk})
                    # Add a small delay for more natural typing effect
                    time.sleep(0.05)
                
                emit('ai_response_complete')
            else:
                print(f"Error from Ollama API: {response.status_code}")
                fallback_response = "I'm sorry, I couldn't process your request right now."
                emit('ai_response_chunk', {'text': fallback_response})
                emit('ai_response_complete')
                emit('error', {'message': f'Failed to get response from AI model: {response.status_code}'})
                
                # Save fallback response
                conn.execute('INSERT INTO chat_messages (id, chat_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)',
                            (ai_message_id, chat_id, 'assistant', fallback_response, now))
                conn.commit()
        
        except Exception as e:
            print(f"Error connecting to Ollama: {str(e)}")
            fallback_response = "I'm sorry, I couldn't connect to the AI model. Make sure Ollama is running with Llama 3.2 installed."
            emit('ai_response_chunk', {'text': fallback_response})
            emit('ai_response_complete')
            emit('error', {'message': f'Error connecting to Ollama: {str(e)}'})
            
            # Save fallback response
            conn.execute('INSERT INTO chat_messages (id, chat_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)',
                        (ai_message_id, chat_id, 'assistant', fallback_response, now))
            conn.commit()
    
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        emit('error', {'message': f'Error: {str(e)}'})
    
    finally:
        conn.close()

@app.route('/forum')
def forum():
    conn = get_db_connection()
    categories = conn.execute('SELECT * FROM forum_categories').fetchall()
    
    # Process categories to add statistics
    result_categories = []
    for category in categories:
        category_id = category['id']
        # Count topics in this category
        topic_count = conn.execute('SELECT COUNT(*) FROM forum_topics WHERE category_id = ?', 
                               (category_id,)).fetchone()[0]
        
        # Get latest topic in this category
        latest_topic = conn.execute('''
            SELECT t.*, u.username FROM forum_topics t
            JOIN users u ON t.user_id = u.id
            WHERE t.category_id = ?
            ORDER BY t.created_at DESC LIMIT 1
        ''', (category_id,)).fetchone()
        
        # Create a new dictionary with all the data we need
        category_data = dict(category)
        category_data['topic_count'] = topic_count
        category_data['latest_topic'] = latest_topic
        result_categories.append(category_data)
    
    conn.close()
    return render_template('forum.html', categories=result_categories)

@app.route('/forum/category/<category_id>')
def forum_category(category_id):
    conn = get_db_connection()
    category = conn.execute('SELECT * FROM forum_categories WHERE id = ?', (category_id,)).fetchone()
    
    if not category:
        conn.close()
        return redirect(url_for('forum'))
    
    topics = conn.execute('''
        SELECT t.*, u.username, 
               (SELECT COUNT(*) FROM forum_replies WHERE topic_id = t.id) as reply_count
        FROM forum_topics t
        JOIN users u ON t.user_id = u.id
        WHERE t.category_id = ?
        ORDER BY t.created_at DESC
    ''', (category_id,)).fetchall()
    
    conn.close()
    return render_template('forum_category.html', category=category, topics=topics)

@app.route('/forum/topic/<topic_id>')
def forum_topic(topic_id):
    conn = get_db_connection()
    topic = conn.execute('''
        SELECT t.*, u.username, c.name as category_name
        FROM forum_topics t
        JOIN users u ON t.user_id = u.id
        JOIN forum_categories c ON t.category_id = c.id
        WHERE t.id = ?
    ''', (topic_id,)).fetchone()
    
    if not topic:
        conn.close()
        return redirect(url_for('forum'))
    
    # Increment view count
    conn.execute('UPDATE forum_topics SET views = views + 1 WHERE id = ?', (topic_id,))
    conn.commit()
    
    replies = conn.execute('''
        SELECT r.*, u.username
        FROM forum_replies r
        JOIN users u ON r.user_id = u.id
        WHERE r.topic_id = ?
        ORDER BY r.created_at
    ''', (topic_id,)).fetchall()
    
    conn.close()
    return render_template('forum_topic.html', topic=topic, replies=replies)

@app.route('/forum/new-topic', methods=['GET', 'POST'])
def new_topic():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        category_id = request.form.get('category')
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not category_id or not title or not content:
            conn = get_db_connection()
            categories = conn.execute('SELECT * FROM forum_categories').fetchall()
            conn.close()
            return render_template('new_topic.html', categories=categories, 
                                 error='All fields are required')
        
        topic_id = str(uuid.uuid4())
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO forum_topics (id, category_id, user_id, title, content, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (topic_id, category_id, session['user_id'], title, content, now, now))
        
        # Award points for creating a topic
        conn.execute('UPDATE users SET points = points + 15 WHERE id = ?', (session['user_id'],))
        
        # Check if this is their first forum post (for achievement)
        post_count = conn.execute('''
            SELECT COUNT(*) FROM forum_topics WHERE user_id = ?
            UNION ALL
            SELECT COUNT(*) FROM forum_replies WHERE user_id = ?
        ''', (session['user_id'], session['user_id'])).fetchone()[0]
        
        if post_count == 1:
            # Award the "Forum Novice" achievement
            conn.execute('''
                INSERT OR IGNORE INTO user_achievements (user_id, achievement_id, earned_at) 
                VALUES (?, ?, ?)
            ''', (session['user_id'], '2', now))
        
        conn.commit()
        conn.close()
        
        return redirect(url_for('forum_topic', topic_id=topic_id))
    
    conn = get_db_connection()
    categories = conn.execute('SELECT * FROM forum_categories').fetchall()
    conn.close()
    
    return render_template('new_topic.html', categories=categories)

@app.route('/forum/topic/<topic_id>/reply', methods=['POST'])
def reply_to_topic(topic_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    content = request.form.get('content')
    
    if not content:
        return redirect(url_for('forum_topic', topic_id=topic_id))
    
    reply_id = str(uuid.uuid4())
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO forum_replies (id, topic_id, user_id, content, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (reply_id, topic_id, session['user_id'], content, now, now))
    
    # Award points for replying
    conn.execute('UPDATE users SET points = points + 10 WHERE id = ?', (session['user_id'],))
    conn.commit()
    conn.close()
    
    return redirect(url_for('forum_topic', topic_id=topic_id))

@app.route('/roadmap')
def roadmap():
    return render_template('roadmap.html')

@app.route('/leaderboard')
def leaderboard():
    conn = get_db_connection()
    users = conn.execute('''
        SELECT id, username, points, level, streak
        FROM users
        ORDER BY points DESC
        LIMIT 20
    ''').fetchall()
    conn.close()
    
    return render_template('leaderboard.html', users=users)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    # Get achievements
    achievements = conn.execute('''
        SELECT a.* FROM achievements a
        JOIN user_achievements ua ON a.id = ua.achievement_id
        WHERE ua.user_id = ?
    ''', (session['user_id'],)).fetchall()
    
    # Get forum activity
    topics = conn.execute('''
        SELECT t.*, c.name as category_name
        FROM forum_topics t
        JOIN forum_categories c ON t.category_id = c.id
        WHERE t.user_id = ?
        ORDER BY t.created_at DESC
        LIMIT 5
    ''', (session['user_id'],)).fetchall()
    
    replies = conn.execute('''
        SELECT r.*, t.title as topic_title
        FROM forum_replies r
        JOIN forum_topics t ON r.topic_id = t.id
        WHERE r.user_id = ?
        ORDER BY r.created_at DESC
        LIMIT 5
    ''', (session['user_id'],)).fetchall()
    
    # Get chat history
    chats = conn.execute('''
        SELECT * FROM chats
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 5
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    
    return render_template('profile.html', user=user, achievements=achievements,
                         topics=topics, replies=replies, chats=chats)

@app.route('/api/chats/<chat_id>/delete', methods=['POST'])
def delete_chat(chat_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    try:
        conn = get_db_connection()
        
        # First, verify the chat belongs to the user
        chat = conn.execute('SELECT * FROM chats WHERE id = ? AND user_id = ?',
                          (chat_id, session['user_id'])).fetchone()
        
        if not chat:
            conn.close()
            return jsonify({'success': False, 'error': 'Chat not found'}), 404
        
        # Delete all messages associated with the chat
        conn.execute('DELETE FROM chat_messages WHERE chat_id = ?', (chat_id,))
        
        # Delete the chat itself
        conn.execute('DELETE FROM chats WHERE id = ?', (chat_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    
    except Exception as e:
        print(f"Error deleting chat: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chats/clear', methods=['POST'])
def clear_all_chats():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    try:
        conn = get_db_connection()
        
        # Get all chat IDs for this user
        chats = conn.execute('SELECT id FROM chats WHERE user_id = ?', 
                           (session['user_id'],)).fetchall()
        
        chat_ids = [chat['id'] for chat in chats]
        
        # Delete all messages for user's chats
        for chat_id in chat_ids:
            conn.execute('DELETE FROM chat_messages WHERE chat_id = ?', (chat_id,))
        
        # Delete all chats for the user
        conn.execute('DELETE FROM chats WHERE user_id = ?', (session['user_id'],))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    
    except Exception as e:
        print(f"Error clearing chats: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ocr', methods=['POST'])
def process_ocr():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    try:
        data = request.json
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'success': False, 'error': 'No image data provided'}), 400
        
        # Extract the base64 data part
        if 'base64,' in image_data:
            image_data = image_data.split('base64,')[1]
        
        # Decode base64 to binary
        image_binary = base64.b64decode(image_data)
        
        # Open image with PIL
        image = Image.open(io.BytesIO(image_binary))
        
        # Process with pytesseract
        text = pytesseract.image_to_string(image)
        
        return jsonify({
            'success': True,
            'text': text
        })
        
    except Exception as e:
        print(f"OCR Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True) 