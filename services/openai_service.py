import os
from openai import OpenAI
import time
import streamlit as st
from functools import lru_cache
import tiktoken
import tenacity

class OpenAIService:
    def __init__(self):
        # Priority order for API key:
        # 1. User's custom key from session
        # 2. Environment variable from .env
        # 3. System default (if available)
        self.client = OpenAI(api_key=self._get_api_key())
        self.max_retries = 5
        self.timeout = 20
        self.cache_ttl = 3600
        self.encoder = tiktoken.encoding_for_model("gpt-4")
        self.max_history_tokens = 2000
        
    def _get_api_key(self):
        # First check session state for user's custom key
        if hasattr(st.session_state, 'custom_openai_key') and st.session_state.custom_openai_key:
            return st.session_state.custom_openai_key
            
        # Then check .env file
        env_key = os.getenv('OPENAI_API_KEY')
        if env_key:
            return env_key
            
        # No key available
        st.error("No OpenAI API key found. Please add your API key in Settings.")
        return None

    def verify_api_key(self, api_key: str) -> bool:
        """Verify if the provided OpenAI API key is valid"""
        if not api_key:
            return False
            
        try:
            # Create a temporary client with the provided key
            temp_client = OpenAI(api_key=api_key)
            
            # Try a simple API call to verify the key
            temp_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            st.error(f"API key verification failed: {str(e)}")
            return False
