import os
import json
from config import get_model_config, get_prompt_config


def generate_stroke_sequence(char):
    if not char or not char.strip():
        return "请输入一个汉字"
    
    char = char.strip()[0]
    
    from agent import get_agent
    llm, _, _ = get_agent("LLM")
    
    prompt = f"""请分析汉字"{char}"的笔法结构，生成详细的笔法解构内容。

请按照以下格式输出：
1. 笔画数量：该字有几画
2. 笔画顺序：按正确笔顺逐笔列出
3. 每笔的书写要点：起笔、行笔、收笔的具体方法
4. 结构分析：该字的间架结构特点
5. 练习建议：初学者应该注意什么

要求：专业但易懂，适合书法初学者理解。"""
    
    try:
        result = llm(prompt)
        
        if isinstance(result, dict):
            content = result.get('content', '')
        else:
            content = str(result)
        
        if content:
            return f"### 🔢 笔法解构：{char}\n\n{content}"
        return "暂未收录该字的笔顺数据，请换个字试试"
    except Exception as e:
        return f"生成笔法解构时出错：{str(e)}"

def generate_image_description(text_input):
    from agent import get_agent
    
    llm, _, _ = get_agent("LLM")
    
    prompt = f"""请根据输入的书法意境词，展开丰富的想象，生成一个详细的视觉场景描述。
    这个描述将用于生成书法意境图像。

    输入词：{text_input}

    请从以下几个方面描述这个意象场景：
    1. 整体氛围（时间、光线、季节）
    2. 主要元素（自然景物、人物活动）
    3. 色彩基调
    4. 情感氛围

    要求：描述要优美、具体、富有诗意，用200字以内描述。"""
    
    try:
        messages = [{"role": "user", "content": prompt}]
        result = llm(messages)
        
        if isinstance(result, dict):
            return result.get('content', str(result))
        return str(result)
    except Exception as e:
        return f"生成描述时出错：{str(e)}"


def iterate_description(current_desc, feedback):
    from agent import get_agent
    
    llm, _, _ = get_agent("LLM")
    
    prompt = f"""请根据用户的反馈，改进意象描述。

    当前描述：
    {current_desc}

    用户反馈：
    {feedback}

    请生成改进后的描述，保持诗意和美感，用200字以内。"""
    
    try:
        messages = [{"role": "user", "content": prompt}]
        result = llm(messages)
        
        if isinstance(result, dict):
            return result.get('content', str(result))
        return str(result)
    except Exception as e:
        return f"改进描述时出错：{str(e)}"