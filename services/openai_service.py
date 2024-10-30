import os
from openai import OpenAI

class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def generate_questions(self, text: str) -> list:
        prompt = f"Generate 3 Socratic questions based on this text: {text}"
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.split('\n')

    def generate_response(self, conversation_history: list) -> str:
        system_prompt = """You are a Socratic tutor. Guide students to understanding through 
        questioning rather than direct answers. Be encouraging and supportive while 
        maintaining a focus on critical thinking."""
        
        messages = [{"role": "system", "content": system_prompt}] + conversation_history
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        return response.choices[0].message.content
