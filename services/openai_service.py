import os
from openai import OpenAI
import time
import streamlit as st

class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.max_retries = 3
        self.timeout = 30

    def _make_api_call_with_retry(self, func, *args, **kwargs):
        """Helper method to handle API calls with retry logic"""
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
                time.sleep(2 ** attempt)  # Exponential backoff

    def generate_questions(self, text: str, num_questions: int = 2) -> list:
        """Generate a specified number of Socratic questions with timeout handling"""
        prompt = f"Generate {num_questions} Socratic questions based on this text: {text}"
        
        try:
            response = self._make_api_call_with_retry(
                self.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "text"},
                timeout=self.timeout
            )
            return response.choices[0].message.content.split('\n')
        except Exception as e:
            st.error(f"Failed to generate questions: {str(e)}")
            return ["Could you tell me more about what you understood from the text?"]

    def generate_response(self, conversation_history: list) -> str:
        """Generate response with timeout handling"""
        system_prompt = """You are a Socratic tutor. Guide students to understanding through 
        questioning rather than direct answers. Be encouraging and supportive while 
        maintaining a focus on critical thinking."""
        
        messages = [{"role": "system", "content": system_prompt}] + conversation_history
        
        try:
            response = self._make_api_call_with_retry(
                self.client.chat.completions.create,
                model="gpt-4",
                messages=messages,
                response_format={"type": "text"},
                timeout=self.timeout
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"Failed to generate response: {str(e)}")
            return "I apologize, but I'm having trouble processing your response. Could you rephrase your thoughts?"
