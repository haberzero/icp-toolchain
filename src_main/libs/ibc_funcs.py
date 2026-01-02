import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from libs.symbol_metadata_helper import SymbolMetadataHelper
# 导入新的辅助类
from libs.symbol_path_helper import SymbolPathHelper
from libs.symbol_replacer import SymbolReplacer
from typedef.exception_types import SymbolNotFoundError
from typedef.ibc_data_types import (AstNodeType, BehaviorStepNode,
                                    ClassMetadata, ClassNode, FileMetadata,
                                    FolderMetadata, FunctionMetadata,
                                    FunctionNode, IbcBaseAstNode,
                                    SymbolMetadata, VariableMetadata,
                                    VariableNode)


class IbcFuncs:
    """IBC代码处理相关的静态工具函数集合
    
    本类作为facade模式，为保持向后兼容，委托给专门的辅助类：
    - SymbolPathHelper: 处理符号路径相关逻辑
    - SymbolMetadataHelper: 处理符号元数据操作
    - SymbolReplacer: 处理符号替换逻辑
    
    推荐直接使用辅助类以获得更清晰的代码结构。
    """
    
    # ==================== MD5计算 ====================
    
    @staticmethod
    def calculate_text_md5(text: str) -> str:
        """计算文本字符串的MD5校验值"""
        try:
            text_hash = hashlib.md5()
            text_hash.update(text.encode('utf-8'))
            return text_hash.hexdigest()
        except UnicodeEncodeError as e:
            raise ValueError(f"文本编码错误,无法转换为UTF-8") from e
        except Exception as e:
            raise RuntimeError(f"计算文本MD5时发生未知错误") from e
    
    @staticmethod
    def calculate_symbols_metadata_md5(symbols_metadata: Dict[str, SymbolMetadata]) -> str:
        """计算符号元数据的MD5校验值
        
        委托给SymbolMetadataHelper.calculate_metadata_md5
        
        Args:
            symbols_metadata: 符号元数据字典
            
        Returns:
            str: MD5校验值
        """
        return SymbolMetadataHelper.calculate_metadata_md5(symbols_metadata)
    
    @staticmethod
    def count_symbols_in_metadata(symbols_metadata: Dict[str, SymbolMetadata]) -> int:
        """统计符号元数据中的符号数量(排除文件夹和文件节点)
        
        委托给SymbolMetadataHelper.count_symbols
        
        Args:
            symbols_metadata: 符号元数据字典
            
        Returns:
            int: 符号数量
        """
        return SymbolMetadataHelper.count_symbols(symbols_metadata)
    
    # ==================== 符号验证 ====================
    
    @staticmethod
    def validate_identifier(identifier: str) -> bool:
        """验证标识符是否符合编程规范
        
        标识符必须以字母或下划线开头,仅包含字母、数字、下划线
        """
        if not identifier:
            return False
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        return re.match(pattern, identifier) is not None
    
    # ==================== 符号路径处理 ====================
    
    @staticmethod
    def build_available_symbol_list(
        symbols_metadata: Dict[str, SymbolMetadata],
        proj_root_dict: Dict[str, Any]
    ) -> List[str]:
        """构建可用依赖符号列表
        
        委托给SymbolMetadataHelper.build_available_symbol_list
        
        Args:
            symbols_metadata: 符号元数据字典，键为完整的点分隔路径（如 src.ball.ball_entity.BallEntity）
            proj_root_dict: 项目根目录字典，用于确定文件名位置
            
        Returns:
            List[str]: 符号列表，每个元素格式为 "$filename.symbol ：功能描述"
        """
        return SymbolMetadataHelper.build_available_symbol_list(symbols_metadata, proj_root_dict)
    
    @staticmethod
    def _simplify_symbol_path(full_symbol_path: str, proj_root_dict: Dict[str, Any]) -> str:
        """简化符号路径（内部方法，保留以保持兼容性）
        
        委托给SymbolPathHelper.simplify_symbol_path
        """
        return SymbolPathHelper.simplify_symbol_path(full_symbol_path, proj_root_dict)
    
    # ==================== 符号元数据更新 ====================
    
    @staticmethod
    def update_symbols_normalized_names(
        symbols_metadata: Dict[str, SymbolMetadata],
        normalized_mapping: Dict[str, str]
    ) -> int:
        """批量更新符号元数据中的 normalized_name
        
        委托给SymbolMetadataHelper.update_normalized_names
        
        Args:
            symbols_metadata: 符号元数据字典（会被原地修改）
            normalized_mapping: 规范化映射 {符号路径: 规范化名称}
            
        Returns:
            int: 成功更新的符号数量
        """
        return SymbolMetadataHelper.update_normalized_names(symbols_metadata, normalized_mapping)
    
    # ==================== 符号替换 ====================
    
    @staticmethod
    def replace_symbols_with_normalized_names(
        ibc_content: str,
        ast_dict: Dict[int, IbcBaseAstNode],
        symbols_metadata: Dict[str, SymbolMetadata],
        current_file_name: str
    ) -> str:
        """将IBC代码内容中的所有符号替换为规范化后的名称
        
        委托给SymbolReplacer.replace_symbols_with_normalized_names
        
        Args:
            ibc_content: IBC代码原始内容
            ast_dict: AST字典
            symbols_metadata: 符号元数据（包含normalized_name）
            current_file_name: 当前文件名（不含路径和扩展名）
            
        Returns:
            str: 替换后的IBC代码内容
        """
        return SymbolReplacer.replace_symbols_with_normalized_names(
            ibc_content, ast_dict, symbols_metadata, current_file_name
        )
    
    @staticmethod
    def _get_normalized_name(symbol_path: str, symbols_metadata: Dict[str, SymbolMetadata]) -> Optional[str]:
        """从symbols_metadata中获取规范化名称（内部方法，保留以保持兼容性）
        
        委托给SymbolMetadataHelper.get_normalized_name
        """
        return SymbolMetadataHelper.get_normalized_name(symbol_path, symbols_metadata)
    
    @staticmethod
    def _get_parent_symbol_path(node: IbcBaseAstNode, ast_dict: Dict[int, IbcBaseAstNode], file_name: str) -> str:
        """获取节点的父符号路径（内部方法，保留以保持兼容性）
        
        委托给SymbolPathHelper.get_parent_symbol_path
        """
        return SymbolPathHelper.get_parent_symbol_path(node, ast_dict, file_name)
    
    @staticmethod
    def _apply_symbol_replacements(
        content: str,
        replacements: Dict[str, Tuple[str, str, int]],
        symbols_metadata: Dict[str, SymbolMetadata]
    ) -> str:
        """应用符号替换到IBC内容（内部方法，等待废弃）
        
        该方法已被SymbolReplacer类接管，保留此方法仅为向后兼容
        """
        # 委托给SymbolReplacer的内部方法
        return SymbolReplacer._apply_symbol_replacements(content, replacements, symbols_metadata)
    
    @staticmethod
    def _replace_dollar_references(
        content: str,
        symbols_metadata: Dict[str, SymbolMetadata],
        replacements: Dict[str, Tuple[str, str, int]]
    ) -> str:
        """替换$符号引用中的符号名称（内部方法，等待废弃）
        
        该方法已被SymbolReplacer类接管，保留此方法仅为向后兼容
        """
        return SymbolReplacer._replace_dollar_references(content, symbols_metadata, replacements)
    

    