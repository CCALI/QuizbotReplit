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
            "SELECT id, password_hash FROM users WHERE username = %s",
            (username,)
        )
        result = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if result and result[1] == Auth.hash_password(password):
            return True, result[0]
        return False, None

    @staticmethod
    def register_user(username: str, password: str) -> bool:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, Auth.hash_password(password))
            )
            
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception:
            return False
