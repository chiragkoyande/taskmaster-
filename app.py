import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from flask_migrate import Migrate

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create a base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with the base class
db = SQLAlchemy(model_class=Base)

# Create the Flask application
app = Flask(__name__)

# Set the secret key from environment
app.secret_key = os.environ.get("SESSION_SECRET", "taskito_secret_key")

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///taskito.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the database with the app
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Import routes after initializing everything to avoid circular imports
with app.app_context():
    # Import models to ensure they're registered with SQLAlchemy
    from models import User, Task, Category, SubTask, Achievement
    
    # Create all tables if they don't exist
    db.create_all()
    
    # Import routes
    from routes import *
    
    # Register user loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
