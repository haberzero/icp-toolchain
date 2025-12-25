from typing import List, Optional
from typedef.issue_recorder_types import TextIssue
from typedef.cmd_data_types import Colors


class TextIssueRecorder:
    """文本问题记录器
    
    用于收集各类命令处理过程中出现的问题信息，供上层代码进行后续操作使用。
    """
    
    def __init__(self):
        self._issues: List[TextIssue] = []
    
    def record_issue(self, issue_content: str) -> None:
        """记录一个问题
        
        Args:
            issue_content: 问题内容
        """
        issue = TextIssue(issue_content=issue_content)
        self._issues.append(issue)
    
    def get_issues(self) -> List[TextIssue]:
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
    
    def get_latest_issue(self) -> Optional[TextIssue]:
        """获取最新的问题记录
        
        Returns:
            Optional[TextIssue]: 最新的问题记录，如果不存在则返回None
        """
        if not self._issues:
            return None
        return self._issues[-1]
    
    def get_all_contents(self) -> List[str]:
        """获取所有问题内容的字符串列表"""
        return [issue.issue_content for issue in self._issues]

    def print_issues_for_retry(self) -> None:
        """打印已记录的问题信息，并说明会用于下一次重试生成"""
        if not self._issues:
            return

        print(f"{Colors.WARNING}以下问题信息已记录，将在下一次向大模型发起重试生成时作为问题列表进行反馈：{Colors.ENDC}")
        for idx, issue in enumerate(self._issues, start=1):
            print(f"  {idx}. {issue.issue_content}")
