from datetime import datetime
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.main import bp
from app.main.save import saveImg
from app.models import QuizAssignment, QuizAttempt, StudentAnswer, User, Quiz, Question, QuestionOption
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

    source_content = None
    source_image_path = None
    source_mime = None

    if not title or not quiz_type or not difficulty:
        flash('Missing required fields.')
        return redirect(url_for('main.dashboard'))

    if 'text' in request.files and request.files['text'].filename:
        source_content = request.files['text'].read().decode('utf-8')
        generated = generate_quiz_from_text(source_content)
    elif 'image' in request.files and request.files['image'].filename:
        image_file = request.files['image']
        image_bytes = image_file.read()

        source_image_path, source_mime = saveImg(image_bytes, image_file.filename)
        
        generated = generate_quiz_from_image(image_bytes)

    else:
        flash('No valid input file provided.')
        return redirect(url_for('main.dashboard'))

    quiz = Quiz(
        title=title,
        description=description,
        quiz_type=quiz_type,
        source_content=source_content,
        source_image_path=source_image_path,
        difficulty_level=difficulty,
        creator=current_user,
        source_mime=source_mime
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

@bp.route('/start_quiz/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def start_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    # Check assignment exists
    assignment = QuizAssignment.query.filter_by(student_id=current_user.id, quiz_id=quiz_id, is_active=True).first()
    if not assignment:
        flash('You are not assigned to this quiz.')
        return redirect(url_for('main.dashboard'))

    # Already completed?
    existing_attempt = QuizAttempt.query.filter_by(student_id=current_user.id, quiz_id=quiz_id, is_completed=True).first()
    if existing_attempt:
        flash('You have already completed this quiz.')
        return redirect(url_for('main.review_attempt', attempt_id=existing_attempt.id))

    # Create new attempt if none exists
    attempt = QuizAttempt.query.filter_by(student_id=current_user.id, quiz_id=quiz_id, is_completed=False).first()
    if not attempt:
        attempt = QuizAttempt(student_id=current_user.id, quiz_id=quiz_id, total_questions=quiz.questions.count())
        db.session.add(attempt)
        db.session.commit()

    if request.method == 'POST':
        def extract_letter(text):
            return text.split(')')[0].strip() if text and ')' in text else text

        for question in quiz.questions:
            answer_key = f'question_{question.id}'
            selected = request.form.get(answer_key)
            if not selected:
                continue

            existing = StudentAnswer.query.filter_by(attempt_id=attempt.id, question_id=question.id).first()
            if not existing:
                selected_letter = extract_letter(selected)
                correct_letter = extract_letter(question.correct_answer)
                is_correct = selected_letter == correct_letter

                db.session.add(StudentAnswer(
                    attempt_id=attempt.id,
                    question_id=question.id,
                    selected_answer=selected,
                    is_correct=is_correct
                ))

        # Finalize attempt
        attempt.is_completed = True
        attempt.time_completed = datetime.utcnow()
        attempt.score = sum(1 for a in attempt.answers if a.is_correct)
        db.session.commit()

        flash('Quiz submitted successfully.')
        return redirect(url_for('main.review_attempt', attempt_id=attempt.id))

    return render_template('main/take_quiz.html', quiz=quiz, attempt=attempt)

@bp.route('/view_assignments')
@login_required
def view_assignments():
    if not current_user.is_instructor():
        flash('Access denied.')
        return redirect(url_for('main.dashboard'))

    assignments = QuizAssignment.query.filter_by(instructor_id=current_user.id).all()
    return render_template('main/view_assignments.html', title="Assigned Quizzes", assignments=assignments)

@bp.route('/instructor/quiz_attempts')
@login_required
def view_all_quiz_attempts():
    if current_user.role != 'instructor':
        flash('Access denied.')
        return redirect(url_for('main.dashboard'))

    # Get all quiz attempts related to quizzes this instructor created
    attempts = (
        QuizAttempt.query
        .join(Quiz)
        .filter(Quiz.creator_id == current_user.id)
        .order_by(QuizAttempt.time_started.desc())
        .all()
    )

    return render_template('main/all_quiz_attempts.html', attempts=attempts)

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
        answer = attempt.answers.filter_by(question_id=question.id).first()
        selected = answer.selected_answer if answer else None
        is_correct = answer.is_correct if answer else False

        response_data.append({
            'question': question.question_text,
            'options': question.options.order_by(QuestionOption.id).all(),
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

@bp.route('/delete_quiz/<int:quiz_id>', methods=['POST'])
@login_required
def delete_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.creator != current_user:
        return "Unauthorized", 403
    db.session.delete(quiz)
    db.session.commit()
    return redirect(url_for('main.my_quizzes'))

@bp.route('/quiz/<int:quiz_id>/attempts', methods=['GET'])
@login_required
def view_quiz_attempts(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.creator != current_user:
        return "Unauthorized", 403
    
    attempts = QuizAttempt.query.filter_by(quiz_id=quiz_id).all()
    return render_template('view_attempts.html', quiz=quiz, attempts=attempts)

@bp.route('/view_assigned_quizzes')
@login_required
def view_assigned_quizzes():
    if current_user.role != 'student':
        flash("Access denied.")
        return redirect(url_for('main.dashboard'))

    # Get quizzes assigned to the current student
    all_assignments = QuizAssignment.query.filter_by(student_id=current_user.id, is_active=True).all()

    # Filter out those already attempted
    visible_assignments = []
    for assignment in all_assignments:
        attempt = QuizAttempt.query.filter_by(student_id=current_user.id, quiz_id=assignment.quiz_id).first()
        if not attempt:
            visible_assignments.append(assignment)

    return render_template(
        'main/view_assigned_quizzes.html',
        title='Assigned Quizzes',
        assignments=visible_assignments
    )
