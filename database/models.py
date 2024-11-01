from datetime import datetime
import psycopg2
import os

def get_db_connection():
    return psycopg2.connect(
        dbname=os.environ['PGDATABASE'],
        user=os.environ['PGUSER'],
        password=os.environ['PGPASSWORD'],
        host=os.environ['PGHOST'],
        port=os.environ['PGPORT']
    )

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Create users table with full name fields
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(200) NOT NULL,
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create conversations table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP
        )
    """)
    
    # Create messages table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER REFERENCES conversations(id),
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Add new columns if they don't exist
    cur.execute("""
        DO $$ 
        BEGIN 
            BEGIN
                ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name VARCHAR(100);
            EXCEPTION 
                WHEN duplicate_column THEN 
                    NULL;
            END;
            BEGIN
                ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name VARCHAR(100);
            EXCEPTION 
                WHEN duplicate_column THEN 
                    NULL;
            END;
        END $$;
    """)
    
    conn.commit()
    cur.close()
    conn.close()
