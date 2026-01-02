import json
import os
from data_store.data_store_path_builder import DataStorePathBuilder


class AppDataStore:
    """应用数据管理器 - 单例模式"""
    
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(AppDataStore, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True

    def load_last_path(self) -> str:
        app_data_json_path = DataStorePathBuilder.get_app_data_file_path("app_data.json")
        
        try:
            if os.path.exists(app_data_json_path):
                with open(app_data_json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("proj_root_dict", "")
        except (json.JSONDecodeError, IOError) as e:
            print(f"读取历史数据文件失败: {e}")
        return ""

    def save_last_path(self, path: str) -> None:
        app_data_json_path = DataStorePathBuilder.get_app_data_file_path("app_data.json")
        
        try:
            # 确保app_data目录存在
            app_data_dir = os.path.dirname(app_data_json_path)
            if app_data_dir and not os.path.exists(app_data_dir):
                os.makedirs(app_data_dir)
                
            # 保存路径到JSON文件
            with open(app_data_json_path, 'w', encoding='utf-8') as f:
                json.dump({"proj_root_dict": path}, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"保存{path}到文件失败: {e}")
    
    def get_sys_prompt_by_name(self, name: str) -> str:
        prompt_path = DataStorePathBuilder.get_sys_prompt_file_path(name)
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""
    
    def get_user_prompt_by_name(self, name: str) -> str:
        prompt_path = DataStorePathBuilder.get_user_prompt_file_path(name)
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""


_instance = AppDataStore()


def get_instance():
    return _instance