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

# Load custom CSS
with open('assets/style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def load_conversation(conversation_id):
    """Load an existing conversation"""
    messages = db_ops.get_conversation_messages(conversation_id)
    st.session_state.messages = [
        {"role": role, "content": content}
        for role, content, *_ in messages
    ]
    st.session_state.conversation_id = conversation_id
    st.session_state.quiz_started = True
    st.session_state.show_transcript = False

def start_new_conversation():
    """Start a new conversation by processing PDFs and generating initial question"""
    try:
        with st.spinner("Processing PDF documents..."):
            text, tables, images, footnotes = pdf_service.extract_text_with_formatting('Readings')
            if not text:
                st.error("No PDFs found in the Readings folder.")
                return False
            
            # Generate summary before chunking
            summary = openai_service.generate_summary(text)
            
            # Then chunk the text for detailed processing
            chunks = pdf_service.chunk_text(text)
            if not chunks:
                st.error("No valid text chunks found.")
                return False
            
            with st.spinner("Starting conversation..."):
                # Generate questions from summary
                initial_question = openai_service.generate_questions(summary, num_questions=1)[0]
                
                # Create conversation with context
                title = f"Quiz on {', '.join(os.listdir('Readings'))}"
                st.session_state.conversation_id = db_ops.create_conversation(
                    st.session_state.user_id,
                    title=title,
                    context=summary
                )
                st.session_state.messages = []
                st.session_state.quiz_started = True
                st.session_state.show_transcript = False
                
                # Save and track initial message
                message_id = db_ops.save_message(st.session_state.conversation_id, "assistant", initial_question)
                AnalyticsOperations.update_message_analytics(message_id)
                AnalyticsOperations.update_conversation_analytics(st.session_state.conversation_id)
                AnalyticsOperations.update_user_analytics(st.session_state.user_id)
                
                st.session_state.messages.append({"role": "assistant", "content": initial_question})
                
                if len(chunks) > 1:
                    st.session_state.remaining_chunks = chunks[1:]
        
        return True
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        return False

def show_conversation_list():
    """Display list of user's conversations"""
    conversations = db_ops.get_user_conversations(st.session_state.user_id)
    
    if not conversations:
        st.info("No conversations found. Start a new quiz!")
        return
    
    st.subheader("Your Conversations")
    
    for conv in conversations:
        conv_id, title, context, start_time, end_time, status, msg_count, last_activity = conv
        
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.write(f"**{title}**")
            st.write(f"Started: {start_time.strftime('%Y-%m-%d %H:%M')}")
        with col2:
            st.write(f"Status: {status.title()}")
            st.write(f"Messages: {msg_count}")
        with col3:
            if status == 'ongoing':
                if st.button("Continue", key=f"continue_{conv_id}"):
                    load_conversation(conv_id)
                    st.rerun()
            else:
                if st.button("View", key=f"view_{conv_id}"):
                    load_conversation(conv_id)
                    st.rerun()
        st.divider()

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
        st.write("Welcome. Select 'Begin Quiz' to start a new quiz or continue an existing conversation.")
    
    # Top controls container
    top_container = st.container()
    col1, col2, col3 = top_container.columns([4, 2, 1])
    
    # Add logout button in top-right
    with col3:
        if st.button("Logout", key="logout"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()
    
    # Begin Quiz button and View Conversations
    with col1:
        if not st.session_state.quiz_started:
            if st.button("Begin New Quiz", key="begin_quiz"):
                if start_new_conversation():
                    st.rerun()
    
    with col2:
        if st.session_state.quiz_started:
            if st.button("View All Conversations", key="view_conversations"):
                st.session_state.quiz_started = False
                st.session_state.conversation_id = None
                st.session_state.messages = []
                st.rerun()
    
    # Show conversation list when not in a quiz
    if not st.session_state.quiz_started:
        show_conversation_list()
        return

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
                # Save and track user message
                message_id = db_ops.save_message(st.session_state.conversation_id, "user", prompt)
                AnalyticsOperations.update_message_analytics(message_id)
                st.session_state.messages.append({"role": "user", "content": prompt})
                
                # Generate and save bot response
                with st.spinner("Thinking..."):
                    bot_response = openai_service.generate_response(st.session_state.messages)
                    message_id = db_ops.save_message(st.session_state.conversation_id, "assistant", bot_response)
                    AnalyticsOperations.update_message_analytics(message_id)
                    st.session_state.messages.append({"role": "assistant", "content": bot_response})
                
                # Update analytics
                AnalyticsOperations.update_conversation_analytics(st.session_state.conversation_id)
                AnalyticsOperations.update_user_analytics(st.session_state.user_id)
                
                st.rerun()
        
        # Action buttons below chat
        if st.session_state.quiz_started:
            button_cols = st.columns([1, 1, 4])
            with button_cols[0]:
                if st.button("End Quiz", key="end_quiz", type="primary"):
                    if st.session_state.conversation_id:
                        db_ops.end_conversation(st.session_state.conversation_id)
                        # Update completion status and analytics
                        with get_db_connection() as conn:
                            cur = conn.cursor()
                            cur.execute(
                                "UPDATE conversations SET completion_status = 'completed' WHERE id = %s",
                                (st.session_state.conversation_id,)
                            )
                            conn.commit()
                        AnalyticsOperations.update_user_analytics(st.session_state.user_id)
                        st.session_state.show_transcript = True
                        st.rerun()
    
    # Show transcript download and new quiz button with consistent layout
    if st.session_state.show_transcript:
        messages = db_ops.get_conversation_messages(st.session_state.conversation_id)
        transcript = db_ops.format_transcript(messages)
        
        button_cols = st.columns([1, 1, 4])
        with button_cols[0]:
            st.download_button(
                label="Download Transcript",
                data=transcript,
                file_name=f"quizbot_transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                key="download_transcript"
            )
        
        with button_cols[1]:
            if st.button("Start New Quiz", key="new_quiz"):
                st.session_state.conversation_id = None
                st.session_state.messages = []
                st.session_state.quiz_started = False
                st.session_state.show_transcript = False
                st.rerun()

if __name__ == "__main__":
    main()
