from app import app, db
from models import User, ForumPost, ForumComment

with app.app_context():
    print("Dropping all tables...")
    db.drop_all()
    print("Creating all tables...")
    db.create_all()
    print("Database recreated successfully!") 