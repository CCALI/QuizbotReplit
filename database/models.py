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
    
    # Create users table with full name fields and role
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(200) NOT NULL,
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            role VARCHAR(20) DEFAULT 'student',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Update role column if it exists, add if it doesn't
    cur.execute('''
        DO $$ 
        BEGIN 
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='users' AND column_name='role') THEN
                ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'student';
            ELSE
                ALTER TABLE users ALTER COLUMN role SET DEFAULT 'student';
            END IF;
        END $$;
    ''')
    
    # Create or update conversations table with additional analytics fields
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            title VARCHAR(200),
            context TEXT,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            response_count INTEGER DEFAULT 0,
            average_response_time FLOAT DEFAULT 0,
            completion_status VARCHAR(20) DEFAULT 'ongoing',
            sentence_count INTEGER DEFAULT 0
        )
    """)
    
    # Add completion_status column if it doesn't exist
    cur.execute('''
        DO $$ 
        BEGIN 
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='conversations' AND column_name='completion_status') THEN
                ALTER TABLE conversations ADD COLUMN completion_status VARCHAR(20) DEFAULT 'ongoing';
            END IF;
        END $$;
    ''')
    
    # Create messages table with additional analytics fields
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER REFERENCES conversations(id),
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            response_time INTEGER,
            word_count INTEGER,
            sentence_count INTEGER
        )
    """)
    
    # Create analytics_summary table with interaction grade
    cur.execute("""
        CREATE TABLE IF NOT EXISTS analytics_summary (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            total_conversations INTEGER DEFAULT 0,
            total_messages INTEGER DEFAULT 0,
            average_response_time FLOAT DEFAULT 0,
            average_session_length FLOAT DEFAULT 0,
            last_active TIMESTAMP,
            completion_rate FLOAT DEFAULT 0,
            interaction_grade INTEGER DEFAULT 1,
            average_word_count FLOAT DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cur.close()
    conn.close()
