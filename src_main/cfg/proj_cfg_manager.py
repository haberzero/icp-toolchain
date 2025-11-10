import sys
import os
import json

# 只在运行过程中管理工程相关配置信息，所有变量都保持在内存
# 这个类本身不应该涉及对持久性文件的存取

class ProjCfgManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ProjCfgManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'proj_root'):
            self.proj_work_dir = ""

    def set_work_dir(self, new_path):
        if not os.path.exists(new_path):
            print(f"错误: 项目根路径 '{new_path}' 不存在")
            return False
        self.proj_work_dir = new_path
        return True
    
    def get_work_dir(self):
        return self.proj_work_dir


_instance = ProjCfgManager()


def get_instance():
    return _instance
