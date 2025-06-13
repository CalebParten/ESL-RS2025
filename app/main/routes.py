from datetime import datetime
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.main import bp
from app.models import QuizAssignment, QuizAttempt, User, Quiz, Question, QuestionOption
from app.main.quiz_gen_langgraph import generate_quiz_from_text, generate_quiz_from_image
from app import db

@bp.route('/')
@bp.route('/index')
def index():
    return render_template('main/index.html', title='ESL Quiz Platform')

@bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('main/dashboard.html', title='Dashboard')

@bp.route('/manage_students', methods=['GET', 'POST'])
@login_required
def manage_students():
    if not current_user.is_instructor():
        flash('Access denied.')
        return redirect(url_for('main.dashboard'))

    students = User.query.filter_by(role='student').all()

    if request.method == 'POST':
        # Update student levels
        for student in students:
            new_level = request.form.get(f'level_{student.id}')
            if new_level and new_level != student.grade_level:
                student.grade_level = new_level
        db.session.commit()
        flash('Student levels updated successfully.')
        return redirect(url_for('main.manage_students'))

    return render_template('main/manage_students.html', title='Manage Students', students=students)

@bp.route('/remove_student/<int:user_id>', methods=['POST'])
@login_required
def remove_student(user_id):
    if not current_user.is_instructor():
        flash('Access denied.')
        return redirect(url_for('main.dashboard'))

    student = User.query.get_or_404(user_id)
    if student.role != 'student':
        flash('Cannot delete non-student user.')
        return redirect(url_for('main.manage_students'))

    db.session.delete(student)
    db.session.commit()
    flash(f'Student {student.name} removed successfully.')
    return redirect(url_for('main.manage_students'))

@bp.route('/generate_quiz', methods=['POST'])
@login_required
def generate_quiz():
    if not current_user.is_instructor():
        flash('Access denied.')
        return redirect(url_for('main.dashboard'))

    quiz_type = request.form.get('quiz_type')
    difficulty = request.form.get('difficulty_level')
    title = request.form.get('title')
    description = request.form.get('description', '')

    if not title or not quiz_type or not difficulty:
        flash('Missing required fields.')
        return redirect(url_for('main.dashboard'))

    if 'text' in request.files and request.files['text'].filename:
        raw_text = request.files['text'].read().decode('utf-8')
        generated = generate_quiz_from_text(raw_text)
        source_content = raw_text
    elif 'image' in request.files and request.files['image'].filename:
        image_bytes = request.files['image'].read()
        generated = generate_quiz_from_image(image_bytes)
        source_content = '[image]'
    else:
        flash('No valid input file provided.')
        return redirect(url_for('main.dashboard'))

    quiz = Quiz(
        title=title,
        description=description,
        quiz_type=quiz_type,
        source_content=source_content,
        difficulty_level=difficulty,
        creator=current_user
    )
    db.session.add(quiz)
    db.session.commit()

    for q in generated.get('questions', []):
        question = Question(
            question_text=q['question'],
            correct_answer=q['correct_answer'],
            explanation=q.get('explanation', ''),
            quiz=quiz
        )
        db.session.add(question)
        db.session.commit()

        for option in q['options']:
            db.session.add(QuestionOption(
                question=question,
                option_text=option,
                is_correct=(option == q['correct_answer'])
            ))

    db.session.commit()
    flash(f'Quiz "{quiz.title}" created successfully.')
    return redirect(url_for('main.dashboard'))

@bp.route('/create_quiz', methods=['GET', 'POST'])
@login_required
def create_quiz():
    if not current_user.is_instructor():
        flash('Access denied.')
        return redirect(url_for('main.dashboard'))
    return render_template('main/create_quiz.html', title='Create New Quiz')


@bp.route('/my_quizzes')
@login_required
def my_quizzes():
    if not current_user.is_instructor():
        flash('Access denied.')
        return redirect(url_for('main.dashboard'))

    quizzes = current_user.created_quizzes.order_by(Quiz.created_at.desc()).all()
    return render_template('main/my_quizzes.html', title='My Quizzes', quizzes=quizzes)

@bp.route('/assign_quiz', methods=['GET', 'POST'])
@login_required
def assign_quiz():
    if not current_user.is_instructor():
        flash('Access denied.')
        return redirect(url_for('main.dashboard'))

    quizzes = current_user.created_quizzes.all()
    students = User.query.filter_by(role='student').order_by(User.name).all()

    if request.method == 'POST':
        quiz_id = request.form.get('quiz_id')
        due_date = request.form.get('due_date')

        selected_students = request.form.getlist('students')

        if not quiz_id or not selected_students:
            flash('Please select a quiz and at least one student.')
            return redirect(url_for('main.assign_quiz'))

        for student_id in selected_students:
            existing = QuizAssignment.query.filter_by(
                quiz_id=quiz_id,
                student_id=student_id,
                is_active=True
            ).first()

            if existing:
                continue 
            
            assignment = QuizAssignment(
                quiz_id=quiz_id,
                student_id=student_id,
                instructor_id=current_user.id,
                due_date=datetime.strptime(due_date, '%Y-%m-%d') if due_date else None
            )
            db.session.add(assignment)

        db.session.commit()
        flash('Quiz assigned successfully.')
        return redirect(url_for('main.dashboard'))

    return render_template('main/assign_quiz.html', title='Assign Quiz', quizzes=quizzes, students=students)

@bp.route('/my_assignments')
@login_required
def my_assignments():
    if current_user.is_instructor():
        assignments = QuizAssignment.query.filter_by(instructor_id=current_user.id).all()
    else:
        assignments = QuizAssignment.query.filter_by(student_id=current_user.id, is_active=True).all()

    enriched_assignments = []
    for a in assignments:
        attempt = QuizAttempt.query.filter_by(quiz_id=a.quiz_id, student_id=a.student_id).first()
        status = "Completed" if attempt and attempt.is_completed else "Not Started"
        enriched_assignments.append({
            'assignment': a,
            'quiz': a.quiz,
            'status': status,
            'due': a.due_date.strftime('%Y-%m-%d') if a.due_date else "No due date"
        })

    return render_template(
        'main/my_assignments.html',
        title='My Assignments',
        assignments=enriched_assignments
    )


@bp.route('/take_quiz/<int:assignment_id>')
@login_required
def take_quiz(assignment_id):
    assignment = QuizAssignment.query.get_or_404(assignment_id)

    if assignment.student_id != current_user.id:
        flash('Access denied.')
        return redirect(url_for('main.dashboard'))

    # Redirect to the quiz-taking page (not yet implemented)
    return redirect(url_for('main.start_quiz', quiz_id=assignment.quiz_id))

@bp.route('/view_assignments')
@login_required
def view_assignments():
    if not current_user.is_instructor():
        flash('Access denied.')
        return redirect(url_for('main.dashboard'))

    assignments = QuizAssignment.query.filter_by(instructor_id=current_user.id).all()
    return render_template('main/view_assignments.html', title="Assigned Quizzes", assignments=assignments)

@bp.route('/review_attempt/<int:attempt_id>')
@login_required
def review_attempt(attempt_id):
    attempt = QuizAttempt.query.get_or_404(attempt_id)

    if current_user.role == 'student' and attempt.student_id != current_user.id:
        flash('Access denied.')
        return redirect(url_for('main.dashboard'))

    if current_user.role == 'instructor' and attempt.quiz.creator_id != current_user.id:
        flash('Access denied.')
        return redirect(url_for('main.dashboard'))

    quiz = attempt.quiz
    student = attempt.student
    questions = quiz.questions

    # Build response set (you can extend this as needed)
    response_data = []
    for question in questions:
        selected = attempt.answers.get(str(question.id)) if attempt.answers else None
        is_correct = selected == question.correct_answer
        response_data.append({
            'question': question.question_text,
            'selected': selected,
            'correct': question.correct_answer,
            'is_correct': is_correct,
            'explanation': question.explanation
        })

    return render_template(
        'main/review_attempt.html',
        title='Review Quiz Attempt',
        quiz=quiz,
        student=student,
        responses=response_data
    )

