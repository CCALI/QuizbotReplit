import streamlit as st
# Set page config before any other Streamlit commands
st.set_page_config(page_title="QuizBot", layout="wide")

import os
from datetime import datetime
from database.models import init_db, get_db_connection
from database.operations import DatabaseOperations
from database.analytics import AnalyticsOperations
from services.openai_service import OpenAIService
from services.pdf_service import PDFService
from utils.auth import Auth

# Initialize services
openai_service = OpenAIService()
pdf_service = PDFService()
db_ops = DatabaseOperations()

# Initialize database
init_db()

# Session state initialization
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = None
if 'conversation_id' not in st.session_state:
    st.session_state.conversation_id = None
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'quiz_started' not in st.session_state:
    st.session_state.quiz_started = False
if 'show_transcript' not in st.session_state:
    st.session_state.show_transcript = False
if 'custom_openai_key' not in st.session_state:
    st.session_state.custom_openai_key = None

# Load custom CSS
with open('assets/style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Rest of the imports and initialization code...

def main():
    # Authentication
    if not st.session_state.user_id:
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login")
                
                if submit:
                    success, user_id, first_name, last_name, _ = Auth.verify_user(username, password)
                    if success:
                        st.session_state.user_id = user_id
                        st.session_state.user_name = f"{first_name or ''} {last_name or ''}".strip() or username
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
        
        with tab2:
            with st.form("register_form"):
                new_username = st.text_input("Choose Username")
                new_password = st.text_input("Choose Password", type="password")
                first_name = st.text_input("First Name")
                last_name = st.text_input("Last Name")
                api_key = st.text_input("OpenAI API Key (Optional)", type="password", 
                                      help="Enter your OpenAI API key if you want to use your own. Leave blank to use system default.")
                
                submit = st.form_submit_button("Register")
                
                if submit:
                    # Validate API key if provided
                    if api_key:
                        if not openai_service.verify_api_key(api_key):
                            st.error("Invalid OpenAI API key. Please check and try again.")
                            return
                    
                    if Auth.register_user(new_username, new_password, first_name, last_name, api_key):
                        st.success("Registration successful! Please login.")
                    else:
                        st.error("Registration failed. Username might be taken.")
        return

    # Main application layout
    st.title("QuizBot")
    
    # Add API key management in settings
    with st.expander("Settings"):
        new_api_key = st.text_input(
            "Update OpenAI API Key",
            type="password",
            help="Enter a new OpenAI API key to use your own account. Leave blank to use system default."
        )
        if st.button("Update API Key"):
            if new_api_key:
                if openai_service.verify_api_key(new_api_key):
                    if Auth.update_api_key(st.session_state.user_id, new_api_key):
                        st.session_state.custom_openai_key = new_api_key
                        st.success("API key updated successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to update API key.")
                else:
                    st.error("Invalid API key. Please check and try again.")
            else:
                # Remove custom API key
                if Auth.update_api_key(st.session_state.user_id, None):
                    st.session_state.custom_openai_key = None
                    st.success("Switched to system default API key.")
                    st.rerun()
                else:
                    st.error("Failed to update API key.")

    # Rest of the main application code...

if __name__ == "__main__":
    main()
