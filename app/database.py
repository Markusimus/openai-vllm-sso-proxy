import sqlite3
from datetime import datetime
import threading
from pathlib import Path

DB_PATH = "/app/data/usage.db"

def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Approved users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS approved_users (
            id INTEGER PRIMARY KEY,
            user_id TEXT UNIQUE NOT NULL,
            email TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Usage logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY,
            request_id TEXT,
            user_id TEXT,
            model TEXT,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            duration_ms INTEGER,
            status TEXT
        )
    """)
    
    # User usage summary for fast quota checks
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_usage_summary (
            user_id TEXT PRIMARY KEY,
            month TEXT,
            total_tokens INTEGER DEFAULT 0,
            request_count INTEGER DEFAULT 0
        )
    """)
    
    conn.commit()
    conn.close()

# Thread-local connection for SQLite
local = threading.local()

def get_db():
    if not hasattr(local, "conn"):
        local.conn = sqlite3.connect(DB_PATH)
    return local.conn

init_db()
