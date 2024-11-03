import streamlit as st
import hashlib
from database.models import get_db_connection

class Auth:
    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def verify_user(username: str, password: str) -> tuple:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """SELECT id, password_hash, first_name, last_name, openai_api_key 
               FROM users WHERE username = %s""",
            (username,)
        )
        result = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if result and result[1] == Auth.hash_password(password):
            # If user has a custom API key, set it in session state
            if result[4]:
                st.session_state.custom_openai_key = result[4]
            return True, result[0], result[2], result[3], 'student'  # Returns success, user_id, first_name, last_name, role
        return False, None, None, None, None

    @staticmethod
    def register_user(username: str, password: str, first_name: str, last_name: str, openai_api_key: str = None) -> bool:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute(
                """INSERT INTO users (username, password_hash, first_name, last_name, role, openai_api_key) 
                   VALUES (%s, %s, %s, %s, 'student', %s)""",
                (username, Auth.hash_password(password), first_name, last_name, openai_api_key)
            )
            
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception:
            return False

    @staticmethod
    def update_api_key(user_id: int, api_key: str) -> bool:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute(
                "UPDATE users SET openai_api_key = %s WHERE id = %s",
                (api_key, user_id)
            )
            
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception:
            return False
