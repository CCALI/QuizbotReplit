import streamlit as st
import pandas as pd
import plotly.express as px
from database.models import get_db_connection
from database.analytics import AnalyticsOperations
from utils.auth import Auth
import os

def run_instructor_dashboard():
    st.title("Instructor Dashboard")
    
    # Check if user is logged in and is an instructor
    if 'user_id' not in st.session_state or not st.session_state.user_id:
        st.warning("Please log in to access the instructor dashboard.")
        return
        
    if not Auth.is_instructor(st.session_state.user_id):
        st.error("Access denied. This page is only accessible to instructors.")
        return
    
    # Create tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Student Progress", "Content Management", "Class Analytics"])
    
    with tab1:
        show_student_progress()
    
    with tab2:
        manage_content()
        
    with tab3:
        show_class_analytics()

def show_student_progress():
    st.subheader("Student Progress")
    
    # Get all students and their progress
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            u.id,
            u.first_name || ' ' || u.last_name as student_name,
            COUNT(DISTINCT c.id) as total_conversations,
            AVG(a.interaction_grade) as avg_grade,
            MAX(c.start_time) as last_activity,
            ROUND(AVG(a.average_response_time)::numeric, 2) as avg_response_time,
            ROUND(AVG(c.sentence_count)::numeric, 2) as avg_sentences
        FROM users u
        LEFT JOIN conversations c ON u.id = c.user_id
        LEFT JOIN analytics_summary a ON u.id = a.user_id
        WHERE u.role = 'student'
        GROUP BY u.id, u.first_name, u.last_name
        ORDER BY last_activity DESC NULLS LAST
    """)
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    if not results:
        st.info("No student data available.")
        return
        
    # Convert to DataFrame
    df = pd.DataFrame(results, columns=[
        'student_id', 'student_name', 'total_conversations',
        'avg_grade', 'last_activity', 'avg_response_time',
        'avg_sentences'
    ])
    
    # Display student list with metrics
    st.dataframe(df.style.format({
        'avg_grade': '{:.1f}',
        'avg_response_time': '{:.1f}',
        'avg_sentences': '{:.1f}'
    }))
    
    # Add student details expander
    student_id = st.selectbox("Select student for detailed view", 
                            options=df['student_id'].tolist(),
                            format_func=lambda x: df[df['student_id'] == x]['student_name'].iloc[0])
    
    if student_id:
        with st.expander("Student Details", expanded=True):
            show_student_details(student_id)

def show_student_details(student_id):
    # Get student's conversation history
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            c.id,
            c.title,
            c.start_time,
            c.end_time,
            c.sentence_count,
            c.completion_status,
            a.interaction_grade
        FROM conversations c
        LEFT JOIN analytics_summary a ON c.user_id = a.user_id
        WHERE c.user_id = %s
        ORDER BY c.start_time DESC
    """, (student_id,))
    
    conversations = cur.fetchall()
    cur.close()
    conn.close()
    
    if conversations:
        df = pd.DataFrame(conversations, columns=[
            'id', 'title', 'start_time', 'end_time', 
            'sentence_count', 'status', 'grade'
        ])
        
        # Show conversation history
        st.write("Conversation History")
        st.dataframe(df.style.format({
            'start_time': lambda x: x.strftime('%Y-%m-%d %H:%M'),
            'end_time': lambda x: x.strftime('%Y-%m-%d %H:%M') if pd.notnull(x) else 'Ongoing',
            'grade': '{:.1f}'
        }))
        
        # Show progress charts
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.line(df, x='start_time', y='sentence_count',
                         title='Engagement Over Time')
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            fig = px.histogram(df, x='grade',
                             title='Grade Distribution',
                             nbins=3)
            st.plotly_chart(fig, use_container_width=True)

def manage_content():
    st.subheader("Content Management")
    
    # Show current reading materials
    st.write("Current Reading Materials")
    readings_folder = "Readings"
    
    if not os.path.exists(readings_folder):
        os.makedirs(readings_folder)
    
    files = [f for f in os.listdir(readings_folder) if f.endswith('.pdf')]
    
    if files:
        for file in files:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(file)
            with col2:
                if st.button("Remove", key=f"remove_{file}"):
                    try:
                        os.remove(os.path.join(readings_folder, file))
                        st.success(f"Removed {file}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error removing file: {str(e)}")
    else:
        st.info("No reading materials uploaded yet.")
    
    # Upload new materials
    st.write("Upload New Material")
    uploaded_file = st.file_uploader("Choose a PDF file", type=['pdf'])
    
    if uploaded_file:
        try:
            with open(os.path.join(readings_folder, uploaded_file.name), 'wb') as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"Uploaded {uploaded_file.name}")
            st.rerun()
        except Exception as e:
            st.error(f"Error uploading file: {str(e)}")

def show_class_analytics():
    st.subheader("Class Analytics")
    
    # Get class-wide analytics
    analytics_data = AnalyticsOperations.get_user_analytics(days=30)
    
    if not analytics_data:
        st.info("No class analytics available yet.")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(analytics_data, columns=[
        'date', 'conversations', 'active_users', 
        'avg_response_time', 'avg_session_length',
        'avg_word_count', 'most_common_grade'
    ])
    
    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Total Students",
            len(df['active_users'].unique()),
            f"{df['active_users'].mean():.1f} avg active/day"
        )
    with col2:
        st.metric(
            "Total Conversations",
            df['conversations'].sum(),
            f"{df['conversations'].mean():.1f} avg/day"
        )
    with col3:
        st.metric(
            "Avg Session Length",
            f"{df['avg_session_length'].mean():.1f} min",
            f"{df['avg_session_length'].std():.1f} min std"
        )
    with col4:
        st.metric(
            "Avg Response Length",
            f"{df['avg_word_count'].mean():.1f} words",
            f"{df['avg_word_count'].std():.1f} words std"
        )
    
    # Detailed analytics charts
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.line(df, x='date', y=['conversations', 'active_users'],
                     title='Daily Activity')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.box(df, y=['avg_response_time', 'avg_session_length'],
                    title='Response Time & Session Length Distribution')
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    run_instructor_dashboard()
