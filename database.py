import sqlite3
import json
import datetime
from config import get_storage_config, get_config

_DB_PATH = None

def get_db_path():
    global _DB_PATH
    if _DB_PATH is None:
        storage_config = get_storage_config()
        data_dir = os.path.join(os.path.dirname(__file__), storage_config.get('data_dir', 'data'))
        os.makedirs(data_dir, exist_ok=True)
        _DB_PATH = os.path.join(data_dir, storage_config.get('db_name', 'ink_pool.db'))
    return _DB_PATH

import os

def init_database():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS works (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT DEFAULT 'default_user',
            image_path TEXT NOT NULL,
            review_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            dimensions TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT DEFAULT 'default_user',
            checkin_date DATE NOT NULL,
            checkin_text TEXT,
            streak_count INTEGER DEFAULT 0,
            favorite_work_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, checkin_date)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS achievements (
            id TEXT PRIMARY KEY,
            user_id TEXT DEFAULT 'default_user',
            name TEXT NOT NULL,
            icon TEXT,
            unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_work(image_path, review_text, user_id='default_user', dimensions=None):
    import datetime
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT INTO works (user_id, image_path, review_text, created_at, dimensions)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, image_path, review_text, current_time, json.dumps(dimensions) if dimensions else None))
    
    work_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return work_id

def get_user_works(user_id='default_user', limit=20):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, image_path, review_text, created_at, dimensions
        FROM works
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (user_id, limit))
    
    works = cursor.fetchall()
    conn.close()
    return works

def save_checkin(user_id='default_user', checkin_text='', streak_count=0):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    today = datetime.date.today().isoformat()
    
    cursor.execute('''
        INSERT OR REPLACE INTO checkins (user_id, checkin_date, checkin_text, streak_count)
        VALUES (?, ?, ?, ?)
    ''', (user_id, today, checkin_text, streak_count))
    
    conn.commit()
    conn.close()

def get_checkin_records(user_id='default_user'):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT checkin_date, checkin_text, streak_count
        FROM checkins
        WHERE user_id = ?
        ORDER BY checkin_date DESC
    ''', (user_id,))
    
    records = cursor.fetchall()
    conn.close()
    return records

def unlock_achievement(achievement_id, name, icon, user_id='default_user'):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR IGNORE INTO achievements (id, user_id, name, icon, unlocked_at)
        VALUES (?, ?, ?, ?, datetime('now'))
    ''', (achievement_id, user_id, name, icon))
    
    conn.commit()
    conn.close()

def get_user_achievements(user_id='default_user'):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, icon, unlocked_at
        FROM achievements
        WHERE user_id = ?
        ORDER BY unlocked_at DESC
    ''', (user_id,))
    
    achievements = cursor.fetchall()
    conn.close()
    return achievements

def get_checkin_stats(user_id='default_user'):
    records = get_checkin_records(user_id)
    
    current_streak = 0
    if records:
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        checkin_dates = [datetime.datetime.strptime(r[0], '%Y-%m-%d').date() for r in records]
        
        if today in checkin_dates:
            current_streak = records[0][2]
        elif yesterday in checkin_dates and records[0][2] > 0:
            current_streak = records[0][2]
    
    return {
        'total_checkins': len(records),
        'current_streak': current_streak,
        'records': records
    }

def save_favorite_work(user_id, work_id, checkin_date=None):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    if checkin_date is None:
        checkin_date = datetime.date.today().isoformat()
    
    cursor.execute('''
        INSERT OR REPLACE INTO checkins (user_id, checkin_date, favorite_work_id)
        VALUES (?, ?, ?)
    ''', (user_id, checkin_date, work_id))
    
    conn.commit()
    conn.close()

def get_today_favorite_work(user_id='default_user'):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    today = datetime.date.today().isoformat()
    
    cursor.execute('''
        SELECT favorite_work_id, checkin_text, streak_count
        FROM checkins
        WHERE user_id = ? AND checkin_date = ?
    ''', (user_id, today))
    
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0]:
        work_id = result[0]
        return get_work_by_id(work_id)
    
    return None

def get_work_by_id(work_id):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, image_path, review_text, created_at, dimensions
        FROM works
        WHERE id = ?
    ''', (work_id,))
    
    work = cursor.fetchone()
    conn.close()
    return work

def get_checkins_by_date(user_id='default_user', checkin_date=None):
    if checkin_date is None:
        checkin_date = datetime.date.today().isoformat()
    
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT c.checkin_date, c.favorite_work_id, c.checkin_text, c.streak_count, w.image_path, w.review_text, w.created_at
        FROM checkins c
        LEFT JOIN works w ON c.favorite_work_id = w.id
        WHERE c.user_id = ? AND c.checkin_date = ?
    ''', (user_id, checkin_date))
    
    result = cursor.fetchone()
    conn.close()
    return result

def get_all_checkins_with_works(user_id='default_user'):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT c.id, c.checkin_date, c.favorite_work_id, c.checkin_text, c.streak_count, w.image_path, w.review_text, w.created_at
        FROM checkins c
        LEFT JOIN works w ON c.favorite_work_id = w.id
        WHERE c.user_id = ?
        ORDER BY c.checkin_date DESC
        LIMIT 30
    ''', (user_id,))
    
    results = cursor.fetchall()
    conn.close()
    return results

def get_recent_checkins_with_reviews(user_id='default_user', days=10):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT c.checkin_date, w.review_text
        FROM checkins c
        LEFT JOIN works w ON c.favorite_work_id = w.id
        WHERE c.user_id = ? AND w.review_text IS NOT NULL AND w.review_text != ''
        ORDER BY c.checkin_date DESC
        LIMIT ?
    ''', (user_id, days))
    
    results = cursor.fetchall()
    conn.close()
    return results

def get_today_checkin_work(user_id='default_user'):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    today = datetime.date.today().isoformat()
    
    cursor.execute('''
        SELECT w.image_path
        FROM checkins c
        LEFT JOIN works w ON c.favorite_work_id = w.id
        WHERE c.user_id = ? AND c.checkin_date = ?
    ''', (user_id, today))
    
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0]:
        return result[0]
    return None