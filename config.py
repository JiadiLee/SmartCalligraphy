import yaml
import os
from pathlib import Path

_CONFIG = None

def load_config(config_path="config.yaml"):
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG
    
    config_file = os.path.join(os.path.dirname(__file__), config_path)
    with open(config_file, 'r', encoding='utf-8') as f:
        _CONFIG = yaml.safe_load(f)
    return _CONFIG

def get_config():
    if _CONFIG is None:
        return load_config()
    return _CONFIG

def get_api_keys():
    config = get_config()
    return config.get('api_keys', {})

def get_model_config():
    config = get_config()
    return config.get('model', {})

def get_prompt_config():
    config = get_config()
    return config.get('prompt', {})

def get_server_config():
    config = get_config()
    return config.get('server', {})

def get_storage_config():
    config = get_config()
    return config.get('storage', {})

def get_achievements_config():
    config = get_config()
    return config.get('achievements', [])

def get_flower_config():
    config = get_config()
    return config.get('flower_order', {})

def get_ui_config():
    config = get_config()
    return config.get('ui', {})

def setup_env():
    api_keys = get_api_keys()
    if api_keys.get('qwen'):
        os.environ["LAZYLLM_QWEN_API_KEY"] = api_keys['qwen']
    if api_keys.get('openai'):
        os.environ["LAZYLLM_OPENAI_API_KEY"] = api_keys['openai']
    if api_keys.get('siliconflow'):
        os.environ["LAZYLLM_SILICONFLOW_API_KEY"] = api_keys['siliconflow']