from app import create_app, db
from app.models import User, Quiz, Question, QuestionOption, QuizAttempt, StudentAnswer, QuizAssignment

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 
        'User': User, 
        'Quiz': Quiz, 
        'Question': Question,
        'QuestionOption': QuestionOption,
        'QuizAttempt': QuizAttempt,
        'StudentAnswer': StudentAnswer,
        'QuizAssignment': QuizAssignment
    }

def get_app():
    return app

if __name__ == '__main__':
    app.run(debug=True)
