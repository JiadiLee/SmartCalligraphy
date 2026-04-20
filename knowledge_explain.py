import os
import sqlite3
import json
import datetime
from config import get_storage_config, get_model_config
from knowledge import search_knowledge, get_all_docs
from database import get_user_works
from video import search_videos

_DB_PATH = None

def get_db_path():
    global _DB_PATH
    if _DB_PATH is None:
        storage_config = get_storage_config()
        base_dir = os.path.join(os.path.dirname(__file__), storage_config.get('data_dir', 'data'))
        _DB_PATH = os.path.join(base_dir, storage_config.get('db_name', 'ink_pool.db'))
    return _DB_PATH

def get_user_recent_works(user_id='default_user', limit=10):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, review_text, created_at
        FROM works
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (user_id, limit))
    
    works = cursor.fetchall()
    conn.close()
    return works

def analyze_issues_from_reviews(reviews):
    issues = {
        '笔画': [],
        '结构': [],
        '章法': [],
        '其他': []
    }
    
    keywords_mapping = {
        '笔画': ['起笔', '收笔', '横', '竖', '撇', '捺', '点', '钩', '折', '笔法', '力度', '粗细'],
        '结构': ['结构', '重心', '分布', '均匀', '对称', '间架', '比例', '高低', '宽窄', '斜正'],
        '章法': ['章法', '布局', '行列', '间距', '留白', '整体'],
    }
    
    for review in reviews:
        if not review:
            continue
        
        review_text = review.lower()
        
        for category, keywords in keywords_mapping.items():
            for keyword in keywords:
                if keyword in review_text:
                    issues[category].append(keyword)
    
    for category in issues:
        issues[category] = list(set(issues[category]))[:5]
    
    return issues

def recommend_knowledge_for_issues(issues):
    recommendations = []
    
    for category, keywords in issues.items():
        for keyword in keywords[:2]:
            results = search_knowledge(keyword, top_k=2)
            for r in results:
                if r not in recommendations:
                    recommendations.append(r)
    
    if not recommendations:
        all_docs = get_all_docs()
        recommendations = [{'title': d['title'], 'content': d['content'], 'difficulty': d['difficulty'], 'tags': d['tags']} for d in all_docs[:3]]
    
    return recommendations[:5]

def recommend_videos_for_keyword(keyword):
    videos = search_videos(keyword)
    if videos:
        return videos[:2]
    return []

def generate_personalized_explanation(user_id='default_user'):
    works = get_user_recent_works(user_id, 10)
    
    if not works:
        return None, None, "暂无练习记录，请先完成墨迹留痕练习"
    
    reviews = [w[1] for w in works if w[1]]
    
    issues = analyze_issues_from_reviews(reviews)
    
    all_keywords = []
    for category, kw_list in issues.items():
        all_keywords.extend(kw_list)
    
    knowledge_recs = recommend_knowledge_for_issues(issues)
    
    video_recs = []
    for kw in all_keywords[:3]:
        vids = recommend_videos_for_keyword(kw)
        video_recs.extend(vids)
    video_recs = video_recs[:3]
    
    explanation = generate_explanation_text(issues, reviews)
    
    return knowledge_recs, video_recs, explanation

def generate_explanation_text(issues, reviews):
    if not reviews:
        return "根据您的练习记录，分析如下："
    
    issues_text = []
    for category, kw_list in issues.items():
        if kw_list:
            issues_text.append(f"{category}: {', '.join(kw_list)}")
    
    if not issues_text:
        issues_text = ["整体表现良好，继续保持练习"]
    
    explanation = "### 📊 问题分析\n\n"
    explanation += "根据您最近的练习，我发现了以下需要注意的方面：\n\n"
    
    for i, text in enumerate(issues_text, 1):
        explanation += f"{i}. {text}\n"
    
    explanation += "\n### 💡 学习建议\n\n"
    explanation += "1. 针对上述问题，建议重点练习相关技法\n"
    explanation += "2. 可以查看典籍库中的对应知识\n"
    explanation += "3. 观看万象库中的教学视频\n"
    explanation += "4. 坚持每日打卡，积小流以成江海\n"
    
    return explanation

def get_personalized_learning_content(user_id='default_user', image=None):
    from agent import evaluate_calligraphy
    
    if image:
        from storage import save_uploaded_image
        saved_path = save_uploaded_image(image)
        review = evaluate_calligraphy(saved_path)
        
        reviews = [review]
    else:
        works = get_user_recent_works(user_id, 5)
        reviews = [w[1] for w in works if w[1]]
    
    if not reviews:
        return "暂无练习记录，请先完成墨迹留痕练习"
    
    issues = analyze_issues_from_reviews(reviews)
    knowledge_recs = recommend_knowledge_for_issues(issues)
    video_recs = recommend_videos_for_issues(issues)
    
    result = "### 💡 个性化学习建议\n\n"
    result += "基于您的练习，我来帮您分析：\n\n"
    
    if issues['笔画']:
        result += "**📌 笔画问题：**\n"
        result += f"- {', '.join(issues['笔画'])}\n\n"
    
    if issues['结构']:
        result += "**📐 结构问题：**\n"
        result += f"- {', '.join(issues['结构'])}\n\n"
    
    if issues['章法']:
        result += "**📄 章法问题：**\n"
        result += f"- {', '.join(issues['章法'])}\n\n"
    
    if knowledge_recs:
        result += "**📚 推荐典籍：**\n"
        for i, k in enumerate(knowledge_recs, 1):
            result += f"{i}. {k['title']} ({k['difficulty']})\n"
        result += "\n"
    
    if video_recs:
        result += "**📺 推荐视频：**\n"
        for i, v in enumerate(video_recs, 1):
            result += f"{i}. {v[1]}\n"
    
    return result

def recommend_videos_for_issues(issues):
    video_recs = []
    
    for category, kw_list in issues.items():
        for keyword in kw_list[:2]:
            videos = search_videos(keyword)
            video_recs.extend(videos)
    
    seen = set()
    unique_videos = []
    for v in video_recs:
        if v[0] not in seen:
            seen.add(v[0])
            unique_videos.append(v)
    
    return unique_videos[:3]