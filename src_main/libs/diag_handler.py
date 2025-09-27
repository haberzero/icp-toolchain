from typing import List, Dict, Any, Optional
from enum import Enum


# 错误类型枚举
class IcbEType(Enum):
    TAB_DETECTED = 1            # 识别到 Tab 字符
    INDENT_MISALIGNMENT = 2     # 缩进数量错误
    INDENT_JUMP = 3             # 缩进跳变错误
    UNEXPECTED_COLON = 4        # 意外的冒号
    UNKNOWN_LINE_TYPE = 5       # 未知行类型
    MISSING_CLASS_NAME = 6      # 缺少类名
    MISSING_FUNCTION_NAME = 7   # 缺少函数名
    MISSING_VAR_NAME = 8        # 缺少变量名
    MISSING_COLON = 9           # 缺少冒号
    UNEXPECTED_SPACE = 10       # 多余的空格
    EXTRA_CONTENT_AFTER_COLON = 11   # 冒号后有多余内容
    UNEXPECTED_NEXT_NODE = 12   # 意外的下一节点类型
    UNEXPECTED_CHILD_NODE = 13  # 意外的子节点类型
    UNEXPECTED_SPECIAL_ALIGN = 14   # 具备特殊缩进对齐的节点 对齐错误
    UNEXPECTED_INDENT_INC = 15      # 意外的缩进增加
    MISSING_INDENT_BLOCKSTART = 16  # 块起始节点之后缺失缩进


# 警告类型枚举
class IcbWType(Enum):
    MYPASS = 1            # 占位符


# 诊断信息类
class DiagInfo:
    def __init__(self, line_num: int, file_path: str):
        self.line_num: int = line_num
        self.file_path: str = file_path
        self.error_type: Optional[IcbEType] = None
        self.warning_type: Optional[IcbWType] = None
        self.message: str = ""


# 诊断处理类
class DiagHandler:
    def __init__(self, file_path: str, file_content: List[str]):
        self.file_path: str = file_path
        self.file_content: List[str] = file_content
        self.diag_table: Dict[int, DiagInfo] = {}  # key: 行号；value: 诊断信息
    
    def _ensure_line_exists(self, line_num: int) -> None:
        if line_num not in self.diag_table:
            self.diag_table[line_num] = DiagInfo(line_num, self.file_path)

    def set_line_error(self, line_num: int, error_type: IcbEType) -> None:
        if not isinstance(error_type, IcbEType):
            raise ValueError(f"Invalid error_type: {error_type}. Must be an instance of IcbEType.")
        self._ensure_line_exists(line_num)
        self.diag_table[line_num].error_type = error_type

    def set_line_warning(self, line_num: int, warning_type: IcbWType) -> None:
        if not isinstance(warning_type, IcbWType):
            raise ValueError(f"Invalid warning_type: {warning_type}. Must be an instance of IcbWType.")
        self._ensure_line_exists(line_num)
        self.diag_table[line_num].warning_type = warning_type

    def set_line_message(self, line_num: int, message: str) -> None:
        self._ensure_line_exists(line_num)
        self.diag_table[line_num].message = message

    def get_line_diag(self, line_num: int) -> Optional[DiagInfo]:
        return self.diag_table.get(line_num)

    def read_diag_table_all(self) -> Dict[int, DiagInfo]:
        return self.diag_table

    def is_diag_table_valid(self) -> bool:
        return bool(self.diag_table)
    
    def get_file_path(self) -> str:
        return self.file_path
    
    def get_file_content(self) -> List[str]:
        return self.file_content