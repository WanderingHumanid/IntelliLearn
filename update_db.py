from app import app, db
from models import ChatMessage, User, ForumPost, ForumComment
from sqlalchemy import Column, Boolean, String, Text
import sqlalchemy as sa

def update_schema():
    """Update the database schema to add new columns to tables"""
    with app.app_context():
        # Create the points_awarded column if it doesn't exist in chat_messages
        inspector = sa.inspect(db.engine)
        
        # Check and update ChatMessage table
        chat_columns = [col['name'] for col in inspector.get_columns('chat_messages')]
        if 'points_awarded' not in chat_columns:
            print("Adding points_awarded column to chat_messages table...")
            conn = db.engine.connect()
            conn.execute(sa.text('ALTER TABLE chat_messages ADD COLUMN points_awarded BOOLEAN DEFAULT 0'))
            conn.commit()
            print("chat_messages table updated successfully!")
        else:
            print("The points_awarded column already exists in chat_messages.")
        
        # Check and update User table for educational details
        user_columns = [col['name'] for col in inspector.get_columns('users')]
        
        # Track if any changes were made
        user_updated = False
        
        # Add education_level column if it doesn't exist
        if 'education_level' not in user_columns:
            print("Adding education_level column to users table...")
            conn = db.engine.connect()
            conn.execute(sa.text('ALTER TABLE users ADD COLUMN education_level VARCHAR(100)'))
            conn.commit()
            user_updated = True
        
        # Add field_of_study column if it doesn't exist
        if 'field_of_study' not in user_columns:
            print("Adding field_of_study column to users table...")
            conn = db.engine.connect()
            conn.execute(sa.text('ALTER TABLE users ADD COLUMN field_of_study VARCHAR(100)'))
            conn.commit()
            user_updated = True
        
        # Add current_courses column if it doesn't exist
        if 'current_courses' not in user_columns:
            print("Adding current_courses column to users table...")
            conn = db.engine.connect()
            conn.execute(sa.text("ALTER TABLE users ADD COLUMN current_courses TEXT DEFAULT '[]'"))
            conn.commit()
            user_updated = True
        
        # Add learning_goals column if it doesn't exist
        if 'learning_goals' not in user_columns:
            print("Adding learning_goals column to users table...")
            conn = db.engine.connect()
            conn.execute(sa.text('ALTER TABLE users ADD COLUMN learning_goals TEXT'))
            conn.commit()
            user_updated = True
        
        # Add career_goals column if it doesn't exist
        if 'career_goals' not in user_columns:
            print("Adding career_goals column to users table...")
            conn = db.engine.connect()
            conn.execute(sa.text('ALTER TABLE users ADD COLUMN career_goals VARCHAR(200)'))
            conn.commit()
            user_updated = True
        
        # Add preferred_learning_style column if it doesn't exist
        if 'preferred_learning_style' not in user_columns:
            print("Adding preferred_learning_style column to users table...")
            conn = db.engine.connect()
            conn.execute(sa.text('ALTER TABLE users ADD COLUMN preferred_learning_style VARCHAR(50)'))
            conn.commit()
            user_updated = True
        
        if user_updated:
            print("Users table updated successfully!")
        else:
            print("All educational fields already exist in users table.")

def update_database():
    with app.app_context():
        try:
            # First check if the tables exist
            inspector = sa.inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'forum_posts' not in tables or 'forum_comments' not in tables or 'forum_reactions' not in tables:
                print("Some forum tables are missing. Creating all tables...")
                db.create_all()
                print("All tables have been created successfully.")
            else:
                # Tables exist, now check for the topic column
                try:
                    post = ForumPost.query.first()
                    print("Database schema appears to be up to date.")
                except Exception as e:
                    if 'no such column' in str(e).lower():
                        print("Schema mismatch detected. Attempting to add missing columns...")
                        # Add topic column using raw SQL
                        conn = db.engine.connect()
                        try:
                            conn.execute(sa.text('ALTER TABLE forum_posts ADD COLUMN topic VARCHAR(50)'))
                            conn.commit()
                            print("Added topic column to forum_posts table.")
                        except Exception as e:
                            if 'duplicate column name' in str(e).lower():
                                print("Topic column already exists.")
                            else:
                                print(f"Error adding topic column: {e}")
                    else:
                        print(f"Unexpected error: {e}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    update_schema()
    update_database() 