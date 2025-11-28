import json
import os

# 对 icp_toolchain app 相关的持久性常用内容进行管理
# 包括上一次运行的配置信息； toolchain app 中常用路径的管理比如系统提示词的存取

class AppDataStore:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(AppDataStore, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.main_script_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.prompt_dir = os.path.join(self.main_script_path, "icp_prompt_sys")
            self.user_prompt_dir = os.path.join(self.main_script_path, "icp_prompt_user")
            self.app_data_dir = os.path.join(self.main_script_path, "app_data")
            
            self.app_data_json_path = os.path.join(self.app_data_dir, "app_data.json")
            self.app_data = ""

    def load_last_path(self):
        try:
            if os.path.exists(self.app_data_json_path):
                with open(self.app_data_json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("proj_root", "")
        except (json.JSONDecodeError, IOError) as e:
            print(f"读取历史数据文件失败: {e}")
        return ""

    def save_last_path(self, path):
        try:
            # 确保app_data目录存在
            if not os.path.exists(self.app_data_dir):
                os.makedirs(self.app_data_dir)
                
            # 保存路径到JSON文件
            with open(self.app_data_json_path, 'w', encoding='utf-8') as f:
                json.dump({"proj_root": path}, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"保存{path}到文件失败: {e}")
            
    def get_prompt_dir(self):
        """获取prompt目录路径"""
        return self.prompt_dir
        
    def get_user_prompt_dir(self):
        """获取用户prompt目录路径"""
        return self.user_prompt_dir


_instance = AppDataStore()


def get_instance():
    return _instance