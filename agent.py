import re
import openai
import lazyllm
from config import get_model_config, get_prompt_config, setup_env

vlm = None
llm = None
ocr = None
judge_prompt = None
growth_prompt = None

def clean_thinking_content(text):
    if not text:
        return text
    # 使用正则表达式移除 <think> 和 </think> 之间的内容
    # re.DOTALL 确保 . 能匹配换行符
    cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return cleaned_text.strip()

def init_agent():
    global vlm, llm, ocr, judge_prompt, growth_prompt
    
    model_config = get_model_config()
    prompt_config = get_prompt_config()

    judge_prompt = prompt_config.get('judge', '')
    growth_prompt = prompt_config.get('growth_analysis', '')
    
    vlm = lazyllm.OnlineChatModule(
        source=model_config.get('source', 'openai'),
        base_url=model_config.get('base_url', None),
        api_key=model_config.get('api_key', None),
        model=model_config.get('vision_model', 'Qwen2.5-VL-72B-Instruct'),
        model_type='VLM',
        timeout=60
    )

    llm = lazyllm.OnlineChatModule(
        source=model_config.get('source', 'openai'),
        base_url=model_config.get('base_url', None),
        api_key=model_config.get('api_key', None),
        model=model_config.get('text_model', 'DeepSeek-V3-250324'),
        timeout=60
    )
    return True

def get_agent(model_type):
    global llm, vlm, ocr, judge_prompt, growth_prompt
    if llm is None:
        init_agent()
    if model_type == "LLM":
        return llm, judge_prompt, growth_prompt
    else:
        return vlm, judge_prompt, growth_prompt

def evaluate_calligraphy_stream(image_path):
    if image_path is None:
        return "请先上传一张书法作品的图片哦！"
    
    vlm, prompt, _ = get_agent("VLM")
    
    if not prompt:
        print("Warning: judge prompt is empty!")
    
    try:
        for chunk in vlm(prompt, lazyllm_files=[image_path], stream=True):
            if isinstance(chunk, dict):
                content = chunk.get('content', '')
            else:
                content = str(chunk)
            yield content
        yield "[DONE]"
        
    except Exception as e:
        yield f"人工智能正在思考中... (发生错误: {str(e)})"

def evaluate_calligraphy(image_path):
    if image_path is None:
        return "请先上传一张书法作品的图片哦！"
    
    result = ""
    for chunk in evaluate_calligraphy_stream(image_path):
        if chunk == "[DONE]":
            break
        result += chunk
    
    if not result:
        return "人工智能未能生成评价，请重试"
    return result

def check_poem_keyword(poem_text, keyword, used_poems=None):
    llm, _, _ = get_agent("LLM")
    
    if used_poems is None:
        used_poems = []
    
    poem_clean = poem_text.strip()
    
    for used_poem in used_poems:
        if poem_clean in used_poem or used_poem in poem_clean:
            return "duplicate", "这句诗已经说过过了，请换一句！"
    
    if len(poem_clean) < 5:
        return False, "请检查是否是完整的诗句（至少5个字）"
    
    if keyword not in poem_clean:
        return False, f"诗句中必须包含关键字【{keyword}】"
    
    try:
        check_prompt = f"""请判断以下文本是否是完整的中文诗句（至少5个字，且读起来像诗的完整句子）。
        文本：{poem_clean}
        请直接回答"是"或"否"，不要返回其他内容。"""
        
        result = llm(check_prompt)
        
        if isinstance(result, dict):
            content = result.get('content', '')
        else:
            content = str(result)
        
        if '是' == content:
            return True, ""
        else:
            return False, "请检查是否是完整的诗句（至少5个字）"
            
    except Exception as e:
        return True, ""

def generate_ai_response(user_poem, keyword, used_poems):
    llm, _, _ = get_agent("LLM")
    
    max_attempts = 3
    
    for attempt in range(max_attempts):
        try:
            all_used = used_poems[:] if used_poems else []
            all_used.append(user_poem)
            
            used_text = "\n".join([f"- {p}" for p in all_used[-10:]]) if all_used else "无"
            
            prompt = f"""你是飞花令游戏的对手。用户刚刚说了诗句："{user_poem}"
            关键字是【{keyword}】。

            已说过的诗句：
            {used_text}

            请对出一句包含关键字【{keyword}】的完整诗句（必须是5个字以上）。
            要求：
            1. 必须包含【{keyword}】字
            2. 必须是完整的诗句
            3. 不能与已说过的诗句重复（包括不能与用户刚说的诗句重复）
            4. 优先选择经典诗句

            如果无法对出，请直接输出"无法对出"。
            否则只输出诗句，不需要其他解释。"""
            
            result = clean_thinking_content(llm(prompt))
            
            if isinstance(result, dict):
                content = result.get('content', '')
            else:
                content = str(result)
            
            content = content.strip()
            
            if '无法对出' in content or not content:
                continue
            
            if keyword not in content:
                continue
            
            if all_used and content in all_used:
                continue
            
            return content, True
            
        except Exception as e:
            print(f"AI response error: {e}")
            continue
    
    return None, False

def analyze_growth(checkin_records):
    if not checkin_records:
        return "暂无打卡记录，无法进行成长分析"
    
    llm, _, growth_prompt = get_agent("VLM")
    
    if not growth_prompt:
        print("Warning: growth prompt is empty!")
    
    records_text = ""
    for i, (checkin_date, review_text) in enumerate(reversed(checkin_records), 1):
        records_text += f"\n【第{i}天】日期：{checkin_date}\nAI点评：{review_text}\n"
    
    prompt = growth_prompt.format(checkin_records=records_text)
    
    result = ""
    try:
        for chunk in llm(prompt, stream=True):
            if isinstance(chunk, dict):
                content = chunk.get('content', '')
            else:
                content = str(chunk)
            result += content
            yield result
        
        yield "[DONE]"
        
    except Exception as e:
        yield f"成长分析发生错误: {str(e)}"

def recognize_text_from_image(image_path):
    if image_path is None:
        return None
    
    ocr, _, _ = get_agent("VLM")
    
    prompt = """请仔细识别图片中的汉字。只输出识别到的汉字，不要输出其他内容。如果没有识别到汉字，请输出"无"。"""
    
    try:
        result = ocr(prompt, lazyllm_files=[image_path])
        
        if isinstance(result, dict):
            content = result.get('content', '')
        else:
            content = str(result)
        
        if content:
            chars = [c for c in content if '\u4e00' <= c <= '\u9fff']
            if chars:
                return ''.join(chars)
        return None
            
    except Exception as e:
        print(f"OCR error: {e}")
        return None


def analyze_calligraphy_for_imagination(image_path):
    if image_path is None:
        return "请先上传一张书法作品的图片哦！"
    
    vlm, _, _ = get_agent("VLM")
    
    prompt = """请仔细分析这张书法作品，发挥你的想象力，描述这幅书法作品所蕴含的意象和意境。
    
请从以下几个方面描述：
1. 整体氛围（时间、光线、季节、情感）
2. 画面应该呈现什么样的场景（自然景物、人物、物品）
3. 色彩基调和建议
4. 艺术风格（水墨画、写意、工笔等）
5. 意境总结

要求：描述要优美、具体、富有诗意，用200字以内描述。这个描述将用于生成意象图像。"""
    
    try:
        result = vlm(prompt, lazyllm_files=[image_path])
        
        if isinstance(result, dict):
            content = result.get('content', '')
        else:
            content = str(result)
        
        if not content:
            return "人工智能未能生成意象描述，请重试"
        return content
            
    except Exception as e:
        return f"分析书法作品时出错：{str(e)}"


def download_image_from_url(url, filename=None):
    import requests
    import os
    from pathlib import Path
    from PIL import Image
    import io
    
    if not url:
        return None
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            if filename is None:
                filename = f"temp_image_{int(os.times().elapsed * 1000)}.png"
            
            save_dir = Path("data/images")
            save_dir.mkdir(parents=True, exist_ok=True)
            
            filepath = save_dir / filename
            
            img = Image.open(io.BytesIO(response.content))
            
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            max_size = 1024
            if img.width > max_size or img.height > max_size:
                ratio = min(max_size / img.width, max_size / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            img.save(filepath, 'PNG', quality=95)
            
            return str(filepath)
    except Exception as e:
        print(f"Download image error: {e}")
    
    return None


def generate_inspiration_image(description):
    if not description or not description.strip():
        return None
    model_config = get_model_config()
    
    prompt = f"""请根据以下意象描述生成一幅精美的中国水墨画风格的图像：

{description}

要求：
- 中国传统水墨画风格
- 意境优美
- 色彩协调
- 画面完整"""
    
    try:
        try:
            client = openai.OpenAI(
                api_key=model_config.get("api_key", None),  
                base_url=model_config.get("base_url", None), 
            )

            response = client.images.generate(
                model=model_config.get("image_model", "Doubao-Seedream-4.0"),
                prompt=prompt,
            )
            print(response)
            if response and response.data:
                image_url = response.data[0].url
                return download_image_from_url(image_url)
        except Exception as e1:
            print(f"OpenAI client failed: {e1}")
        
        return None
        
    except Exception as e:
        print(f"Image generation error: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_calligraphy_template(char):
    if not char or not char.strip():
        return None
    
    model_config = get_model_config()
    prompt = f"""请生成一个标准的硬笔书法范本图片，要求：
- 清晰地展示汉字"{char}"的楷书书写
- 米字格或田字格背景
- 笔画清晰，结构规范
- 适合初学者临摹
- 纯白色背景，只显示汉字和格子"""

    try:
        client = openai.OpenAI(
            api_key=model_config.get("api_key", None),  
            base_url=model_config.get("base_url", None), 
        )

        response = client.images.generate(
            model=model_config.get("image_model", "Doubao-Seedream-4.0"),
            prompt=prompt,
        )
        
        if response and response.data:
            image_url = response.data[0].url
            print("TEST for LJD, image_url:========", image_url)
            return download_image_from_url(image_url, f"template_char_0.png")
        return None
        
    except Exception as e:
        print(f"Calligraphy template generation error: {e}")
        import traceback
        traceback.print_exc()
        return None