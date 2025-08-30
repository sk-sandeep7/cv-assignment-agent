import os
import json
from openai import AzureOpenAI
from dotenv import load_dotenv
from get_examples import select_few_shots

load_dotenv()

# Initialize Azure OpenAI Client
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("OPENAI_API_VERSION"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
)

deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

def generate_questions_with_openai(topics, num_questions):
    """
    Generates a specified number of assignment questions based on topics using the OpenAI API.
    """
    few_shots = select_few_shots(topics, k=3)
    formatted_few_shots = json.dumps(few_shots, indent=2)

    system_prompt = f"""You are a JSON generation service. Your sole purpose is to take a list of topics and a number, and return a valid JSON object. You must not output any other text, explanations, or conversational filler.

The JSON object you generate must have a single root key called "questions". The value of "questions" must be a JSON array containing exactly {num_questions} question objects.

Even if {num_questions} is 1, the "questions" key must still contain an array with that single object.

Each object in the "questions" array must have the following structure:
{{
  "question": "The actual question text?",
  "topic": ["List", "of", "relevant", "CV", "topics"],
  "marks": "<an integer mark between 1 and 8>"
}}

Here is an example of a well-formed response to use as a reference for style and content:
{{
  "questions": {formatted_few_shots}
}}
"""
    user_prompt = f"""
Topics: {", ".join(topics)}
Number of Questions to Generate: {num_questions}
"""

    try:
        response = client.chat.completions.create(
            model=deployment_name,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )
        
        response_content = response.choices[0].message.content
        # The response is expected to be a JSON object containing a key with the array, e.g., {"questions": [...]}.
        # We need to extract that array.
        json_response = json.loads(response_content)
        
        # Find the array in the response object, regardless of the key
        for key, value in json_response.items():
            if isinstance(value, list):
                return value
        
        print("Failed to find a list in the JSON response.")
        return []

    except Exception as e:
        print(f"Failed to generate questions with OpenAI: {e}")
        return []


def generate_custom_question_with_openai(user_input):
    """
    Rephrases a user-provided question using the OpenAI API.
    """
    system_prompt = """You are a JSON generation service. Your sole purpose is to take a user's proposed assignment question and return a single, valid JSON object. You must not output any other text, explanations, or conversational filler.

The JSON object you generate must have the following structure:
{{
  "question": "The refined, clear, and well-structured question text.",
  "topic": ["A", "list", "of", "relevant", "CV", "topics"],
  "marks": "<an integer mark between 1 and 8>"
}}

Here is an example:
---
User Input: "make a hough transform thing to find lines"
Your Output:
{{
  "question": "Implement the Hough Transform from scratch to detect straight lines in a binary edge-detected image. Your implementation should include creating and visualizing the parameter space (Hough space). Finally, draw the detected lines over the original image.",
  "topic": ["Hough Transform", "Edge Detection", "Feature Extraction", "Image Processing"],
  "marks": 7
}}
---
Now, process the user's input and provide only the JSON object as output.
"""
    try:
        response = client.chat.completions.create(
            model=deployment_name,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            temperature=0.0,
        )
        response_content = response.choices[0].message.content
        return json.loads(response_content)

    except Exception as e:
        print(f"Failed to generate custom question with OpenAI: {e}")
        return None
