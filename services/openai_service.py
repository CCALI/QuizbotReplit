import os
from openai import OpenAI
import time
import streamlit as st
from functools import lru_cache
import tiktoken

class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.max_retries = 3
        self.timeout = 30
        self.cache_ttl = 3600  # Cache TTL in seconds
        self.encoder = tiktoken.encoding_for_model("gpt-4")
        
    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string"""
        return len(self.encoder.encode(text))

    def _make_api_call_with_retry(self, func, *args, **kwargs):
        """Helper method to handle API calls with retry logic and detailed error messages"""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if "rate_limit" in str(e).lower():
                    wait_time = 2 ** attempt
                    st.warning(f"Rate limit reached. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                elif "timeout" in str(e).lower():
                    st.warning("Request timed out. Retrying...")
                    time.sleep(2)
                else:
                    if attempt == self.max_retries - 1:
                        st.error(f"Failed after {self.max_retries} attempts: {str(e)}")
                        raise e
                    time.sleep(2)
        
        if last_error:
            raise last_error

    @lru_cache(maxsize=100)
    def generate_summary(self, text: str) -> str:
        """Generate summary with token limit and caching"""
        try:
            # Limit input tokens
            max_input_tokens = 4000
            current_tokens = self.count_tokens(text)
            
            if current_tokens > max_input_tokens:
                chunks = []
                current_chunk = []
                current_chunk_tokens = 0
                
                for line in text.split('\n'):
                    line_tokens = self.count_tokens(line)
                    if current_chunk_tokens + line_tokens > max_input_tokens:
                        chunks.append('\n'.join(current_chunk))
                        current_chunk = [line]
                        current_chunk_tokens = line_tokens
                    else:
                        current_chunk.append(line)
                        current_chunk_tokens += line_tokens
                
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                
                summaries = []
                for chunk in chunks:
                    response = self._make_api_call_with_retry(
                        self.client.chat.completions.create,
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": "Generate a concise summary (max 200 words) of this text section:"},
                            {"role": "user", "content": chunk}
                        ],
                        response_format={"type": "text"},
                        timeout=self.timeout
                    )
                    summaries.append(response.choices[0].message.content)
                
                # Combine summaries
                combined_summary = " ".join(summaries)
                if self.count_tokens(combined_summary) > max_input_tokens:
                    final_response = self._make_api_call_with_retry(
                        self.client.chat.completions.create,
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": "Create a final concise summary (max 200 words) from these section summaries:"},
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
                        {"role": "system", "content": "Generate a concise summary (max 200 words) of the following text:"},
                        {"role": "user", "content": text}
                    ],
                    response_format={"type": "text"},
                    timeout=self.timeout
                )
                return response.choices[0].message.content
                
        except Exception as e:
            st.error(f"Failed to generate summary: {str(e)}")
            return "Failed to generate summary. Starting with first question..."

    @lru_cache(maxsize=100)
    def generate_questions(self, text: str, num_questions: int = 2) -> list:
        """Generate questions with caching and error handling"""
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
        """Generate response with improved error handling"""
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
        
        try:
            # Limit conversation history tokens
            max_history_tokens = 3000
            current_tokens = sum(self.count_tokens(msg["content"]) for msg in conversation_history)
            
            if current_tokens > max_history_tokens:
                # Keep the most recent messages that fit within the token limit
                truncated_history = []
                current_tokens = self.count_tokens(system_prompt)
                
                for msg in reversed(conversation_history):
                    msg_tokens = self.count_tokens(msg["content"])
                    if current_tokens + msg_tokens <= max_history_tokens:
                        truncated_history.insert(0, msg)
                        current_tokens += msg_tokens
                    else:
                        break
                
                conversation_history = truncated_history
            
            messages = [{"role": "system", "content": system_prompt}] + conversation_history
            
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
