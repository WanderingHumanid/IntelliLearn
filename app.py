from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response, stream_with_context, flash, send_from_directory
import os
import requests
import json
import random
import time
import datetime
import uuid
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from models import db, User, Roadmap, ForumPost, ForumComment, StudyResource, PremiumFeature, ChatMessage, ForumReaction
from werkzeug.utils import secure_filename
from ocr_utils import save_uploaded_file, extract_text_from_image, perform_tr_ocr, perform_tesseract_ocr
import base64
from PIL import Image

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///intellilearn.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure file uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}

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
def index():
    if 'username' in session:
        # If user is logged in, show dashboard button
        return render_template('index.html', logged_in=True)
    return render_template('index.html', logged_in=False)

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
    return redirect(url_for('index'))

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
    username = session['username']
    user = User.query.filter_by(username=username).first()
    
    # Generate a new conversation ID if not in session
    if 'conversation_id' not in session:
        session['conversation_id'] = f"conv_{int(time.time())}_{user.id}"
    
    # Get previous messages for this conversation
    previous_messages = ChatMessage.query.filter_by(
        user_id=user.id,
        conversation_id=session['conversation_id']
    ).order_by(ChatMessage.created_at).all()
    
    # Get a list of all conversations for this user
    conversation_list = []
    
    # Get all unique conversation IDs for this user
    conversation_ids = db.session.query(ChatMessage.conversation_id).filter_by(
        user_id=user.id
    ).distinct().all()
    
    for conv_id in conversation_ids:
        conv_id = conv_id[0]  # Extract the string from the tuple
        
        # Skip the current conversation
        if conv_id == session.get('conversation_id'):
            continue
            
        # Get the first message of the conversation for timestamp
        first_message = ChatMessage.query.filter_by(
            user_id=user.id,
            conversation_id=conv_id
        ).order_by(ChatMessage.created_at).first()
        
        if first_message:
            # Get a snippet of the conversation (first user message)
            first_user_message = ChatMessage.query.filter_by(
                user_id=user.id,
                conversation_id=conv_id,
                is_user=True
            ).order_by(ChatMessage.created_at).first()
            
            snippet = first_user_message.content if first_user_message else "No messages"
            # Limit snippet length
            if len(snippet) > 30:
                snippet = snippet[:30] + "..."
                
            conversation_list.append({
                'id': conv_id,
                'created_at': first_message.created_at,
                'snippet': snippet
            })
    
    # Sort conversations by creation time (newest first)
    conversation_list.sort(key=lambda x: x['created_at'], reverse=True)
    
    return render_template('ai_chat.html', previous_messages=previous_messages, conversation_list=conversation_list)

@app.route('/api/load-conversation/<conversation_id>')
@login_required
def load_conversation(conversation_id):
    username = session['username']
    user = User.query.filter_by(username=username).first()
    
    # Validate that this conversation belongs to the user
    conversation = ChatMessage.query.filter_by(
        user_id=user.id,
        conversation_id=conversation_id
    ).first()
    
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404
    
    # Set the conversation ID in the session
    session['conversation_id'] = conversation_id
    
    # Get all messages for this conversation
    messages = ChatMessage.query.filter_by(
        user_id=user.id,
        conversation_id=conversation_id
    ).order_by(ChatMessage.created_at).all()
    
    # Convert messages to dict
    messages_list = [message.to_dict() for message in messages]
    
    return jsonify({
        "success": True,
        "conversation_id": conversation_id,
        "messages": messages_list
    })

def allowed_file(filename, allowed_extensions=None):
    """Check if a filename has an allowed extension"""
    if allowed_extensions is None:
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    def generate():
        username = session['username']
        message = request.json.get('message', '')
        
        # Get user data
        user = User.query.filter_by(username=username).first()
        
        # Create conversation ID if not in session
        if 'conversation_id' not in session:
            session['conversation_id'] = f"conv_{int(time.time())}_{user.id}"
            
        conversation_id = session['conversation_id']
        
        # Save user message to database
        user_message = ChatMessage(
            user_id=user.id,
            content=message,
            is_user=True,
            conversation_id=conversation_id
        )
        db.session.add(user_message)
        db.session.commit()
        
        # Get previous messages for context (last 10 messages)
        previous_messages = ChatMessage.query.filter_by(
            user_id=user.id,
            conversation_id=conversation_id
        ).order_by(ChatMessage.created_at.desc()).limit(10).all()
        
        # Reverse to get chronological order
        previous_messages.reverse()
        
        # Prepare context about the user
        context = f"You are an AI learning assistant for {username}. Their current level is {user.level} with {user.points} points. "
        
        # Add educational profile information if available
        if user.education_level:
            context += f"Their education level is {user.education_level}. "
        
        if user.field_of_study:
            context += f"They are studying {user.field_of_study}. "
        
        # Add current courses if available
        try:
            current_courses = json.loads(user.current_courses or '[]')
            if current_courses:
                context += f"They are currently taking these courses: {', '.join(current_courses)}. "
        except:
            app.logger.error("Error parsing current courses")
        
        if user.learning_goals:
            context += f"Their learning goals are: {user.learning_goals}. "
            
        if user.career_goals:
            context += f"Their career goals are: {user.career_goals}. "
            
        if user.preferred_learning_style:
            context += f"Their preferred learning style is {user.preferred_learning_style}. "
        
        # Get user roadmaps
        user_roadmaps = Roadmap.query.filter_by(creator_id=user.id).all()
        if user_roadmaps:
            roadmap_titles = [roadmap.title for roadmap in user_roadmaps]
            context += f"They are working on the following roadmaps: {', '.join(roadmap_titles)}. "
        
        completed_topics = user.get_completed_topics()
        if completed_topics:
            context += f"They have completed these topics: {', '.join(completed_topics)}."
        
        # Add conversation history to the prompt
        conversation_history = ""
        for msg in previous_messages:
            if msg.is_user:
                conversation_history += f"User: {msg.content}\n"
            else:
                conversation_history += f"Assistant: {msg.content}\n"
        
        # Prepare prompt for Ollama
        prompt = f"{context}\n\nConversation history:\n{conversation_history}\n\nUser: {message}\n\nAssistant:"
        
        # Store AI response as we receive it
        ai_response_content = ""
        
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
                    ai_response_content += data['response']
                    yield data['response']
        
        # Save AI response to database
        ai_message = ChatMessage(
            user_id=user.id,
            content=ai_response_content,
            is_user=False,
            conversation_id=conversation_id
        )
        db.session.add(ai_message)
        
        # Award points for chatting with the AI assistant
        # Only award points once per conversation to prevent spam
        last_point_award = ChatMessage.query.filter_by(
            user_id=user.id,
            conversation_id=conversation_id,
            is_user=True,
            points_awarded=True
        ).order_by(ChatMessage.created_at.desc()).first()
        
        # Check if last point award was more than 5 minutes ago
        award_points = False
        if not last_point_award:
            award_points = True
        else:
            time_diff = datetime.datetime.utcnow() - last_point_award.created_at
            if time_diff.total_seconds() > 300:  # 5 minutes
                award_points = True
        
        if award_points:
            user.points += 2
            
            # Level up if points threshold reached
            if user.points >= user.level * 100:
                user.level += 1
                
            # Mark this message as having awarded points
            user_message.points_awarded = True
            
        db.session.commit()
        
    return Response(stream_with_context(generate()), content_type='text/plain')

@app.route('/api/upload-file', methods=['POST'])
@login_required
def upload_file():
    # Check if a file was uploaded
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    
    # Check if the file was selected
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
        
    # Check if the file type is allowed
    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400
    
    # Get user data
    username = session['username']
    user = User.query.filter_by(username=username).first()
    
    # Create conversation ID if not in session
    if 'conversation_id' not in session:
        session['conversation_id'] = f"conv_{int(time.time())}_{user.id}"
        
    conversation_id = session['conversation_id']
    
    try:
        # Save the file
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1].lower()
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Determine file type
        file_type = file.content_type if hasattr(file, 'content_type') else "application/octet-stream"
        message_type = 'image' if file_type.startswith('image/') else 'document'
        
        # Process with OCR if it's an image
        ocr_text = ""
        use_tr_ocr = request.form.get('ocr_method', 'tr') == 'tr'
        
        if message_type == 'image':
            try:
                # Extract text using OCR
                app.logger.info(f"Processing image with OCR (TR-OCR={use_tr_ocr})")
                ocr_text = extract_text_from_image(file_path, use_tr_ocr=use_tr_ocr)
                
                # If OCR fails or returns an empty result, set a generic message
                if not ocr_text or ocr_text.startswith("Error") or ocr_text.startswith("Failed"):
                    app.logger.warning("OCR failed or returned empty result")
                    ocr_text = f"[Image uploaded: {filename}]"
                else:
                    app.logger.info("OCR succeeded")
            except Exception as e:
                app.logger.error(f"OCR error: {str(e)}")
                ocr_text = f"[Image uploaded: {filename}]"
        
        # Create a message with the content being either the OCR text or a default message
        content = ocr_text if ocr_text else f"Uploaded {message_type}: {filename}"
        
        # Save message to database
        message = ChatMessage(
            user_id=user.id,
            content=content,
            is_user=True,
            conversation_id=conversation_id,
            message_type=message_type,
            has_file=True,
            file_path=file_path,
            file_type=file_type,
            file_name=filename
        )
        db.session.add(message)
        
        # Award points for uploading a file
        user.points += 3
        
        # Level up if points threshold reached
        if user.points >= user.level * 100:
            user.level += 1
        
        # Mark this message as having awarded points
        message.points_awarded = True
            
        db.session.commit()
        
        # Generate AI response to the uploaded content
        if message_type == 'image':
            ai_prompt = f"I've uploaded an image and here's the extracted text: {content}"
        else:
            ai_prompt = f"I've uploaded a document: {filename}"
        
        # Get previous messages for context (last 10 messages)
        previous_messages = ChatMessage.query.filter_by(
            user_id=user.id,
            conversation_id=conversation_id
        ).order_by(ChatMessage.created_at.desc()).limit(10).all()
        
        # Reverse to get chronological order
        previous_messages.reverse()
        
        # Prepare context about the user
        context = f"You are an AI learning assistant for {username}. Their current level is {user.level} with {user.points} points. "
        
        # Add educational profile information if available
        if user.education_level:
            context += f"Their education level is {user.education_level}. "
        
        if user.field_of_study:
            context += f"They are studying {user.field_of_study}. "
        
        # Add current courses if available
        try:
            current_courses = json.loads(user.current_courses or '[]')
            if current_courses:
                context += f"They are currently taking these courses: {', '.join(current_courses)}. "
        except:
            app.logger.error("Error parsing current courses")
        
        if user.learning_goals:
            context += f"Their learning goals are: {user.learning_goals}. "
            
        if user.career_goals:
            context += f"Their career goals are: {user.career_goals}. "
            
        if user.preferred_learning_style:
            context += f"Their preferred learning style is {user.preferred_learning_style}. "
        
        # Prepare conversation history for the prompt
        conversation_history = ""
        for msg in previous_messages:
            if msg.is_user:
                if msg.message_type != 'text':
                    conversation_history += f"User: I uploaded a {msg.message_type} with the content: {msg.content}\n"
                else:
                    conversation_history += f"User: {msg.content}\n"
            else:
                conversation_history += f"Assistant: {msg.content}\n"
        
        # Prepare prompt for Ollama
        prompt = f"{context}\n\nConversation history:\n{conversation_history}\n\nUser: {ai_prompt}\n\nAssistant:"
        
        # Get response from Ollama
        try:
            response = requests.post(
                OLLAMA_API,
                json={"model": "llama3.2", "prompt": prompt}
            )
            
            try:
                result = response.json()
                ai_response = result.get('response', '')
            except json.JSONDecodeError as je:
                app.logger.error(f"JSON decode error: {je}")
                # Try to get text response when JSON parsing fails
                ai_response = "I'm having trouble processing the file content."
                if response.text:
                    try:
                        # Get the response from the first line only to avoid malformed JSON
                        line = response.text.split('\n')[0]
                        if '{' in line and '}' in line:
                            parsed = json.loads(line)
                            if 'response' in parsed:
                                ai_response = parsed['response']
                    except:
                        pass
        except Exception as e:
            app.logger.error(f"Error getting AI response: {str(e)}")
            ai_response = "I'm sorry, I couldn't process that file properly."
        
        # Save AI response to database
        ai_message = ChatMessage(
            user_id=user.id,
            content=ai_response,
            is_user=False,
            conversation_id=conversation_id
        )
        db.session.add(ai_message)
        
        # Award points for chatting with the AI assistant
        # Only award points once per conversation to prevent spam
        last_point_award = ChatMessage.query.filter_by(
            user_id=user.id,
            conversation_id=conversation_id,
            is_user=True,
            points_awarded=True
        ).order_by(ChatMessage.created_at.desc()).first()
        
        # Check if last point award was more than 5 minutes ago
        award_points = False
        if not last_point_award:
            award_points = True
        else:
            time_diff = datetime.datetime.utcnow() - last_point_award.created_at
            if time_diff.total_seconds() > 300:  # 5 minutes
                award_points = True
        
        if award_points:
            user.points += 2
            
            # Level up if points threshold reached
            if user.points >= user.level * 100:
                user.level += 1
                
            # Mark this message as having awarded points
            ai_message.points_awarded = True
            
        db.session.commit()
        
        # Return success with file info
        return jsonify({
            "success": True,
            "message": message.to_dict(),
            "points": user.points,
            "level": user.level
        })
    
    except Exception as e:
        app.logger.error(f"File upload error: {str(e)}")
        return jsonify({"error": f"Error processing file: {str(e)}"}), 500

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/new-conversation', methods=['POST'])
@login_required
def new_conversation():
    """Create a new conversation by removing the conversation_id from session"""
    if 'conversation_id' in session:
        session.pop('conversation_id')
    
    return jsonify({
        "success": True,
        "message": "New conversation started"
    })

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

@app.route('/profile')
@login_required
def profile():
    username = session['username']
    user = User.query.filter_by(username=username).first()
    return render_template('profile.html', user=user)

@app.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    username = session['username']
    user = User.query.filter_by(username=username).first()
    
    # Update educational fields
    user.education_level = request.form.get('education_level', '')
    user.field_of_study = request.form.get('field_of_study', '')
    user.current_courses = request.form.get('current_courses', '[]') 
    user.learning_goals = request.form.get('learning_goals', '')
    user.career_goals = request.form.get('career_goals', '')
    user.preferred_learning_style = request.form.get('preferred_learning_style', '')
    
    db.session.commit()
    
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile'))

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
    # Get posts from database, ordered by creation time (newest first)
    # Use distinct() to ensure no duplicate posts are returned
    posts = ForumPost.query.distinct(ForumPost.id).order_by(ForumPost.created_at.desc()).all()
    post_dicts = []
    
    # Get current user if logged in
    current_user_id = None
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
            current_user_id = user.id
    
    # Process each post to add user reaction information
    for post in posts:
        post_dict = post.to_dict()
        
        # Add user reactions for logged-in users
        if current_user_id:
            # Check if user has reacted to this post
            user_post_reaction = ForumReaction.query.filter_by(
                user_id=current_user_id, 
                post_id=post.id
            ).first()
            
            if user_post_reaction:
                post_dict['user_reaction'] = user_post_reaction.reaction_type
            else:
                post_dict['user_reaction'] = None
                
            # Check for reactions to comments
            for comment_dict in post_dict['comments']:
                user_comment_reaction = ForumReaction.query.filter_by(
                    user_id=current_user_id, 
                    comment_id=comment_dict['id']
                ).first()
                
                if user_comment_reaction:
                    comment_dict['user_reaction'] = user_comment_reaction.reaction_type
                else:
                    comment_dict['user_reaction'] = None
        
        post_dicts.append(post_dict)
    
    return render_template('forum.html', posts=post_dicts)

@app.route('/api/forum-post', methods=['POST'])
@login_required
def api_forum_post():
    username = session['username']
    title = ''
    content = ''
    has_image = False
    image_path = None
    
    # Handle form data for multipart/form-data
    if request.content_type and 'multipart/form-data' in request.content_type:
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        image = request.files.get('image')
        
        if image and image.filename and allowed_file(image.filename, {'png', 'jpg', 'jpeg', 'gif'}):
            filename = secure_filename(image.filename)
            timestamp = int(time.time())
            image_filename = f"forum_{timestamp}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            
            # Resize image before saving
            try:
                img = Image.open(image)
                # Maintain aspect ratio
                max_size = (800, 800)
                img.thumbnail(max_size, Image.LANCZOS)
                img.save(file_path)
            except Exception as e:
                # Fallback if image processing fails
                try:
                    image.save(file_path)
                except:
                    # Log error but continue without image
                    app.logger.error(f"Error saving image: {str(e)}")
                
            has_image = True
            image_path = image_filename
    else:
        # Handle JSON data
        title = request.json.get('title', '').strip()
        content = request.json.get('content', '').strip()
    
    if not title or not content:
        return jsonify({"error": "Title and content are required"}), 400
    
    user = User.query.filter_by(username=username).first()
    
    new_post = ForumPost(
        title=title,
        content=content,
        author_id=user.id,
        has_image=has_image,
        image_path=image_path
    )
    
    db.session.add(new_post)
    
    # Award points for creating a forum post
    user.points += 5
    
    # Level up if points threshold reached
    if user.points >= user.level * 100:
        user.level += 1
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "post": new_post.to_dict(),
        "points": user.points,
        "level": user.level
    })

@app.route('/api/forum-comment', methods=['POST'])
@login_required
def api_forum_comment():
    username = session['username']
    post_id = None
    content = ''
    has_image = False
    image_path = None
    
    # Handle form data for multipart/form-data
    if request.content_type and 'multipart/form-data' in request.content_type:
        post_id = request.form.get('post_id')
        content = request.form.get('content', '').strip()
        image = request.files.get('image')
        
        if image and image.filename and allowed_file(image.filename, {'png', 'jpg', 'jpeg', 'gif'}):
            filename = secure_filename(image.filename)
            timestamp = int(time.time())
            image_filename = f"comment_{timestamp}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            
            # Resize image before saving
            try:
                img = Image.open(image)
                # Maintain aspect ratio
                max_size = (800, 800)
                img.thumbnail(max_size, Image.LANCZOS)
                img.save(file_path)
            except Exception as e:
                # Fallback if image processing fails
                try:
                    image.save(file_path)
                except:
                    # Log error but continue without image
                    app.logger.error(f"Error saving comment image: {str(e)}")
                
            has_image = True
            image_path = image_filename
    else:
        # Handle JSON data
        post_id = request.json.get('post_id')
        content = request.json.get('content', '').strip()
    
    if not post_id or not content:
        return jsonify({"error": "Post ID and content are required"}), 400
    
    user = User.query.filter_by(username=username).first()
    post = ForumPost.query.get(post_id)
    
    if not post:
        return jsonify({"error": "Post not found"}), 404
    
    new_comment = ForumComment(
        content=content,
        author_id=user.id,
        post_id=post_id,
        has_image=has_image,
        image_path=image_path
    )
    
    db.session.add(new_comment)
    
    # Award points for adding a comment
    user.points += 2
    
    # Level up if points threshold reached
    if user.points >= user.level * 100:
        user.level += 1
        
    db.session.commit()
    
    return jsonify({
        "success": True,
        "comment": new_comment.to_dict(),
        "points": user.points,
        "level": user.level
    })

@app.route('/api/delete-forum-post', methods=['POST'])
@login_required
def delete_forum_post():
    post_id = request.json.get('post_id')
    if not post_id:
        return jsonify({"error": "Post ID is required"}), 400
    
    username = session['username']
    user = User.query.filter_by(username=username).first()
    
    # Find the post
    post = ForumPost.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404
    
    # Check if the user is the author of the post
    if post.author_id != user.id:
        return jsonify({"error": "You can only delete your own posts"}), 403
    
    # Delete the post (this will cascade to comments and reactions due to the relationship)
    db.session.delete(post)
    db.session.commit()
    
    return jsonify({"success": True})

@app.route('/api/delete-forum-comment', methods=['POST'])
@login_required
def delete_forum_comment():
    comment_id = request.json.get('comment_id')
    if not comment_id:
        return jsonify({"error": "Comment ID is required"}), 400
    
    username = session['username']
    user = User.query.filter_by(username=username).first()
    
    # Find the comment
    comment = ForumComment.query.get(comment_id)
    if not comment:
        return jsonify({"error": "Comment not found"}), 404
    
    # Check if the user is the author of the comment
    if comment.author_id != user.id:
        return jsonify({"error": "You can only delete your own comments"}), 403
    
    # Delete the comment (this will cascade to reactions due to the relationship)
    db.session.delete(comment)
    db.session.commit()
    
    return jsonify({"success": True})

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

@app.route('/quiz-generator')
@login_required
def quiz_generator():
    return render_template('quiz_generator.html')

@app.route('/api/generate-quiz', methods=['POST'])
@login_required
def generate_quiz_api():
    data = request.json
    
    # Extract quiz parameters
    topic = data.get('topic', '')
    quiz_type = data.get('quiz_type', 'mcq')
    question_count = int(data.get('question_count', 10))
    difficulty = data.get('difficulty', 'intermediate')
    
    if not topic:
        return jsonify({'error': 'Topic is required'})
    
    try:
        # Create structured prompt for quiz generation
        if quiz_type == 'mcq':
            prompt = f"""
            You are an expert educational quiz creator with years of experience. 
            
            TASK: Create a well-crafted multiple-choice quiz on: {topic}
            
            REQUIREMENTS:
            - Generate exactly {question_count} {difficulty} level questions
            - Each question must have exactly 4 options (A, B, C, D)
            - Questions should test different aspects of the topic
            - Questions should be clear, concise, and unambiguous
            - Include a mix of recall, application, and analysis questions appropriate for {difficulty} level
            - Ensure all answers have similar length and format to avoid giving hints
            - Make sure the correct answer is distributed among all options (don't always make it option A)
            
            RESPONSE FORMAT:
            You MUST return ONLY valid JSON that matches this exact schema:
            {{
                "questions": [
                    {{
                        "question": "Question text here?",
                        "options": ["Option A", "Option B", "Option C", "Option D"],
                        "correct_index": 0
                    }}
                ]
            }}
            
            CONSTRAINTS:
            - The "correct_index" MUST be the 0-based index of the correct answer in the options array
            - Each question MUST have exactly 4 options
            - DO NOT include answer explanations in the JSON
            - DO NOT include any markdown, text, or other content outside the JSON object
            - DO NOT use nested quotes that would break the JSON structure
            - The JSON MUST be valid and properly formatted
            """
        else:
            prompt = f"""
            You are an expert educational quiz creator with years of experience.
            
            TASK: Create a high-quality direct answer quiz on: {topic}
            
            REQUIREMENTS:
            - Generate exactly {question_count} {difficulty} level questions
            - Questions should require specific, factual answers
            - Questions should test different aspects of the topic
            - Questions should be clear, concise, and unambiguous
            - Include a mix of recall, application, and critical thinking questions appropriate for {difficulty} level
            - Answers should be concise but complete (typically 1-3 words or a short phrase)
            
            RESPONSE FORMAT:
            You MUST return ONLY valid JSON that matches this exact schema:
            {{
                "questions": [
                    {{
                        "question": "Question text here?",
                        "answer": "Correct answer text"
                    }}
                ]
            }}
            
            CONSTRAINTS:
            - The "answer" MUST be the precise, correct answer to the question
            - Answers should be concise but complete
            - DO NOT include any markdown, text, or other content outside the JSON object
            - DO NOT use nested quotes that would break the JSON structure 
            - The JSON MUST be valid and properly formatted
            """
        
        # Call Ollama API to generate quiz
        response = requests.post(
            OLLAMA_API,
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False
            }
        )
        
        if response.status_code != 200:
            return jsonify({'error': f'Error generating quiz. Status code: {response.status_code}'})
        
        result = response.json()
        response_text = result.get('response', '')
        
        # Extract JSON from response
        try:
            # Try to find JSON content in the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_content = response_text[json_start:json_end]
                try:
                    quiz_data = json.loads(json_content)
                except json.JSONDecodeError:
                    # Try cleaning the JSON content - sometimes there are issues with escaped quotes
                    cleaned_json = json_content.replace('\\"', '"').replace('\\\\', '\\')
                    try:
                        quiz_data = json.loads(cleaned_json)
                    except json.JSONDecodeError:
                        # If still failing, try removing potential markdown backticks
                        if json_content.startswith('```json'):
                            json_content = json_content[7:]
                        if json_content.endswith('```'):
                            json_content = json_content[:-3]
                        quiz_data = json.loads(json_content.strip())
            else:
                # In case the response doesn't have curly braces but is a valid JSON
                try:
                    quiz_data = json.loads(response_text)
                except json.JSONDecodeError:
                    # Last attempt - try to find content between markdown code blocks
                    if '```json' in response_text and '```' in response_text[response_text.find('```json')+7:]:
                        code_start = response_text.find('```json') + 7
                        code_end = response_text.find('```', code_start)
                        if code_end > code_start:
                            json_content = response_text[code_start:code_end].strip()
                            quiz_data = json.loads(json_content)
                    else:
                        raise json.JSONDecodeError("Could not parse JSON from response", response_text, 0)
            
            # Validate quiz data format
            if not isinstance(quiz_data, dict) or 'questions' not in quiz_data:
                return jsonify({'error': 'Invalid quiz format: missing "questions" field'})
            
            if not isinstance(quiz_data['questions'], list) or len(quiz_data['questions']) == 0:
                return jsonify({'error': 'Invalid quiz format: "questions" must be a non-empty array'})
            
            # Validate expected structure for individual questions based on quiz type
            if quiz_type == 'mcq':
                for i, question in enumerate(quiz_data['questions']):
                    if 'question' not in question or 'options' not in question or 'correct_index' not in question:
                        return jsonify({'error': f'Invalid question format at index {i}: missing required fields'})
                    
                    if not isinstance(question['options'], list) or len(question['options']) != 4:
                        return jsonify({'error': f'Invalid question format at index {i}: must have exactly 4 options'})
                    
                    if not isinstance(question['correct_index'], int) or question['correct_index'] < 0 or question['correct_index'] > 3:
                        return jsonify({'error': f'Invalid question format at index {i}: correct_index must be between 0 and 3'})
            else:  # direct answer questions
                for i, question in enumerate(quiz_data['questions']):
                    if 'question' not in question or 'answer' not in question:
                        return jsonify({'error': f'Invalid question format at index {i}: missing required fields'})
            
            # Log generated quiz
            username = session['username']
            user = User.query.filter_by(username=username).first()
            
            # Add activity for quiz generation
            user.points += 2
            
            # Level up if points threshold reached
            if user.points >= user.level * 100:
                user.level += 1
                
            db.session.commit()
            
            return jsonify({'quiz': quiz_data})
        except json.JSONDecodeError as e:
            # Return detailed error for JSON parsing failures
            return jsonify({
                'error': 'Failed to parse quiz data',
                'details': str(e),
                'raw_response': response_text[:500] + ('...' if len(response_text) > 500 else '')
            })
    except Exception as e:
        print(f"Error generating quiz: {str(e)}")
        return jsonify({'error': f'An error occurred while generating the quiz: {str(e)}'})

@app.route('/api/evaluate-quiz', methods=['POST'])
@login_required
def evaluate_quiz_api():
    data = request.json
    
    quiz = data.get('quiz', {})
    user_answers = data.get('answers', {})
    
    if not quiz or not user_answers:
        return jsonify({'error': 'Quiz and answers are required'})
    
    try:
        # Handle MCQ evaluation
        if 'correct_index' in quiz.get('questions', [{}])[0]:
            correct_count = 0
            evaluation = []
            
            for idx, question in enumerate(quiz.get('questions', [])):
                q_id = str(idx)
                user_answer = user_answers.get(q_id, {})
                
                if user_answer.get('type') == 'mcq':
                    selected_index = user_answer.get('selectedIndex')
                    is_correct = selected_index == question.get('correct_index')
                    
                    if is_correct:
                        correct_count += 1
                        
                    evaluation.append({
                        'correct': is_correct,
                        'selectedIndex': selected_index,
                        'correctIndex': question.get('correct_index')
                    })
                    
            # Generate feedback
            total = len(quiz.get('questions', []))
            percent = (correct_count / total) * 100 if total > 0 else 0
            
            feedback = get_score_feedback(percent)
            
            # Award points for completing quiz
            username = session['username']
            user = User.query.filter_by(username=username).first()
            
            # Add bonus points based on score 
            bonus_points = max(1, int(percent / 20))  # 1-5 points based on score
            user.points += 5 + bonus_points
            
            # Level up if points threshold reached
            if user.points >= user.level * 100:
                user.level += 1
                
            db.session.commit()
            
            return jsonify({
                'results': {
                    'correct': correct_count,
                    'total': total,
                    'percent': percent,
                    'feedback': feedback,
                    'evaluation': evaluation
                }
            })
            
        # Handle direct answer evaluation
        else:
            # Create a structured prompt for AI to evaluate direct answers
            eval_prompt = f"""
            You are an expert educational assessment specialist responsible for evaluating quiz answers.

            TASK: Evaluate the following quiz responses for accuracy against the answer key.
            
            EVALUATION CRITERIA:
            - Accept answers that contain the same key concepts as the correct answer
            - Allow for minor spelling errors or typos
            - Accept synonyms or equivalent phrasings
            - Accept answers with additional information as long as the core correct answer is included
            - Be strict about numerical values, dates, and proper names
            - For conceptual questions, focus on whether the user demonstrates understanding

            QUIZ QUESTIONS AND ANSWERS:
            """
            
            for idx, question in enumerate(quiz.get('questions', [])):
                q_id = str(idx)
                user_answer = user_answers.get(q_id, {})
                
                if user_answer.get('type') == 'direct':
                    eval_prompt += f"Question {idx+1}: {question.get('question')}\n"
                    eval_prompt += f"Correct answer: {question.get('answer')}\n"
                    eval_prompt += f"User answer: {user_answer.get('answerText', '')}\n\n"
            
            eval_prompt += """
            RESPONSE FORMAT:
            You MUST return ONLY valid JSON that matches this exact schema:
            {
                "evaluation": [
                    {
                        "questionIndex": 0,
                        "correct": true,
                        "explanation": "Brief explanation (only needed for incorrect answers)",
                        "correctAnswer": "The correct answer from the answer key"
                    }
                ],
                "correct_count": 5,
                "total_count": 10,
                "feedback": "Brief overall performance feedback based on the score, with specific suggestions for improvement"
            }
            
            CONSTRAINTS:
            - The "correct" field MUST be a boolean (true/false)
            - Only include explanations for incorrect answers
            - Your feedback should be constructive and helpful
            - DO NOT include any markdown, text, or other content outside the JSON object
            - DO NOT use nested quotes that would break the JSON structure
            - The JSON MUST be valid and properly formatted
            """
            
            # Call Ollama API to evaluate answers
            response = requests.post(
                OLLAMA_API,
                json={
                    "model": "mistral",
                    "prompt": eval_prompt,
                    "stream": False
                }
            )
            
            if response.status_code != 200:
                return jsonify({'error': f'Error evaluating quiz. Status code: {response.status_code}'})
            
            result = response.json()
            response_text = result.get('response', '')
            
            # Extract JSON from response
            try:
                # Try to find JSON content in the response
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_content = response_text[json_start:json_end]
                    try:
                        eval_data = json.loads(json_content)
                    except json.JSONDecodeError:
                        # Try cleaning the JSON content
                        cleaned_json = json_content.replace('\\"', '"').replace('\\\\', '\\')
                        try:
                            eval_data = json.loads(cleaned_json)
                        except json.JSONDecodeError:
                            # If still failing, try removing potential markdown backticks
                            if json_content.startswith('```json'):
                                json_content = json_content[7:]
                            if json_content.endswith('```'):
                                json_content = json_content[:-3]
                            eval_data = json.loads(json_content.strip())
                else:
                    try:
                        eval_data = json.loads(response_text)
                    except json.JSONDecodeError:
                        # Last attempt - try to find content between markdown code blocks
                        if '```json' in response_text and '```' in response_text[response_text.find('```json')+7:]:
                            code_start = response_text.find('```json') + 7
                            code_end = response_text.find('```', code_start)
                            if code_end > code_start:
                                json_content = response_text[code_start:code_end].strip()
                                eval_data = json.loads(json_content)
                        else:
                            raise json.JSONDecodeError("Could not parse JSON from response", response_text, 0)
                
                # Validate evaluation data format
                if not isinstance(eval_data, dict):
                    return jsonify({'error': 'Invalid evaluation format: response is not a valid JSON object'})
                
                if 'evaluation' not in eval_data:
                    return jsonify({'error': 'Invalid evaluation format: missing "evaluation" field'})
                
                if not isinstance(eval_data['evaluation'], list):
                    return jsonify({'error': 'Invalid evaluation format: "evaluation" must be an array'})
                
                # Extract evaluation results with validation
                correct_count = eval_data.get('correct_count', 0)
                if not isinstance(correct_count, int):
                    # Try to count correct answers from evaluation array
                    correct_count = sum(1 for item in eval_data['evaluation'] if item.get('correct', False))
                
                total_count = eval_data.get('total_count', len(quiz.get('questions', [])))
                if not isinstance(total_count, int) or total_count <= 0:
                    total_count = len(quiz.get('questions', []))
                
                percent = (correct_count / total_count) * 100 if total_count > 0 else 0
                
                # Generate feedback
                feedback = get_score_feedback(percent)
                
                # Award points for completing quiz
                username = session['username']
                user = User.query.filter_by(username=username).first()
                
                # Add bonus points based on score
                bonus_points = max(1, int(percent / 20))  # 1-5 points based on score
                user.points += 5 + bonus_points
                
                # Level up if points threshold reached
                if user.points >= user.level * 100:
                    user.level += 1
                    
                db.session.commit()
                
                return jsonify({
                    'results': {
                        'correct': correct_count,
                        'total': total_count,
                        'percent': percent,
                        'feedback': feedback,
                        'evaluation': eval_data.get('evaluation', [])
                    }
                })
                
            except json.JSONDecodeError as e:
                return jsonify({'error': f'Invalid evaluation data: {str(e)}. Response: {response_text[:100]}...'})
    
    except Exception as e:
        print(f"Error evaluating quiz: {str(e)}")
        return jsonify({'error': f'An error occurred while evaluating the quiz: {str(e)}'}) 


@app.route('/api/ocr-process', methods=['POST'])
@login_required
def ocr_process():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'})
    
    if file and allowed_file(file.filename, {'png', 'jpg', 'jpeg'}):
        try:
            # Create a secure filename
            filename = secure_filename(file.filename)
            timestamp = int(time.time())
            new_filename = f"{timestamp}_{filename}"
            
            # Save file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
            file.save(file_path)
            
            # Call Ollama API for OCR processing
            # First, encode the image to base64
            with open(file_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Create structured prompt for OCR
            prompt = f"""
            You are an OCR (Optical Character Recognition) system. Extract all text from the image I'm sending.
            
            Here's the image (base64 encoded):
            {encoded_image}
            
            Return ONLY the extracted text. No explanations, no descriptions, no additional text.
            If you can't read some parts, indicate this with [unreadable] in your response.
            """
            
            # Call Ollama API
            response = requests.post(
                OLLAMA_API,
                json={
                    "model": "mistral",
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            if response.status_code != 200:
                return jsonify({'error': f'Error processing image. Status code: {response.status_code}'})
            
            result = response.json()
            text = result.get('response', '').strip()
            
            # Award a small number of points for using OCR
            username = session['username']
            user = User.query.filter_by(username=username).first()
            
            user.points += 1
            if user.points >= user.level * 100:
                user.level += 1
                
            db.session.commit()
            
            return jsonify({
                'success': True,
                'text': text,
                'file_path': file_path
            })
            
        except Exception as e:
            print(f"Error in OCR processing: {str(e)}")
            return jsonify({'error': f'Error processing image: {str(e)}'})
    
    return jsonify({'error': 'Invalid file type. Only PNG and JPEG images are supported.'})

def get_score_feedback(percent):
    """Generate feedback based on quiz score percentage"""
    if percent >= 90:
        return "<p>Excellent job! You have a strong understanding of this topic.</p>"
    elif percent >= 80:
        return "<p>Great work! You have a good grasp of the material with just a few areas to review.</p>"
    elif percent >= 70:
        return "<p>Good effort! You understand most of the concepts but might need to review some areas.</p>"
    elif percent >= 60:
        return "<p>You're on the right track, but there are several concepts you should review to strengthen your knowledge.</p>"
    elif percent >= 40:
        return "<p>You have some understanding of the topic, but need to review the material more thoroughly.</p>"
    else:
        return "<p>This topic seems challenging for you. Consider revisiting the fundamentals and trying again.</p>"

def update_user_points(user_id, points_to_add):
    """Update user points and handle level progression"""
    try:
        # Get current user data
        user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return False
            
        # Update points
        new_points = user['points'] + points_to_add
        
        # Check for level up
        current_level = user['level']
        points_for_next_level = current_level * 100
        
        if new_points >= points_for_next_level:
            # Level up
            new_level = current_level + 1
            db.execute(
                """
                UPDATE users 
                SET points = ?, level = ? 
                WHERE id = ?
                """, 
                (new_points, new_level, user_id)
            )
            
            # Log level up activity
            db.execute(
                """
                INSERT INTO user_activities (user_id, activity_type, description, points)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, 'level_up', f'Advanced to level {new_level}', 0)
            )
        else:
            # Just update points
            db.execute(
                """
                UPDATE users 
                SET points = ? 
                WHERE id = ?
                """, 
                (new_points, user_id)
            )
        
        db.commit()
        return True
        
    except Exception as e:
        print(f"Error updating user points: {str(e)}")
        return False

# Create study resources page
@app.route('/study-resources')
@login_required
def study_resources():
    # Get filter parameters from query string
    resource_type = request.args.get('type', None)
    subject = request.args.get('subject', None)
    
    # Create dummy resources data
    resources = [
        {
            'id': 1,
            'title': 'Introduction to Machine Learning',
            'description': 'A beginner-friendly guide to the fundamentals of machine learning',
            'resource_type': 'notes',
            'subject': 'Data Science',
            'url': '#',
            'is_premium': False
        },
        {
            'id': 2,
            'title': 'Advanced Python Programming',
            'description': 'Deep dive into Python\'s advanced features for experienced developers',
            'resource_type': 'video',
            'subject': 'Programming',
            'url': '#',
            'is_premium': False
        },
        {
            'id': 3,
            'title': 'Data Structures and Algorithms',
            'description': 'Comprehensive guide to essential CS concepts',
            'resource_type': 'notes',
            'subject': 'Computer Science',
            'url': '#',
            'is_premium': False
        },
        {
            'id': 4,
            'title': 'Web Development with React',
            'description': 'Learn modern frontend development with React',
            'resource_type': 'video',
            'subject': 'Web Development',
            'url': '#',
            'is_premium': False
        },
        {
            'id': 5,
            'title': 'Statistical Methods for Data Analysis',
            'description': 'Understanding statistical concepts for data science',
            'resource_type': 'notes', 
            'subject': 'Data Science',
            'url': '#',
            'is_premium': False
        },
        {
            'id': 6,
            'title': 'Practice Problems - Data Structures',
            'description': 'Test your knowledge with these practice problems',
            'resource_type': 'questions',
            'subject': 'Computer Science',
            'url': '#',
            'is_premium': False
        }
    ]
    
    # Apply filters if provided
    if resource_type:
        resources = [r for r in resources if r['resource_type'] == resource_type]
    if subject:
        resources = [r for r in resources if r['subject'] == subject]
    
    # Get distinct subjects for filter dropdown
    subjects = list(set(r['subject'] for r in resources))
    
    return render_template('study_resources.html', 
                          resources=resources,
                          subjects=subjects,
                          selected_type=resource_type,
                          selected_subject=subject)

@app.route('/add-study-resource', methods=['GET', 'POST'])
@login_required
def add_study_resource():
    if request.method == 'POST':
        # Get form data
        title = request.form.get('title')
        description = request.form.get('description')
        resource_type = request.form.get('type')
        content = request.form.get('content')
        subject = request.form.get('subject')
        
        # In a real application, you would save this to the database
        # For now, just show a success message
        flash('Resource added successfully! You earned 8 points.', 'success')
        
        # Award points for adding a resource
        username = session['username']
        user = User.query.filter_by(username=username).first()
        user.points += 8
        
        # Level up if points threshold reached
        if user.points >= user.level * 100:
            user.level += 1
            
        db.session.commit()
        
        return redirect(url_for('study_resources'))
    
    return render_template('add_study_resource.html')

# Premium features page
@app.route('/premium')
@login_required
def premium():
    # Create dummy premium features data
    features = [
        {
            'id': 1,
            'title': 'Unlimited AI Assistant Usage',
            'description': 'Get unlimited access to our AI learning assistant for personalized help',
            'icon': 'robot'
        },
        {
            'id': 2,
            'title': 'Advanced Quiz Generation',
            'description': 'Generate more complex and customized quizzes for better learning',
            'icon': 'question-circle'
        },
        {
            'id': 3,
            'title': 'Priority Support',
            'description': '24/7 access to our support team for any questions or issues',
            'icon': 'headset'
        },
        {
            'id': 4,
            'title': 'Exclusive Content',
            'description': 'Access premium study resources and learning materials',
            'icon': 'crown'
        }
    ]
    
    # Check if user is premium
    username = session['username']
    user = User.query.filter_by(username=username).first()
    is_premium = getattr(user, 'is_premium', False)
    premium_until = getattr(user, 'premium_until', None)
    
    return render_template('premium.html', 
                          features=features,
                          is_premium=is_premium,
                          premium_until=premium_until)

# Mock upgrade to premium
@app.route('/upgrade-premium', methods=['POST'])
@login_required
def upgrade_premium():
    plan_duration = request.form.get('plan', '1')  # 1, 3, 6, or 12 months
    
    username = session['username']
    user = User.query.filter_by(username=username).first()
    
    # Set mock premium features
    user.is_premium = True
    
    # Calculate premium expiration based on plan
    duration_months = int(plan_duration)
    premium_until = datetime.datetime.utcnow() + datetime.timedelta(days=30*duration_months)
    user.premium_until = premium_until
    
    db.session.commit()
    
    flash(f'You\'ve successfully upgraded to premium for {duration_months} months!', 'success')
    return redirect(url_for('premium'))

@app.route('/api/forum-reaction', methods=['POST'])
@login_required
def api_forum_reaction():
    username = session['username']
    post_id = request.json.get('post_id')
    comment_id = request.json.get('comment_id')
    reaction_type = request.json.get('reaction_type')
    
    if not reaction_type or (not post_id and not comment_id):
        return jsonify({"error": "Reaction type and target (post or comment) are required"}), 400
    
    if reaction_type not in ['like', 'dislike']:
        return jsonify({"error": "Invalid reaction type"}), 400
    
    user = User.query.filter_by(username=username).first()
    
    # Check if this is a post or comment reaction
    if post_id:
        post = ForumPost.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404
        
        # Check if user already reacted to this post
        existing_reaction = ForumReaction.query.filter_by(user_id=user.id, post_id=post_id).first()
        if existing_reaction:
            # If the same reaction, remove it (toggle)
            if existing_reaction.reaction_type == reaction_type:
                db.session.delete(existing_reaction)
                if reaction_type == 'like':
                    post.likes = max(0, post.likes - 1)
                    # Remove points for likes if removed
                    if post.author_id != user.id:  # Don't remove points for self-likes
                        post_author = User.query.get(post.author_id)
                        post_author.points = max(0, post_author.points - 1)
                else:
                    post.dislikes = max(0, post.dislikes - 1)
            else:
                # If different reaction, update it
                old_type = existing_reaction.reaction_type
                existing_reaction.reaction_type = reaction_type
                if old_type == 'like':
                    post.likes = max(0, post.likes - 1)
                    post.dislikes += 1
                    
                    # Handle points transfer for like -> dislike
                    if post.author_id != user.id:  # Don't adjust points for self-reactions
                        post_author = User.query.get(post.author_id)
                        post_author.points = max(0, post_author.points - 1)  # Remove like point
                else:
                    post.dislikes = max(0, post.dislikes - 1)
                    post.likes += 1
                    
                    # Handle points transfer for dislike -> like
                    if post.author_id != user.id:  # Don't adjust points for self-reactions
                        post_author = User.query.get(post.author_id)
                        post_author.points += 1  # Add like point
        else:
            # New reaction
            new_reaction = ForumReaction(
                user_id=user.id,
                post_id=post_id,
                reaction_type=reaction_type
            )
            db.session.add(new_reaction)
            
            if reaction_type == 'like':
                post.likes += 1
                # Award point to post author for getting a like
                if post.author_id != user.id:  # Don't award points for self-likes
                    post_author = User.query.get(post.author_id)
                    post_author.points += 1
                    
                    # Level up if points threshold reached
                    if post_author.points >= post_author.level * 100:
                        post_author.level += 1
            else:
                post.dislikes += 1
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "post": post.to_dict()
        })
        
    elif comment_id:
        comment = ForumComment.query.get(comment_id)
        if not comment:
            return jsonify({"error": "Comment not found"}), 404
        
        # Check if user already reacted to this comment
        existing_reaction = ForumReaction.query.filter_by(user_id=user.id, comment_id=comment_id).first()
        if existing_reaction:
            # If the same reaction, remove it (toggle)
            if existing_reaction.reaction_type == reaction_type:
                db.session.delete(existing_reaction)
                if reaction_type == 'like':
                    comment.likes = max(0, comment.likes - 1)
                    # Remove points for likes if removed
                    if comment.author_id != user.id:  # Don't remove points for self-likes
                        comment_author = User.query.get(comment.author_id)
                        comment_author.points = max(0, comment_author.points - 1)
                else:
                    comment.dislikes = max(0, comment.dislikes - 1)
            else:
                # If different reaction, update it
                old_type = existing_reaction.reaction_type
                existing_reaction.reaction_type = reaction_type
                if old_type == 'like':
                    comment.likes = max(0, comment.likes - 1)
                    comment.dislikes += 1
                    
                    # Handle points transfer for like -> dislike
                    if comment.author_id != user.id:  # Don't adjust points for self-reactions
                        comment_author = User.query.get(comment.author_id)
                        comment_author.points = max(0, comment_author.points - 1)  # Remove like point
                else:
                    comment.dislikes = max(0, comment.dislikes - 1)
                    comment.likes += 1
                    
                    # Handle points transfer for dislike -> like
                    if comment.author_id != user.id:  # Don't adjust points for self-reactions
                        comment_author = User.query.get(comment.author_id)
                        comment_author.points += 1  # Add like point
        else:
            # New reaction
            new_reaction = ForumReaction(
                user_id=user.id,
                comment_id=comment_id,
                reaction_type=reaction_type
            )
            db.session.add(new_reaction)
            
            if reaction_type == 'like':
                comment.likes += 1
                # Award point to comment author for getting a like
                if comment.author_id != user.id:  # Don't award points for self-likes
                    comment_author = User.query.get(comment.author_id)
                    comment_author.points += 1
                    
                    # Level up if points threshold reached
                    if comment_author.points >= comment_author.level * 100:
                        comment_author.level += 1
            else:
                comment.dislikes += 1
        
        db.session.commit()
        
        # Get the post to return updated data
        post = ForumPost.query.get(comment.post_id)
        
        return jsonify({
            "success": True,
            "post": post.to_dict()
        })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create tables if they don't exist
    app.run(debug=True) 