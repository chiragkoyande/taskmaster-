from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Define User model with UserMixin for Flask-Login compatibility
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Define relationships
    tasks = db.relationship('Task', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    categories = db.relationship('Category', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    achievements = db.relationship('Achievement', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

# Define Category model for task categorization
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    
    # Define relationship
    tasks = db.relationship('Task', backref='category', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Category {self.name}>'

# Define Task model
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    due_time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Priority levels: 1 (Low), 2 (Medium), 3 (High)
    priority = db.Column(db.Integer, nullable=False)
    
    # Task status: 0 (Not Started), 1 (In Progress), 2 (Completed)
    status = db.Column(db.Integer, default=0)
    
    # Progress tracking (0-100%)
    progress = db.Column(db.Integer, default=0)
    
    # Track if a task has been selected for progress tracking
    track_progress = db.Column(db.Boolean, default=False)
    
    # For recurring tasks
    is_recurring = db.Column(db.Boolean, default=False)
    
    # For completed tasks (to remove from dashboard but keep data)
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    
    # Define relationship
    subtasks = db.relationship('SubTask', backref='task', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Task {self.title}>'
    
    def update_progress_from_subtasks(self):
        """Update task progress based on completed subtasks."""
        subtasks_count = self.subtasks.count()
        if subtasks_count > 0:
            completed_count = self.subtasks.filter_by(is_completed=True).count()
            self.progress = int((completed_count / subtasks_count) * 100)
        else:
            # If no subtasks, progress is based on task status
            if self.status == 0:  # Not Started
                self.progress = 0
            elif self.status == 1:  # In Progress
                self.progress = 50
            elif self.status == 2:  # Completed
                self.progress = 100

# Define SubTask model
class SubTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    
    def __repr__(self):
        return f'<SubTask {self.title}>'

# Define Achievement model for user rewards
class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    trophy_level = db.Column(db.Integer, default=1)  # 1 (Bronze), 2 (Silver), 3 (Gold)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<Achievement {self.name}>'
