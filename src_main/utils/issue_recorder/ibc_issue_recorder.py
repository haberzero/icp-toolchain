from typing import List, Dict, Any
from typedef.issue_recorder_types import IbcIssue


class IbcIssueRecorder:
    """IBC分析问题记录器
    
    用于收集IBC分析过程中出现的错误信息，供上层代码进行后续操作使用。
    """
    
    def __init__(self):
        self._issues: List[IbcIssue] = []
    
    def record_issue(self, message: str, line_num: int, line_content: str) -> None:
        """记录一个问题
        
        Args:
            message: 错误消息
            line_num: 行号
            line_content: 行内容
        """
        issue = IbcIssue(
            message=message,
            line_num=line_num,
            line_content=line_content
        )
        self._issues.append(issue)
    
    def get_issues(self) -> List[IbcIssue]:
        """获取所有记录的问题"""
        return self._issues.copy()
    
    def has_issues(self) -> bool:
        """是否有记录的问题"""
        return len(self._issues) > 0
    
    def clear(self) -> None:
        """清空所有问题记录"""
        self._issues.clear()
    
    def get_issue_count(self) -> int:
        """获取问题数量"""
        return len(self._issues)
    
    def to_dict_list(self) -> List[Dict[str, Any]]:
        """将所有问题转换为字典列表"""
        return [issue.to_dict() for issue in self._issues]
    
    def print_issues(self) -> None:
        """打印所有问题"""
        for issue in self._issues:
            print(f"Line {issue.line_num}: {issue.message}")
            print(f"  {issue.line_content}")
