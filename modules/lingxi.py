import gradio as gr
from pathlib import Path
from agent import analyze_calligraphy_for_imagination, generate_inspiration_image, generate_calligraphy_template


current_description = ""
current_uploaded_image = None


def build_image_gen_ui():
    global current_description, current_uploaded_image
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 🖼️ 意象生成")
            gr.Markdown("上传书法作品，人工智能帮你生成意象图")
            
            image_input = gr.Image(
                label="上传书法作品",
                type="filepath",
                height=400
            )
            
            analyze_btn = gr.Button("🔍 分析作品并生成意象", variant="primary")
            
            loading_msg = gr.Markdown("*上传作品后点击分析按钮，如长时间未响应请耐心等待...*")
        
        with gr.Column(scale=2):
            gr.Markdown("### 📝 意象描述")
            desc_output = gr.Markdown("*分析结果将显示在这里*", elem_classes="my-markdown-card")
            
            gr.Markdown("### 🎨 生成的意象图")
            image_output = gr.Image(
                label="意象图",
                height=400,
                visible=False
            )
            image_hint = gr.Markdown("*意象图生成时间较长，请耐心等待...*", visible=False)
    
    def handle_analyze_and_generate(image_path):
        global current_description, current_uploaded_image
        
        if image_path is None:
            return "*请先上传书法作品图片*", gr.update(visible=False), gr.update(visible=False), "*请先上传书法作品图片*"
        
        current_uploaded_image = image_path
        
        desc = analyze_calligraphy_for_imagination(image_path)
        current_description = desc
        
        if not desc or "出错" in desc:
            return desc, gr.update(visible=False), gr.update(visible=False), desc
        
        yield desc, gr.update(visible=False), gr.update(visible=True), "⏳ 正在生成意象图，请稍候..."
        
        image_result = generate_inspiration_image(desc)
        
        print(f"[意象生成] 结果: {image_result}")
        
        import time
        time.sleep(0.2)
        
        if image_result and Path(image_result).exists():
            print(f"[意象生成] 文件存在，大小: {Path(image_result).stat().st_size} bytes")
            yield desc, gr.update(value=image_result, visible=True), gr.update(visible=False), "✅ 意象图生成完成"
        elif image_result and (image_result.startswith('http://') or image_result.startswith('https://')):
            yield desc, gr.update(value=image_result, visible=True), gr.update(visible=False), "✅ 意象图生成完成"
        else:
            print(f"[意象生成] 文件不存在或无效: {image_result}")
            yield desc, gr.update(visible=False), gr.update(visible=False), "⚠️ 意象图生成失败，请重试"
    
    analyze_btn.click(
        fn=handle_analyze_and_generate,
        inputs=image_input,
        outputs=[desc_output, image_output, image_hint, loading_msg]
    )


def build_stroke_ui():
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 🔢 笔法解构")
            gr.Markdown("输入写不好的字，查看笔法解构")
            
            char_input = gr.Textbox(
                label="输入单字",
                placeholder="请输入一个汉字",
                lines=1,
                max_lines=1
            )
            
            analyze_btn = gr.Button("🔍 分析笔法", variant="primary")
            
            gr.Markdown("### 📄 临摹范本")
            template_image = gr.Image(
                label="硬笔书法范本",
                height=400,
                visible=False
            )
            template_hint = gr.Markdown("*范本生成时间较长，请耐心等待...*", visible=False)
        
        with gr.Column(scale=2):
            gr.Markdown("### 📊 笔法详情")
            stroke_output = gr.Markdown("输入汉字，点击分析按钮...", elem_classes="my-markdown-card", elem_id="stroke-output")
    
    analyze_btn.click(
        fn=handle_stroke_analysis,
        inputs=char_input,
        outputs=[stroke_output, template_image, template_hint]
    )


def handle_stroke_analysis(char):
    if not char or not char.strip():
        return "请输入一个汉字", gr.update(visible=False), gr.update(visible=False)
    
    char = char.strip()[0]
    
    from inspiration import generate_stroke_sequence
    result = generate_stroke_sequence(char)
    
    yield result, gr.update(visible=False), "⏳ 正在生成临摹范本，请稍候..."
    
    template_url = generate_calligraphy_template(char)
    
    print(f"[临摹范本] 结果: {template_url}")
    
    import time
    time.sleep(0.2)
    
    if template_url and Path(template_url).exists():
        print(f"[临摹范本] 文件存在，大小: {Path(template_url).stat().st_size} bytes")
        yield result, gr.update(value=template_url, visible=True), gr.update(visible=False)
    else:
        print(f"[临摹范本] 文件不存在或无效: {template_url}")
        yield result, gr.update(visible=False), "⚠️ 范本生成失败，请重试"


def build_module_ui():
    build_image_gen_ui()
    with gr.Row():
        gr.Markdown("---")
    build_stroke_ui()