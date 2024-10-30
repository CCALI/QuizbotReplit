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
        cur.execute(
            "SELECT role, content FROM messages WHERE conversation_id = %s ORDER BY timestamp",
            (conversation_id,)
        )
        messages = cur.fetchall()
        cur.close()
        conn.close()
        return messages
