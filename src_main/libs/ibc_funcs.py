import os
import json
import re
import hashlib
from typing import List, Dict, Optional, Union, Set, Any

from typedef.ibc_data_types import (
    IbcBaseAstNode, ClassNode, FunctionNode, VariableNode, 
    BehaviorStepNode, SymbolType, VisibilityTypes, SymbolNode
)
from typedef.exception_types import SymbolNotFoundError

class IbcFuncs:
    """IBC代码处理相关的静态工具函数集合"""
    
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
    
    # ==================== 符号规范化响应解析 ====================
    
    @staticmethod
    def parse_symbol_normalizer_response(response: str) -> Dict[str, Dict[str, str]]:
        """解析符号规范化AI的响应
        
        Args:
            response: AI返回的JSON格式响应
            
        Returns:
            Dict[str, Dict[str, str]]: 符号规范化结果字典
                格式: {"原始符号名": {"normalized_name": "规范化名", "visibility": "可见性"}}
        """
        try:
            # 解析JSON
            result = json.loads(response)
            
            # 有效的可见性值列表
            valid_visibilities = [v.value for v in VisibilityTypes]
            
            # 验证结果格式
            validated_result = {}
            for symbol_name, symbol_data in result.items():
                if 'normalized_name' in symbol_data and 'visibility' in symbol_data:
                    # 验证normalized_name符合标识符规范
                    if IbcFuncs.validate_identifier(symbol_data['normalized_name']):
                        # 验证visibility是预定义值
                        if symbol_data['visibility'] in valid_visibilities:
                            validated_result[symbol_name] = symbol_data
                        else:
                            print(f"    警告: 符号 {symbol_name} 的可见性值无效: {symbol_data['visibility']},使用默认值")
                            # 仍然保留该符号,但使用默认可见性
                            symbol_data['visibility'] = 'module_local'
                            validated_result[symbol_name] = symbol_data
                    else:
                        print(f"    警告: 符号 {symbol_name} 的规范化名称无效: {symbol_data['normalized_name']}")
            
            return validated_result
            
        except json.JSONDecodeError as e:
            print(f"    错误: 解析AI响应JSON失败: {e}")
            return {}
        except Exception as e:
            print(f"    错误: 处理AI响应失败: {e}")
            return {}
    
    # ==================== 符号映射构建 ====================
    
    @staticmethod
    def build_symbol_mapping(symbol_table: Dict[str, SymbolNode]) -> Dict[str, str]:
        """构建符号名映射字典
        
        Args:
            symbol_table: 文件符号表字典
            
        Returns:
            Dict[str, str]: {原始名称 -> 规范化名称} 映射
        """
        mapping = {}
        for symbol_name, symbol in symbol_table.items():
            if symbol.normalized_name:
                mapping[symbol.symbol_name] = symbol.normalized_name
        return mapping
    
    # ==================== 符号表更新 ====================
    
    @staticmethod
    def update_symbol_normalized_name(
        symbol_table: Dict[str, SymbolNode],
        symbol_name: str,
        normalized_name: str
    ) -> None:
        """
        更新符号的规范化名称
        
        Args:
            symbol_table: 符号表字典
            symbol_name: 符号名称
            normalized_name: 规范化名称
            
        Raises:
            SymbolNotFoundError: 当符号不存在时抛出
        """
        symbol = symbol_table.get(symbol_name)
        if symbol is None:
            raise SymbolNotFoundError(symbol_name, "更新规范化名称")
        
        symbol.normalized_name = normalized_name
    
    @staticmethod
    def update_symbol_visibility(
        symbol_table: Dict[str, SymbolNode],
        symbol_name: str,
        visibility: VisibilityTypes
    ) -> None:
        """
        更新符号的可见性
        
        Args:
            symbol_table: 符号表字典
            symbol_name: 符号名称
            visibility: 可见性
            
        Raises:
            SymbolNotFoundError: 当符号不存在时抛出
        """
        symbol = symbol_table.get(symbol_name)
        if symbol is None:
            raise SymbolNotFoundError(symbol_name, "更新可见性")
        
        symbol.visibility = visibility
    
    @staticmethod
    def update_symbol_normalized_info(
        symbol_table: Dict[str, SymbolNode],
        symbol_name: str,
        normalized_name: str,
        visibility: VisibilityTypes
    ) -> None:
        """
        同时更新符号的规范化名称和可见性
        
        Args:
            symbol_table: 符号表字典
            symbol_name: 符号名称
            normalized_name: 规范化名称
            visibility: 可见性
            
        Raises:
            SymbolNotFoundError: 当符号不存在时抛出
        """
        symbol = symbol_table.get(symbol_name)
        if symbol is None:
            raise SymbolNotFoundError(symbol_name, "更新规范化信息")
        
        symbol.normalized_name = normalized_name
        symbol.visibility = visibility
    
    # ==================== AST符号替换 ====================
    
    @staticmethod
    def replace_symbols_in_ast(
        ast_dict: Dict[int, IbcBaseAstNode],
        symbol_mapping: Dict[str, str],
        vector_db_manager=None
    ) -> None:
        """在AST中替换符号为规范化名称
        
        Args:
            ast_dict: AST节点字典
            symbol_mapping: 符号映射字典 {原始名称 -> 规范化名称}
            vector_db_manager: 符号向量数据库管理器(可选,用于$ref$引用查找)
        """
        for uid, node in ast_dict.items():
            if isinstance(node, ClassNode):
                IbcFuncs._replace_class_symbols(node, symbol_mapping)
            elif isinstance(node, FunctionNode):
                IbcFuncs._replace_function_symbols(node, symbol_mapping)
            elif isinstance(node, VariableNode):
                IbcFuncs._replace_variable_symbols(node, symbol_mapping)
            elif isinstance(node, BehaviorStepNode):
                IbcFuncs._replace_behavior_symbols(node, symbol_mapping, vector_db_manager)
    
    @staticmethod
    def _replace_class_symbols(node: ClassNode, symbol_mapping: Dict[str, str]) -> None:
        """替换类节点中的符号"""
        # 替换类名
        if node.identifier in symbol_mapping:
            node.identifier = symbol_mapping[node.identifier]
        
        # 替换继承参数中的符号
        if node.inh_params:
            new_params = {}
            for param_name, param_desc in node.inh_params.items():
                new_name = symbol_mapping.get(param_name, param_name)
                new_params[new_name] = param_desc
            node.inh_params = new_params
    
    @staticmethod
    def _replace_function_symbols(node: FunctionNode, symbol_mapping: Dict[str, str]) -> None:
        """替换函数节点中的符号"""
        # 替换函数名
        if node.identifier in symbol_mapping:
            node.identifier = symbol_mapping[node.identifier]
        
        # 替换参数中的符号
        if node.params:
            new_params = {}
            for param_name, param_desc in node.params.items():
                new_name = symbol_mapping.get(param_name, param_name)
                new_params[new_name] = param_desc
            node.params = new_params
    
    @staticmethod
    def _replace_variable_symbols(node: VariableNode, symbol_mapping: Dict[str, str]) -> None:
        """替换变量节点中的符号"""
        # 替换变量名
        if node.identifier in symbol_mapping:
            node.identifier = symbol_mapping[node.identifier]
    
    @staticmethod
    def _replace_behavior_symbols(
        node: BehaviorStepNode,
        symbol_mapping: Dict[str, str],
        vector_db_manager=None
    ) -> None:
        """替换行为步骤节点中的符号"""
        if not node.content:
            return
        
        # 替换行为描述中的符号引用
        content = node.content
        
        # 1. 替换本地符号(不在$...$中的符号)
        for original_name, normalized_name in symbol_mapping.items():
            # 使用单词边界确保完整匹配
            pattern = r'\b' + re.escape(original_name) + r'\b'
            content = re.sub(pattern, normalized_name, content)
        
        # 2. 处理$ref_symbols$引用
        if vector_db_manager:
            content = IbcFuncs._replace_ref_symbols(content, vector_db_manager)
        
        node.content = content
    
    @staticmethod
    def _replace_ref_symbols(content: str, vector_db_manager) -> str:
        """替换内容中的$ref_symbols引用
        
        Args:
            content: 原始内容
            vector_db_manager: 向量数据库管理器
            
        Returns:
            str: 替换后的内容
        """
        # 查找所有$...$模式
        pattern = r'\$([^$]+)\$'
        matches = re.finditer(pattern, content)
        
        replacements = []
        for match in matches:
            ref_text = match.group(1)
            
            # 使用向量搜索查找最匹配的符号
            normalized_name = vector_db_manager.search_symbol(ref_text)
        
            replacements.append((match.group(0), f"${normalized_name}$"))
        
        # 执行替换
        for old_text, new_text in replacements:
            content = content.replace(old_text, new_text)
        
        return content
    
