import streamlit as st
# Set page config before any other Streamlit commands
st.set_page_config(page_title="QuizBot", layout="wide")

import os
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

    # Main application layout
    st.title("QuizBot")
    
    # Quiz controls in sidebar
    with st.sidebar:
        if not st.session_state.quiz_started:
            if st.button("Begin Quiz", use_container_width=True):
                if start_new_conversation():
                    st.rerun()
        else:
            if st.button("End Quiz", type="primary", use_container_width=True):
                if st.session_state.conversation_id:
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
                        mime="text/plain",
                        use_container_width=True
                    )
                    
                    st.session_state.conversation_id = None
                    st.session_state.messages = []
                    st.session_state.quiz_started = False
                    st.rerun()

    # Chat interface
    if st.session_state.quiz_started and st.session_state.conversation_id:
        # Create main chat container
        chat_container = st.container()
        
        # Message area with auto-scroll
        with chat_container:
            messages_area = st.empty()
            
            # Combine all messages into HTML
            messages_html = ""
            for message in st.session_state.messages:
                role_style = "user-message" if message["role"] == "user" else "bot-message"
                icon = "👤" if message["role"] == "user" else "🤖"
                messages_html += f"""
                    <div class="chat-message {role_style}">
                        <div class="chat-icon">{icon}</div>
                        <div class="message-content">{message["content"]}</div>
                    </div>
                """
            
            # Display all messages in the empty container
            messages_area.markdown(f"""
                <div class="chat-container">
                    <div class="message-area" id="message-area">
                        {messages_html}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Input area at the bottom
            input_container = st.container()
            with input_container:
                cols = st.columns([8, 2])
                with cols[0]:
                    user_input = st.text_input("", 
                                             placeholder="Type your response here...", 
                                             key="user_input", 
                                             label_visibility="collapsed")
        
        # Auto-scroll script
        st.markdown("""
            <script>
                function scrollToBottom() {
                    var messageArea = document.querySelector('.message-area');
                    if (messageArea) {
                        messageArea.scrollTop = messageArea.scrollHeight;
                    }
                }
                // Call immediately and after a short delay to ensure content is loaded
                scrollToBottom();
                setTimeout(scrollToBottom, 100);
            </script>
        """, unsafe_allow_html=True)
        
        if user_input:
            # Save user message
            db_ops.save_message(st.session_state.conversation_id, "user", user_input)
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # Generate and save bot response
            with st.spinner("Thinking..."):
                bot_response = openai_service.generate_response(st.session_state.messages)
                db_ops.save_message(st.session_state.conversation_id, "assistant", bot_response)
                st.session_state.messages.append({"role": "assistant", "content": bot_response})
            
            st.rerun()

if __name__ == "__main__":
    main()
