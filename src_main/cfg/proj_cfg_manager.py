import sys
import os
import json



# class MccpDirContentManager:
#     _instance = None  # 类变量用于保存单例实例

#     def __new__(cls, *args, **kwargs):
#         if cls._instance is None:
#             cls._instance = super(MccpDirContentManager, cls).__new__(cls)
#             cls._instance.init_project_path(*args, **kwargs)
#         return cls._instance


class ProjCfgManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ProjCfgManager, cls).__new__(cls)
            cls._instance.inst_init(*args, **kwargs)
        return cls._instance

    def inst_init(self, project_root: str = ""):
        # 暂不启用，目前考虑是main获取实例以后直接set项目路径
        pass

    def set_proj_root(self, new_path):
        if not os.path.exists(new_path):
            print(f"错误: 项目根路径 '{new_path}' 不存在")
            return False

        self.proj_root = new_path
        return True
    
    def get_proj_root(self):
        return self.proj_root


# 创建一个单例实例，供模块导入时使用
_instance = ProjCfgManager()

# 提供一个全局访问方法
def get_instance():
    return _instance

