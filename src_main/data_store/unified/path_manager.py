import os

from run_time_cfg import proj_run_time_cfg


class PathManager:
    """
    Unified Path Manager for both Toolchain and Project paths.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(PathManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True

    # --- Toolchain Paths ---

    def get_toolchain_root(self) -> str:
        """Returns the src_main directory."""
        # Assuming this file is in src_main/data_store/unified/
        current_file = os.path.abspath(__file__)
        unified_dir = os.path.dirname(current_file)
        data_store_dir = os.path.dirname(unified_dir)
        src_main_dir = os.path.dirname(data_store_dir)
        return src_main_dir

    def get_sys_prompt_dir(self) -> str:
        return os.path.join(self.get_toolchain_root(), "icp_prompt_sys")

    def get_user_prompt_dir(self) -> str:
        return os.path.join(self.get_toolchain_root(), "icp_prompt_user")

    def get_app_data_dir(self) -> str:
        return os.path.join(self.get_toolchain_root(), "app_data")
    
    def get_app_data_file(self, filename: str) -> str:
        return os.path.join(self.get_app_data_dir(), filename)

    # --- Project Paths ---

    def _get_proj_cfg(self):
        return proj_run_time_cfg.get_instance()

    def get_work_dir(self) -> str:
        return self._get_proj_cfg().get_work_dir_path()

    def get_proj_data_dir(self) -> str:
        return os.path.join(self.get_work_dir(), self._get_proj_cfg().get_icp_proj_data_dir_name())

    def get_proj_config_dir(self) -> str:
        return os.path.join(self.get_work_dir(), '.icp_proj_config')

    def get_staging_dir(self) -> str:
        return os.path.join(self.get_work_dir(), self._get_proj_cfg().get_staging_layer_dir_name())

    def get_ibc_dir(self) -> str:
        return os.path.join(self.get_work_dir(), self._get_proj_cfg().get_behavioral_layer_dir_name())

    def get_target_dir(self) -> str:
        return os.path.join(self.get_work_dir(), self._get_proj_cfg().get_target_layer_dir_name())

    def get_proj_data_file(self, filename: str) -> str:
        return os.path.join(self.get_proj_data_dir(), filename)
    
    def get_staging_file(self, filename: str) -> str:
        return os.path.join(self.get_staging_dir(), filename)

    def get_ibc_file(self, relative_path: str) -> str:
        """
        Constructs the full path for an IBC file.
        relative_path: e.g., "utils/my_util" -> "work_dir/src_ibc/utils/my_util.ibc"
        """
        if not relative_path.endswith('.ibc'):
            relative_path += '.ibc'
        return os.path.join(self.get_ibc_dir(), relative_path)

_instance = PathManager()
def get_instance() -> PathManager:
    return _instance
