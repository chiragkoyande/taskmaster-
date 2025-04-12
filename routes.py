from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from datetime import datetime, date, time, timedelta
import json

from app import app, db
from models import User, Task, Category, SubTask, Achievement
from forms import LoginForm, RegistrationForm, TaskForm, CategoryForm
from utils import calculate_achievements, get_task_progress_stats, get_task_completion_stats

@app.route('/')
@app.route('/index')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password', 'danger')
            return redirect(url_for('login'))
        
        login_user(user)
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('dashboard')
        return redirect(next_page)
    
    return render_template('login.html', title='Sign In', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        
        db.session.add(user)
        
        # Create default categories for new user
        default_categories = [
            {"name": "Work", "is_default": True},
            {"name": "Personal", "is_default": True}
        ]
        
        for cat in default_categories:
            category = Category(name=cat["name"], is_default=cat["is_default"], user=user)
            db.session.add(category)
        
        db.session.commit()
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', title='Register', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get active tasks (non-completed)
    active_tasks = Task.query.filter_by(
        user_id=current_user.id, 
        is_completed=False
    ).order_by(Task.due_date, Task.due_time).all()
    
    # Get tasks due today
    today = date.today()
    today_tasks = [task for task in active_tasks if task.due_date == today]
    
    # Get upcoming tasks (not including today)
    upcoming_tasks = [task for task in active_tasks if task.due_date > today]
    
    # Get overdue tasks
    overdue_tasks = [task for task in active_tasks if task.due_date < today]
    
    # Get categories for filtering
    categories = Category.query.filter_by(user_id=current_user.id).all()
    
    # Get progress stats
    progress_stats = get_task_progress_stats(current_user.id)
    
    # Get completion stats
    completion_stats = get_task_completion_stats(current_user.id)
    
    # Prepare tasks data for notifications
    tasks_data = []
    for task in today_tasks + upcoming_tasks + overdue_tasks:
        task_data = {
            'id': task.id,
            'title': task.title,
            'due_date': task.due_date.isoformat(),
            'due_time': task.due_time.strftime('%H:%M'),
            'completed': task.is_completed
        }
        tasks_data.append(task_data)
    
    return render_template(
        'dashboard.html', 
        title='Dashboard',
        today_tasks=today_tasks,
        upcoming_tasks=upcoming_tasks,
        overdue_tasks=overdue_tasks,
        categories=categories,
        progress_stats=progress_stats,
        completion_stats=completion_stats,
        tasks_data=json.dumps(tasks_data)
    )

@app.route('/task/new', methods=['GET', 'POST'])
@login_required
def new_task():
    form = TaskForm()
    
    # Load categories for the current user
    form.category_id.choices = [
        (c.id, c.name) for c in Category.query.filter_by(user_id=current_user.id).all()
    ]
    
    if form.validate_on_submit():
        task = Task(
            title=form.title.data,
            description=form.description.data,
            due_date=form.due_date.data,
            due_time=form.due_time.data,
            priority=form.priority.data,
            category_id=form.category_id.data,
            is_recurring=form.is_recurring.data,
            track_progress=form.track_progress.data,
            user_id=current_user.id
        )
        db.session.add(task)
        db.session.commit()
        
        # Add subtasks if there are any
        if form.subtasks.data:
            for subtask_form in form.subtasks:
                # Check if the title is not empty
                if subtask_form.title.data and subtask_form.title.data.strip():
                    subtask = SubTask(
                        title=subtask_form.title.data,
                        is_completed=subtask_form.is_completed.data,
                        task_id=task.id
                    )
                    db.session.add(subtask)
            
            db.session.commit()
            
            # Update task progress based on subtasks
            task.update_progress_from_subtasks()
            db.session.commit()
        
        flash('Task created successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('task_form.html', title='New Task', form=form, task=None)

@app.route('/task/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    form = TaskForm(obj=task)
    
    # Load categories for the current user
    form.category_id.choices = [
        (c.id, c.name) for c in Category.query.filter_by(user_id=current_user.id).all()
    ]
    
    # Pre-populate subtasks
    if request.method == 'GET':
        # Clear any existing entries
        while len(form.subtasks) > 0:
            form.subtasks.pop_entry()
            
        # Add the task's subtasks
        for subtask in task.subtasks:
            form.subtasks.append_entry({
                'title': subtask.title,
                'is_completed': subtask.is_completed
            })
    
    if form.validate_on_submit():
        task.title = form.title.data
        task.description = form.description.data
        task.due_date = form.due_date.data
        task.due_time = form.due_time.data
        task.priority = form.priority.data
        task.category_id = form.category_id.data
        task.is_recurring = form.is_recurring.data
        task.track_progress = form.track_progress.data
        
        # Delete existing subtasks
        SubTask.query.filter_by(task_id=task.id).delete()
        
        # Add new subtasks if there are any
        if form.subtasks.data:
            for subtask_form in form.subtasks:
                # Check if the title is not empty
                if subtask_form.title.data and subtask_form.title.data.strip():
                    subtask = SubTask(
                        title=subtask_form.title.data,
                        is_completed=subtask_form.is_completed.data,
                        task_id=task.id
                    )
                    db.session.add(subtask)
            
            db.session.commit()
            
            # Update task progress based on subtasks
            task.update_progress_from_subtasks()
            db.session.commit()
        else:
            # If no subtasks, set progress based on completion status
            if task.is_completed:
                task.progress = 100
            else:
                task.progress = 0
            db.session.commit()
        
        flash('Task updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('task_form.html', title='Edit Task', form=form, task=task)

@app.route('/task/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/task/<int:task_id>/complete', methods=['POST'])
@login_required
def complete_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    
    # If the task is recurring, create a new task for tomorrow
    if task.is_recurring:
        new_task = Task(
            title=task.title,
            description=task.description,
            due_date=date.today() + timedelta(days=1),
            due_time=task.due_time,
            priority=task.priority,
            category_id=task.category_id,
            is_recurring=True,
            track_progress=task.track_progress,
            user_id=current_user.id
        )
        db.session.add(new_task)
        
        # Copy subtasks
        for subtask in task.subtasks:
            new_subtask = SubTask(
                title=subtask.title,
                is_completed=False,
                task_id=new_task.id
            )
            db.session.add(new_subtask)
    
    # Mark the task as completed
    task.is_completed = True
    task.status = 2  # Completed
    task.progress = 100
    task.completed_at = datetime.utcnow()
    
    # Mark all subtasks as completed
    for subtask in task.subtasks:
        subtask.is_completed = True
    
    db.session.commit()
    
    # Check for achievements
    new_achievements = calculate_achievements(current_user.id)
    if new_achievements:
        achievement_names = [a.name for a in new_achievements]
        flash(f'Congratulations! You earned new achievements: {", ".join(achievement_names)}', 'success')
    
    flash('Task completed successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/task/<int:task_id>/progress', methods=['POST'])
@login_required
def update_task_progress(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    
    progress = request.json.get('progress', 0)
    task.progress = progress
    
    # Update task status based on progress
    if progress == 0:
        task.status = 0  # Not Started
    elif progress < 100:
        task.status = 1  # In Progress
    else:
        task.status = 2  # Completed
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/task/<int:task_id>/subtask/<int:subtask_id>/toggle', methods=['POST'])
@login_required
def toggle_subtask(task_id, subtask_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    subtask = SubTask.query.filter_by(id=subtask_id, task_id=task.id).first_or_404()
    
    # Toggle subtask completion
    subtask.is_completed = not subtask.is_completed
    db.session.commit()
    
    # Update task progress
    task.update_progress_from_subtasks()
    db.session.commit()
    
    return jsonify({
        'subtask_completed': subtask.is_completed,
        'task_progress': task.progress
    })

@app.route('/category/new', methods=['GET', 'POST'])
@login_required
def new_category():
    form = CategoryForm()
    
    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            user_id=current_user.id,
            is_default=False
        )
        db.session.add(category)
        db.session.commit()
        flash('Category created successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('category_form.html', title='New Category', form=form)

@app.route('/achievements')
@login_required
def achievements():
    user_achievements = Achievement.query.filter_by(user_id=current_user.id).order_by(
        Achievement.trophy_level.desc(), Achievement.earned_at.desc()
    ).all()
    
    # Get stats for achievements page
    completed_tasks_count = Task.query.filter_by(
        user_id=current_user.id, 
        is_completed=True
    ).count()
    
    high_priority_completed = Task.query.filter_by(
        user_id=current_user.id, 
        is_completed=True,
        priority=3
    ).count()
    
    # Calculate streak (consecutive days with completed tasks)
    streak = 0
    # Implementation of streak calculation would go here
    
    return render_template(
        'achievements.html', 
        title='Achievements',
        achievements=user_achievements,
        completed_tasks=completed_tasks_count,
        high_priority_completed=high_priority_completed,
        streak=streak,
        Achievement=Achievement
    )

@app.route('/progress')
@login_required
def progress():
    # Get tracking tasks
    tracking_tasks = Task.query.filter_by(
        user_id=current_user.id,
        track_progress=True,
        is_completed=False
    ).all()
    
    # Get recently completed tasks
    completed_tasks = Task.query.filter_by(
        user_id=current_user.id,
        is_completed=True
    ).order_by(Task.completed_at.desc()).limit(5).all()
    
    # Get progress stats by category
    categories = Category.query.filter_by(user_id=current_user.id).all()
    category_stats = []
    
    for category in categories:
        total_tasks = Task.query.filter_by(
            user_id=current_user.id,
            category_id=category.id
        ).count()
        
        completed_count = Task.query.filter_by(
            user_id=current_user.id,
            category_id=category.id,
            is_completed=True
        ).count()
        
        if total_tasks > 0:
            completion_rate = (completed_count / total_tasks) * 100
        else:
            completion_rate = 0
            
        category_stats.append({
            'name': category.name,
            'total': total_tasks,
            'completed': completed_count,
            'completion_rate': completion_rate
        })
    
    return render_template(
        'progress.html',
        title='Progress Tracking',
        tracking_tasks=tracking_tasks,
        completed_tasks=completed_tasks,
        category_stats=category_stats
    )

@app.route('/profile')
@login_required
def profile():
    tasks_count = Task.query.filter_by(user_id=current_user.id).count()
    completed_count = Task.query.filter_by(
        user_id=current_user.id, 
        is_completed=True
    ).count()
    
    achievements_count = Achievement.query.filter_by(user_id=current_user.id).count()
    categories_count = Category.query.filter_by(user_id=current_user.id).count()
    
    # Get recent achievements for display
    recent_achievements = Achievement.query.filter_by(user_id=current_user.id).order_by(Achievement.earned_at.desc()).limit(3).all()
    
    return render_template(
        'profile.html',
        title='Profile',
        tasks_count=tasks_count,
        completed_count=completed_count,
        achievements_count=achievements_count,
        categories_count=categories_count,
        Achievement=Achievement,
        recent_achievements=recent_achievements
    )

@app.route('/filter_tasks', methods=['POST'])
@login_required
def filter_tasks():
    # Get filter parameters
    category_id = request.json.get('category_id')
    priority = request.json.get('priority')
    status = request.json.get('status')
    
    # Base query
    query = Task.query.filter_by(user_id=current_user.id, is_completed=False)
    
    # Apply filters
    if category_id and category_id != 'all':
        query = query.filter_by(category_id=int(category_id))
    
    if priority and priority != 'all':
        query = query.filter_by(priority=int(priority))
    
    if status and status != 'all':
        if status == 'upcoming':
            query = query.filter(Task.due_date > date.today())
        elif status == 'today':
            query = query.filter(Task.due_date == date.today())
        elif status == 'overdue':
            query = query.filter(Task.due_date < date.today())
    
    # Get filtered tasks
    tasks = query.order_by(Task.due_date, Task.due_time).all()
    
    # Convert tasks to JSON
    tasks_json = []
    for task in tasks:
        tasks_json.append({
            'id': task.id,
            'title': task.title,
            'due_date': task.due_date.strftime('%Y-%m-%d'),
            'due_time': task.due_time.strftime('%H:%M'),
            'priority': task.priority,
            'progress': task.progress,
            'category_id': task.category_id,
            'category_name': task.category.name
        })
    
    return jsonify(tasks_json)
