import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from database.analytics import AnalyticsOperations
import numpy as np

def run_analytics_dashboard():
    st.title("QuizBot Analytics Dashboard")
    
    # Check if user is logged in and has admin access
    if 'user_id' not in st.session_state or not st.session_state.user_id:
        st.warning("Please log in to view analytics.")
        return
    
    # Time range selector
    time_range = st.selectbox(
        "Select Time Range",
        ["Last 7 Days", "Last 30 Days", "Last 90 Days"],
        index=1
    )
    
    days = int(time_range.split()[1])
    
    # Get analytics data
    analytics_data = AnalyticsOperations.get_user_analytics(days=days)
    
    if not analytics_data:
        st.info("No data available for the selected time range.")
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
            "Total Conversations",
            int(df['conversations'].sum()),
            f"{float(df['conversations'].mean()):.1f} avg/day"
        )
    with col2:
        st.metric(
            "Active Users",
            int(df['active_users'].sum()),
            f"{float(df['active_users'].mean()):.1f} avg/day"
        )
    with col3:
        st.metric(
            "Avg Session Length",
            f"{float(df['avg_session_length'].mean()):.1f} min",
            f"{float(df['avg_session_length'].std()):.1f} min std"
        )
    with col4:
        st.metric(
            "Avg Word Count",
            f"{float(df['avg_word_count'].mean()):.1f}",
            f"{float(df['avg_word_count'].std()):.1f} std"
        )
    
    # Engagement Trends
    st.subheader("Engagement Trends")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['conversations'],
        name='Conversations',
        mode='lines+markers'
    ))
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['active_users'],
        name='Active Users',
        mode='lines+markers'
    ))
    fig.update_layout(
        title='Daily Engagement',
        xaxis_title='Date',
        yaxis_title='Count',
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Interaction Grade Distribution
    st.subheader("Interaction Grade Distribution")
    grade_counts = df['most_common_grade'].value_counts()
    fig = px.pie(
        values=grade_counts.values,
        names=grade_counts.index,
        title='Distribution of Interaction Grades',
        labels={'most_common_grade': 'Grade', 'value': 'Count'},
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Response Analysis
    st.subheader("Response Analysis")
    cols = st.columns(2)
    
    with cols[0]:
        # Response Time Box Plot
        fig = px.box(
            df,
            y='avg_response_time',
            title='Response Time Distribution'
        )
        fig.update_layout(
            yaxis_title='Average Response Time (seconds)'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with cols[1]:
        # Word Count Trends
        fig = px.line(
            df,
            x='date',
            y='avg_word_count',
            title='Average Word Count Over Time'
        )
        fig.update_layout(
            xaxis_title='Date',
            yaxis_title='Average Word Count'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Session Length Trends
    st.subheader("Session Length Trends")
    fig = px.line(
        df,
        x='date',
        y='avg_session_length',
        title='Average Session Length Over Time'
    )
    fig.update_layout(
        xaxis_title='Date',
        yaxis_title='Average Session Length (minutes)'
    )
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    run_analytics_dashboard()
