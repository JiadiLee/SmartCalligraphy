import gradio as gr
from config import get_server_config, load_config, setup_env
from database import init_database
from agent import init_agent

load_config()
init_database()
init_agent()

from video import init_video_database
init_video_database()

from knowledge import init_knowledge_database, init_knowledge_index
init_knowledge_database()
init_knowledge_index()

from modules import suyuan, mochi, lingxi


def create_main_app():
    server_config = get_server_config()
    
    with gr.Blocks() as demo:
        gr.Markdown(f"# 🖌️ {server_config.get('title', '墨池笔冢')}")
        gr.Markdown(f"*{server_config.get('subtitle', '积跬步以至千里，积小流以成江海')}*")
        
        with gr.Row():
            with gr.Column(scale=1, variant="panel"):
                gr.Markdown("#### 🔍 溯源寻踪")
                gr.Markdown("*追本溯源，寻找笔墨背后的逻辑与规律，构建系统化的知识网络。*")
                
                btn_video = gr.Button("🌌 万象库", size="sm")
                btn_knowledge = gr.Button("📜 典籍库", size="sm")
                btn_explain = gr.Button("💡 豁然开朗", size="sm")
                
                gr.Markdown("---")
                
                gr.Markdown("#### 🏠 墨池笔冢")
                gr.Markdown("*日拱一卒，功不唐捐。记录每一次笔墨的沉淀。*")
                
                btn_practice = gr.Button("✍️ 墨迹留痕", size="sm")
                btn_checkin = gr.Button("📅 笔耕不辍", size="sm")
                btn_game = gr.Button("🎮 飞花令", size="sm")
                
                gr.Markdown("---")
                
                gr.Markdown("#### ✨ 灵犀一点")
                gr.Markdown("*心有灵犀，一点就通。人工智能辅助完成从字到画的跨越。*")
                
                btn_image_gen = gr.Button("🖼️ 意象生成", size="sm")
                btn_stroke = gr.Button("🔢 笔法解构", size="sm")
            
            with gr.Column(scale=4):
                with gr.Group(visible=False) as video_content:
                    video_list_display, video_dropdown, upload_msg = suyuan.build_video_ui()
                    demo.load(
                        fn=suyuan.refresh_video_display,
                        inputs=[],
                        outputs=[video_list_display, video_dropdown]
                    )
                
                with gr.Group(visible=False) as knowledge_content:
                    result = suyuan.build_knowledge_ui()
                    knowledge_result, video_select, doc_list_dropdown = result
                    
                    from modules.suyuan import get_video_choices, get_doc_list_choices, format_all_documents
                    video_choices = get_video_choices()
                    doc_choices = get_doc_list_choices()
                    demo.load(
                        fn=lambda: (gr.update(choices=video_choices), gr.update(choices=doc_choices), format_all_documents()),
                        inputs=[],
                        outputs=[video_select, doc_list_dropdown, knowledge_result]
                    )
                
                with gr.Group(visible=False) as explain_content:
                    explain_result = suyuan.build_explain_ui()
                    if explain_result:
                        chat_history_dropdown, chat_history_state = explain_result
                        demo.load(
                            fn=suyuan.load_explain_chat_history,
                            outputs=[chat_history_state, chat_history_dropdown]
                        )
                
                with gr.Group(visible=False) as practice_content:
                    mochi.build_practice_ui()
                
                with gr.Group(visible=False) as checkin_content:
                    result = mochi.build_checkin_ui()
                    checkin_gallery, year_state, month_state, day_state, checkin_msg, total_streak_display, achievements_display, history_gallery, history_checkin_text, history_date_label, history_checkin_msg, growth_result = result
                    demo.load(
                        fn=mochi.load_default_checkin_work,
                        inputs=[year_state, month_state, day_state],
                        outputs=[checkin_gallery, checkin_msg, total_streak_display]
                    )
                    demo.load(
                        fn=mochi.load_default_checkin_history,
                        outputs=[history_gallery, history_checkin_text, history_date_label, history_checkin_msg]
                    )
                    demo.load(
                        fn=lambda: mochi.get_achievements_markdown('default_user'),
                        outputs=[achievements_display]
                    )
                
                with gr.Group(visible=False) as game_content:
                    game_work_image, game_loading_msg = mochi.build_game_ui()
                    demo.load(
                        fn=lambda: (mochi.get_today_checkin_work('default_user') or gr.update(), "*点击识别按钮加载今日打卡作品*"),
                        outputs=[game_work_image, game_loading_msg]
                    )
                
                with gr.Group(visible=False) as image_gen_content:
                    lingxi.build_image_gen_ui()
                
                with gr.Group(visible=False) as stroke_content:
                    lingxi.build_stroke_ui()
        
        def show_video():
            from modules.suyuan import get_video_choices, refresh_video_display
            video_choices = get_video_choices()
            video_html, video_dropdown_update = refresh_video_display()
            return (
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                video_html,
                video_dropdown_update
            )
        
        def show_knowledge():
            from modules.suyuan import get_video_choices, get_doc_list_choices, format_all_documents
            video_choices = get_video_choices()
            doc_choices = get_doc_list_choices()
            all_docs_md = format_all_documents()
            return (
                gr.update(visible=False),
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(choices=video_choices),
                gr.update(choices=doc_choices),
                gr.update(value=all_docs_md)
            )
        
        def show_explain():
            return (
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False)
            )
        
        def show_practice():
            return (
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False)
            )
        
        def show_checkin():
            import datetime
            now = datetime.datetime.now()
            img, msg, total = mochi.load_default_checkin_work(str(now.year), str(now.month).zfill(2), str(now.day).zfill(2))
            return (
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                img,
                msg,
                total
            )
        
        def show_game():
            from database import get_today_checkin_work
            mochi.clear_game_state()
            work_image = get_today_checkin_work('default_user')
            loading_msg = "*点击识别按钮加载今日打卡作品*" if not work_image else "已加载今日打卡作品"
            return (
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=False),
                work_image or gr.update(),
                loading_msg
            )
        
        def show_image_gen():
            return (
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=True),
                gr.update(visible=False)
            )
        
        def show_stroke():
            return (
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=True)
            )
        
        btn_video.click(fn=show_video, outputs=[video_content, knowledge_content, explain_content, practice_content, checkin_content, game_content, image_gen_content, stroke_content, video_list_display, video_dropdown])
        btn_knowledge.click(fn=show_knowledge, outputs=[video_content, knowledge_content, explain_content, practice_content, checkin_content, game_content, image_gen_content, stroke_content, video_select, doc_list_dropdown, knowledge_result])
        btn_explain.click(fn=show_explain, outputs=[video_content, knowledge_content, explain_content, practice_content, checkin_content, game_content, image_gen_content, stroke_content])
        
        btn_practice.click(fn=show_practice, outputs=[video_content, knowledge_content, explain_content, practice_content, checkin_content, game_content, image_gen_content, stroke_content])
        btn_checkin.click(fn=show_checkin, outputs=[video_content, knowledge_content, explain_content, practice_content, checkin_content, game_content, image_gen_content, stroke_content, checkin_gallery, checkin_msg, total_streak_display])
        btn_game.click(fn=show_game, outputs=[video_content, knowledge_content, explain_content, practice_content, checkin_content, game_content, image_gen_content, stroke_content, game_work_image, game_loading_msg])
        
        btn_image_gen.click(fn=show_image_gen, outputs=[video_content, knowledge_content, explain_content, practice_content, checkin_content, game_content, image_gen_content, stroke_content])
        btn_stroke.click(fn=show_stroke, outputs=[video_content, knowledge_content, explain_content, practice_content, checkin_content, game_content, image_gen_content, stroke_content])
    
    return demo

if __name__ == "__main__":
    server_config = get_server_config()
    demo = create_main_app()
    
    custom_css = """
.my-markdown-card {
    background-color: white !important;
    padding: 16px !important;
    border-radius: 8px !important;
    border: 1px solid #e5e7eb !important;
}
.full-width-btn {
    height: 46px !important;
}
#chat-display {
    max-height: 500px !important;
    overflow-y: auto !important;
    padding: 16px !important;
}
#stroke-output {
    max-height: 400px !important;
    overflow-y: auto !important;
}
"""

    demo.launch(
        server_name=server_config.get('host', '0.0.0.0'),
        server_port=server_config.get('port', 7860),
        css=custom_css, theme=gr.themes.Soft()
    )