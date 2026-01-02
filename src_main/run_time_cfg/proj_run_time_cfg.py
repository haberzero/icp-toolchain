import sys
import os
import json

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
    
    def _trig_update_config(self):
        """触发配置更新，使配置文件的修改生效"""
        self._config_cache = None
        self._load_config()
    
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


_instance = ProjRunTimeCfg()


def get_instance():
    return _instance
