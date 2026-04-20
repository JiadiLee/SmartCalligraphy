import gradio as gr
import sqlite3
import random
import datetime
from config import get_ui_config, get_server_config
from storage import save_uploaded_image
from database import (
    save_work, get_user_works, save_checkin, get_checkin_stats, 
    unlock_achievement, get_user_achievements, save_favorite_work, 
    get_today_favorite_work, get_work_by_id, get_all_checkins_with_works, 
    get_checkins_by_date, get_db_path, get_recent_checkins_with_reviews,
    get_today_checkin_work
)
from config import get_achievements_config, get_flower_config
import agent as agent_module


def get_achievements_markdown(user_id='default_user'):
    achievements = get_user_achievements(user_id)
    if not achievements:
        return "暂无成就，快去打卡吧！"
    md = "**🏆 成就徽章**："
    for ach in achievements:
        ach_id, name, icon, unlocked_at = ach
        if name and icon:
            if md != "**🏆 成就徽章**：":
                md += "  "
            md += f"{icon} **{name}**"
    if not md:
        return "暂无成就，快去打卡吧！"
    return md


def build_practice_ui():
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 📸 上传您的书法作品")
            
            input_image = gr.Image(
                label="点击上传", 
                type="filepath", 
                height=349
            )
            
            submit_btn = gr.Button(
                "🔍 开始 人工智能点评", 
                variant="primary", 
                size="lg"
            )
        
        with gr.Column(scale=2):
            gr.Markdown("### 📝 人工智能的点评")
            output_text = gr.Markdown(
                value="上传作品后点击点评按钮，人工智能将为您分析作品...",
                height=390,
                container=True,
                elem_classes=["my-markdown-card"]
            )
    
    submit_btn.click(
        fn=handle_evaluate,
        inputs=input_image,
        outputs=output_text,
        api_name="evaluate"
    )
    
    with gr.Row(): 
        with gr.Column(scale=2):
            gr.HTML("<h3 style='text-align:center'>📜 历史作品</h3>")

    with gr.Row():
        current_year = datetime.datetime.now().year
        current_month = datetime.datetime.now().month
        current_day = datetime.datetime.now().day
        years = [str(y) for y in range(current_year - 2, current_year + 1)]
        months = [str(m).zfill(2) for m in range(1, 13)]
        days = [str(d).zfill(2) for d in range(1, 32)]
        
        with gr.Column(scale=1):
            year_dropdown = gr.Dropdown(
                label="年",
                choices=years,
                value=str(current_year)
            )
        
        with gr.Column(scale=1):
            month_dropdown = gr.Dropdown(
                label="月",
                choices=months,
                value=str(current_month).zfill(2)
            )
        
        with gr.Column(scale=1):
            day_dropdown = gr.Dropdown(
                label="日",
                choices=days,
                value=str(current_day).zfill(2)
            )
        
        with gr.Column(scale=1):
            query_btn = gr.Button("🔍 查询", variant="primary")
        
        history_index = gr.State(value=0)
    
    with gr.Row():
        prev_btn = gr.Button("◀️ 上一张")
        next_btn = gr.Button("▶️ 下一张")
    
    with gr.Row():
        with gr.Column(scale=1):
            history_image = gr.Image(
                label="历史作品",
                type="filepath",
                height=349,
                interactive=False
            )
            history_time = gr.HTML("<div style='text-align:center;font-weight:bold'>暂无时间信息</div>")
        
        with gr.Column(scale=2):
            history_review = gr.Markdown(
                label="历史点评",
                height=350,
                container=True,
                elem_classes=["my-markdown-card"]
            )
            history_msg = gr.Markdown("*点击上下张按钮切换作品*")
    
    query_btn.click(
        fn=get_works_by_date,
        inputs=[year_dropdown, month_dropdown, day_dropdown],
        outputs=[history_image, history_review, history_index, history_time, history_msg]
    )
    
    prev_btn.click(
        fn=get_prev_work,
        inputs=[history_index, year_dropdown, month_dropdown, day_dropdown, history_image, history_review, history_time],
        outputs=[history_image, history_review, history_index, history_time, history_msg]
    )
    
    next_btn.click(
        fn=get_next_work,
        inputs=[history_index, year_dropdown, month_dropdown, day_dropdown, history_image, history_review, history_time],
        outputs=[history_image, history_review, history_index, history_time, history_msg]
    )


def handle_evaluate(image):
    if image is None:
        return "请先上传一张书法作品的图片哦！"
    
    saved_path = save_uploaded_image(image)
    
    result = ""
    from agent import evaluate_calligraphy_stream
    for chunk in evaluate_calligraphy_stream(saved_path):
        if chunk == "[DONE]":
            break
        result += chunk
        yield result
    
    if result:
        save_work(saved_path, result)


def get_works_by_date(year, month, day):
    works = get_user_works(limit=100)
    
    if not works:
        return gr.update(), "暂无作品", 0, "<div style='text-align:center;font-weight:bold'>暂无时间信息</div>", "*无作品*"
    
    date_str = f"{year}-{month}-{day}"
    works = [w for w in works if w[3] and w[3][:10] == date_str]
    
    if not works:
        return gr.update(), "暂无该日期的作品", 0, "<div style='text-align:center;font-weight:bold'>暂无时间信息</div>", "*该日期无作品*"
    
    works_sorted = sorted(works, key=lambda x: x[3], reverse=True)
    work = works_sorted[0]
    timestamp = work[3] if work[3] else "未知"
    return work[1], work[2] or "暂无点评", 0, f"<div style='text-align:center;font-weight:bold'>创建时间: {timestamp}</div>", "*查询成功*"


def get_prev_work(current_index, year="2026", month="04", day="01", prev_image=None, prev_review=None, prev_time=None):
    works = get_user_works(limit=100)
    
    date_str = f"{year}-{month}-{day}"
    works = [w for w in works if w[3] and w[3][:10] == date_str]
    works_sorted = sorted(works, key=lambda x: x[3], reverse=True)
    
    if not works_sorted:
        return prev_image, prev_review, current_index, gr.update(), "*已到达最早，没有更早的作品了*"
    
    new_index = current_index - 1
    if new_index < 0:
        return prev_image, prev_review, current_index, gr.update(), "*已到达最早，没有更早的作品了*"
    
    work = works_sorted[new_index]
    timestamp = work[3] if work[3] else "未知"
    return work[1], work[2] or "暂无点评", new_index, f"<div style='text-align:center;font-weight:bold'>创建时间: {timestamp}</div>", "*点击上下张按钮切换*"


def get_next_work(current_index, year="2026", month="04", day="01", prev_image=None, prev_review=None, prev_time=None):
    works = get_user_works(limit=100)
    
    date_str = f"{year}-{month}-{day}"
    works = [w for w in works if w[3] and w[3][:10] == date_str]
    works_sorted = sorted(works, key=lambda x: x[3], reverse=True)
    
    if not works_sorted:
        return prev_image, prev_review, current_index, gr.update(), "*已到达最晚，没有更晚的作品了*"
    
    new_index = current_index + 1
    if new_index >= len(works_sorted):
        return prev_image, prev_review, current_index, gr.update(), "*已到达最早，没有更早的作品了*"
    
    work = works_sorted[new_index]
    timestamp = work[3] if work[3] else "未知"
    return work[1], work[2] or "暂无点评", new_index, f"<div style='text-align:center;font-weight:bold'>创建时间: {timestamp}</div>", "*点击上下张按钮切换*"


def calculate_streak(user_id='default_user'):
    stats = get_checkin_stats(user_id)
    return stats.get('total_checkins', 0)


def build_checkin_ui():
    checkin_index = gr.State(value=0)
    
    current_date = datetime.datetime.now()
    current_year = current_date.year
    current_month = current_date.month
    current_day = current_date.day
    
    year_state = gr.State(str(current_year))
    month_state = gr.State(str(current_month).zfill(2))
    day_state = gr.State(str(current_day).zfill(2))
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 📅 笔耕不辍")
            gr.Markdown("从今天的书法作品中选择最满意的进行打卡吧~")
            
            checkin_gallery = gr.Image(
                label="选择打卡的作品",
                type="filepath",
                height=250,
                interactive=False
            )
            
            with gr.Row():
                prev_btn = gr.Button("◀️ 上一张", size="sm")
                next_btn = gr.Button("▶️ 下一张", size="sm")
            
            checkin_msg = gr.Markdown("*点击上下张按钮切换作品*")
            
            checkin_input = gr.Textbox(
                label="今日感想",
                placeholder="今天练习了什么？有什么收获？",
                lines=3
            )
            
            checkin_btn = gr.Button("✅ 确认打卡", variant="primary", size="lg")
            
            checkin_btn_msg = gr.Markdown("")
            
            checkin_btn_state = gr.State(value="confirm")
        
        with gr.Column(scale=1):
            total_streak_display = gr.Markdown("*累计打卡天数*")
            
            achievements_display = gr.Markdown("暂无成就，快去打卡吧！")
            
            gr.Markdown("<br>")
            
            gr.Markdown("### 📅 打卡历史")
            history_date_label = gr.HTML("<div style='text-align:center;font-weight:bold;font-size:18px;color:#333;'>2026-04-15</div>")
            
            history_gallery = gr.Image(
                type="filepath",
                height=240,
                interactive=False
            )
            
            with gr.Row():
                prev_history_btn = gr.Button("◀️ 上一张", size="sm")
                next_history_btn = gr.Button("▶️ 下一张", size="sm")
            
            history_checkin_text = gr.Textbox(
                label="感想",
                interactive=False,
                lines=2
            )
            
            history_checkin_msg = gr.Markdown("<div style='text-align:center;'>-</div>")
            
            history_checkin_index = gr.State(value=0)
    
    prev_btn.click(
        fn=get_prev_work_checkin,
        inputs=[checkin_index, year_state, month_state, day_state, checkin_gallery],
        outputs=[checkin_gallery, checkin_index]
    )
    
    next_btn.click(
        fn=get_next_work_checkin,
        inputs=[checkin_index, year_state, month_state, day_state, checkin_gallery],
        outputs=[checkin_gallery, checkin_index]
    )
    
    checkin_btn.click(
        fn=handle_checkin_from_gallery,
        inputs=[checkin_gallery, checkin_input, year_state, month_state, day_state],
        outputs=[total_streak_display, achievements_display, checkin_btn_msg, history_gallery, history_checkin_text, history_date_label, history_checkin_msg]
    )
    
    prev_history_btn.click(
        fn=get_prev_checkin_history,
        inputs=[history_checkin_index],
        outputs=[history_gallery, history_checkin_index, history_checkin_text, history_date_label, history_checkin_msg]
    )
    
    next_history_btn.click(
        fn=get_next_checkin_history,
        inputs=[history_checkin_index],
        outputs=[history_gallery, history_checkin_index, history_checkin_text, history_date_label, history_checkin_msg]
    )
    
    with gr.Row():
        gr.Markdown("<hr>")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 📈 成长轨迹")
            gr.Markdown("分析您最近的打卡记录，看看有没有进步~")
        
        with gr.Column(scale=1):
            analyze_growth_btn = gr.Button("🔍 分析成长轨迹", variant="primary")
    
    with gr.Row():
        growth_result = gr.Markdown(
            value="*点击按钮分析最近10天的成长*",
            height=400,
            container=True,
            elem_classes=["my-markdown-card"]
        )
    
    analyze_growth_btn.click(
        fn=handle_analyze_growth,
        inputs=[],
        outputs=growth_result
    )
    
    return checkin_gallery, year_state, month_state, day_state, checkin_msg, total_streak_display, achievements_display, history_gallery, history_checkin_text, history_date_label, history_checkin_msg, growth_result


def get_prev_work_checkin(current_index, year, month, day, current_image):
    works = get_user_works(limit=100)
    
    date_str = f"{year}-{month}-{day}"
    works = [w for w in works if w[3] and w[3][:10] == date_str]
    works_sorted = sorted(works, key=lambda x: x[3], reverse=True)
    
    if not works_sorted:
        return current_image, current_index
    
    new_index = current_index - 1
    if new_index < 0:
        new_index = len(works_sorted) - 1
    
    work = works_sorted[new_index]
    return work[1], new_index


def get_next_work_checkin(current_index, year, month, day, current_image):
    works = get_user_works(limit=100)
    
    date_str = f"{year}-{month}-{day}"
    works = [w for w in works if w[3] and w[3][:10] == date_str]
    works_sorted = sorted(works, key=lambda x: x[3], reverse=True)
    
    if not works_sorted:
        return current_image, current_index
    
    new_index = current_index + 1
    if new_index >= len(works_sorted):
        new_index = 0
    
    work = works_sorted[new_index]
    return work[1], new_index


def get_checkin_history_works(user_id='default_user'):
    checkins = get_all_checkins_with_works(user_id)
    return sorted(checkins, key=lambda x: x[2], reverse=True) if checkins else []


def load_default_checkin_history():
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    works = get_checkin_history_works('default_user')
    if not works:
        return gr.update(), "暂无打卡历史", "<div style='text-align:center;font-weight:bold;font-size:16px;color:#666;'>暂无日期</div>", ""
    for i, work in enumerate(works):
        if work[1] == today:
            checkin_date = work[1]
            checkin_text = work[3] or "无感想"
            image_path = work[5]
            date_label = f"<div style='text-align:center;font-weight:bold;font-size:18px;color:#333;'>{checkin_date}</div>"
            return image_path, checkin_text, date_label, ""
    work = works[0]
    checkin_date = work[1]
    checkin_text = work[3] or "无感想"
    image_path = work[5]
    date_label = f"<div style='text-align:center;font-weight:bold;font-size:18px;color:#333;'>{checkin_date}</div>"
    return image_path, checkin_text, date_label, ""


def get_prev_checkin_history(current_index):
    works = get_checkin_history_works('default_user')
    if not works:
        return gr.update(), current_index, "暂无打卡历史", "<div style='text-align:center;font-weight:bold;font-size:18px;color:#333;'>暂无日期</div>", ""
    new_index = current_index - 1
    if new_index < 0:
        current_date = works[current_index][1]
        current_checkin_text = works[current_index][3] or "无感想"
        msg = "<div style='text-align:center;font-weight:bold;color:#E74C3C;'>已经到最晚的打卡日期啦</div>"
        return gr.update(), current_index, current_checkin_text, f"<div style='text-align:center;font-weight:bold;font-size:18px;color:#333;'>{current_date}</div>", msg
    work = works[new_index]
    checkin_date = work[1]
    checkin_text = work[3] or "无感想"
    image_path = work[5]
    date_label = f"<div style='text-align:center;font-weight:bold;font-size:18px;color:#333;'>{checkin_date}</div>"
    return image_path, new_index, checkin_text, date_label, ""


def get_next_checkin_history(current_index):
    works = get_checkin_history_works('default_user')
    if not works:
        return gr.update(), current_index, "暂无打卡历史", "<div style='text-align:center;font-weight:bold;font-size:18px;color:#333;'>暂无日期</div>", ""
    new_index = current_index + 1
    if new_index >= len(works):
        current_date = works[current_index][1]
        current_checkin_text = works[current_index][3] or "无感想"
        msg = "<div style='text-align:center;font-weight:bold;color:#E74C3C;'>已经到最早的打卡日期啦</div>"
        return gr.update(), current_index, current_checkin_text, f"<div style='text-align:center;font-weight:bold;font-size:18px;color:#333;'>{current_date}</div>", msg
    work = works[new_index]
    checkin_date = work[1]
    checkin_text = work[3] or "无感想"
    image_path = work[5]
    date_label = f"<div style='text-align:center;font-weight:bold;font-size:18px;color:#333;'>{checkin_date}</div>"
    return image_path, new_index, checkin_text, date_label, ""


def check_and_unlock_achievements(streak_count, user_id='default_user'):
    achievements_config = get_achievements_config()
    unlocked = []
    
    existing_achievements = get_user_achievements(user_id)
    unlocked_ids = {ach[0] for ach in existing_achievements}
    
    for ach in achievements_config:
        if streak_count >= ach.get('requirement', 0):
            if ach['id'] not in unlocked_ids:
                unlock_achievement(ach['id'], ach['name'], ach['icon'], user_id)
                unlocked.append(ach['name'])
    
    return unlocked


def handle_checkin_from_gallery(image_path, checkin_text, year, month, day, user_id='default_user'):
    if image_path is None:
        return gr.update(), "请先选择作品！", gr.update(), gr.update(), "*请先选择作品！*"
    
    works = get_user_works(limit=100)
    
    date_str = f"{year}-{month}-{day}"
    works = [w for w in works if w[3] and w[3][:10] == date_str]
    
    if not works:
        works = get_user_works(limit=100)
        if works:
            work = works[0]
            work_id = work[0]
            checkin_date = f"{year}-{month}-{day}"
        else:
            return gr.update(), "作品未找到", gr.update(), gr.update(), "*作品未找到*"
    else:
        work = works[0]
        work_id = work[0]
        checkin_date = f"{year}-{month}-{day}"
    
    existing = get_checkins_by_date(user_id, checkin_date)
    
    total_checkins = calculate_streak(user_id)
    
    if existing and existing[1]:
        history_result = load_default_checkin_history()
        history_img = history_result[0] if history_result else gr.update()
        history_text = history_result[1] if history_result else "*暂无打卡历史*"
        history_date_label = history_result[2] if len(history_result) > 2 else "<div style='text-align:center;font-weight:bold;'>暂无日期</div>"
        history_checkin_msg = history_result[3] if len(history_result) > 3 else ""
        return f"### 📊 已打卡 **{total_checkins}** 天", gr.update(), "✅ 今日已完成打卡，请不要重复打卡！", history_img, history_text, history_date_label, history_checkin_msg
    else:
        new_total = total_checkins + 1
    
    save_favorite_work(user_id, work_id, checkin_date)
    
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE checkins SET checkin_text = ?, streak_count = ?
        WHERE user_id = ? AND checkin_date = ?
    ''', (checkin_text or "", new_total, user_id, checkin_date))
    conn.commit()
    conn.close()
    
    unlocked = check_and_unlock_achievements(new_total, user_id)
    
    result = f"### 📊 已打卡 **{new_total}** 天"
    
    achievement_md = get_achievements_markdown(user_id)
    if unlocked:
        result += "\n\n🎉 **新成就解锁！**\n"
        for ach in unlocked:
            result += f"- {ach}\n"
    
    history_result = load_default_checkin_history()
    history_img = history_result[0] if history_result else gr.update()
    history_text = history_result[1] if history_result else "*暂无打卡历史*"
    history_date_label = history_result[2] if len(history_result) > 2 else "<div style='text-align:center;font-weight:bold;'>暂无日期</div>"
    history_checkin_msg = history_result[3] if len(history_result) > 3 else ""
    
    new_btn_msg = "✅ 打卡成功！"
    return result, achievement_md, new_btn_msg, history_img, history_text, history_date_label, history_checkin_msg


def handle_analyze_growth(user_id='default_user'):
    from agent import analyze_growth
    from database import get_recent_checkins_with_reviews
    
    recent_checkins = get_recent_checkins_with_reviews(user_id, days=10)
    
    if not recent_checkins:
        return "暂无足够的打卡记录进行分析，请先进行打卡练习~"
    
    for chunk in analyze_growth(recent_checkins):
        if chunk == "[DONE]":
            continue
        yield chunk


def load_default_checkin_work(year, month, day):
    works = get_user_works(limit=100)
    total_checkins = calculate_streak('default_user')
    
    date_str = f"{year}-{month}-{day}"
    works = [w for w in works if w[3] and w[3][:10] == date_str]
    works_sorted = sorted(works, key=lambda x: x[3], reverse=True)
    
    if not works_sorted:
        return gr.update(), "暂无今日作品，请先让AI进行评价哦~", f"### 📊 已打卡 **{total_checkins}** 天"
    
    work = works_sorted[0]
    return work[1], "<div style='text-align:center;font-size:14px;color:#888;'>*点击上下张按钮切换作品*</div>", f"### 📊 已打卡 **{total_checkins}** 天"


current_keyword = None
recognized_chars = []
all_recognized_chars = []
used_poems = []
chat_history = ""


def build_game_ui():
    global current_keyword, recognized_chars, used_poems, chat_history
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 🎮 飞花令")
            gr.Markdown("从今天打卡的书法作品中识别文字，选择后开始游戏！")
            
            work_image = gr.Image(
                label="今日打卡作品",
                type="filepath",
                height=275,
                interactive=False
            )
            
            loading_msg = gr.Markdown("*点击识别按钮加载今日打卡作品*")
            
            recognize_btn = gr.Button("🔍 识别文字", variant="primary")
            
            char_dropdown = gr.Dropdown(
                label="选择关键字",
                choices=[],
                interactive=True
            )
            
            start_game_btn = gr.Button("🎲 开始游戏", variant="primary")
        
        with gr.Column(scale=2):
            gr.Markdown("### 🏮 诗词接龙")
            gr.Markdown("请写出包含指定字的诗句，挑战你的诗词储备！")
            
            keyword_display = gr.Markdown("**当前关键字：** 请先识别文字")
            
            poem_input = gr.Textbox(
                label="请输入诗句",
                placeholder="例：举头望明月",
                lines=1
            )
            
            submit_poem_btn = gr.Button("✅ 提交", variant="primary")
            
            result_display = gr.Textbox(
                label="聊天记录",
                value="请点击开始游戏",
                lines=10,
                max_lines=10,
                interactive=False
            )
            
            restart_btn = gr.Button("🔄 重新开始", variant="secondary")
    
    recognize_btn.click(
        fn=handle_recognize_chars,
        inputs=[],
        outputs=[char_dropdown, work_image, loading_msg]
    )
    
    start_game_btn.click(
        fn=handle_start_game_from_dropdown,
        inputs=char_dropdown,
        outputs=[result_display, keyword_display]
    )
    
    submit_poem_btn.click(
        fn=handle_poem_check,
        inputs=poem_input,
        outputs=result_display
    )
    
    restart_btn.click(
        fn=reset_game,
        inputs=[],
        outputs=[keyword_display, result_display, char_dropdown]
    )
    
    return work_image, loading_msg


def handle_recognize_chars(user_id='default_user'):
    image_path = get_today_checkin_work(user_id)
    
    if not image_path:
        return gr.update(choices=[]), None, "*暂无今日打卡作品，请先完成打卡！*"
    
    from agent import recognize_text_from_image
    chars = recognize_text_from_image(image_path)
    
    if not chars:
        return gr.update(choices=[]), image_path, "*未能识别到文字，请重试*"
    
    global recognized_chars, all_recognized_chars
    all_chars = list(chars)
    all_recognized_chars = all_chars.copy()
    total_count = len(all_chars)
    random.shuffle(all_chars)
    recognized_chars = all_chars[:8] if total_count >= 8 else all_chars
    
    choices = recognized_chars if recognized_chars else []
    first_value = choices[0] if choices else None
    return gr.update(choices=choices, value=first_value), image_path, f"*已识别到 {total_count} 个汉字，随机选择 {len(recognized_chars)} 个用于飞花令*"


def handle_start_game_from_dropdown(selected_char):
    global current_keyword
    
    if not selected_char:
        return gr.update(value="请先选择关键字！"), gr.update(value="**当前关键字：** 请先选择关键字")
    
    current_keyword = selected_char
    return gr.update(value=f"请写出含【{current_keyword}】的诗句"), gr.update(value=f"**当前关键字：** 【{current_keyword}】")


def handle_poem_check(poem_text):
    global current_keyword, used_poems, chat_history
    
    if current_keyword is None:
        return "⚠️ 请先点击「开始游戏」选择一个关键字后再提交诗句！\n\n" + chat_history
    
    if not poem_text or not poem_text.strip():
        return chat_history
    
    poem_text = poem_text.strip()
    
    if current_keyword not in poem_text:
        chat_history += f"\n❌ 诗句中必须包含【{current_keyword}】字哦，请再试一次！"
        return chat_history
    
    is_correct, feedback = agent_module.check_poem_keyword(poem_text, current_keyword, used_poems)
    
    if is_correct == "duplicate":
        chat_history += f"\n❌ 这句诗已经说过过了，请换一句！"
        return chat_history
    
    if is_correct is True:
        used_poems.append(poem_text)
        chat_history += f"\n👤 你：{poem_text}"
        
        ai_poem, ai_success = agent_module.generate_ai_response(poem_text, current_keyword, used_poems)
        
        if ai_success:
            used_poems.append(ai_poem)
            chat_history += f"\n🤖 AI：{ai_poem}"
            chat_history += f"\n\n➡️ 请继续输入包含【{current_keyword}】的诗句，或点击「重新开始」换一个新的关键字！"
            return chat_history
        else:
            chat_history += f"\n🤖 AI：无法对出"
            chat_history += f"\n\n🎉 AI连续3次无法对出，你赢了！点击「重新开始」开始新游戏！"
            current_keyword = None
            used_poems = []
            return chat_history
    elif is_correct is False:
        chat_history += f"\n❌ {feedback}"
        chat_history += f"\n\n💡 游戏结束，点击「重新开始」开始新游戏！"
        current_keyword = None
        used_poems = []
        return chat_history
    else:
        return chat_history


def clear_game_state():
    global current_keyword, used_poems, chat_history, recognized_chars, all_recognized_chars
    current_keyword = None
    used_poems = []
    chat_history = ""
    recognized_chars = []
    all_recognized_chars = []


def reset_game():
    global current_keyword, used_poems, chat_history, recognized_chars, all_recognized_chars
    current_keyword = None
    used_poems = []
    chat_history = "请点击开始游戏"
    
    if all_recognized_chars:
        import random
        random.shuffle(all_recognized_chars)
        new_recognized_chars = all_recognized_chars[:8]
        recognized_chars = new_recognized_chars
        new_choice = new_recognized_chars[0]
        return gr.update(value="**当前关键字：** " + new_choice), chat_history, gr.update(value=new_choice, choices=new_recognized_chars)
    elif recognized_chars:
        import random
        random.shuffle(recognized_chars)
        new_choice = recognized_chars[0]
        return gr.update(value="**当前关键字：** " + new_choice), chat_history, gr.update(value=new_choice, choices=recognized_chars)
    else:
        return gr.update(value="**当前关键字：** 请先识别文字"), chat_history, gr.update(value="", choices=[])


def build_module_ui():
    build_practice_ui()
    with gr.Row():
        gr.Markdown("---")
    build_checkin_ui()
    with gr.Row():
        gr.Markdown("---")
    build_game_ui()