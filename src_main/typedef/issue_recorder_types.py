from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class IbcIssue:
    """IBC分析问题记录
    
    用于存储IBC分析过程中发现的单个错误信息
    """
    message: str  # 错误消息
    line_num: int  # 行号
    line_content: str  # 行内容
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "message": self.message,
            "line_num": self.line_num,
            "line_content": self.line_content
        }


@dataclass
class TextIssue:
    """文本问题记录
    
    用于存储各类命令处理过程中发现的文本问题信息
    """
    issue_content: str  # 问题内容
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "issue_content": self.issue_content
        }

# 新问题记录器格式，分为普通text issue和code issue两种形式
@dataclass
class IssueBase:
    """所有 Issue 的基类"""
    message: str
    severity: str = "error"  # error, warning, info
    
    def to_dict(self) -> Dict[str, Any]:
        return {"message": self.message, "severity": self.severity}

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.message}"

@dataclass
class SimpleTextIssue(IssueBase):
    """简单的文本问题 (重命名为 SimpleTextIssue 以避免与旧的 TextIssue 冲突)"""
    pass

@dataclass
class CodeIssue(IssueBase):
    """代码相关问题，包含行号和上下文"""
    line_num: int = 0
    line_content: str = ""
    file_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "line_num": self.line_num,
            "line_content": self.line_content,
            "file_path": self.file_path
        })
        return d

    def __str__(self) -> str:
        loc = f"{self.file_path}:" if self.file_path else ""
        loc += f"Line {self.line_num}" if self.line_num > 0 else ""
        loc_str = f" ({loc})" if loc else ""
        context_str = f"\n    Context: {self.line_content.strip()}" if self.line_content else ""
        return f"[{self.severity.upper()}]{loc_str} {self.message}{context_str}"
