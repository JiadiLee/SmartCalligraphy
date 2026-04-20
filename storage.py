import os
import shutil
import hashlib
import datetime
from config import get_storage_config

_IMAGES_DIR = None

def get_images_dir():
    global _IMAGES_DIR
    if _IMAGES_DIR is None:
        storage_config = get_storage_config()
        base_dir = os.path.join(os.path.dirname(__file__), storage_config.get('data_dir', 'data'))
        _IMAGES_DIR = os.path.join(base_dir, storage_config.get('images_dir', 'images'))
        os.makedirs(_IMAGES_DIR, exist_ok=True)
    return _IMAGES_DIR

def save_uploaded_image(image_file, user_id='default_user'):
    if image_file is None:
        return None
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    hash_id = hashlib.md5(f"{user_id}{timestamp}".encode()).hexdigest()[:8]
    
    ext = os.path.splitext(image_file.name)[1] if hasattr(image_file, 'name') else '.jpg'
    filename = f"{timestamp}_{hash_id}{ext}"
    
    user_dir = os.path.join(get_images_dir(), user_id)
    os.makedirs(user_dir, exist_ok=True)
    
    dest_path = os.path.join(user_dir, filename)
    
    if hasattr(image_file, 'read'):
        with open(dest_path, 'wb') as f:
            f.write(image_file.read())
    else:
        shutil.copy(image_file, dest_path)
    
    return dest_path

def delete_image(image_path):
    if os.path.exists(image_path):
        os.remove(image_path)

def list_user_images(user_id='default_user'):
    user_dir = os.path.join(get_images_dir(), user_id)
    if not os.path.exists(user_dir):
        return []
    
    images = []
    for f in os.listdir(user_dir):
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
            images.append(os.path.join(user_dir, f))
    return sorted(images, reverse=True)