from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
import json

from typedef.cmd_data_types import Colors
from typedef.issue_recorder_types import IssueBase, SimpleTextIssue, CodeIssue


class IssueRecorder:
    """
    通用问题记录器，提供两种记录格式：简单text信息，代码分析信息（包括行号和原始代码）
    """
    
    def __init__(self):
        self._issues: List[IssueBase] = []

    def add_issue(self, 
                  message: str, 
                  severity: str = "error", 
                  line_num: int = 0, 
                  line_content: str = "", 
                  file_path: str = ""):
        """
        通用添加问题方法。
        
        - 如果只提供 message，记录为 SimpleTextIssue。
        - 如果提供了 line_num 或 line_content 或 file_path，自动记录为 CodeIssue。
        """
        if line_num > 0 or line_content or file_path:
            issue = CodeIssue(
                message=message,
                severity=severity,
                line_num=line_num,
                line_content=line_content,
                file_path=file_path
            )
        else:
            issue = SimpleTextIssue(message=message, severity=severity)
            
        self._issues.append(issue)

    def clear(self):
        self._issues.clear()

    def has_issues(self) -> bool:
        return len(self._issues) > 0

    def get_issue_count(self) -> int:
        return len(self._issues)

    def get_issues(self) -> List[IssueBase]:
        return self._issues.copy()

    def to_dict_list(self) -> List[Dict[str, Any]]:
        return [issue.to_dict() for issue in self._issues]

    def get_formatted_text(self) -> str:
        """获取适合放入 Prompt 的格式化文本"""
        if not self._issues:
            return ""
        
        lines = []
        for idx, issue in enumerate(self._issues, 1):
            lines.append(f"{idx}. {str(issue)}")
        return "\n".join(lines)

    def print_issues(self):
        """控制台友好打印"""
        if not self._issues:
            return
            
        print(f"{Colors.WARNING}发现以下问题 ({len(self._issues)}):{Colors.ENDC}")
        for issue in self._issues:
            color = Colors.FAIL if issue.severity == "error" else Colors.WARNING
            print(f"{color}{str(issue)}{Colors.ENDC}")
