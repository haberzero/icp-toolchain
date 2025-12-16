"""Issue记录数据管理器 - 统一管理运行过程中错误信息的持久化存储"""
import json
import os
from typing import Dict, Any, Optional
from typedef.cmd_data_types import Colors


class IssueRecorderDataStore:
    """Issue记录数据管理器 - 单例模式"""
    
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(IssueRecorderDataStore, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
    
    # ==================== Issue数据存储管理 ====================
    
    def build_issue_path(self, work_dir: str, stage: str) -> str:
        """
        构建Issue记录文件路径: work_dir/temp/issues/{stage}_issues.json
        
        Args:
            work_dir: 工作目录路径
            stage: 阶段名称（如：depend_analysis, depend_refine等）
            
        Returns:
            str: Issue记录文件的完整路径
        """
        temp_dir = os.path.join(work_dir, 'temp', 'issues')
        return os.path.join(temp_dir, f"{stage}_issues.json")
    
    def save_issue(self, issue_path: str, issue_data: Dict[str, Any]) -> bool:
        """
        保存Issue记录到文件
        
        Args:
            issue_path: Issue记录文件路径
            issue_data: Issue数据字典
            
        Returns:
            bool: 是否保存成功
        """
        try:
            directory = os.path.dirname(issue_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            with open(issue_path, 'w', encoding='utf-8') as f:
                json.dump(issue_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"{Colors.WARNING}保存Issue记录失败: {e}{Colors.ENDC}")
            return False
    
    def load_issue(self, issue_path: str) -> Dict[str, Any]:
        """
        加载Issue记录，失败返回空字典
        
        Args:
            issue_path: Issue记录文件路径
            
        Returns:
            Dict[str, Any]: Issue数据字典
        """
        if not os.path.exists(issue_path):
            return {}
        
        try:
            with open(issue_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"{Colors.WARNING}读取Issue记录失败: {e}{Colors.ENDC}")
            return {}
    
    def append_issue_record(
        self, 
        work_dir: str, 
        stage: str, 
        attempt: int,
        error_type: str,
        error_message: str,
        current_output: str
    ) -> bool:
        """
        追加Issue记录到指定阶段的文件中
        
        Args:
            work_dir: 工作目录路径
            stage: 阶段名称
            attempt: 尝试次数
            error_type: 错误类型
            error_message: 错误信息
            current_output: 当前输出内容
            
        Returns:
            bool: 是否追加成功
        """
        issue_path = self.build_issue_path(work_dir, stage)
        
        # 加载现有的Issue记录
        issue_data = self.load_issue(issue_path)
        
        # 初始化结构（如果不存在）
        if "stage" not in issue_data:
            issue_data["stage"] = stage
        if "attempts" not in issue_data:
            issue_data["attempts"] = []
        
        # 添加新的尝试记录
        attempt_record = {
            "attempt_number": attempt,
            "error_type": error_type,
            "error_message": error_message,
            "current_output": current_output
        }
        issue_data["attempts"].append(attempt_record)
        
        # 保存回文件
        return self.save_issue(issue_path, issue_data)
    
    def get_latest_issue(self, work_dir: str, stage: str) -> Optional[Dict[str, Any]]:
        """
        获取指定阶段的最新Issue记录
        
        Args:
            work_dir: 工作目录路径
            stage: 阶段名称
            
        Returns:
            Optional[Dict[str, Any]]: 最新的Issue记录，如果不存在则返回None
        """
        issue_path = self.build_issue_path(work_dir, stage)
        issue_data = self.load_issue(issue_path)
        
        if not issue_data or "attempts" not in issue_data:
            return None
        
        attempts = issue_data.get("attempts", [])
        if not attempts:
            return None
        
        # 返回最后一次尝试的记录
        return attempts[-1]
    
    def clear_issue(self, work_dir: str, stage: str) -> bool:
        """
        清除指定阶段的Issue记录
        
        Args:
            work_dir: 工作目录路径
            stage: 阶段名称
            
        Returns:
            bool: 是否清除成功
        """
        issue_path = self.build_issue_path(work_dir, stage)
        
        if not os.path.exists(issue_path):
            return True
        
        try:
            os.remove(issue_path)
            return True
        except Exception as e:
            print(f"{Colors.WARNING}删除Issue记录失败: {e}{Colors.ENDC}")
            return False


# 单例实例
_instance = IssueRecorderDataStore()


def get_instance() -> IssueRecorderDataStore:
    """获取IssueRecorderDataStore单例实例"""
    return _instance