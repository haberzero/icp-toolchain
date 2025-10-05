from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class DiagInfo:
    line_num: int
    file_path: str
    error_type: Optional[str] = None
    warning_type: Optional[str] = None
    message: str = ""

class IcbEType(Enum):
    # 缩进错误
    TAB_DETECTED = "ICB_TAB_DETECTED"
    INDENT_MISALIGNMENT = "ICB_INDENT_MISALIGNMENT"
    INDENT_JUMP = "ICB_INDENT_JUMP"
    MISSING_INDENT_BLOCKSTART = "ICB_MISSING_INDENT_BLOCKSTART"
    UNEXPECTED_INDENT_INC = "ICB_UNEXPECTED_INDENT_INC"
    UNEXPECTED_SPECIAL_ALIGN = "ICB_UNEXPECTED_SPECIAL_ALIGN"
    
    # 语法错误
    UNEXPECTED_COLON = "ICB_UNEXPECTED_COLON"
    MISSING_COLON = "ICB_MISSING_COLON"
    EXTRA_CONTENT_AFTER_COLON = "ICB_EXTRA_CONTENT_AFTER_COLON"
    UNEXPECTED_SPACE = "ICB_UNEXPECTED_SPACE"
    UNKNOWN_LINE_TYPE = "ICB_UNKNOWN_LINE_TYPE"
    KEYWORD_FORMAT_ERROR = "ICB_KEYWORD_FORMAT_ERROR"
    
    # 具体元素错误
    MISSING_CLASS_NAME = "ICB_MISSING_CLASS_NAME"
    MISSING_FUNCTION_NAME = "ICB_MISSING_FUNCTION_NAME"
    MISSING_VAR_NAME = "ICB_MISSING_VAR_NAME"
    MISSING_MODULE_NAME = "ICB_MISSING_MODULE_NAME"
    
    # 结构错误
    UNEXPECTED_NEXT_NODE = "ICB_UNEXPECTED_NEXT_NODE"
    UNEXPECTED_CHILD_NODE = "ICB_UNEXPECTED_CHILD_NODE"
    
    # Module相关错误
    MODULE_NOT_AT_TOP = "ICB_MODULE_NOT_AT_TOP"


class IcbWType(Enum):
    # 警告类型
    pass

class DiagHandler:
    def __init__(self, file_path: str, file_content: List[str]):
        self.file_path = file_path
        self.file_content = file_content
        self.diag_table: List[DiagInfo] = []
    
    def set_line_error(self, line_num: int, error_type: IcbEType, message: str = ""):
        """设置某一行的错误信息"""
        if not message:
            message = self._get_default_error_message(error_type)
        
        diag_info = DiagInfo(
            line_num=line_num,
            file_path=self.file_path,
            error_type=error_type.value,
            message=message
        )
        self.diag_table.append(diag_info)
    
    def set_line_warning(self, line_num: int, warning_type: IcbWType, message: str = ""):
        """设置某一行的警告信息"""
        if not message:
            message = self._get_default_warning_message(warning_type)
        
        diag_info = DiagInfo(
            line_num=line_num,
            file_path=self.file_path,
            warning_type=warning_type.value,
            message=message
        )
        self.diag_table.append(diag_info)
    
    def is_diag_table_valid(self) -> bool:
        """检查诊断表是否包含任何诊断信息"""
        return len(self.diag_table) > 0
    
    def get_diag_table(self) -> List[DiagInfo]:
        """获取诊断信息表"""
        return self.diag_table
    
    def _get_default_error_message(self, error_type: IcbEType) -> str:
        """获取默认错误消息"""
        error_messages = {
            IcbEType.TAB_DETECTED: "检测到使用了tab字符，请使用空格进行缩进",
            IcbEType.INDENT_MISALIGNMENT: "缩进未对齐，缩进必须是4个空格的整数倍",
            IcbEType.INDENT_JUMP: "缩进跳跃错误，不允许直接从低层级缩进到高层级",
            IcbEType.MISSING_INDENT_BLOCKSTART: "缺少缩进，块开始语句后应进行缩进",
            IcbEType.UNEXPECTED_INDENT_INC: "意外的缩进增加，非块开始语句不应增加缩进",
            IcbEType.UNEXPECTED_SPECIAL_ALIGN: "特殊对齐错误，特殊对齐行应与上一行保持相同缩进",
            IcbEType.UNEXPECTED_COLON: "意外的冒号，行首不应直接以冒号开始",
            IcbEType.MISSING_COLON: "缺少冒号，声明语句后应使用冒号",
            IcbEType.EXTRA_CONTENT_AFTER_COLON: "冒号后存在多余内容",
            IcbEType.UNEXPECTED_SPACE: "存在意外的空格",
            IcbEType.UNKNOWN_LINE_TYPE: "未知的行类型",
            IcbEType.KEYWORD_FORMAT_ERROR: "关键字格式错误，关键字后应有空格和相应内容",
            IcbEType.MISSING_CLASS_NAME: "缺少类名",
            IcbEType.MISSING_FUNCTION_NAME: "缺少函数名",
            IcbEType.MISSING_VAR_NAME: "缺少变量名",
            IcbEType.MISSING_MODULE_NAME: "缺少模块名",
            IcbEType.UNEXPECTED_NEXT_NODE: "意外的下一行节点类型",
            IcbEType.UNEXPECTED_CHILD_NODE: "意外的子节点类型",
            IcbEType.MODULE_NOT_AT_TOP: "module声明必须出现在文件顶部，不能在其他声明之后出现"
        }
        return error_messages.get(error_type, "未知错误")
    
    def _get_default_warning_message(self, warning_type: IcbWType) -> str:
        """获取默认警告消息"""
        # 暂无默认警告消息
        return "未知警告"