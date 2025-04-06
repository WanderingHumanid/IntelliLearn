from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
import sqlalchemy as sa
from alembic import op
import sqlite3

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///intellilearn.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database with the app
db = SQLAlchemy(app)

# Define the ChatMessage model here to avoid importing dependencies
class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_user = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, nullable=True)
    conversation_id = db.Column(db.String(50), nullable=False)
    message_type = db.Column(db.String(20), default='text')
    has_file = db.Column(db.Boolean, default=False)
    file_path = db.Column(db.String(255), nullable=True)
    file_type = db.Column(db.String(50), nullable=True)
    file_name = db.Column(db.String(255), nullable=True)

# Run this script to create the ChatMessage table
with app.app_context():
    # Create uploads directory if it doesn't exist
    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
        print(f"Created uploads directory at {uploads_dir}")
    
    # Create tables
    db.create_all()
    print("Database migration complete. The ChatMessage table has been created/updated with new fields.")

# Add topic field to forum posts
from app import app, db
from models import ForumPost

def migrate_add_topic_field():
    with app.app_context():
        try:
            # Get the database path
            db_path = 'instance/app.db'
            
            # Connect to the SQLite database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if column exists
            cursor.execute("PRAGMA table_info(forum_posts)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'topic' not in columns:
                # Add the topic column if it doesn't exist
                cursor.execute("ALTER TABLE forum_posts ADD COLUMN topic VARCHAR(50)")
                conn.commit()
                print("Added 'topic' column to forum_posts table.")
            else:
                print("The 'topic' column already exists in forum_posts table.")
                
            conn.close()
        except Exception as e:
            print(f"Error during migration: {e}")

if __name__ == "__main__":
    migrate_add_topic_field() 