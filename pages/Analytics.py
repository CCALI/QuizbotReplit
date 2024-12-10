import streamlit as st
import plotly.express as px
import pandas as pd
from database.models import get_db_connection

def calculate_engagement_score(interactions, words):
    """Calculate engagement score based on chat interactions and word count"""
    if interactions >= 5 and words >= 500:
        return 3
    elif interactions <= 2 or words <= 50:
        return 1
    else:
        return 2

def run_analytics_dashboard():
    st.title("QuizBot Analytics Dashboard")
    
    # Check if user is logged in
    if 'user_id' not in st.session_state or not st.session_state.user_id:
        st.warning("Please log in to view analytics.")
        return
    
    # Get conversation metrics
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            c.title,
            COUNT(CASE WHEN m.role = 'user' THEN 1 END) as chat_interactions,
            SUM(CASE WHEN m.role = 'user' THEN COALESCE(m.word_count, 0) ELSE 0 END) as total_words
        FROM conversations c
        LEFT JOIN messages m ON c.id = m.conversation_id
        WHERE c.user_id = %s
        GROUP BY c.id, c.title
        ORDER BY c.start_time DESC
    """, (st.session_state.user_id,))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    if not results:
        st.info("No conversation data available yet.")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(results, columns=['title', 'chat_interactions', 'total_words'])
    
    # Handle NULL values in calculations
    df['engagement_score'] = df.apply(
        lambda x: calculate_engagement_score(
            x['chat_interactions'] or 0,  # Handle NULL
            x['total_words'] or 0  # Handle NULL
        ), 
        axis=1
    )
    
    # First Dashboard - Conversation Metrics
    st.header("Conversation Metrics")
    
    # Display metrics in a table
    st.dataframe(
        df[['title', 'chat_interactions', 'total_words']],
        column_config={
            'title': 'Conversation',
            'chat_interactions': 'Number of Interactions',
            'total_words': 'Total Words'
        },
        hide_index=True
    )
    
    # Second Dashboard - Engagement Scores
    st.header("Engagement Scores")
    
    # Calculate average engagement score
    avg_score = df['engagement_score'].mean()
    
    # Display average score
    st.metric(
        "Average Engagement Score",
        f"{avg_score:.1f}",
        help="Score 3: ≥5 chats AND ≥500 words\nScore 2: In between\nScore 1: ≤2 chats OR ≤50 words"
    )
    
    # Show score distribution
    fig = px.histogram(
        df,
        x='engagement_score',
        nbins=3,
        title='Distribution of Engagement Scores',
        labels={'engagement_score': 'Score', 'count': 'Number of Conversations'},
        range_x=[0.5, 3.5]  # Center the bars on 1, 2, 3
    )
    
    fig.update_layout(
        bargap=0.2,
        xaxis=dict(tickmode='array', tickvals=[1, 2, 3])
    )
    
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    run_analytics_dashboard()
