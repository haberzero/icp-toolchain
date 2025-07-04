from typing import List, Dict, Any, Optional
from enum import Enum


# 错误类型枚举
class EType(Enum):
    TAB_DETECTED = 1            # 识别到 Tab 字符
    INDENT_MISALIGNMENT = 2     # 缩进数量错误
    INDENT_JUMP = 3             # 缩进跳变错误


# 警告类型枚举
class WType(Enum):
    MYPASS = 1            # 占位符


# 诊断处理类
class DiagHandler:
    def __init__(self):
        self.diag_table = {}  # key: 行号；value: dict of error info

    def _ensure_line_exists(self, line_num: int) -> None:
        if line_num not in self.diag_table:
            self.diag_table[line_num] = {
                'EType': None,      # 错误信息类型
                'WType': None,      # 警告信息类型
            }

    def set_line_error(self, line_num: int, error_type: EType) -> None:
        if not isinstance(error_type, EType):
            raise ValueError(f"Invalid error_type: {error_type}. Must be an instance of EType.")
        self._ensure_line_exists(line_num)
        self.diag_table[line_num]['error_type'] = error_type

    def set_line_warning(self, line_num: int, warning_type: WType) -> None:
        if not isinstance(warning_type, WType):
            raise ValueError(f"Invalid warning_type: {warning_type}. Must be an instance of WType.")
        self._ensure_line_exists(line_num)
        self.diag_table[line_num]['warning_type'] = warning_type

    def read_diag_table_all(self) -> Dict[int, Dict[str, Any]]:
        return self.diag_table

    def is_diag_table_valid(self) -> bool:
        return bool(self.diag_table)