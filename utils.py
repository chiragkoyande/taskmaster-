from datetime import datetime, timedelta
from models import User, Task, Category, SubTask, Achievement
from app import db

def calculate_achievements(user_id):
    """Calculate and award achievements based on task completion."""
    user = User.query.get(user_id)
    if not user:
        return []
    
    new_achievements = []
    
    # Get completed tasks count
    completed_tasks_count = Task.query.filter_by(
        user_id=user_id, 
        is_completed=True
    ).count()
    
    # Achievement definitions with thresholds
    achievement_definitions = [
        {
            'name': 'Task Beginner',
            'description': 'Complete your first task',
            'threshold': 1,
            'trophy_level': 1
        },
        {
            'name': 'Task Enthusiast',
            'description': 'Complete 10 tasks',
            'threshold': 10,
            'trophy_level': 1
        },
        {
            'name': 'Task Master',
            'description': 'Complete 25 tasks',
            'threshold': 25,
            'trophy_level': 2
        },
        {
            'name': 'Task Guru',
            'description': 'Complete 50 tasks',
            'threshold': 50,
            'trophy_level': 2
        },
        {
            'name': 'Task Legend',
            'description': 'Complete 100 tasks',
            'threshold': 100,
            'trophy_level': 3
        }
    ]
    
    # Check each achievement definition
    for achievement_def in achievement_definitions:
        # Skip if already earned
        existing_achievement = Achievement.query.filter_by(
            user_id=user_id, 
            name=achievement_def['name']
        ).first()
        
        if existing_achievement:
            continue
            
        # Award achievement if threshold met
        if completed_tasks_count >= achievement_def['threshold']:
            achievement = Achievement(
                name=achievement_def['name'],
                description=achievement_def['description'],
                trophy_level=achievement_def['trophy_level'],
                user_id=user_id
            )
            db.session.add(achievement)
            new_achievements.append(achievement)
    
    # Check for priority achievements
    high_priority_completed = Task.query.filter_by(
        user_id=user_id, 
        is_completed=True,
        priority=3
    ).count()
    
    priority_achievements = [
        {
            'name': 'Priority Handler',
            'description': 'Complete 5 high-priority tasks',
            'threshold': 5,
            'trophy_level': 1
        },
        {
            'name': 'Priority Master',
            'description': 'Complete 20 high-priority tasks',
            'threshold': 20,
            'trophy_level': 2
        }
    ]
    
    for achievement_def in priority_achievements:
        existing_achievement = Achievement.query.filter_by(
            user_id=user_id, 
            name=achievement_def['name']
        ).first()
        
        if existing_achievement:
            continue
            
        if high_priority_completed >= achievement_def['threshold']:
            achievement = Achievement(
                name=achievement_def['name'],
                description=achievement_def['description'],
                trophy_level=achievement_def['trophy_level'],
                user_id=user_id
            )
            db.session.add(achievement)
            new_achievements.append(achievement)
    
    # Check for streak achievements (consecutive days with completed tasks)
    # Implementation of streak achievement would go here
    
    db.session.commit()
    return new_achievements

def get_task_progress_stats(user_id):
    """Get statistics about task progress for the dashboard."""
    # Count tasks by status
    not_started = Task.query.filter_by(
        user_id=user_id, 
        is_completed=False,
        status=0
    ).count()
    
    in_progress = Task.query.filter_by(
        user_id=user_id, 
        is_completed=False,
        status=1
    ).count()
    
    completed = Task.query.filter_by(
        user_id=user_id, 
        is_completed=True
    ).count()
    
    # Calculate percentage distribution
    total = not_started + in_progress + completed
    
    if total > 0:
        not_started_percent = (not_started / total) * 100
        in_progress_percent = (in_progress / total) * 100
        completed_percent = (completed / total) * 100
    else:
        not_started_percent = 0
        in_progress_percent = 0
        completed_percent = 0
    
    # Return stats
    return {
        'not_started': not_started,
        'in_progress': in_progress,
        'completed': completed,
        'total': total,
        'not_started_percent': not_started_percent,
        'in_progress_percent': in_progress_percent,
        'completed_percent': completed_percent
    }

def get_task_completion_stats(user_id):
    """Get statistics about task completion over time."""
    # Get tasks completed in the last 7 days
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    
    completed_tasks = Task.query.filter(
        Task.user_id == user_id,
        Task.is_completed == True,
        Task.completed_at >= seven_days_ago
    ).all()
    
    # Group by day
    daily_completion = {}
    for i in range(7):
        day = now - timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        daily_completion[day_str] = 0
    
    for task in completed_tasks:
        day_str = task.completed_at.strftime('%Y-%m-%d')
        if day_str in daily_completion:
            daily_completion[day_str] += 1
    
    # Format for chart.js
    labels = list(daily_completion.keys())
    labels.reverse()  # Show oldest first
    
    data = list(daily_completion.values())
    data.reverse()  # Match labels order
    
    return {
        'labels': labels,
        'data': data
    }
