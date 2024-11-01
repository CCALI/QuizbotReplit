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
            SELECT m.role, m.content, m.timestamp, 
                   c.start_time, c.end_time,
                   u.first_name, u.last_name
            FROM messages m
            JOIN conversations c ON m.conversation_id = c.id
            JOIN users u ON c.user_id = u.id
            WHERE m.conversation_id = %s 
            ORDER BY m.timestamp""",
            (conversation_id,)
        )
        messages = cur.fetchall()
        cur.close()
        conn.close()
        return messages

    @staticmethod
    def format_transcript(messages) -> str:
        if not messages:
            return "No messages found in conversation."
        
        # Get conversation details and user info from the first message
        _, _, _, start_time, end_time, first_name, last_name = messages[0]
        user_full_name = f"{first_name} {last_name}".strip() or "Anonymous User"
        
        # Format header
        transcript = [
            "=== QuizBot Conversation Transcript ===",
            f"Student: {user_full_name}",
            f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"{'Ended: ' + end_time.strftime('%Y-%m-%d %H:%M:%S') if end_time else 'Status: Ongoing'}",
            "=" * 50,
            ""
        ]
        
        # Format messages
        for role, content, timestamp, *_ in messages:
            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            speaker = "QuizBot" if role == "assistant" else user_full_name
            transcript.extend([
                f"[{timestamp_str}] {speaker}:",
                f"{content}",
                "-" * 40,
                ""
            ])
        
        return "\n".join(transcript)
