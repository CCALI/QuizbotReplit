import streamlit as st
from datetime import datetime, timedelta
from .models import get_db_connection
import pandas as pd
import numpy as np
import re

class AnalyticsOperations:
    @staticmethod
    def count_sentences(text):
        """Count the number of sentences in a text"""
        if not text:
            return 0
        # Simple sentence counting based on period, exclamation, and question marks
        sentences = re.split(r'[.!?]+', text)
        # Filter out empty strings
        return len([s for s in sentences if s.strip()])

    @staticmethod
    def update_message_analytics(message_id):
        """Update analytics for a single message"""
        conn = get_db_connection()
        cur = conn.cursor()
        message_content = None  # Initialize the variable
        
        try:
            # Get message content and handle potential None result
            cur.execute("SELECT content FROM messages WHERE id = %s", (message_id,))
            result = cur.fetchone()
            if result:
                message_content = result[0]
            
            if not message_content:
                return
                
            sentence_count = AnalyticsOperations.count_sentences(message_content)
            
            # Calculate message metrics including sentence count
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
                    END,
                    sentence_count = %s
                FROM message_metrics mm
                WHERE m.id = mm.id
                RETURNING mm.conversation_id
            """, (message_id, sentence_count))
            
            # Get the conversation_id
            result = cur.fetchone()
            if result:
                conversation_id = result[0]
                
                # Update conversation sentence count
                cur.execute("""
                    UPDATE conversations
                    SET sentence_count = (
                        SELECT COALESCE(SUM(sentence_count), 0)
                        FROM messages
                        WHERE conversation_id = %s
                        AND role = 'user'
                    )
                    WHERE id = %s
                """, (conversation_id, conversation_id))
            
            conn.commit()
        except Exception as e:
            st.error(f"Error updating message analytics: {str(e)}")
        finally:
            cur.close()
            conn.close()
