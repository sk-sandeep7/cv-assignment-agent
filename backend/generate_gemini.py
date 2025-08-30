from langchain_openai import AzureChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from get_examples import select_few_shots
import json
from dotenv import load_dotenv
import os
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# Initialize Azure OpenAI LLM for LangChain
llm = AzureChatOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    openai_api_version=os.getenv("OPENAI_API_VERSION"),
    deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    temperature=0.7
)

prompt_template = PromptTemplate(
    input_variables=["few_shots", "topics", "num_questions"],
    template="""You are a JSON generation service. Your sole purpose is to take a list of topics and a number, and return a valid JSON array of assignment questions. You must not output any other text, explanations, or conversational filler.

The JSON array you generate must contain exactly {num_questions} objects. Each object must have the following structure:
{{
  "question": "The actual question text?",
  "topic": ["List", "of", "relevant", "CV", "topics"],
  "marks": "<an integer mark between 1 and 8>"
}}

Here are some examples of well-formed question objects to use as a reference for style and content:
{few_shots}

Now, process the following request and provide only the JSON array as output.

Topics: {topics}
Number of Questions to Generate: {num_questions}
"""
)

custom_prompt_template = PromptTemplate(
    input_variables=["user_input"],
    template="""You are a JSON generation service. Your sole purpose is to take a user's proposed assignment question and return a single, valid JSON object. You must not output any other text, explanations, or conversational filler.

The user's input is:
"{{user_input}}"

The JSON object you generate must have the following structure:
{{
  "question": "The refined, clear, and well-structured question text.",
  "topic": ["A", "list", "of", "relevant", "CV", "topics"],
  "marks": <an integer mark between 1 and 8>
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
)

def generate_questions_with_langchain(topics, num_questions):
    few_shots = select_few_shots(topics, k=3)
    formatted_few_shots = json.dumps(few_shots, indent=2)

    chain = prompt_template | llm | StrOutputParser()

    result = chain.invoke({
        "few_shots": formatted_few_shots,
        "topics": ", ".join(topics),
        "num_questions": num_questions
    })

    # Try parsing response as JSON
    try:
        start = result.find("[")
        end = result.rfind("]") + 1
        return json.loads(result[start:end])
    except Exception as e:
        print("Failed to parse output:", e)
        print("Raw result:\n", result)
        return []

def generate_custom_question_with_langchain(user_input):
    chain = custom_prompt_template | llm | StrOutputParser()
    result = chain.invoke({"user_input": user_input})

    try:
        # The model should return a single JSON object.
        start = result.find("{")
        end = result.rfind("}") + 1
        return json.loads(result[start:end])
    except Exception as e:
        print("Failed to parse custom question output:", e)
        print("Raw result for custom question:\n", result)
        return None
