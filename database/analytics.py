from datetime import datetime, timedelta
from .models import get_db_connection
import pandas as pd
import numpy as np

class AnalyticsOperations:
    @staticmethod
    def update_message_analytics(message_id):
        """Update analytics for a single message"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            # Calculate message metrics
            cur.execute("""
                WITH message_metrics AS (
                    SELECT 
                        m.id,
                        m.conversation_id,
                        c.user_id,
                        LENGTH(m.content) - LENGTH(REPLACE(m.content, ' ', '')) + 1 as word_count,
                        EXTRACT(EPOCH FROM (m.timestamp - LAG(m.timestamp) OVER (
                            PARTITION BY m.conversation_id 
                            ORDER BY m.timestamp
                        ))) as response_time
                    FROM messages m
                    JOIN conversations c ON m.conversation_id = c.id
                    WHERE m.id = %s
                )
                UPDATE messages m
                SET 
                    word_count = mm.word_count,
                    response_time = CASE 
                        WHEN mm.response_time > 3600 THEN NULL 
                        ELSE mm.response_time 
                    END
                FROM message_metrics mm
                WHERE m.id = mm.id
            """, (message_id,))
            
            conn.commit()
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def update_conversation_analytics(conversation_id):
        """Update analytics for a conversation"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                WITH conversation_metrics AS (
                    SELECT 
                        conversation_id,
                        COUNT(*) FILTER (WHERE role = 'user') as response_count,
                        AVG(response_time) FILTER (WHERE response_time < 3600) as avg_response_time
                    FROM messages
                    WHERE conversation_id = %s
                    GROUP BY conversation_id
                )
                UPDATE conversations c
                SET 
                    response_count = cm.response_count,
                    average_response_time = cm.avg_response_time
                FROM conversation_metrics cm
                WHERE c.id = cm.conversation_id
            """, (conversation_id,))
            
            conn.commit()
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def update_user_analytics(user_id):
        """Update analytics summary for a user"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                WITH user_metrics AS (
                    SELECT 
                        c.user_id,
                        COUNT(DISTINCT c.id) as total_conversations,
                        COUNT(m.id) FILTER (WHERE m.role = 'user') as total_messages,
                        AVG(m.response_time) FILTER (WHERE m.response_time < 3600) as avg_response_time,
                        AVG(EXTRACT(EPOCH FROM (c.end_time - c.start_time)) / 60) 
                            FILTER (WHERE c.end_time IS NOT NULL) as avg_session_length,
                        MAX(m.timestamp) as last_active,
                        CAST(COUNT(*) FILTER (WHERE c.completion_status = 'completed') AS FLOAT) / 
                            NULLIF(COUNT(*), 0) * 100 as completion_rate
                    FROM conversations c
                    LEFT JOIN messages m ON c.id = m.conversation_id
                    WHERE c.user_id = %s
                    GROUP BY c.user_id
                )
                INSERT INTO analytics_summary (
                    user_id, total_conversations, total_messages, 
                    average_response_time, average_session_length,
                    last_active, completion_rate, updated_at
                )
                SELECT 
                    user_id, total_conversations, total_messages,
                    avg_response_time, avg_session_length,
                    last_active, completion_rate, CURRENT_TIMESTAMP
                FROM user_metrics
                ON CONFLICT (user_id) DO UPDATE 
                SET 
                    total_conversations = EXCLUDED.total_conversations,
                    total_messages = EXCLUDED.total_messages,
                    average_response_time = EXCLUDED.average_response_time,
                    average_session_length = EXCLUDED.average_session_length,
                    last_active = EXCLUDED.last_active,
                    completion_rate = EXCLUDED.completion_rate,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id,))
            
            conn.commit()
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def get_user_analytics(user_id=None, days=30):
        """Get analytics data for visualization"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            if user_id:
                # Individual user analytics
                cur.execute("""
                    SELECT 
                        u.username,
                        a.total_conversations,
                        a.total_messages,
                        ROUND(a.average_response_time::numeric, 2) as avg_response_time,
                        ROUND(a.average_session_length::numeric, 2) as avg_session_length,
                        a.last_active,
                        ROUND(a.completion_rate::numeric, 2) as completion_rate
                    FROM analytics_summary a
                    JOIN users u ON a.user_id = u.id
                    WHERE a.user_id = %s
                """, (user_id,))
                return cur.fetchone()
            else:
                # Overall analytics
                cur.execute("""
                    SELECT 
                        DATE(m.timestamp) as date,
                        COUNT(DISTINCT c.id) as conversations,
                        COUNT(DISTINCT c.user_id) as active_users,
                        ROUND(AVG(m.response_time) FILTER (WHERE m.response_time < 3600)::numeric, 2) as avg_response_time,
                        ROUND(AVG(EXTRACT(EPOCH FROM (c.end_time - c.start_time)) / 60) 
                            FILTER (WHERE c.end_time IS NOT NULL)::numeric, 2) as avg_session_length
                    FROM messages m
                    JOIN conversations c ON m.conversation_id = c.id
                    WHERE m.timestamp >= CURRENT_DATE - INTERVAL '%s days'
                    GROUP BY DATE(m.timestamp)
                    ORDER BY date DESC
                """, (days,))
                return cur.fetchall()
        finally:
            cur.close()
            conn.close()
