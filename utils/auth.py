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
            "SELECT id, password_hash, first_name, last_name, role FROM users WHERE username = %s",
            (username,)
        )
        result = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if result and result[1] == Auth.hash_password(password):
            return True, result[0], result[2], result[3], result[4]  # Returns success, user_id, first_name, last_name, role
        return False, None, None, None, None

    @staticmethod
    def register_user(username: str, password: str, first_name: str, last_name: str, role: str = 'student') -> bool:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute(
                """INSERT INTO users (username, password_hash, first_name, last_name, role) 
                   VALUES (%s, %s, %s, %s, %s)""",
                (username, Auth.hash_password(password), first_name, last_name, role)
            )
            
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception:
            return False
            
    @staticmethod
    def is_instructor(user_id: int) -> bool:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT role FROM users WHERE id = %s", (user_id,))
        result = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return result and result[0] == 'instructor'
