import sys
import os
import json
from typedef.ai_data_types import ChatApiConfig, EmbeddingApiConfig

# 运行过程中目标工程相关配置信息管理

class ProjRunTimeCfg:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ProjRunTimeCfg, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'proj_root_dict'):
            self.proj_work_dir_path = ""
            self._config_cache = None
            self._api_config_cache = None

    def set_work_dir_path(self, new_path):
        if not os.path.exists(new_path):
            print(f"错误: 项目根路径 '{new_path}' 不存在")
            return
        self.proj_work_dir_path = new_path
    
    def get_work_dir_path(self):
        if not self.proj_work_dir_path:
            print("错误: 项目根路径未设置")
            raise Exception("项目根路径未设置")
        return self.proj_work_dir_path
    
    def _load_config(self):
        """加载配置文件并缓存"""
        if self._config_cache is None:
            config_file_path = os.path.join(self.proj_work_dir_path, '.icp_proj_config', 'icp_config.json')
            if not os.path.exists(config_file_path):
                print(f"错误: 配置文件 '{config_file_path}' 不存在")
                raise Exception("配置文件不存在")
            with open(config_file_path, 'r', encoding='utf-8') as f:
                self._config_cache = json.load(f)
        return self._config_cache
    
    def _load_api_config(self):
        """加载API配置文件并缓存"""
        if self._api_config_cache is None:
            api_config_file_path = os.path.join(self.proj_work_dir_path, '.icp_proj_config', 'icp_api_config.json')
            if not os.path.exists(api_config_file_path):
                print(f"错误: API配置文件 '{api_config_file_path}' 不存在")
                raise Exception("API配置文件不存在")
            with open(api_config_file_path, 'r', encoding='utf-8') as f:
                self._api_config_cache = json.load(f)
        return self._api_config_cache
    
    def _trig_update_config(self):
        """触发配置更新，使配置文件的修改生效"""
        self._config_cache = None
        self._load_config()
    
    def _trig_update_api_config(self):
        """触发API配置更新，使API配置文件的修改生效"""
        self._api_config_cache = None
        self._load_api_config()
    
    def _get_path_mapping(self):
        """获取路径映射配置"""
        config = self._load_config()
        path_mapping = config.get('path_mapping', {})
        if not path_mapping:
            print("警告: 配置文件中不存在路径映射信息，使用默认值")
        return path_mapping
    
    def get_target_language(self):
        config = self._load_config()
        return config.get('target_language', 'Python')

    def get_target_suffix(self):
        config = self._load_config()
        return config.get('target_suffix', '.py')
    
    def get_is_extra_suffix(self):
        path_mapping = self._get_path_mapping()
        return path_mapping.get('is_extra_suffix', True)

    def get_icp_proj_data_dir_name(self):
        """获取项目数据目录名称"""
        path_mapping = self._get_path_mapping()
        return path_mapping.get('icp_proj_data_dir', 'icp_proj_data')
    
    def get_staging_layer_dir_name(self):
        """获取staging层目录名称"""
        path_mapping = self._get_path_mapping()
        return path_mapping.get('staging_layer_dir', 'src_staging')
    
    def get_behavioral_layer_dir_name(self):
        """获取behavioral层目录名称"""
        path_mapping = self._get_path_mapping()
        return path_mapping.get('behavioral_layer_dir', 'src_ibc')
    
    def get_target_layer_dir_name(self):
        """获取target层目录名称"""
        path_mapping = self._get_path_mapping()
        return path_mapping.get('target_layer_dir', 'src_main')
    
    # ==================== API配置相关方法 ====================
    def check_specific_ai_handler_config_exists(self, handler_type: str):
        """检查指定类型的处理器配置是否存在"""
        api_config = self._load_api_config()
        return handler_type in api_config
    
    def get_chat_handler_config(self, handler_type: str) -> ChatApiConfig:
        """获取指定类型的对话处理器配置"""
        api_config = self._load_api_config()
        chat_config = api_config.get(handler_type, {})
        return ChatApiConfig(
            base_url=chat_config.get('api-url', ''),
            api_key=chat_config.get('api-key', ''),
            model=chat_config.get('model', '')
        )
    
    def get_embedding_handler_config(self, handler_type: str) -> EmbeddingApiConfig:
        """获取指定类型的嵌入处理器配置"""
        api_config = self._load_api_config()
        embedding_config = api_config.get(handler_type, {})
        return EmbeddingApiConfig(
            base_url=embedding_config.get('api-url', ''),
            api_key=embedding_config.get('api-key', ''),
            model=embedding_config.get('model', '')
        )


_instance = ProjRunTimeCfg()


def get_instance():
    return _instance
