"""配置加载器 - 统一管理命令处理器的配置加载逻辑"""
import os
import json
from typing import Dict, Any, Tuple
from typedef.cmd_data_types import Colors


class ConfigLoader:
    """配置加载器
    
    职责：
    - 统一加载项目配置文件
    - 统一加载依赖分析结果
    - 构建文件路径配置
    - 错误处理和验证
    
    所有方法均为静态方法，可独立使用。
    """
    
    @staticmethod
    def load_icp_config(work_config_dir_path: str) -> Dict[str, Any]:
        """加载ICP配置文件
        
        Args:
            work_config_dir_path: 工作配置目录路径
            
        Returns:
            Dict[str, Any]: ICP配置字典，加载失败时返回空字典
        """
        work_icp_config_file_path = os.path.join(work_config_dir_path, 'icp_config.json')
        
        try:
            with open(work_icp_config_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取ICP配置文件失败: {e}{Colors.ENDC}")
            return {}
    
    @staticmethod
    def load_dependency_analysis(work_data_dir_path: str) -> Tuple[bool, Dict[str, Any]]:
        """加载依赖分析结果
        
        Args:
            work_data_dir_path: 工作数据目录路径
            
        Returns:
            Tuple[bool, Dict]: (是否成功, 依赖分析结果字典)
        """
        final_dir_content_file = os.path.join(work_data_dir_path, 'icp_dir_content_with_depend.json')
        
        try:
            with open(final_dir_content_file, 'r', encoding='utf-8') as f:
                final_dir_structure_str = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取依赖分析结果失败: {e}{Colors.ENDC}")
            return False, {}
        
        if not final_dir_structure_str:
            print(f"  {Colors.FAIL}错误: 依赖分析结果内容为空{Colors.ENDC}")
            return False, {}
        
        try:
            final_dir_json_dict = json.loads(final_dir_structure_str)
        except json.JSONDecodeError as e:
            print(f"  {Colors.FAIL}错误: 依赖分析结果JSON解析失败: {e}{Colors.ENDC}")
            return False, {}
        
        if "proj_root_dict" not in final_dir_json_dict or "dependent_relation" not in final_dir_json_dict:
            print(f"  {Colors.FAIL}错误: 依赖分析结果缺少必要的节点(proj_root_dict或dependent_relation){Colors.ENDC}")
            return False, {}
        
        return True, final_dir_json_dict
    
    @staticmethod
    def get_ibc_dir_path(work_dir_path: str, icp_config: Dict[str, Any]) -> str:
        """获取IBC目录路径
        
        Args:
            work_dir_path: 工作目录路径
            icp_config: ICP配置字典
            
        Returns:
            str: IBC目录的完整路径
        """
        if "file_system_mapping" in icp_config:
            ibc_dir_name = icp_config["file_system_mapping"].get("ibc_dir_name", "src_ibc")
        else:
            ibc_dir_name = "src_ibc"
        
        return os.path.join(work_dir_path, ibc_dir_name)
    
    @staticmethod
    def get_target_dir_path(work_dir_path: str, icp_config: Dict[str, Any]) -> str:
        """获取目标代码目录路径
        
        Args:
            work_dir_path: 工作目录路径
            icp_config: ICP配置字典
            
        Returns:
            str: 目标代码目录的完整路径
        """
        if "file_system_mapping" in icp_config:
            target_dir_name = icp_config["file_system_mapping"].get("target_dir_name", "src_target")
        else:
            target_dir_name = "src_target"
        
        return os.path.join(work_dir_path, target_dir_name)
    
    @staticmethod
    def get_staging_dir_path(work_dir_path: str) -> str:
        """获取staging目录路径
        
        Args:
            work_dir_path: 工作目录路径
            
        Returns:
            str: staging目录的完整路径
        """
        return os.path.join(work_dir_path, 'src_staging')
    
    @staticmethod
    def load_user_requirements(user_data_store) -> str:
        """加载用户需求
        
        Args:
            user_data_store: 用户数据存储实例
            
        Returns:
            str: 用户需求字符串，加载失败时返回空字符串
        """
        user_requirements_str = user_data_store.get_user_prompt()
        if not user_requirements_str:
            print(f"  {Colors.FAIL}错误: 未找到用户原始需求{Colors.ENDC}")
            return ""
        return user_requirements_str
    
    @staticmethod
    def load_implementation_plan(work_data_dir_path: str) -> str:
        """加载文件级实现规划
        
        Args:
            work_data_dir_path: 工作数据目录路径
            
        Returns:
            str: 实现规划字符串，加载失败时返回空字符串
        """
        implementation_plan_file = os.path.join(work_data_dir_path, 'icp_implementation_plan.txt')
        try:
            with open(implementation_plan_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 读取文件级实现规划失败: {e}{Colors.ENDC}")
            return ""
    
    @staticmethod
    def load_extracted_params(work_data_dir_path: str) -> str:
        """加载提取的参数
        
        Args:
            work_data_dir_path: 工作数据目录路径
            
        Returns:
            str: 提取的参数JSON字符串，加载失败时返回空字符串
        """
        extracted_params_file = os.path.join(work_data_dir_path, 'extracted_params.json')
        try:
            with open(extracted_params_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 读取提取参数失败: {e}，将使用空参数{Colors.ENDC}")
            return ""
    
    @staticmethod
    def load_allowed_libs(work_data_dir_path: str) -> str:
        """加载允许的第三方库清单
        
        Args:
            work_data_dir_path: 工作数据目录路径
            
        Returns:
            str: 第三方库清单文本，加载失败时返回默认文本
        """
        allowed_libs_text = "（不允许使用任何第三方库）"
        refined_requirements_file = os.path.join(work_data_dir_path, 'refined_requirements.json')
        
        try:
            with open(refined_requirements_file, 'r', encoding='utf-8') as rf:
                refined = json.load(rf)
                libs = refined.get('ExternalLibraryDependencies', {}) if isinstance(refined, dict) else {}
                if isinstance(libs, dict) and libs:
                    allowed_libs_text = "\n".join(f"- {name}: {desc}" for name, desc in libs.items())
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 读取第三方库清单失败: {e}{Colors.ENDC}")
        
        return allowed_libs_text
    
    @staticmethod
    def validate_directory_exists(dir_path: str, dir_name: str) -> bool:
        """验证目录是否存在
        
        Args:
            dir_path: 目录路径
            dir_name: 目录名称（用于错误提示）
            
        Returns:
            bool: 目录存在返回True，否则返回False并打印错误信息
        """
        if not os.path.exists(dir_path):
            print(f"  {Colors.FAIL}错误: {dir_name}目录不存在: {dir_path}{Colors.ENDC}")
            return False
        return True
