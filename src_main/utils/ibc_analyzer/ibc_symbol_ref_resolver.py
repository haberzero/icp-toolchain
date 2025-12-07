import sys
import os

from typing import Dict, List, Tuple, Optional
from typedef.ibc_data_types import (
    IbcBaseAstNode, ModuleNode, FunctionNode, VariableNode, BehaviorStepNode,
    FileSymbolTable, SymbolNode, SymbolType
)
from libs.dir_json_funcs import DirJsonFuncs


class SymbolRefResolver:
    def __init__(self, proj_root_dict: Dict):
        """
        初始化符号引用解析器
        
        Args:
            proj_root_dict:
        """
        self.proj_root_dict = proj_root_dict
        
        # 获取所有有效的文件路径
        self.valid_file_paths = set(DirJsonFuncs.get_all_file_paths(proj_root_dict))
        
        print(f"初始化符号引用解析器")
        print(f"  有效文件路径数: {len(self.valid_file_paths)}")
        print(f"  AST节点数: {len(ast_dict)}")
    