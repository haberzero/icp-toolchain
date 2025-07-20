# 暂时弃用，失败的设计。
# 不增加不必要的实体模块，各文件各自直接从json获取配置数据即可

# import os
# import json


# class MccpConfigManager:
#     _instance = None  # 类变量用于保存单例实例

#     def __new__(cls, *args, **kwargs):
#         if cls._instance is None:
#             cls._instance = super(MccpConfigManager, cls).__new__(cls)
#             cls._instance.initialize(*args, **kwargs)
#         return cls._instance

#     # 初始化配置管理器
#     def initialize(self, project_path=""):
#         self.project_path = project_path
#         self.config_path = ""
#         if project_path:
#             self.set_project_path(project_path)

#     def set_project_path(self, project_path):
#         self.project_path = project_path
#         self.config_path = os.path.join(project_path, '.mccp_config', 'mccp_config.json')
#         # 处理斜杠方向
#         self.config_path = self.config_path.replace('\\', '/')
#         self.config_data = self._load_config()

#     # 加载配置文件数据，如果文件不存在则返回空字典
#     def _load_config(self):
#         if os.path.exists(self.config_path):
#             try:
#                 with open(self.config_path, 'r', encoding='utf-8') as f:
#                     return json.load(f)
#             except Exception as e:
#                 print(f"警告: 加载配置文件失败 - {str(e)}")
#         return {}

#     # 读取配置参数，param_path: 参数路径，支持嵌套参数，如 'fileSystemMapping.targetLayerDir'，返回: 参数值或None
#     def read_param(self, param_path):
#         keys = param_path.split('.')
#         current_data = self.config_data

#         for key in keys:
#             if isinstance(current_data, dict) and key in current_data:
#                 current_data = current_data[key]
#             else:
#                 print(f"警告: 参数 '{param_path}' 不存在于配置文件中")
#                 return None
#         return current_data

#     # 写入配置参数，param_path: 参数路径，支持嵌套参数，如 'fileSystemMapping.targetLayerDir'，value: 要写入的参数值，返回: 是否写入成功
#     def write_param(self, param_path, value):
#         keys = param_path.split('.')
#         current_data = self.config_data

#         # 遍历除最后一个键之外的所有键，创建嵌套结构
#         for key in keys[:-1]:
#             if key not in current_data or not isinstance(current_data[key], dict):
#                 current_data[key] = {}
#             current_data = current_data[key]

#         # 设置最后一个键的值
#         current_data[keys[-1]] = value

#         # 保存配置文件
#         try:
#             # 创建目录（如果不存在）
#             os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
#             with open(self.config_path, 'w', encoding='utf-8') as f:
#                 json.dump(self.config_data, f, ensure_ascii=False, indent=4)
#             return True
#         except Exception as e:
#             print(f"错误: 写入配置文件失败 - {str(e)}")
#             return False

#     # 获取所有配置数据
#     def get_all_config(self):
#         return self.config_data

#     # 设置所有配置数据，new_config: 新的配置字典，返回: 是否设置成功
#     def set_all_config(self, new_config):
#         if not isinstance(new_config, dict):
#             print("错误: 配置数据必须是字典类型")
#             return False

#         self.config_data = new_config
#         try:
#             os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
#             with open(self.config_path, 'w', encoding='utf-8') as f:
#                 json.dump(self.config_data, f, ensure_ascii=False, indent=4)
#             return True
#         except Exception as e:
#             print(f"错误: 写入配置文件失败 - {str(e)}")
#             return False

#     # 获取项目根路径
#     def get_proj_path(self):
#         return self.project_path

#     # 设置项目根路径，new_path: 新的项目根路径，返回: 是否设置成功
#     def set_proj_path(self, new_path):
#         if not os.path.exists(new_path):
#             print(f"错误: 项目根路径 '{new_path}' 不存在")
#             return False

#         self.project_path = new_path
#         self.config_path = os.path.join(new_path, '.mccp_config', 'mccp_config.json')


# # 创建一个单例实例，供模块导入时使用
# _instance = MccpConfigManager()

# # 提供一个全局访问方法
# def get_instance():
#     return _instance
