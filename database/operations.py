from .models import get_db_connection
from datetime import datetime

class DatabaseOperations:
    @staticmethod
    def save_message(conversation_id: int, role: str, content: str):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s)",
            (conversation_id, role, content)
        )
        conn.commit()
        cur.close()
        conn.close()

    @staticmethod
    def create_conversation(user_id: int) -> int:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO conversations (user_id) VALUES (%s) RETURNING id",
            (user_id,)
        )
        conversation_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return conversation_id

    @staticmethod
    def end_conversation(conversation_id: int):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE conversations SET end_time = %s WHERE id = %s",
            (datetime.now(), conversation_id)
        )
        conn.commit()
        cur.close()
        conn.close()

    @staticmethod
    def get_conversation_messages(conversation_id: int):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT role, content, timestamp, 
                   (SELECT start_time FROM conversations WHERE id = %s) as start_time,
                   (SELECT end_time FROM conversations WHERE id = %s) as end_time
            FROM messages 
            WHERE conversation_id = %s 
            ORDER BY timestamp""",
            (conversation_id, conversation_id, conversation_id)
        )
        messages = cur.fetchall()
        cur.close()
        conn.close()
        return messages

    @staticmethod
    def format_transcript(messages) -> str:
        if not messages:
            return "No messages found in conversation."
        
        # Get conversation start and end times from the first message
        start_time = messages[0][3]
        end_time = messages[0][4]
        
        # Format header
        transcript = [
            "=== QuizBot Conversation Transcript ===",
            f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"{'Ended: ' + end_time.strftime('%Y-%m-%d %H:%M:%S') if end_time else 'Status: Ongoing'}",
            "=" * 50,
            ""
        ]
        
        # Format messages
        for role, content, timestamp, _, _ in messages:
            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            speaker = "QuizBot" if role == "assistant" else "You"
            transcript.extend([
                f"[{timestamp_str}] {speaker}:",
                f"{content}",
                "-" * 40,
                ""
            ])
        
        return "\n".join(transcript)
