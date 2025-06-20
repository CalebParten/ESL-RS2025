# ESL GenAI Quiz Platform

AI-powered quiz platform for English language learners.

## Quick Start

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize database:
```bash
python init_db.py
```

4. Run the application:
```bash
python run.py
```

Visit http://localhost:5000 to see your app!

## Week 1 Features ✅
- User authentication (students & instructors)
- Role-based access control
- Database schema ready for quiz generation
- Responsive web interface

Ready for Week 2: GenAI integration with LangGraph!




Add veiw for student to reveiw past attempts
add num questions and asnwers for quiz gen
fix delete quiz if taken (dont delete move to history table)

if time
Points per question in quiz, and compute base on points
