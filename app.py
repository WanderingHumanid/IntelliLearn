from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response, stream_with_context, flash
import os
import requests
import json
import random
import time
import datetime
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from models import db, User, Roadmap, ForumPost, ForumComment, StudyResource, PremiumFeature

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///intellilearn.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database with the app
db.init_app(app)

# Ollama API endpoint
OLLAMA_API = "http://localhost:11434/api/generate"

# Register custom filters
@app.template_filter('timestamp_format')
def timestamp_format(timestamp):
    """Format a Unix timestamp into a readable date"""
    if isinstance(timestamp, str):
        try:
            dt = datetime.datetime.fromisoformat(timestamp)
            return dt.strftime('%b %d, %Y - %H:%M')
        except ValueError:
            return timestamp
    elif isinstance(timestamp, (int, float)):
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime('%b %d, %Y - %H:%M')
    return timestamp

# Context processor to add user data to all templates
@app.context_processor
def inject_user():
    user_data = None
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
            user_data = user.to_dict()
    return dict(user=user_data)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Premium required decorator
def premium_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        
        user = User.query.filter_by(username=session['username']).first()
        if not user or not user.is_premium:
            flash("This feature requires a premium subscription", "error")
            return redirect(url_for('premium'))
            
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
        
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            session['username'] = username
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template('signup.html', error='Username already exists')
        
        new_user = User(
            username=username,
            password=password,
            points=0,
            level=1,
            streak=0
        )
        
        db.session.add(new_user)
        db.session.commit()
        
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
    user = User.query.filter_by(username=username).first()
    
    user_roadmaps = Roadmap.query.filter_by(creator_id=user.id).all()
    roadmaps_data = [roadmap.to_dict() for roadmap in user_roadmaps]
    
    return render_template('dashboard.html', 
                          user=user.to_dict(), 
                          roadmaps=roadmaps_data)

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
        
        # Get user data
        user = User.query.filter_by(username=username).first()
        
        # Prepare context about the user
        context = f"You are an AI learning assistant for {username}. Their current level is {user.level} with {user.points} points. "
        
        # Get user roadmaps
        user_roadmaps = Roadmap.query.filter_by(creator_id=user.id).all()
        if user_roadmaps:
            roadmap_titles = [roadmap.title for roadmap in user_roadmaps]
            context += f"They are working on the following roadmaps: {', '.join(roadmap_titles)}. "
        
        completed_topics = user.get_completed_topics()
        if completed_topics:
            context += f"They have completed these topics: {', '.join(completed_topics)}."
        
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
    
    # Get user
    user = User.query.filter_by(username=username).first()
    
    # For non-premium users, check if they have exceeded their roadmap limit
    if not user.is_premium:
        roadmap_count = Roadmap.query.filter_by(creator_id=user.id).count()
        if roadmap_count >= 3:
            return jsonify({"error": "You've reached the maximum number of roadmaps for free users. Upgrade to premium for unlimited roadmaps."}), 403
    
    # Generate roadmap using Ollama
    prompt = f"""Create a detailed learning roadmap for {topic}. 
    The roadmap should be comprehensive and cover the subject in detail.
    Each topic should have clear descriptions and specific resources.
    Structure the roadmap as a JSON object with the following format:
    {{
      "title": "{topic} Learning Path",
      "description": "A comprehensive roadmap to master {topic}",
      "topics": [
        {{
          "name": "Topic 1",
          "description": "Detailed description of the topic",
          "resources": ["Resource 1", "Resource 2"],
          "estimated_hours": 5,
          "subtopics": [
            {{
              "name": "Subtopic 1.1",
              "description": "Description of the subtopic",
              "resources": ["Resource 1", "Resource 2"],
              "estimated_hours": 2
            }}
          ]
        }}
      ]
    }}
    
    Make sure all JSON is properly formatted and can be parsed correctly.
    Include a minimum of 5 main topics, each with at least 2 subtopics.
    For each topic and subtopic, provide detailed descriptions and relevant learning resources.
    """
    
    try:
        response = requests.post(
            OLLAMA_API,
            json={"model": "llama3.2", "prompt": prompt}
        )
        
        result = response.json()
        roadmap_text = result.get('response', '')
        
        # Extract JSON from the response
        import re
        
        # First try to extract from code blocks
        json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        matches = re.findall(json_pattern, roadmap_text)
        
        roadmap_json = None
        
        # Try each match until we find valid JSON
        for match_text in matches:
            try:
                # Clean up the text
                cleaned_text = match_text.strip()
                roadmap_json = json.loads(cleaned_text)
                break  # Found valid JSON, exit loop
            except json.JSONDecodeError:
                continue  # Try the next match
        
        # If code block extraction failed, try to find JSON directly
        if not roadmap_json:
            # Find the outermost JSON object
            json_start = roadmap_text.find('{')
            if json_start != -1:
                open_braces = 0
                for i in range(json_start, len(roadmap_text)):
                    if roadmap_text[i] == '{':
                        open_braces += 1
                    elif roadmap_text[i] == '}':
                        open_braces -= 1
                        if open_braces == 0:  # Found the end of the JSON object
                            json_end = i + 1
                            try:
                                json_text = roadmap_text[json_start:json_end]
                                # Remove any control characters or non-ASCII characters
                                json_text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', json_text)
                                roadmap_json = json.loads(json_text)
                                break
                            except json.JSONDecodeError:
                                pass  # Continue searching
        
        # If all else fails, try a more aggressive approach
        if not roadmap_json:
            # Remove all newlines and extra spaces
            cleaned_text = re.sub(r'\s+', ' ', roadmap_text)
            # Find JSON-like structures
            json_pattern = r'{.*}'
            match = re.search(json_pattern, cleaned_text)
            if match:
                try:
                    roadmap_json = json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        
        # If we still don't have valid JSON, return error
        if not roadmap_json:
            return jsonify({"error": "Failed to parse roadmap from AI response. Please try again with a different topic."}), 500
        
        # Ensure roadmap has the required structure
        if "topics" not in roadmap_json:
            roadmap_json["topics"] = []
        
        # Ensure each topic has all required fields
        for topic in roadmap_json.get("topics", []):
            if "estimated_hours" not in topic:
                topic["estimated_hours"] = 5
            if "resources" not in topic:
                topic["resources"] = []
            if "subtopics" not in topic:
                topic["subtopics"] = []
        
        # Add roadmap to database
        new_roadmap = Roadmap(
            title=roadmap_json.get('title', f"{topic} Learning Path"),
            description=roadmap_json.get('description', f"A learning roadmap for {topic}"),
            content=json.dumps(roadmap_json),
            creator_id=user.id
        )
        
        db.session.add(new_roadmap)
        db.session.commit()
        
        return jsonify({"roadmap": new_roadmap.to_dict()})
    
    except Exception as e:
        app.logger.error(f"Error creating roadmap: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/roadmap/<int:roadmap_id>')
@login_required
def view_roadmap(roadmap_id):
    roadmap = Roadmap.query.get_or_404(roadmap_id)
    return render_template('roadmap_view.html', roadmap=roadmap.to_dict())

@app.route('/api/complete-topic', methods=['POST'])
@login_required
def api_complete_topic():
    username = session['username']
    roadmap_id = request.json.get('roadmap_id')
    topic_name = request.json.get('topic_name')
    
    # Get user and roadmap
    user = User.query.filter_by(username=username).first()
    roadmap = Roadmap.query.get(roadmap_id)
    
    if not roadmap:
        return jsonify({"error": "Roadmap not found"}), 404
    
    # Update completed topics for roadmap
    completed_topics = roadmap.get_completed_topics()
    if topic_name not in completed_topics:
        completed_topics.append(topic_name)
        roadmap.set_completed_topics(completed_topics)
        
        # Update user's completed topics and points
        user_completed_topics = user.get_completed_topics()
        if topic_name not in user_completed_topics:
            user_completed_topics.append(topic_name)
            user.set_completed_topics(user_completed_topics)
            
            # Award points
            user.points += 10
            
            # Level up if points threshold reached
            if user.points >= user.level * 100:
                user.level += 1
            
            # Update streak
            user.streak += 1
        
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "points": user.points, 
            "level": user.level,
            "streak": user.streak
        })
    else:
        return jsonify({"error": "Topic already completed"}), 400

@app.route('/forum')
def forum():
    posts = ForumPost.query.order_by(ForumPost.created_at.desc()).all()
    return render_template('forum.html', posts=[post.to_dict() for post in posts])

@app.route('/api/forum-post', methods=['POST'])
@login_required
def api_forum_post():
    username = session['username']
    title = request.json.get('title', '')
    content = request.json.get('content', '')
    
    if not title or not content:
        return jsonify({"error": "Title and content are required"}), 400
    
    user = User.query.filter_by(username=username).first()
    
    new_post = ForumPost(
        title=title,
        content=content,
        author_id=user.id
    )
    
    db.session.add(new_post)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "post": new_post.to_dict()
    })

@app.route('/api/forum-comment', methods=['POST'])
@login_required
def api_forum_comment():
    username = session['username']
    post_id = request.json.get('post_id')
    content = request.json.get('content', '')
    
    if not post_id or not content:
        return jsonify({"error": "Post ID and content are required"}), 400
    
    user = User.query.filter_by(username=username).first()
    post = ForumPost.query.get(post_id)
    
    if not post:
        return jsonify({"error": "Post not found"}), 404
    
    new_comment = ForumComment(
        content=content,
        author_id=user.id,
        post_id=post_id
    )
    
    db.session.add(new_comment)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "comment": new_comment.to_dict()
    })

@app.route('/leaderboard')
def leaderboard():
    users = User.query.order_by(User.points.desc()).all()
    
    # Calculate highest points and streak
    highest_points = max([user.points for user in users]) if users else 0
    highest_streak = max([user.streak for user in users]) if users else 0
    
    # Get current user if logged in
    current_user = None
    next_level_points = 0
    if 'username' in session:
        current_user = User.query.filter_by(username=session['username']).first()
        if current_user:
            # Assuming level up is every 100 points
            next_level_points = 100 - (current_user.points % 100)
    
    return render_template('leaderboard.html', 
                          leaderboard=[user.to_dict() for user in users],
                          highest_points=highest_points,
                          highest_streak=highest_streak,
                          user=current_user,
                          next_level_points=next_level_points)

@app.route('/api/generate-quiz', methods=['POST'])
@login_required
def api_generate_quiz():
    topic = request.json.get('topic', '')
    
    # Generate quiz using Ollama
    prompt = f"Create a quiz about {topic} with 5 multiple-choice questions. Format as JSON: {{\"questions\":[{{\"question\": \"Question text\", \"options\": [\"Option A\", \"Option B\", \"Option C\", \"Option D\"], \"correct_index\": 0}}]}}."
    
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

# New Route: Study Resources
@app.route('/study-resources')
@login_required
def study_resources():
    # Get filter parameters
    resource_type = request.args.get('type', None)
    subject = request.args.get('subject', None)
    
    # Base query
    query = StudyResource.query
    
    # Apply filters if provided
    if resource_type:
        query = query.filter_by(resource_type=resource_type)
    if subject:
        query = query.filter_by(subject=subject)
    
    # For non-premium users, exclude premium resources
    user = User.query.filter_by(username=session['username']).first()
    if not user.is_premium:
        query = query.filter_by(is_premium=False)
    
    # Get distinct subjects for filter dropdown
    subjects = db.session.query(StudyResource.subject).distinct().all()
    subjects = [s[0] for s in subjects if s[0]]
    
    # Get resources
    resources = query.all()
    
    return render_template('study_resources.html', 
                          resources=[r.to_dict() for r in resources],
                          subjects=subjects,
                          selected_type=resource_type,
                          selected_subject=subject)

# New Route: Add Study Resource
@app.route('/add-study-resource', methods=['GET', 'POST'])
@login_required
def add_study_resource():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        resource_type = request.form['type']
        content = request.form['content']
        subject = request.form['subject']
        is_premium = 'is_premium' in request.form
        
        # Only admin or premium users can add premium resources
        user = User.query.filter_by(username=session['username']).first()
        if is_premium and not user.is_premium:
            is_premium = False
        
        new_resource = StudyResource(
            title=title,
            description=description,
            resource_type=resource_type,
            content=content,
            subject=subject,
            is_premium=is_premium
        )
        
        db.session.add(new_resource)
        db.session.commit()
        
        return redirect(url_for('study_resources'))
    
    return render_template('add_study_resource.html')

# New Route: AI Study Help - Premium Feature
@app.route('/ai-study-help', methods=['GET', 'POST'])
@premium_required
def ai_study_help():
    if request.method == 'POST':
        topic = request.form['topic']
        question = request.form['question']
        
        # Generate response using Ollama
        prompt = f"Act as a tutor helping with {topic}. Question: {question}"
        
        response = requests.post(
            OLLAMA_API,
            json={"model": "llama3.2", "prompt": prompt}
        )
        
        try:
            result = response.json()
            answer = result.get('response', '')
            return render_template('ai_study_help.html', topic=topic, question=question, answer=answer)
        except Exception as e:
            return render_template('ai_study_help.html', error=str(e))
    
    return render_template('ai_study_help.html')

# New Route: Premium Features
@app.route('/premium')
@login_required
def premium():
    # Get all active premium features
    features = PremiumFeature.query.filter_by(is_active=True).all()
    
    # Check if user is already premium
    user = User.query.filter_by(username=session['username']).first()
    is_premium = user.is_premium
    premium_until = user.premium_until
    
    return render_template('premium.html', 
                          features=[f.to_dict() for f in features],
                          is_premium=is_premium,
                          premium_until=premium_until)

# New Route: Upgrade to Premium (mock payment)
@app.route('/upgrade-premium', methods=['POST'])
@login_required
def upgrade_premium():
    # In a real application, this would handle payment processing
    # For now, we'll just upgrade the user
    
    plan_duration = request.form.get('plan', '1') # 1, 3, 6, or 12 months
    
    user = User.query.filter_by(username=session['username']).first()
    
    # Set premium expiration based on selected plan
    duration_months = int(plan_duration)
    user.is_premium = True
    
    if user.premium_until and user.premium_until > datetime.datetime.utcnow():
        # If already premium, extend the duration
        user.premium_until = user.premium_until + datetime.timedelta(days=30*duration_months)
    else:
        # New premium subscription
        user.premium_until = datetime.datetime.utcnow() + datetime.timedelta(days=30*duration_months)
    
    db.session.commit()
    
    flash(f"You've successfully upgraded to premium for {duration_months} months!", "success")
    return redirect(url_for('premium'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create tables if they don't exist
    app.run(debug=True) 