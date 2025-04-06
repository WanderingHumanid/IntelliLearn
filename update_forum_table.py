# Script to add topic column to forum_posts table
from app import app, db
from models import ForumPost
import sqlite3
import os

def add_topic_column():
    try:
        with app.app_context():
            # First, check if the column exists in the model
            # If it doesn't exist in the database, SQLAlchemy will add it
            post = ForumPost.query.first()
            if hasattr(post, 'topic'):
                print("Topic column already exists in the model.")
            else:
                print("Topic column doesn't exist in the model. Make sure to update models.py.")

            # Just to be sure, also try to add it directly via SQLite
            try:
                db.engine.execute('ALTER TABLE forum_posts ADD COLUMN topic VARCHAR(50)')
                print("Successfully added topic column to forum_posts table with SQLAlchemy.")
            except Exception as e:
                if 'duplicate column name' in str(e).lower():
                    print("Column already exists in the database.")
                else:
                    print(f"SQLAlchemy error: {e}")
                    
                    # Try using direct SQLite connection as a fallback
                    try:
                        # Get the database path
                        db_path = os.path.join(app.instance_path, 'app.db')
                        
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
                            print("Added 'topic' column to forum_posts table using direct SQLite connection.")
                        else:
                            print("The 'topic' column already exists in the database.")
                            
                        conn.close()
                    except Exception as inner_e:
                        print(f"SQLite direct connection error: {inner_e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_topic_column() 