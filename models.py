from flask_sqlalchemy import SQLAlchemy
import datetime
import json

db = SQLAlchemy()

# User model
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    points = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    streak = db.Column(db.Integer, default=0)
    completed_topics = db.Column(db.Text, default='[]')  # JSON string of completed topics
    is_premium = db.Column(db.Boolean, default=False)
    premium_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Educational details
    education_level = db.Column(db.String(100), nullable=True)  # e.g., High School, Bachelor's, Master's
    field_of_study = db.Column(db.String(100), nullable=True)  # e.g., Computer Science, Biology
    current_courses = db.Column(db.Text, default='[]')  # JSON string of current courses
    learning_goals = db.Column(db.Text, nullable=True)  # Learning objectives
    career_goals = db.Column(db.String(200), nullable=True)  # Career aspirations
    preferred_learning_style = db.Column(db.String(50), nullable=True)  # e.g., Visual, Auditory, Reading/Writing
    
    # Relationships
    roadmaps = db.relationship('Roadmap', backref='creator', lazy=True)
    forum_posts = db.relationship('ForumPost', backref='author', lazy=True)
    forum_comments = db.relationship('ForumComment', backref='author', lazy=True)
    chat_messages = db.relationship('ChatMessage', backref='user', lazy=True)
    
    def get_completed_topics(self):
        if self.completed_topics:
            return json.loads(self.completed_topics)
        return []
    
    def set_completed_topics(self, topics):
        self.completed_topics = json.dumps(topics)
    
    def get_current_courses(self):
        if self.current_courses:
            return json.loads(self.current_courses)
        return []
    
    def set_current_courses(self, courses):
        self.current_courses = json.dumps(courses)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'points': self.points,
            'level': self.level,
            'streak': self.streak,
            'completed_topics': self.get_completed_topics(),
            'is_premium': self.is_premium,
            'premium_until': self.premium_until.isoformat() if self.premium_until else None,
            'education_level': self.education_level,
            'field_of_study': self.field_of_study,
            'current_courses': self.get_current_courses(),
            'learning_goals': self.learning_goals,
            'career_goals': self.career_goals,
            'preferred_learning_style': self.preferred_learning_style
        }

# Chat Message model for maintaining chat history
class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_user = db.Column(db.Boolean, default=True)  # True if message from user, False if from AI
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    conversation_id = db.Column(db.String(50), nullable=False)  # Used to group messages by conversation
    message_type = db.Column(db.String(20), default='text')  # text, image, document, etc.
    has_file = db.Column(db.Boolean, default=False)  # Whether this message includes a file
    file_path = db.Column(db.String(255), nullable=True)  # Path to the uploaded file if any
    file_type = db.Column(db.String(50), nullable=True)  # MIME type of the file if any
    file_name = db.Column(db.String(255), nullable=True)  # Original name of the file if any
    points_awarded = db.Column(db.Boolean, default=False)  # Whether points were awarded for this message
    
    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'is_user': self.is_user,
            'created_at': self.created_at.isoformat(),
            'conversation_id': self.conversation_id,
            'message_type': self.message_type,
            'has_file': self.has_file,
            'file_name': self.file_name,
            'file_type': self.file_type
        }

# Roadmap model
class Roadmap(db.Model):
    __tablename__ = 'roadmaps'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=False)  # JSON string of roadmap content
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    completed_topics = db.Column(db.Text, default='[]')  # JSON string of completed topics
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def get_content(self):
        return json.loads(self.content)
    
    def set_content(self, content):
        self.content = json.dumps(content)
    
    def get_completed_topics(self):
        if self.completed_topics:
            return json.loads(self.completed_topics)
        return []
    
    def set_completed_topics(self, topics):
        self.completed_topics = json.dumps(topics)
    
    def to_dict(self):
        roadmap_content = self.get_content()
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'topics': roadmap_content.get('topics', []),
            'creator': self.creator.username,
            'creator_id': self.creator_id,
            'completed_topics': self.get_completed_topics(),
            'created_at': self.created_at.isoformat()
        }

# Forum post model
class ForumPost(db.Model):
    __tablename__ = 'forum_posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    has_image = db.Column(db.Boolean, default=False)
    image_path = db.Column(db.String(255), nullable=True)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    
    # Relationships
    comments = db.relationship('ForumComment', backref='post', lazy=True, cascade='all, delete-orphan')
    reactions = db.relationship('ForumReaction', backref='post', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'author': self.author.username,
            'author_id': self.author_id,
            'timestamp': self.created_at.timestamp(),
            'has_image': self.has_image,
            'image_path': self.image_path,
            'likes': self.likes,
            'dislikes': self.dislikes,
            'comments': [comment.to_dict() for comment in self.comments]
        }

# Forum comment model
class ForumComment(db.Model):
    __tablename__ = 'forum_comments'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_posts.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    has_image = db.Column(db.Boolean, default=False)
    image_path = db.Column(db.String(255), nullable=True)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    
    # Relationships
    reactions = db.relationship('ForumReaction', backref='comment', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'author': self.author.username,
            'author_id': self.author_id,
            'post_id': self.post_id,
            'timestamp': self.created_at.timestamp(),
            'has_image': self.has_image,
            'image_path': self.image_path,
            'likes': self.likes,
            'dislikes': self.dislikes
        }

# Forum reaction model (for likes/dislikes)
class ForumReaction(db.Model):
    __tablename__ = 'forum_reactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_posts.id'), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('forum_comments.id'), nullable=True)
    reaction_type = db.Column(db.String(10), nullable=False)  # 'like' or 'dislike'
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('reactions', lazy=True))
    
    __table_args__ = (
        db.CheckConstraint('(post_id IS NULL) != (comment_id IS NULL)', name='reaction_target_check'),
        db.UniqueConstraint('user_id', 'post_id', name='unique_post_reaction'),
        db.UniqueConstraint('user_id', 'comment_id', name='unique_comment_reaction'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'post_id': self.post_id,
            'comment_id': self.comment_id,
            'reaction_type': self.reaction_type,
            'created_at': self.created_at.isoformat()
        }

# Study Resource model
class StudyResource(db.Model):
    __tablename__ = 'study_resources'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    resource_type = db.Column(db.String(50), nullable=False)  # video, note, question, etc.
    content = db.Column(db.Text)  # URL or content text
    subject = db.Column(db.String(100))
    is_premium = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'resource_type': self.resource_type,
            'content': self.content,
            'subject': self.subject,
            'is_premium': self.is_premium,
            'created_at': self.created_at.isoformat()
        }

# Premium Feature model (tracks which premium features are available)
class PremiumFeature(db.Model):
    __tablename__ = 'premium_features'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    price = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'is_active': self.is_active
        } 