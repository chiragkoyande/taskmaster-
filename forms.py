from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField
from wtforms import DateField, TimeField, BooleanField, IntegerField, FieldList, FormField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from models import User

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', 
                                    validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please log in instead.')

class SubTaskForm(FlaskForm):
    title = StringField('Subtask Title', validators=[DataRequired()])
    is_completed = BooleanField('Completed')

class TaskForm(FlaskForm):
    title = StringField('Task Title', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[DataRequired()])
    due_date = DateField('Due Date', validators=[DataRequired()])
    due_time = TimeField('Due Time', validators=[DataRequired()])
    priority = SelectField('Priority', choices=[
        (3, 'High'), 
        (2, 'Medium'), 
        (1, 'Low')
    ], coerce=int, validators=[DataRequired()])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    is_recurring = BooleanField('Daily Recurring Task')
    track_progress = BooleanField('Track Progress for this Task')
    subtasks = FieldList(FormField(SubTaskForm), min_entries=0)
    add_subtask = SubmitField('Add Subtask')
    submit = SubmitField('Save Task')

class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=50)])
    submit = SubmitField('Create Category')
