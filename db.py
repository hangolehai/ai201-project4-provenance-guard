import sqlite3
import os
import json

DB_FILE = 'provenance.db'

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            content_id TEXT PRIMARY KEY,
            creator_id TEXT,
            timestamp TEXT,
            attribution TEXT,
            confidence REAL,
            llm_score REAL,
            stylometric_score REAL,
            status TEXT,
            appeal_reasoning TEXT,
            has_metadata INTEGER DEFAULT 0
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS verified_creators (
            creator_id TEXT PRIMARY KEY,
            verification_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def insert_log(content_id, creator_id, timestamp, attribution, confidence, llm_score, stylometric_score, status="classified", appeal_reasoning=None, has_metadata=0):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO audit_log (content_id, creator_id, timestamp, attribution, confidence, llm_score, stylometric_score, status, appeal_reasoning, has_metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (content_id, creator_id, timestamp, attribution, confidence, llm_score, stylometric_score, status, appeal_reasoning, has_metadata))
    conn.commit()
    conn.close()

def get_logs():
    conn = get_db_connection()
    logs = conn.execute('SELECT * FROM audit_log ORDER BY timestamp DESC').fetchall()
    conn.close()
    return [dict(ix) for ix in logs]

def update_log_appeal(content_id, creator_reasoning):
    conn = get_db_connection()
    conn.execute('''
        UPDATE audit_log
        SET status = 'under_review', appeal_reasoning = ?
        WHERE content_id = ?
    ''', (creator_reasoning, content_id))
    conn.commit()
    conn.close()

def verify_creator(creator_id, timestamp):
    conn = get_db_connection()
    conn.execute('INSERT OR REPLACE INTO verified_creators (creator_id, verification_date) VALUES (?, ?)', (creator_id, timestamp))
    conn.commit()
    conn.close()

def is_creator_verified(creator_id):
    conn = get_db_connection()
    res = conn.execute('SELECT 1 FROM verified_creators WHERE creator_id = ?', (creator_id,)).fetchone()
    conn.close()
    return res is not None

def get_analytics():
    conn = get_db_connection()
    total = conn.execute('SELECT COUNT(*) FROM audit_log').fetchone()[0]
    if total == 0:
        return {"total_submissions": 0}
        
    ai_count = conn.execute("SELECT COUNT(*) FROM audit_log WHERE attribution='likely_ai'").fetchone()[0]
    human_count = conn.execute("SELECT COUNT(*) FROM audit_log WHERE attribution='likely_human'").fetchone()[0]
    uncertain_count = conn.execute("SELECT COUNT(*) FROM audit_log WHERE attribution='uncertain'").fetchone()[0]
    
    under_review = conn.execute("SELECT COUNT(*) FROM audit_log WHERE status='under_review'").fetchone()[0]
    avg_conf = conn.execute("SELECT AVG(confidence) FROM audit_log").fetchone()[0]
    conn.close()
    
    return {
        "total_submissions": total,
        "detection_patterns": {
            "likely_ai": ai_count,
            "likely_human": human_count,
            "uncertain": uncertain_count
        },
        "appeal_rate_percentage": (under_review / total) * 100,
        "average_confidence_score": round(avg_conf, 3)
    }
