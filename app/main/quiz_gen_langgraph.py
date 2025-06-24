import ollama
import json
import subprocess
import re
import base64

# Extract JSON substring from the output
def extract_json(text):
    try:
        code_block_match = re.search(r"```json\n([\s\S]+?)```", text)
        if code_block_match:
            json_part = code_block_match.group(1).strip()
            return json.loads(json_part)

        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError as e:
        print("JSON decode error:", e)
    return None

def generate_quiz_from_text(text, num_questions=3, num_options=4):
    option_letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G'][:num_options]
    formatted_options = ', '.join(option_letters)

    prompt = f"""
You are a quiz generator AI. Read the following passage and generate {num_questions} multiple-choice comprehension questions.
Each question should have {num_options} options labeled {formatted_options}.
Return only a JSON object in this exact structure:

Text:
{text}

Output format (JSON):
{{
  "questions": [
    {{
      "question": "...",
      "options": ["Option1", "Option2", "Option3", "..."],
      "correct_answer": "",  // Use letter like "A", "B", etc.
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
        return format_checker(output)




def generate_quiz_from_image(image_bytes, num_questions=3, num_options=4):
    try:
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        option_letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G'][:num_options]
        formatted_options = ', '.join(option_letters)

        prompt = f"""
You are an educational assistant. Look at the image and generate {num_questions} multiple-choice questions about its contents.
Each question should have {num_options} answer choices labeled {formatted_options}, a correct letter (e.g. "A", "B"), and a short explanation.
Return only a JSON object in this exact structure:

Output format (JSON):
{{
  "questions": [
    {{
      "question": "...",
      "options": ["Option1", "Option2", "Option3", "..."],
      "correct_answer": "",  // Use letter like "A", "B", etc.
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
            return format_checker(output)

    except Exception as e:
        return {
            "questions": [{
                "question": "Error processing image.",
                "options": [],
                "correct_answer": "",
                "explanation": str(e)
            }]
        }


def format_checker(bad_output, max_attempts=5):

    for attempt in range(max_attempts):
        fix_prompt = f"""
The following is a malformed quiz response that contains question and answer content but is not in valid JSON format.

Please fix it so that it is a *valid JSON object*, matching the following structure, and output ONLY the JSON in a Python-style markdown code block (using triple backticks):

```json
{{
  "questions": [
    {{
      "question": "What color is the sky?",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "A",
      "explanation": "Sky is blue due to Rayleigh scattering."
    }}
  ]
}}
```

Here is the input to fix:
{bad_output}
"""

        try:
            result = ollama.chat(
                model='llama3.2',
                messages=[{'role': 'user', 'content': fix_prompt}]
            )
            corrected = result['message']['content']
            corrected = extract_json(corrected)
            return json.loads(corrected)
        except Exception:
            continue

    return {
        "questions": [{
            "question": "Error after multiple attempts to fix malformed JSON.",
            "options": [],
            "correct_answer": "",
            "explanation": bad_output
        }]
    }
