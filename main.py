import streamlit as st
import os
from database.models import init_db
from database.operations import DatabaseOperations
from services.openai_service import OpenAIService
from services.pdf_service import PDFService
from utils.auth import Auth
import asyncio
import time

# Initialize services
openai_service = OpenAIService()
pdf_service = PDFService()
db_ops = DatabaseOperations()

# Initialize database
init_db()

# Session state initialization
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'conversation_id' not in st.session_state:
    st.session_state.conversation_id = None
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'quiz_started' not in st.session_state:
    st.session_state.quiz_started = False

# Load custom CSS
with open('assets/style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def start_new_conversation():
    """Start a new conversation by processing PDFs and generating questions"""
    try:
        with st.spinner("Processing PDF documents..."):
            # Extract text from all PDFs
            text = pdf_service.extract_text_from_pdfs()
            if not text:
                st.error("No PDFs found in the Readings folder.")
                return False
            
            # Process first chunk only for initial questions
            chunks = pdf_service.chunk_text(text)
            if not chunks:
                st.error("No valid text chunks found.")
                return False
            
            # Generate initial questions from first chunk
            with st.spinner("Generating initial questions..."):
                questions = openai_service.generate_questions(chunks[0], num_questions=2)
                
                # Create new conversation
                st.session_state.conversation_id = db_ops.create_conversation(st.session_state.user_id)
                st.session_state.messages = []
                st.session_state.quiz_started = True
                
                # Save and display initial questions
                st.success("Quiz ready!")
                st.subheader("Let's discuss these questions:")
                for i, question in enumerate(questions, 1):
                    db_ops.save_message(st.session_state.conversation_id, "assistant", question)
                    st.session_state.messages.append({"role": "assistant", "content": question})
                
                # Store remaining chunks for later use
                if len(chunks) > 1:
                    st.session_state.remaining_chunks = chunks[1:]
        
        return True
    except Exception as e:
        st.error(f"An error occurred while starting the quiz: {str(e)}")
        return False

def main():
    st.title("QuizBot - Socratic Learning Assistant")

    # Authentication
    if not st.session_state.user_id:
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login")
                
                if submit:
                    success, user_id = Auth.verify_user(username, password)
                    if success:
                        st.session_state.user_id = user_id
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
        
        with tab2:
            with st.form("register_form"):
                new_username = st.text_input("Choose Username")
                new_password = st.text_input("Choose Password", type="password")
                submit = st.form_submit_button("Register")
                
                if submit:
                    if Auth.register_user(new_username, new_password):
                        st.success("Registration successful! Please login.")
                    else:
                        st.error("Registration failed. Username might be taken.")
        return

    # Main application
    col1, col2 = st.columns([1, 1])
    with col1:
        if not st.session_state.quiz_started and st.button("Begin Quiz"):
            start_new_conversation()
            st.rerun()
    
    with col2:
        if st.session_state.conversation_id and st.button("End Quiz"):
            db_ops.end_conversation(st.session_state.conversation_id)
            messages = db_ops.get_conversation_messages(st.session_state.conversation_id)
            
            transcript = "\n\n".join([
                f"{'You' if role == 'user' else 'QuizBot'}: {content}"
                for role, content in messages
            ])
            
            st.download_button(
                label="Download Transcript",
                data=transcript,
                file_name="conversation_transcript.txt",
                mime="text/plain"
            )
            
            st.session_state.conversation_id = None
            st.session_state.messages = []
            st.session_state.quiz_started = False
            st.rerun()

    # Chat interface
    if st.session_state.quiz_started and st.session_state.conversation_id:
        # Create a container for chat history
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        
        # Display conversation
        for message in st.session_state.messages:
            role_style = "user-message" if message["role"] == "user" else "bot-message"
            icon = "👤" if message["role"] == "user" else "🤖"
            st.markdown(
                f'''
                <div class="chat-message {role_style}">
                    <div class="chat-icon">{icon}</div>
                    <div class="message-content">{message["content"]}</div>
                </div>
                ''',
                unsafe_allow_html=True
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Input field at the bottom
        st.markdown('<div class="chat-input">', unsafe_allow_html=True)
        user_input = st.text_input("Your response:", key="user_input")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if user_input:
            # Save user message
            db_ops.save_message(st.session_state.conversation_id, "user", user_input)
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # Generate and save bot response
            with st.spinner("Thinking..."):
                bot_response = openai_service.generate_response(st.session_state.messages)
                db_ops.save_message(st.session_state.conversation_id, "assistant", bot_response)
                st.session_state.messages.append({"role": "assistant", "content": bot_response})
            
            # Clear input and rerun to update chat
            st.rerun()

if __name__ == "__main__":
    main()
