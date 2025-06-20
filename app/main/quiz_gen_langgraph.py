import ollama
import json
import subprocess
import re
import base64

# Extract JSON substring from the output
def extract_json(text):
    try:
        # Greedily match a JSON object
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return json.loads(match.group())
    except json.JSONDecodeError:
        pass
    return None

def generate_quiz_from_text(text):
    prompt = f"""
You are a quiz generator AI. Read the following passage and generate 3 multiple-choice comprehension questions.
Each question should have 4 options (A, B, C, D), a correct answer, and a brief explanation.
Return only a JSON object in this exact structure:

Text:
{text}

Output format (JSON):
{{
  "questions": [
    {{
      "question": "...",
      "options": ["QuestionAnswer1", "QuestionAnswer2", "QuestionAnswer3", "QuestionAnswer4"],
      "correct_answer": "",(A,B,C....)
      "explanation": "..."
    }}
  ]
}}
"""

    result = subprocess.run(
        ["ollama", "run", "llama3.2"],
        input=prompt,
        capture_output=True,
        text=True,
    )

    output = result.stdout.strip()

    quiz_data = extract_json(output)

    if quiz_data:
        return quiz_data
    else:
        return {
            "questions": [{
                "question": "Error generating questions.",
                "options": [],
                "correct_answer": "",
                "explanation": output  # Show full output for debugging
            }]
        }



def generate_quiz_from_image(image_bytes):
    try:
        # Encode image to base64
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')

        prompt = f"""
You are an educational assistant. Look at the image and generate 3 multiple-choice questions about its contents.
Each question should test visual comprehension.
Return only a JSON object in this exact structure:

Output format (JSON):
{{
  "questions": [
    {{
      "question": "...",
      "options": ["QuestionAnswer1", "QuestionAnswer2", "QuestionAnswer3", "QuestionAnswer4"],
      "correct_answer": "",(A,B,C....)
      "explanation": "..."
    }}
  ]
}}
"""
        response = ollama.chat(
            model='llama3.2-vision',
            messages=[
                {
                    'role': 'user',
                    'content': prompt,
                    'images': [image_b64]
                }
            ]
        )

        output = response['message']['content']
        quiz_data = extract_json(output)

        if quiz_data:
            return quiz_data
        else:
            return {
                "questions": [{
                    "question": "Error generating image-based questions.",
                    "options": [],
                    "correct_answer": "",
                    "explanation": output  # Helpful for debugging
                }]
            }

    except Exception as e:
        return {
            "questions": [{
                "question": "Error processing image.",
                "options": [],
                "correct_answer": "",
                "explanation": str(e)
            }]
        }

def format_checker():
    return

# print(generate_quiz_from_text("I pledge allegiance to the Flag of the United States of America, and to the Republic for which it stands, one Nation under God, indivisible, with liberty and justice for all"))
# print(generate_quiz_from_text("I live in a house near the mountains. I have two brothers and one sister, and I was born last. My father teaches mathematics, and my mother is a nurse at a big hospital. My brothers are very smart and work hard in school. My sister is a nervous girl, but she is very kind. My grandmother also lives with us. She came from Italy when I was two years old. She has grown old, but she is still very strong. She cooks the best food!"))