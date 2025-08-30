import os
import json
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize Azure OpenAI Client
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("OPENAI_API_VERSION"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
)

deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

def generate_evaluation_rubrics_with_openai(question: str):
    """
    Generates evaluation rubrics for a given assignment question using the OpenAI API.
    """
    system_prompt = """You are an expert in academic assessments for Computer Vision. Your task is to create a detailed evaluation rubric for a given assignment question. The rubric must be a valid JSON object.

The root of the JSON object should be a "rubric" key, which contains an array of criteria objects. Each criterion object must have two keys: "criterion" (a string describing the assessment point) and "marks" (an integer).

The total marks for all criteria should sum up to the marks assigned to the question, which will be mentioned in the user prompt.

Example:
---
User Input: "Implement the Hough Transform from scratch to detect straight lines in a binary edge-detected image. (7 marks)"
Your Output:
{
  "rubric": [
    {
      "criterion": "Correct implementation of the Hough accumulator space.",
      "marks": 3
    },
    {
      "criterion": "Accurate detection and visualization of peaks in the accumulator.",
      "marks": 2
    },
    {
      "criterion": "Correctly drawing the detected lines back onto the original image.",
      "marks": 2
    }
  ]
}
---

Now, generate the rubric for the following question.
"""
    try:
        response = client.chat.completions.create(
            model=deployment_name,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            temperature=0.1,
        )
        response_content = response.choices[0].message.content
        return json.loads(response_content)

    except Exception as e:
        print(f"Failed to generate evaluation rubrics with OpenAI: {e}")
        return None
