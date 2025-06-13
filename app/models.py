from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import LargeBinary
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='student')  # 'student' or 'instructor'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Student-specific fields
    grade_level = db.Column(db.String(20))  # beginner, intermediate, advanced
    
    # Relationships
    created_quizzes = db.relationship('Quiz', backref='creator', lazy='dynamic', cascade='all, delete-orphan')
    quiz_attempts = db.relationship('QuizAttempt', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.name}>'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_instructor(self):
        return self.role == 'instructor'
    
    def is_student(self):
        return self.role == 'student'

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    quiz_type = db.Column(db.String(50))
    source_content = db.Column(db.Text)
    source_image_path = db.Column(db.String(255))
    source_mime = db.Column(db.String(50))
    difficulty_level = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Foreign Keys
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    questions = db.relationship('Question', backref='quiz', lazy='dynamic', cascade='all, delete-orphan')
    attempts = db.relationship('QuizAttempt', backref='quiz', lazy='dynamic')
    assignments = db.relationship('QuizAssignment', backref='quiz', lazy='dynamic')
    
    def __repr__(self):
        return f'<Quiz {self.title}>'

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), default='multiple_choice')
    correct_answer = db.Column(db.String(500))
    explanation = db.Column(db.Text)
    
    # Foreign Keys
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    
    # Relationships
    options = db.relationship('QuestionOption', backref='question', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Question {self.id}>'

class QuestionOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    option_text = db.Column(db.String(500), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    
    # Foreign Keys
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    
    def __repr__(self):
        return f'<Option {self.option_text[:50]}>'

class QuizAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Float)
    total_questions = db.Column(db.Integer)
    time_started = db.Column(db.DateTime, default=datetime.utcnow)
    time_completed = db.Column(db.DateTime)
    is_completed = db.Column(db.Boolean, default=False)
    
    # Foreign Keys
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    
    # Relationships
    answers = db.relationship('StudentAnswer', backref='attempt', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<QuizAttempt {self.id}>'

class StudentAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    selected_answer = db.Column(db.String(500))
    is_correct = db.Column(db.Boolean)
    time_answered = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Keys
    attempt_id = db.Column(db.Integer, db.ForeignKey('quiz_attempt.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    
    def __repr__(self):
        return f'<Answer {self.id}>'

class QuizAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    student = db.relationship('User', foreign_keys=[student_id])
    instructor = db.relationship('User', foreign_keys=[instructor_id])
    
    def __repr__(self):
        return f'<Assignment {self.id}>'
