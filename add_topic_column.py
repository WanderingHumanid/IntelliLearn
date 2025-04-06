# Script to add topic column to forum_posts table
import sqlite3
import os

def add_topic_column():
    try:
        # Get the database path
        db_path = 'instance/app.db'
        
        # Check if the database file exists
        if not os.path.exists(db_path):
            print(f"Database file not found at {db_path}")
            return
        
        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='forum_posts'")
        if not cursor.fetchone():
            print("Table forum_posts does not exist")
            conn.close()
            return
        
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
    add_topic_column() 