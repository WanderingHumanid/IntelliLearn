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
    
    # Relationships
    roadmaps = db.relationship('Roadmap', backref='creator', lazy=True)
    forum_posts = db.relationship('ForumPost', backref='author', lazy=True)
    forum_comments = db.relationship('ForumComment', backref='author', lazy=True)
    
    def get_completed_topics(self):
        if self.completed_topics:
            return json.loads(self.completed_topics)
        return []
    
    def set_completed_topics(self, topics):
        self.completed_topics = json.dumps(topics)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'points': self.points,
            'level': self.level,
            'streak': self.streak,
            'completed_topics': self.get_completed_topics(),
            'is_premium': self.is_premium,
            'premium_until': self.premium_until.isoformat() if self.premium_until else None
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
    
    # Relationships
    comments = db.relationship('ForumComment', backref='post', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'author': self.author.username,
            'author_id': self.author_id,
            'created_at': self.created_at.isoformat(),
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
    
    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'author': self.author.username,
            'author_id': self.author_id,
            'post_id': self.post_id,
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