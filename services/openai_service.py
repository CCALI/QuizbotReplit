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

    def generate_summary(self, text: str) -> str:
        try:
            # Break text into smaller chunks if too long
            max_tokens = 4000
            if len(text) > max_tokens * 4:  # Approximate chars to tokens
                chunks = [text[i:i+max_tokens*4] for i in range(0, len(text), max_tokens*4)]
                summaries = []
                
                for chunk in chunks:
                    response = self._make_api_call_with_retry(
                        self.client.chat.completions.create,
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": "Generate a concise summary of this text section:"},
                            {"role": "user", "content": chunk}
                        ],
                        response_format={"type": "text"},
                        timeout=self.timeout
                    )
                    summaries.append(response.choices[0].message.content)
                
                # Combine summaries
                combined_summary = " ".join(summaries)
                
                # Generate final summary if needed
                if len(combined_summary) > max_tokens * 4:
                    final_response = self._make_api_call_with_retry(
                        self.client.chat.completions.create,
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": "Create a final concise summary from these section summaries:"},
                            {"role": "user", "content": combined_summary}
                        ],
                        response_format={"type": "text"},
                        timeout=self.timeout
                    )
                    return final_response.choices[0].message.content
                return combined_summary
                
            else:
                response = self._make_api_call_with_retry(
                    self.client.chat.completions.create,
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "Generate a concise summary of the following text:"},
                        {"role": "user", "content": text}
                    ],
                    response_format={"type": "text"},
                    timeout=self.timeout
                )
                return response.choices[0].message.content
                
        except Exception as e:
            st.error(f"Failed to generate summary: {str(e)}")
            return "Failed to generate summary. Starting with first question..."

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
        system_prompt = '''You are a professional Socratic tutor operating in a law school-like setting. Your role is to:

1. Guide students through critical thinking using questions, never directly providing answers
2. Maintain strict professionalism - avoid jokes, pop culture references, or informal language
3. Stay focused on the academic topic - politely redirect off-topic conversations back to the quiz
4. Accept and accommodate reasonable accessibility requests (e.g., dyslexia support, clearer formatting)
5. Decline requests for:
   - Speaking in different personas/styles (e.g., pirates, celebrities)
   - Creating poems, jokes, or entertainment content
   - Discussing unrelated topics
   - Providing direct answers

When redirecting, use professional, positive language such as:
"Let's focus on the question at hand..."
"That's an interesting point, but let's return to our discussion of..."
"To help you better understand the concept..."

Remember: Your goal is to help students develop critical thinking skills through focused, professional dialogue.'''
        
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
