import os

from run_time_cfg import proj_run_time_cfg


class DataStorePathBuilder:
    """数据存储路径构建器"""
    
    # ==================== 工具链内部资源路径 ====================
    # 用于访问icp-toolchain工具链自身的资源文件
    
    @staticmethod
    def _get_toolchain_root_path() -> str:
        """获取工具链根目录（src_main目录）"""
        # 当前文件位于 src_main/data_store/ 目录下
        current_file = os.path.abspath(__file__)
        data_store_dir = os.path.dirname(current_file)
        src_main_dir = os.path.dirname(data_store_dir)
        return src_main_dir
    
    @staticmethod
    def _get_sys_prompt_dir_path() -> str:
        """获取系统提示词目录"""
        return os.path.join(DataStorePathBuilder._get_toolchain_root_path(), "icp_prompt_sys")
    
    @staticmethod
    def _get_user_prompt_dir_path() -> str:
        """获取用户提示词模板目录"""
        return os.path.join(DataStorePathBuilder._get_toolchain_root_path(), "icp_prompt_user")
    
    @staticmethod
    def get_sys_prompt_file_path(prompt_name: str) -> str:
        """获取系统提示词文件路径
        
        Args:
            prompt_name: 提示词文件名（不含.md扩展名）或完整文件名
        """
        if not prompt_name.endswith('.md'):
            prompt_name = f"{prompt_name}.md"
        return os.path.join(DataStorePathBuilder._get_sys_prompt_dir_path(), prompt_name)
    
    @staticmethod
    def get_user_prompt_file_path(prompt_name: str) -> str:
        """获取用户提示词模板文件路径
        
        Args:
            prompt_name: 提示词模板文件名（不含.md扩展名）或完整文件名
        """
        if not prompt_name.endswith('.md'):
            prompt_name = f"{prompt_name}.md"
        return os.path.join(DataStorePathBuilder._get_user_prompt_dir_path(), prompt_name)
    
    @staticmethod
    def _get_app_data_dir_path() -> str:
        """获取应用数据目录"""
        return os.path.join(DataStorePathBuilder._get_toolchain_root_path(), "app_data")
    
    @staticmethod
    def get_app_data_file_path(app_data_file_name: str) -> str:
        """获取应用数据文件路径
        
        Args:
            app_data_file_name: 应用数据文件名
        """
        return os.path.join(DataStorePathBuilder._get_app_data_dir_path(), app_data_file_name)
    
    # ==================== 目标工程根级路径 ====================
    # 用于访问用户目标工程中的文件和目录
    # 便于未来通过配置文件灵活调整目标工程目录结构，比如修改默认的icp_proj_data目录名 等

    @staticmethod
    def _get_proj_data_dir_path() -> str:
        """获取项目数据目录"""
        cfg = proj_run_time_cfg.get_instance()
        work_dir_path = cfg.get_work_dir_path()
        proj_data_dir_name = cfg.get_icp_proj_data_dir_name()
        return os.path.join(work_dir_path, proj_data_dir_name)
    
    @staticmethod
    def _get_proj_config_dir_path() -> str:
        """获取项目配置目录（.icp_proj_config）"""
        cfg = proj_run_time_cfg.get_instance()
        work_dir_path = cfg.get_work_dir_path()
        return os.path.join(work_dir_path, '.icp_proj_config')
    
    @staticmethod
    def get_staging_dir_path() -> str:
        """获取中间产物目录（staging层）"""
        cfg = proj_run_time_cfg.get_instance()
        work_dir_path = cfg.get_work_dir_path()
        staging_dir_name = cfg.get_staging_layer_dir_name()
        return os.path.join(work_dir_path, staging_dir_name)
    
    @staticmethod
    def get_ibc_dir_path() -> str:
        """获取IBC代码目录（behavioral层）"""
        cfg = proj_run_time_cfg.get_instance()
        work_dir_path = cfg.get_work_dir_path()
        ibc_dir_name = cfg.get_behavioral_layer_dir_name()
        return os.path.join(work_dir_path, ibc_dir_name)
    
    @staticmethod
    def get_target_code_dir_path() -> str:
        """获取目标代码目录（target层）"""
        cfg = proj_run_time_cfg.get_instance()
        work_dir_path = cfg.get_work_dir_path()
        target_dir_name = cfg.get_target_layer_dir_name()
        return os.path.join(work_dir_path, target_dir_name)
    
    # ==================== 项目数据文件路径 ====================
    @staticmethod
    def get_icp_proj_data_file_path(file_name: str) -> str:
        """获取项目数据文件路径
        
        Args:
            file_name: 文件名
        """
        return os.path.join(DataStorePathBuilder._get_proj_data_dir_path(), file_name)
    
    @staticmethod
    def get_proj_config_file_path(file_name: str) -> str:
        """获取项目配置文件路径
        
        Args:
            file_name: 文件名
        """
        return os.path.join(DataStorePathBuilder._get_proj_config_dir_path(), file_name)

