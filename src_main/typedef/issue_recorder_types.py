from typing import Dict, Any
from dataclasses import dataclass


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
