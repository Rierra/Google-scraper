import sqlite3
from datetime import datetime
from contextlib import contextmanager

import os

class Database:
    def __init__(self, db_path=None):
        # Use environment variable or default
        self.db_path = db_path or os.getenv('DATABASE_PATH', 'rankings.db')
        
        # Ensure directory exists for database
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        self.init_db()
    
    @contextmanager
    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def init_db(self):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            
            # Keywords table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL,
                    url TEXT NOT NULL,
                    country TEXT,
                    proxy TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(keyword, url, country)
                )
            ''')
            
            # Position history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS position_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword_id INTEGER NOT NULL,
                    position INTEGER,
                    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE CASCADE
                )
            ''')
            
            # Processing queue table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processing_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword_id INTEGER NOT NULL,
                    queued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE CASCADE
                )
            ''')
            
            conn.commit()
    
    def add_keyword(self, keyword, url, country=None, proxy=None):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    'INSERT INTO keywords (keyword, url, country, proxy) VALUES (?, ?, ?, ?)',
                    (keyword, url, country, proxy)
                )
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                return None  # Already exists
    
    def get_all_keywords(self):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT k.id, k.keyword, k.url, k.country, k.proxy, k.created_at,
                       h.position, h.checked_at
                FROM keywords k
                LEFT JOIN (
                    SELECT keyword_id, position, checked_at,
                           ROW_NUMBER() OVER (PARTITION BY keyword_id ORDER BY checked_at DESC) as rn
                    FROM position_history
                ) h ON k.id = h.keyword_id AND h.rn = 1
                ORDER BY k.id DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def add_position_check(self, keyword_id, position):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO position_history (keyword_id, position) VALUES (?, ?)',
                (keyword_id, position)
            )
    
    def get_position_history(self, keyword_id, limit=10):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT position, checked_at FROM position_history WHERE keyword_id = ? ORDER BY checked_at DESC LIMIT ?',
                (keyword_id, limit)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_keyword(self, keyword_id):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM keywords WHERE id = ?', (keyword_id,))

    def update_keyword(self, keyword_id, keyword, url, country=None, proxy=None):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE keywords SET keyword = ?, url = ?, country = ?, proxy = ? WHERE id = ?',
                (keyword, url, country, proxy, keyword_id)
            )
            return cursor.rowcount > 0 # Returns True if a row was updated
