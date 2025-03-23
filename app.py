from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response, stream_with_context
import os
import requests
import json
import random
import time
import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Load database from file if it exists
def load_db():
    global users_db, roadmaps_db, forum_posts
    try:
        if os.path.exists('data/db.json'):
            with open('data/db.json', 'r') as f:
                data = json.load(f)
                users_db = data.get('users', {})
                roadmaps_db = data.get('roadmaps', {})
                forum_posts = data.get('forum_posts', [])
        else:
            # Create directory if it doesn't exist
            os.makedirs('data', exist_ok=True)
            users_db = {}
            roadmaps_db = {}
            forum_posts = []
    except Exception as e:
        print(f"Error loading database: {e}")
        users_db = {}
        roadmaps_db = {}
        forum_posts = []

# Save database to file
def save_db():
    try:
        with open('data/db.json', 'w') as f:
            json.dump({
                'users': users_db,
                'roadmaps': roadmaps_db,
                'forum_posts': forum_posts
            }, f)
    except Exception as e:
        print(f"Error saving database: {e}")

# Initialize database
load_db()

# Ollama API endpoint
OLLAMA_API = "http://localhost:11434/api/generate"

# Register custom filters
@app.template_filter('timestamp_format')
def timestamp_format(timestamp):
    """Format a Unix timestamp into a readable date"""
    dt = datetime.datetime.fromtimestamp(timestamp)
    return dt.strftime('%b %d, %Y - %H:%M')

# Context processor to add user data to all templates
@app.context_processor
def inject_user():
    user_data = None
    if 'username' in session and session['username'] in users_db:
        user_data = users_db[session['username']]
    return dict(user=user_data)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    if 'username' in session:
        # If user is logged in, redirect to dashboard
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in users_db and users_db[username]['password'] == password:
            session['username'] = username
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in users_db:
            return render_template('signup.html', error='Username already exists')
        
        users_db[username] = {
            'password': password,
            'points': 0,
            'level': 1,
            'streak': 0,
            'roadmaps': [],
            'completed_topics': []
        }
        
        # Save the updated database
        save_db()
        
        session['username'] = username
        return redirect(url_for('dashboard'))
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    username = session['username']
    user_data = users_db[username]
    
    user_roadmaps = []
    for roadmap_id in user_data['roadmaps']:
        if roadmap_id in roadmaps_db:
            user_roadmaps.append(roadmaps_db[roadmap_id])
    
    return render_template('dashboard.html', 
                          user=user_data, 
                          roadmaps=user_roadmaps)

@app.route('/ai-chat')
@login_required
def ai_chat():
    return render_template('ai_chat.html')

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    def generate():
        username = session['username']
        message = request.json.get('message', '')
        
        # Prepare context about the user
        user_data = users_db[username]
        context = f"You are an AI learning assistant for {username}. Their current level is {user_data['level']} with {user_data['points']} points. "
        
        if user_data['roadmaps']:
            context += f"They are working on the following roadmaps: {', '.join([roadmaps_db[r]['title'] for r in user_data['roadmaps'] if r in roadmaps_db])}. "
        
        if user_data['completed_topics']:
            context += f"They have completed these topics: {', '.join(user_data['completed_topics'])}."
        
        # Prepare prompt for Ollama
        prompt = f"{context}\n\nUser: {message}\n\nAssistant:"
        
        # Stream response from Ollama
        response = requests.post(
            OLLAMA_API,
            json={"model": "llama3.2", "prompt": prompt, "stream": True},
            stream=True
        )
        
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                if 'response' in data:
                    yield data['response']
        
    return Response(stream_with_context(generate()), content_type='text/plain')

@app.route('/roadmap-creator')
@login_required
def roadmap_creator():
    return render_template('roadmap_creator.html')

@app.route('/api/create-roadmap', methods=['POST'])
@login_required
def api_create_roadmap():
    username = session['username']
    topic = request.json.get('topic', '')
    
    # Generate roadmap using Ollama
    prompt = f"Create a detailed learning roadmap for {topic}. Include main topics, subtopics, resources, and estimated time to complete each section. Format as JSON with the following structure: {{\"title\": \"{topic} Learning Path\", \"description\": \"...\", \"topics\": [{{\"name\": \"Topic 1\", \"description\": \"...\", \"resources\": [\"...\"], \"estimated_hours\": 5, \"subtopics\": [{{\"name\": \"Subtopic 1.1\", \"description\": \"...\", \"resources\": [\"...\"], \"estimated_hours\": 2}}]}}]}}"
    
    response = requests.post(
        OLLAMA_API,
        json={"model": "llama3.2", "prompt": prompt}
    )
    
    try:
        result = response.json()
        roadmap_text = result.get('response', '')
        
        # Extract JSON from the response
        import re
        json_pattern = r'```json\s*([\s\S]*?)\s*```'
        match = re.search(json_pattern, roadmap_text)
        
        if match:
            roadmap_json = json.loads(match.group(1))
        else:
            # Try to extract JSON without the markdown code block
            json_start = roadmap_text.find('{')
            json_end = roadmap_text.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                roadmap_json = json.loads(roadmap_text[json_start:json_end])
            else:
                return jsonify({"error": "Failed to parse roadmap from AI response"}), 500
        
        # Add roadmap to database
        roadmap_id = str(int(time.time()))
        roadmaps_db[roadmap_id] = roadmap_json
        roadmaps_db[roadmap_id]['id'] = roadmap_id
        roadmaps_db[roadmap_id]['creator'] = username
        roadmaps_db[roadmap_id]['completed_topics'] = []
        
        # Add roadmap to user's roadmaps
        users_db[username]['roadmaps'].append(roadmap_id)
        
        return jsonify({"roadmap": roadmaps_db[roadmap_id]})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/roadmap/<roadmap_id>')
@login_required
def view_roadmap(roadmap_id):
    if roadmap_id not in roadmaps_db:
        return redirect(url_for('dashboard'))
    
    roadmap = roadmaps_db[roadmap_id]
    return render_template('roadmap_view.html', roadmap=roadmap)

@app.route('/api/complete-topic', methods=['POST'])
@login_required
def api_complete_topic():
    username = session['username']
    roadmap_id = request.json.get('roadmap_id', '')
    topic_name = request.json.get('topic_name', '')
    
    if roadmap_id not in roadmaps_db or roadmap_id not in users_db[username]['roadmaps']:
        return jsonify({"error": "Roadmap not found"}), 404
    
    # Mark topic as completed
    if topic_name not in roadmaps_db[roadmap_id]['completed_topics']:
        roadmaps_db[roadmap_id]['completed_topics'].append(topic_name)
        
        # Add to user's completed topics
        if topic_name not in users_db[username]['completed_topics']:
            users_db[username]['completed_topics'].append(topic_name)
        
        # Add points
        users_db[username]['points'] += 10
        
        # Update streak
        users_db[username]['streak'] += 1
        
        # Level up if needed
        if users_db[username]['points'] >= users_db[username]['level'] * 100:
            users_db[username]['level'] += 1
        
        # Save the updated database
        save_db()
    
    return jsonify({
        "success": True,
        "points": users_db[username]['points'],
        "level": users_db[username]['level'],
        "streak": users_db[username]['streak']
    })

@app.route('/forum')
def forum():
    return render_template('forum.html', posts=forum_posts)

@app.route('/api/forum-post', methods=['POST'])
@login_required
def api_forum_post():
    username = session['username']
    title = request.json.get('title', '')
    content = request.json.get('content', '')
    
    post_id = str(int(time.time()))
    post = {
        'id': post_id,
        'title': title,
        'content': content,
        'author': username,
        'timestamp': time.time(),
        'comments': []
    }
    
    forum_posts.append(post)
    
    # Add points for posting
    users_db[username]['points'] += 5
    
    # Save the updated database
    save_db()
    
    return jsonify({"success": True, "post": post})

@app.route('/api/forum-comment', methods=['POST'])
@login_required
def api_forum_comment():
    username = session['username']
    post_id = request.json.get('post_id', '')
    content = request.json.get('content', '')
    
    for post in forum_posts:
        if post['id'] == post_id:
            comment = {
                'id': str(int(time.time())),
                'content': content,
                'author': username,
                'timestamp': time.time()
            }
            post['comments'].append(comment)
            
            # Add points for commenting
            users_db[username]['points'] += 2
            
            # Save the updated database
            save_db()
            
            return jsonify({"success": True, "comment": comment})
    
    return jsonify({"error": "Post not found"}), 404

@app.route('/leaderboard')
def leaderboard():
    # Sort users by points
    sorted_users = sorted(
        [{"username": u, **data} for u, data in users_db.items()],
        key=lambda x: x['points'],
        reverse=True
    )
    
    # Calculate highest points and streak
    highest_points = max([u['points'] for u in sorted_users]) if sorted_users else 0
    highest_streak = max([u['streak'] for u in sorted_users]) if sorted_users else 0
    
    # Calculate next level points
    next_level_points = 0
    if 'username' in session and session['username'] in users_db:
        current_user = users_db[session['username']]
        next_level_points = 100 - (current_user['points'] % 100)
    
    return render_template('leaderboard.html', 
                          leaderboard=sorted_users,
                          highest_points=highest_points,
                          highest_streak=highest_streak,
                          next_level_points=next_level_points)

@app.route('/api/generate-quiz', methods=['POST'])
@login_required
def api_generate_quiz():
    topic = request.json.get('topic', '')
    
    # Generate quiz using Ollama
    prompt = f"Create a quiz with 5 multiple-choice questions about {topic}. Format as JSON with the following structure: {{\"questions\": [{{\"question\": \"...\", \"options\": [\"A. ...\", \"B. ...\", \"C. ...\", \"D. ...\"], \"correct_index\": 0}}]}}"
    
    response = requests.post(
        OLLAMA_API,
        json={"model": "llama3.2", "prompt": prompt}
    )
    
    try:
        result = response.json()
        quiz_text = result.get('response', '')
        
        # Extract JSON from the response
        import re
        json_pattern = r'```json\s*([\s\S]*?)\s*```'
        match = re.search(json_pattern, quiz_text)
        
        if match:
            quiz_json = json.loads(match.group(1))
        else:
            # Try to extract JSON without the markdown code block
            json_start = quiz_text.find('{')
            json_end = quiz_text.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                quiz_json = json.loads(quiz_text[json_start:json_end])
            else:
                return jsonify({"error": "Failed to parse quiz from AI response"}), 500
        
        return jsonify({"quiz": quiz_json})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 