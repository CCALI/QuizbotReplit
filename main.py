import streamlit as st
# Set page config before any other Streamlit commands
st.set_page_config(page_title="QuizBot", layout="wide")

import os
from datetime import datetime
from database.models import init_db
from database.operations import DatabaseOperations
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

# Load custom CSS
with open('assets/style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def start_new_conversation():
    """Start a new conversation by processing PDFs and generating initial question"""
    try:
        with st.spinner("Processing PDF documents..."):
            text = pdf_service.extract_text_from_pdfs()
            if not text:
                st.error("No PDFs found in the Readings folder.")
                return False
            
            chunks = pdf_service.chunk_text(text)
            if not chunks:
                st.error("No valid text chunks found.")
                return False
            
            with st.spinner("Starting conversation..."):
                initial_question = openai_service.generate_questions(chunks[0], num_questions=1)[0]
                
                st.session_state.conversation_id = db_ops.create_conversation(st.session_state.user_id)
                st.session_state.messages = []
                st.session_state.quiz_started = True
                st.session_state.show_transcript = False
                
                db_ops.save_message(st.session_state.conversation_id, "assistant", initial_question)
                st.session_state.messages.append({"role": "assistant", "content": initial_question})
                
                if len(chunks) > 1:
                    st.session_state.remaining_chunks = chunks[1:]
        
        return True
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        return False

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
                    success, user_id, first_name, last_name = Auth.verify_user(username, password)
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
                submit = st.form_submit_button("Register")
                
                if submit:
                    if Auth.register_user(new_username, new_password, first_name, last_name):
                        st.success("Registration successful! Please login.")
                    else:
                        st.error("Registration failed. Username might be taken.")
        return

    # Main application layout
    st.title("QuizBot")
    
    if not st.session_state.quiz_started:
        st.write("Welcome. Select 'Begin Quiz' to start the quiz. Select 'End Quiz' when you are done to download a transcript of the quiz.")
    
    # Top controls container
    top_container = st.container()
    col1, col2 = top_container.columns([6, 1])
    
    with col1:
        if not st.session_state.quiz_started:
            if st.button("Begin Quiz", key="begin_quiz"):
                if start_new_conversation():
                    st.rerun()
    
    # End Quiz button always in the same position
    with col2:
        if st.session_state.quiz_started:
            if st.button("End Quiz", key="end_quiz", type="primary"):
                if st.session_state.conversation_id:
                    db_ops.end_conversation(st.session_state.conversation_id)
                    st.session_state.show_transcript = True
                    st.rerun()

    # Chat interface using Streamlit's native components
    if st.session_state.quiz_started and st.session_state.conversation_id:
        chat_container = st.container()
        
        with chat_container:
            # Display messages
            for message in st.session_state.messages:
                with st.chat_message(message["role"], avatar="🤖" if message["role"] == "assistant" else "👤"):
                    st.write(message["content"])
            
            # Chat input
            if prompt := st.chat_input("Type your response here..."):
                # Save user message
                db_ops.save_message(st.session_state.conversation_id, "user", prompt)
                st.session_state.messages.append({"role": "user", "content": prompt})
                
                # Generate and save bot response
                with st.spinner("Thinking..."):
                    bot_response = openai_service.generate_response(st.session_state.messages)
                    db_ops.save_message(st.session_state.conversation_id, "assistant", bot_response)
                    st.session_state.messages.append({"role": "assistant", "content": bot_response})
                
                st.rerun()
    
    # Show transcript download after ending quiz
    if st.session_state.show_transcript:
        messages = db_ops.get_conversation_messages(st.session_state.conversation_id)
        transcript = db_ops.format_transcript(messages)
        
        st.download_button(
            label="Download Transcript",
            data=transcript,
            file_name=f"quizbot_transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            key="download_transcript"
        )
        
        if st.button("Start New Quiz", key="new_quiz"):
            st.session_state.conversation_id = None
            st.session_state.messages = []
            st.session_state.quiz_started = False
            st.session_state.show_transcript = False
            st.rerun()

if __name__ == "__main__":
    main()
