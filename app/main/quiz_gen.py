from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Quiz, Question, QuestionOption
from quiz_gen_langgraph import generate_quiz_from_text, generate_quiz_from_image
from save import saveImg
import logging
import run

app = run.get_app()

quiz_bp = Blueprint('quiz_gen', __name__)

@quiz_bp.route('/generate_quiz', methods=['POST'])
@login_required
def generate_quiz():
    quiz_type = request.form.get('quiz_type')  # 'comprehension' or 'description'
    difficulty = request.form.get('difficulty_level')
    title = request.form.get('title')
    description = request.form.get('description', '')

    source_content = None
    source_image_path = None
    source_mime = None

    app.logger.info("Test")
    print("Test???")
    if 'text' in request.files:
        source_content = request.files['text'].read().decode('utf-8')
        generated = generate_quiz_from_text(source_content)

    elif 'image' in request.files:
        image_file = request.files['image']
        image_bytes = image_file.read()
        import pickle
        with open('/home/bassturtle4/Documents/GitHub/ESL-RS2025/debug_uploaded_image.pkl', 'wb') as f:
            pickle.dump(image_bytes, f)

        source_image_path, source_mime = saveImg(image_bytes, image_file.filename)

        generated = generate_quiz_from_image(image_bytes)


    else:
        return jsonify({"error": "No valid input provided"}), 400

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

    for q in generated['questions']:
        question = Question(
            question_text=q['question'],
            correct_answer=q['correct_answer'],
            explanation=q.get('explanation', ''),
            quiz=quiz
        )
        db.session.add(question)
        db.session.commit()

        for opt in q['options']:
            db.session.add(QuestionOption(
                question=question,
                option_text=opt,
                is_correct=(opt == q['correct_answer'])
            ))

    db.session.commit()
    return jsonify({'message': 'Quiz created successfully', 'quiz_id': quiz.id})