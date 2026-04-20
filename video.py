import os
import sqlite3
import json
import datetime
import hashlib
import shutil
from config import get_storage_config, get_config

_VIDEOS_DIR = None
_DB_PATH = None

def get_videos_dir():
    global _VIDEOS_DIR
    if _VIDEOS_DIR is None:
        storage_config = get_storage_config()
        base_dir = os.path.join(os.path.dirname(__file__), storage_config.get('data_dir', 'data'))
        _VIDEOS_DIR = os.path.join(base_dir, storage_config.get('videos_dir', 'videos'))
        os.makedirs(_VIDEOS_DIR, exist_ok=True)
    return _VIDEOS_DIR

def get_db_path():
    global _DB_PATH
    if _DB_PATH is None:
        storage_config = get_storage_config()
        base_dir = os.path.join(os.path.dirname(__file__), storage_config.get('data_dir', 'data'))
        _DB_PATH = os.path.join(base_dir, storage_config.get('db_name', 'ink_pool.db'))
    return _DB_PATH

def init_video_database():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            video_path TEXT NOT NULL,
            thumbnail_path TEXT,
            difficulty TEXT DEFAULT 'entry',
            tags TEXT,
            uploader TEXT DEFAULT 'admin',
            views INTEGER DEFAULT 0,
            duration INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_video_metadata(title, description, video_path, difficulty='entry', tags=None, uploader='admin', thumbnail_path=None, duration=None):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO videos (title, description, video_path, thumbnail_path, difficulty, tags, uploader, duration)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (title, description, video_path, thumbnail_path, difficulty, json.dumps(tags) if tags else None, uploader, duration))
    
    video_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return video_id

def update_video_views(video_id):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('UPDATE videos SET views = views + 1 WHERE id = ?', (video_id,))
    
    conn.commit()
    conn.close()

def get_all_videos(difficulty=None, limit=50):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    if difficulty:
        cursor.execute('''
            SELECT id, title, description, video_path, thumbnail_path, difficulty, tags, views, duration, created_at
            FROM videos
            WHERE difficulty = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (difficulty, limit))
    else:
        cursor.execute('''
            SELECT id, title, description, video_path, thumbnail_path, difficulty, tags, views, duration, created_at
            FROM videos
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
    
    videos = cursor.fetchall()
    conn.close()
    return videos

def search_videos(keyword, difficulty=None):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    query = '''
        SELECT id, title, description, video_path, thumbnail_path, difficulty, tags, views, duration, created_at
        FROM videos
        WHERE (title LIKE ? OR description LIKE ? OR tags LIKE ?)
    '''
    params = (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%')
    
    if difficulty:
        query += ' AND difficulty = ?'
        params = params + (difficulty,)
    
    cursor.execute(query, params)
    videos = cursor.fetchall()
    conn.close()
    return videos

def get_video_by_id(video_id):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, title, description, video_path, thumbnail_path, difficulty, tags, views, duration, created_at
        FROM videos
        WHERE id = ?
    ''', (video_id,))
    
    video = cursor.fetchone()
    conn.close()
    return video

def check_video_title_exists(title):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM videos WHERE title = ?', (title,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def delete_video(video_id):
    video = get_video_by_id(video_id)
    if video:
        video_path = video[3]
        if os.path.exists(video_path):
            os.remove(video_path)
        
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute('DELETE FROM videos WHERE id = ?', (video_id,))
        conn.commit()
        conn.close()
        return True
    return False

def save_uploaded_video(video_file, title, description, difficulty='entry', tags=None):
    if video_file is None:
        return None
    
    config = get_config().get('video', {})
    allowed_formats = config.get('allowed_formats', ['mp4', 'webm', 'mov'])
    max_size = config.get('max_file_size', 104857600)
    
    ext = os.path.splitext(video_file.name)[1][1:].lower()
    if ext not in allowed_formats:
        return None
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    hash_id = hashlib.md5(f"{timestamp}".encode()).hexdigest()[:8]
    filename = f"{timestamp}_{hash_id}.{ext}"
    
    user_dir = get_videos_dir()
    os.makedirs(user_dir, exist_ok=True)
    
    dest_path = os.path.join(user_dir, filename)
    
    if hasattr(video_file, 'read'):
        with open(dest_path, 'wb') as f:
            f.write(video_file.read())
    else:
        shutil.copy(video_file, dest_path)
    
    video_id = save_video_metadata(title, description, dest_path, difficulty, tags)
    
    return video_id