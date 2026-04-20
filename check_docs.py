import sqlite3
conn = sqlite3.connect('data/ink_pool.db')
cursor = conn.cursor()
cursor.execute('SELECT id, title, file_path FROM knowledge_docs')
rows = cursor.fetchall()
for r in rows:
    print(f"ID:{r[0]}, Title:{repr(r[1])}, Path:{r[2][:80] if r[2] else None}")
conn.close()
