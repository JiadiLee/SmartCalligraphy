import os
import json
import sqlite3
import uuid
from config import get_storage_config, get_config, get_model_config

try:
    import lazyllm
    LAZYLLM_AVAILABLE = True
except ImportError:
    LAZYLLM_AVAILABLE = False
    lazyllm = None

_DOCUMENTS = None
_RETRIEVER = None
_LLM = None
_RAG_PIPELINE = None
_STOP_FLAG = False

def get_db_path():
    storage_config = get_storage_config()
    base_dir = os.path.join(os.path.dirname(__file__), storage_config.get('data_dir', 'data'))
    _DB_PATH = os.path.join(base_dir, storage_config.get('db_name', 'ink_pool.db'))
    return _DB_PATH

def get_chroma_dir():
    storage_config = get_storage_config()
    base_dir = os.path.join(os.path.dirname(__file__), storage_config.get('data_dir', 'data'))
    _CHROMA_DIR = os.path.join(base_dir, storage_config.get('chroma_name', 'chroma_db'))
    return _CHROMA_DIR

def get_docs_dir():
    storage_config = get_storage_config()
    base_dir = os.path.join(os.path.dirname(__file__), storage_config.get('data_dir', 'data'))
    docs_dir = os.path.join(base_dir, 'documents')
    os.makedirs(docs_dir, exist_ok=True)
    return docs_dir

def get_index_path():
    storage_config = get_storage_config()
    base_dir = os.path.join(os.path.dirname(__file__), storage_config.get('data_dir', 'data'))
    os.makedirs(base_dir, exist_ok=True)
    knowledge_config = get_config().get('knowledge', {})
    return os.path.join(base_dir, knowledge_config.get('faiss_index_file', 'knowledge.index'))

def init_knowledge_database():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_docs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            difficulty TEXT DEFAULT 'entry',
            tags TEXT,
            file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doc_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id INTEGER,
            video_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (doc_id) REFERENCES knowledge_docs(id),
            FOREIGN KEY (video_id) REFERENCES videos(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT DEFAULT 'default_user',
            query TEXT NOT NULL,
            answer TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def init_knowledge_index():
    global _DOCUMENTS, _RETRIEVER, _LLM, _RAG_PIPELINE
    
    if not LAZYLLM_AVAILABLE:
        print("Warning: lazyllm not available")
        return
    
    init_knowledge_database()
    docs_dir = get_docs_dir()
    
    if not os.path.exists(docs_dir):
        os.makedirs(docs_dir, exist_ok=True)
    
    model_config = get_model_config()
    source = model_config.get('source', 'openai')
    base_url = model_config.get('base_url', 'https://llmapi.paratera.com/v1')
    api_key = model_config.get('api_key', '')
    
    os.environ['LAZYLLM_BASE_URL'] = base_url
    os.environ['LAZYLLM_API_KEY'] = api_key
    
    try:
        embed_model = lazyllm.OnlineEmbeddingModule(
            source="siliconflow",
            api_key=model_config.get('siliconflow_key', None),
            embed_model_name=model_config.get('embed_model', 'GLM-Embedding-2')
        )
        chroma_dir = get_chroma_dir()
        store_conf = {
            'type': 'chroma',
            'kwargs': {
                'dir': chroma_dir
            }
        }
        _DOCUMENTS = lazyllm.Document(
            dataset_path=docs_dir,
            embed=embed_model,
            manager=False,
            store_conf=store_conf
        )
        
        _RETRIEVER = lazyllm.Retriever(
            doc=_DOCUMENTS,
            group_name="CoarseChunk",
            similarity="cosine",
            topk=3
        )
        
        _LLM = lazyllm.OnlineChatModule(
            source=model_config.get('source', 'openai'),
            base_url=model_config.get('base_url', None),
            api_key=model_config.get('api_key', None),
            model=model_config.get('text_model', 'Qwen2.5-VL-72B-Instruct'),
            timeout=60
        )
        
        prompt = '你是一位书法知识问答助手。请根据以下参考资料回答用户的问题。\n\n参考资料：\n{context_str}\n\n问题：{query}'
        _LLM.prompt(lazyllm.ChatPrompter(instruction=prompt, extra_keys=['context_str']))
        
        with lazyllm.pipeline() as ppl:
            ppl.retriever = _RETRIEVER
            
            def formatter_func(nodes, query=None):
                return dict(
                    context_str="".join([node.get_content() for node in nodes]) if nodes else "",
                    query=query if query else ""
                )
            ppl.formatter = formatter_func
            ppl.llm = _LLM
        
        _RAG_PIPELINE = lazyllm.ActionModule(ppl)
        _RAG_PIPELINE.start()
        
        print("RAG pipeline initialized successfully")
        
    except Exception as e:
        print(f"Warning: Failed to init RAG pipeline: {e}")
        print("Knowledge search will use simple text matching instead")
        _DOCUMENTS = None
        _RETRIEVER = None
        _LLM = None
        _RAG_PIPELINE = None

def add_document_to_kb(title, content, file_path=None):
    doc_uuid = str(uuid.uuid4())
    
    if file_path is None:
        docs_dir = get_docs_dir()
        safe_title = "".join(c for c in title if c not in r'<>:"/\|?*')
        file_name = f"{doc_uuid}-{safe_title}.txt"
        file_path = os.path.join(docs_dir, file_name)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO knowledge_docs (id, title, content, difficulty, tags, file_path)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (doc_uuid, title, content, 'entry', json.dumps([]), file_path))
    
    conn.commit()
    conn.close()
    
    if _DOCUMENTS is not None:
        try:
            _DOCUMENTS.update()
        except:
            pass
    
    return doc_uuid

def search_knowledge(query, top_k=5):
    """
    搜索知识库，支持文档分块聚合。
    通过内容中的标题线索和文本相似度，将chunk聚合到原始文档。
    """
    if _RETRIEVER is None:
        return simple_search(query, top_k)
    
    try:
        # 获取更多 chunk 以便聚合
        doc_node_list = _RETRIEVER(query=query)
        print(f"[DEBUG] Retrieved {len(doc_node_list)} chunks from retriever")
        
        # 先获取所有知识库文档，用于匹配和聚合
        all_kb_docs = []
        try:
            conn = sqlite3.connect(get_db_path())
            cursor = conn.cursor()
            cursor.execute('SELECT id, title, content FROM knowledge_docs')
            all_kb_docs = cursor.fetchall()
            conn.close()
            print(f"[DEBUG] Loaded {len(all_kb_docs)} documents from KB")
        except Exception as e:
            print(f"[DEBUG] Could not load KB docs: {e}")
        
        # 用于聚合文档的字典：doc_id -> {chunks, title, difficulty, tags}
        doc_aggregator = {}
        
        for node in doc_node_list:
            node_content = node.get_content() if hasattr(node, 'get_content') else str(node)
            
            # 提取 chunk 元数据
            chunk_meta = {
                'content': node_content,
                'doc_id': None,
                'title': None,
                'difficulty': 'entry',
                'tags': []
            }
            
            # 1. 从 metadata 提取信息
            if hasattr(node, 'metadata') and node.metadata:
                chunk_meta['doc_id'] = (node.metadata.get('doc_id') or 
                                       node.metadata.get('id') or 
                                       node.metadata.get('source_id') or
                                       node.metadata.get('document_id'))
                chunk_meta['title'] = node.metadata.get('title')
                chunk_meta['difficulty'] = node.metadata.get('difficulty', 'entry')
                try:
                    chunk_meta['tags'] = json.loads(node.metadata.get('tags', '[]'))
                except:
                    pass
            
            # 2. 从 global_metadata 提取
            if not chunk_meta['doc_id'] and hasattr(node, 'global_metadata') and node.global_metadata:
                chunk_meta['doc_id'] = (node.global_metadata.get('doc_id') or 
                                       node.global_metadata.get('id') or 
                                       node.global_metadata.get('source_id'))
                if not chunk_meta['title']:
                    chunk_meta['title'] = node.global_metadata.get('title')
            
            # 3. 从 docpath 或 content 中提取文件名作为候选标题
            if not chunk_meta['title']:
                if hasattr(node, 'docpath') and node.docpath:
                    chunk_meta['title'] = os.path.basename(node.docpath)
                else:
                    # 尝试从内容首行提取标题（如 "《木及其部首的写法》教学设计"）
                    first_line = node_content.split('\n')[0].strip()
                    if len(first_line) <= 100 and not first_line.startswith('{') and not first_line.startswith('#'):
                        chunk_meta['title'] = first_line
            
            print(f"[DEBUG] Chunk: doc_id={chunk_meta['doc_id']}, title={chunk_meta['title'][:30] if chunk_meta['title'] else None}...")
            
            # 聚合：使用 doc_id 或 title 作为 key
            doc_key = chunk_meta['doc_id'] if chunk_meta['doc_id'] is not None else chunk_meta['title']
            
            if doc_key not in doc_aggregator:
                doc_aggregator[doc_key] = {
                    'chunks': [],
                    'title': chunk_meta['title'] or '相关文档',
                    'difficulty': chunk_meta['difficulty'],
                    'tags': chunk_meta['tags'],
                    'doc_id': chunk_meta['doc_id']
                }
            
            doc_aggregator[doc_key]['chunks'].append(node_content)
        
        # 将聚合的 chunks 转换为结果格式
        results = []
        for doc_key, info in doc_aggregator.items():
            # 组合所有 chunk 内容
            combined_content = ' '.join(info['chunks'])
            if len(combined_content) > 500:
                combined_content = combined_content[:500] + "..."
            
            # 如果还没有 doc_id，尝试通过标题匹配数据库
            doc_id = info['doc_id']
            if doc_id is None and info['title'] and info['title'] != '相关文档':
                best_match = find_best_doc_match(info['title'], all_kb_docs)
                if best_match:
                    doc_id = best_match[0]
                    if info['difficulty'] == 'entry' and best_match[2]:
                        info['difficulty'] = best_match[2]
                print(f"[DEBUG] Matched doc_id={doc_id} for title '{info['title'][:30]}'")
            
            results.append({
                'id': doc_id,
                'title': info['title'],
                'content': combined_content,
                'difficulty': info['difficulty'],
                'tags': info['tags'],
                'score': 1.0
            })
        
        print(f"[DEBUG] Aggregated into {len(results)} documents")
        return results[:top_k]
        
    except Exception as e:
        print(f"Search error: {e}")
        import traceback
        traceback.print_exc()
        return simple_search(query, top_k)


def find_best_doc_match(chunk_title, kb_docs):
    """
    通过标题相似度为 chunk 找到最匹配的数据库文档。
    返回 (doc_id, title, difficulty, tags) 或 None
    """
    if not chunk_title or not kb_docs:
        return None
    
    # 清理文件名：去除哈希前缀和扩展名
    import re
    clean_chunk = re.sub(r'^\d+_[a-f0-9]+_', '', chunk_title)  # 移除哈希前缀
    clean_chunk = os.path.splitext(clean_chunk)[0]  # 移除扩展名
    
    best_score = -1
    best_doc = None
    
    for doc in kb_docs:
        doc_id, doc_title, doc_content = doc
        score = 0
        
        # 1. 标题完全匹配
        if chunk_title.strip() == doc_title.strip():
            score += 100
        # 2. 清理后的文件名匹配文档标题
        elif clean_chunk.strip() in doc_title.strip() or doc_title.strip() in clean_chunk.strip():
            score += 80
        # 3. 文件名关键词匹配
        else:
            clean_chunk_lower = clean_chunk.lower()
            doc_title_lower = doc_title.lower()
            # 计算重叠词数
            chunk_words = set(clean_chunk_lower.replace('.docx','').replace('.txt','').split())
            title_words = set(doc_title_lower.split())
            overlap = len(chunk_words & title_words)
            if overlap > 0:
                score += 20 * overlap
        
        if score > best_score:
            best_score = score
            best_doc = doc
    
    return best_doc if best_score > 0 else None


def simple_search(query, top_k=5):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, title, content, difficulty, tags, file_path FROM knowledge_docs')
    docs = cursor.fetchall()
    conn.close()
    
    query_lower = query.lower()
    results = []
    
    for doc in docs:
        score = 0
        if query_lower in doc[1].lower():
            score += 10
        if query_lower in doc[2].lower():
            score += 5
        
        if score > 0:
            results.append({
                'id': doc[0],
                'title': doc[1],
                'content': doc[2],
                'difficulty': doc[3],
                'tags': json.loads(doc[4]) if doc[4] else [],
                'file_path': doc[5],
                'score': score
            })
    
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:top_k]

def get_all_docs():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, title, content, difficulty, tags, file_path FROM knowledge_docs ORDER BY id')
    docs = cursor.fetchall()
    conn.close()
    
    return [{'id': d[0], 'title': d[1], 'content': d[2], 'difficulty': d[3], 'tags': json.loads(d[4]) if d[4] else [], 'file_path': d[5]} for d in docs]

def delete_knowledge_doc(doc_id):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('SELECT file_path FROM knowledge_docs WHERE id = ?', (doc_id,))
    doc = cursor.fetchone()
    
    if doc and doc[0]:
        file_path = doc[0]
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
    
    cursor.execute('DELETE FROM doc_videos WHERE doc_id = ?', (doc_id,))
    cursor.execute('DELETE FROM knowledge_docs WHERE id = ?', (doc_id,))
    conn.commit()
    conn.close()
    
    if _DOCUMENTS is not None:
        try:
            _DOCUMENTS.update()
        except:
            pass
    
    return True

def add_knowledge_doc(title, content, difficulty='entry', tags=None, file_path=None):
    return add_document_to_kb(title, content, file_path)

def link_doc_video(doc_id, video_id):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO doc_videos (doc_id, video_id)
        VALUES (?, ?)
    ''', (doc_id, video_id))
    
    conn.commit()
    conn.close()
    
    return True

def save_chat_history(user_id, query, answer):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO chat_history (user_id, query, answer)
        VALUES (?, ?, ?)
    ''', (user_id, query, answer))
    conn.commit()
    conn.close()

def get_chat_history(user_id, limit=20):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        SELECT query, answer, created_at FROM chat_history 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (user_id, limit))
    results = cursor.fetchall()
    conn.close()
    return [[str(row[2]), row[0]] for row in results]


def get_full_chat_history(user_id, limit=20):
    """返回完整的聊天历史，包含问题和答案"""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, query, answer, created_at FROM chat_history 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (user_id, limit))
    results = cursor.fetchall()
    conn.close()
    return [{'id': row[0], 'query': row[1], 'answer': row[2], 'created_at': str(row[3])} for row in results]


def delete_chat_history_record(user_id, query):
    """删除指定的历史记录"""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM chat_history 
        WHERE user_id = ? AND query = ?
    ''', (user_id, query))
    conn.commit()
    conn.close()
    return True

def get_doc_videos(doc_id):
    from video import get_all_videos
    
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('SELECT video_id FROM doc_videos WHERE doc_id = ?', (doc_id,))
    video_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    if not video_ids:
        return []
    
    all_videos = get_all_videos(limit=100)
    linked_videos = []
    for v in all_videos:
        v_id = v[0]
        if v_id in video_ids:
            linked_videos.append({
                'id': v[0],
                'title': v[1],
                'description': v[2],
                'path': v[3],
                'views': v[7]
            })
    
    return linked_videos

def find_related_videos(query, top_k=3):
    from video import search_videos, get_all_videos
    
    query_lower = query.lower()
    all_videos = get_all_videos(limit=50)
    
    if not all_videos:
        return []
    
    scored_videos = []
    for v in all_videos:
        v_id, v_title, v_desc, v_path, _, _, _, v_views, _, _ = v
        score = 0
        
        if v_title and query_lower in v_title.lower():
            score += 10
        if v_desc and query_lower in v_desc.lower():
            score += 5
        
        if score > 0:
            scored_videos.append({
                'id': v_id,
                'title': v_title,
                'description': v_desc,
                'views': v_views,
                'score': score
            })
    
    scored_videos.sort(key=lambda x: x['score'], reverse=True)
    return scored_videos[:top_k]

def set_stop_flag():
    global _STOP_FLAG
    _STOP_FLAG = True

def reset_stop_flag():
    global _STOP_FLAG
    _STOP_FLAG = False

def query_rag(question):
    global _RAG_PIPELINE, _STOP_FLAG
    
    if _RAG_PIPELINE is None:
        return "RAG系统未初始化，请先上传文档到知识库"
    
    reset_stop_flag()
    
    try:
        result = _RAG_PIPELINE(query=question)
        return str(result) if result else "未找到相关答案"
    except Exception as e:
        print(f"RAG query error: {e}")
        return f"查询出错: {str(e)}"

def query_rag_stream(question):
    global _RAG_PIPELINE, _STOP_FLAG
    
    if _RAG_PIPELINE is None:
        yield "RAG系统未初始化，请先上传文档到知识库"
        return
    
    reset_stop_flag()
    
    try:
        if hasattr(_RAG_PIPELINE, 'stream'):
            for chunk in _RAG_PIPELINE.stream(query=question):
                if _STOP_FLAG:
                    break
                yield str(chunk)
        else:
            result = _RAG_PIPELINE(query=question)
            yield str(result) if result else "未找到相关答案"
    except Exception as e:
        print(f"RAG query error: {e}")
        yield f"查询出错: {str(e)}"

def rebuild_index():
    global _DOCUMENTS
    
    if _DOCUMENTS is not None:
        try:
            _DOCUMENTS.update()
        except Exception as e:
            print(f"Failed to update documents: {e}")