import re
from typing import Dict, List, Optional, Set
from typedef.ibc_data_types import (
    IbcBaseAstNode, ClassNode, FunctionNode, VariableNode, 
    BehaviorStepNode, FileSymbolTable
)

class IbcSymbolFuncs:
    """Ibc符号相关功能"""
    
    def __init__(
        self, 
        ast_dict: Dict[int, IbcBaseAstNode],
        symbol_table: FileSymbolTable,
        vector_db_manager
    ):
        """
        初始化符号替换处理器
        
        Args:
            ast_dict: AST节点字典
            symbol_table: 文件符号表
            vector_db_manager: 符号向量数据库管理器
        """
        self.ast_dict = ast_dict
        self.symbol_table = symbol_table
        self.vector_db_manager = vector_db_manager
        
        # 构建符号名映射: {原始名称 -> 规范化名称}
        self.symbol_mapping = self._build_symbol_mapping()
    
    def _build_symbol_mapping(self) -> Dict[str, str]:
        """构建符号名映射"""
        mapping = {}
        for uid, symbol in self.symbol_table.get_all_symbols().items():
            if symbol.normalized_name:
                mapping[symbol.symbol_name] = symbol.normalized_name
        return mapping
    
    def replace_symbols_in_ast(self) -> None:
        """在AST中替换符号"""
        for uid, node in self.ast_dict.items():
            if isinstance(node, ClassNode):
                self._replace_class_symbols(node)
            elif isinstance(node, FunctionNode):
                self._replace_function_symbols(node)
            elif isinstance(node, VariableNode):
                self._replace_variable_symbols(node)
            elif isinstance(node, BehaviorStepNode):
                self._replace_behavior_symbols(node)
    
    def _replace_class_symbols(self, node: ClassNode) -> None:
        """替换类节点中的符号"""
        # 替换类名
        if node.identifier in self.symbol_mapping:
            node.identifier = self.symbol_mapping[node.identifier]
        
        # 替换继承参数中的符号
        if node.inh_params:
            new_params = {}
            for param_name, param_desc in node.inh_params.items():
                new_name = self.symbol_mapping.get(param_name, param_name)
                new_params[new_name] = param_desc
            node.inh_params = new_params
    
    def _replace_function_symbols(self, node: FunctionNode) -> None:
        """替换函数节点中的符号"""
        # 替换函数名
        if node.identifier in self.symbol_mapping:
            node.identifier = self.symbol_mapping[node.identifier]
        
        # 替换参数中的符号
        if node.params:
            new_params = {}
            for param_name, param_desc in node.params.items():
                new_name = self.symbol_mapping.get(param_name, param_name)
                new_params[new_name] = param_desc
            node.params = new_params
    
    def _replace_variable_symbols(self, node: VariableNode) -> None:
        """替换变量节点中的符号"""
        # 替换变量名
        if node.identifier in self.symbol_mapping:
            node.identifier = self.symbol_mapping[node.identifier]
    
    def _replace_behavior_symbols(self, node: BehaviorStepNode) -> None:
        """替换行为步骤节点中的符号"""
        if not node.content:
            return
        
        # 替换行为描述中的符号引用
        content = node.content
        
        # 1. 替换本地符号（不在$...$中的符号）
        for original_name, normalized_name in self.symbol_mapping.items():
            # 使用单词边界确保完整匹配
            pattern = r'\b' + re.escape(original_name) + r'\b'
            content = re.sub(pattern, normalized_name, content)
        
        # 2. 处理$ref_symbols$引用
        content = self._replace_ref_symbols(content, node.symbol_refs)
        
        node.content = content
    
    def _replace_ref_symbols(self, content: str, symbol_refs: List[str]) -> str:
        """
        替换内容中的$ref_symbols$引用
        
        Args:
            content: 原始内容
            symbol_refs: 符号引用列表
            
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
            normalized_name = self.vector_db_manager.search_symbol(ref_text)
        
            replacements.append((match.group(0), f"${normalized_name}$"))
        
        # 执行替换
        for old_text, new_text in replacements:
            content = content.replace(old_text, new_text)
        
        return content
