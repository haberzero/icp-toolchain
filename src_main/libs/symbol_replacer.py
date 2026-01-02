import re
from typing import Any, Dict, List, Tuple

from libs.symbol_metadata_helper import SymbolMetadataHelper
from libs.symbol_path_helper import SymbolPathHelper
from typedef.ibc_data_types import (BehaviorStepNode, ClassMetadata, ClassNode,
                                    FileMetadata, FolderMetadata,
                                    FunctionMetadata, FunctionNode,
                                    IbcBaseAstNode, SymbolMetadata,
                                    VariableMetadata, VariableNode)


class SymbolReplacer:
    """符号替换处理类
    
    提供将IBC代码中的符号替换为规范化名称的功能
    """
    
    @staticmethod
    def replace_symbols_with_normalized_names(
        ibc_content: str,
        ast_dict: Dict[int, IbcBaseAstNode],
        symbols_metadata: Dict[str, SymbolMetadata],
        current_file_name: str
    ) -> str:
        """将IBC代码内容中的所有符号替换为规范化后的名称
        
        该方法遍历AST，找到所有定义的符号（类名、函数名、变量名、参数名）和
        所有符号引用（$引用），然后用规范化后的名称替换原始文本中的相应位置。
        
        Args:
            ibc_content: IBC代码原始内容
            ast_dict: AST字典
            symbols_metadata: 符号元数据（包含normalized_name）
            current_file_name: 当前文件名（不含路径和扩展名）
            
        Returns:
            str: 替换后的IBC代码内容
        """
        # 收集所有需要替换的符号映射
        replacements = SymbolReplacer._collect_symbol_replacements(
            ast_dict, symbols_metadata, current_file_name
        )
        
        # 执行替换
        result = SymbolReplacer._apply_symbol_replacements(
            ibc_content, replacements, symbols_metadata
        )
        
        return result
    
    @staticmethod
    def _collect_symbol_replacements(
        ast_dict: Dict[int, IbcBaseAstNode],
        symbols_metadata: Dict[str, SymbolMetadata],
        current_file_name: str
    ) -> Dict[str, Tuple[str, str, int]]:
        """收集所有需要替换的符号映射
        
        Args:
            ast_dict: AST字典
            symbols_metadata: 符号元数据
            current_file_name: 当前文件名
            
        Returns:
            Dict[str, Tuple[str, str, int]]: 
                {原始名称: (规范化名称, 符号类型, 优先级)}
        """
        replacements = {}
        
        # 遍历AST收集符号
        for uid, node in ast_dict.items():
            if uid == 0:  # 跳过根节点
                continue
            
            # 处理类节点
            if isinstance(node, ClassNode) and node.identifier:
                SymbolReplacer._collect_class_replacements(
                    node, ast_dict, symbols_metadata, current_file_name, replacements
                )
            
            # 处理函数节点
            elif isinstance(node, FunctionNode) and node.identifier:
                SymbolReplacer._collect_function_replacements(
                    node, ast_dict, symbols_metadata, current_file_name, replacements
                )
            
            # 处理变量节点
            elif isinstance(node, VariableNode) and node.identifier:
                SymbolReplacer._collect_variable_replacements(
                    node, ast_dict, symbols_metadata, current_file_name, replacements
                )
        
        # 从 symbols_metadata 中收集所有其他符号（特别是 behavior 中的局部变量）
        for symbol_path, meta in symbols_metadata.items():
            # 跳过文件夹和文件节点
            if isinstance(meta, (FolderMetadata, FileMetadata)):
                continue
            
            # 只处理有normalized_name的dataclass
            if isinstance(meta, (ClassMetadata, FunctionMetadata, VariableMetadata)):
                normalized_name = meta.normalized_name
                if not normalized_name:
                    continue
                
                # 提取原始名称（symbol_path 的最后一部分）
                original_name = symbol_path.split('.')[-1]
                
                # 如果还没有被添加，就加入
                if original_name not in replacements and normalized_name != original_name:
                    # 优先级设为1，在普通符号之后替换
                    replacements[original_name] = (normalized_name, meta.type, 1)
        
        return replacements
    
    @staticmethod
    def _collect_class_replacements(
        node: ClassNode,
        ast_dict: Dict[int, IbcBaseAstNode],
        symbols_metadata: Dict[str, SymbolMetadata],
        current_file_name: str,
        replacements: Dict[str, Tuple[str, str, int]]
    ) -> None:
        """收集类节点的符号替换"""
        symbol_path = f"{current_file_name}.{node.identifier}"
        normalized = SymbolMetadataHelper.get_normalized_name(symbol_path, symbols_metadata)
        
        if normalized and normalized != node.identifier:
            # 类名的优先级最高（3），因为可能包含在其他标识符中
            replacements[node.identifier] = (normalized, 'class', 3)
        
        # 处理类的继承参数
        for param_name in node.inh_params.keys():
            param_path = f"{symbol_path}.{param_name}"
            param_normalized = SymbolMetadataHelper.get_normalized_name(param_path, symbols_metadata)
            if param_normalized and param_normalized != param_name:
                replacements[param_name] = (param_normalized, 'param', 1)
    
    @staticmethod
    def _collect_function_replacements(
        node: FunctionNode,
        ast_dict: Dict[int, IbcBaseAstNode],
        symbols_metadata: Dict[str, SymbolMetadata],
        current_file_name: str,
        replacements: Dict[str, Tuple[str, str, int]]
    ) -> None:
        """收集函数节点的符号替换"""
        # 获取父节点路径
        parent_path = SymbolPathHelper.get_parent_symbol_path(node, ast_dict, current_file_name)
        symbol_path = f"{parent_path}.{node.identifier}" if parent_path else f"{current_file_name}.{node.identifier}"
        normalized = SymbolMetadataHelper.get_normalized_name(symbol_path, symbols_metadata)
        
        if normalized and normalized != node.identifier:
            replacements[node.identifier] = (normalized, 'func', 2)
        
        # 处理函数参数
        for param_name in node.params.keys():
            param_symbol_path = f"{symbol_path}.{param_name}"
            param_normalized = SymbolMetadataHelper.get_normalized_name(param_symbol_path, symbols_metadata)
            if param_normalized and param_normalized != param_name:
                replacements[param_name] = (param_normalized, 'param', 1)
    
    @staticmethod
    def _collect_variable_replacements(
        node: VariableNode,
        ast_dict: Dict[int, IbcBaseAstNode],
        symbols_metadata: Dict[str, SymbolMetadata],
        current_file_name: str,
        replacements: Dict[str, Tuple[str, str, int]]
    ) -> None:
        """收集变量节点的符号替换"""
        # 获取父节点路径
        parent_path = SymbolPathHelper.get_parent_symbol_path(node, ast_dict, current_file_name)
        symbol_path = f"{parent_path}.{node.identifier}" if parent_path else f"{current_file_name}.{node.identifier}"
        normalized = SymbolMetadataHelper.get_normalized_name(symbol_path, symbols_metadata)
        
        if normalized and normalized != node.identifier:
            replacements[node.identifier] = (normalized, 'var', 2)
    
    @staticmethod
    def _apply_symbol_replacements(
        content: str,
        replacements: Dict[str, Tuple[str, str, int]],
        symbols_metadata: Dict[str, SymbolMetadata]
    ) -> str:
        """应用符号替换到IBC内容
        
        策略：
        1. 按照优先级和长度排序（先长后短，避免部分匹配）
        2. 使用正则表达式进行精确的标识符边界匹配
        3. 处理$符号引用
        
        Args:
            content: 原始内容
            replacements: 替换映射 {原始名称: (规范化名称, 类型, 优先级)}
            symbols_metadata: 符号元数据（用于处理$引用）
            
        Returns:
            str: 替换后的内容
        """
        result = content
        
        # 按优先级和长度排序（优先级高的先处理，同优先级的长的先处理）
        sorted_replacements = sorted(
            replacements.items(),
            key=lambda x: (-x[1][2], -len(x[0]))  # 优先级降序，长度降序
        )
        
        # 执行普通标识符替换
        for original, (normalized, sym_type, _) in sorted_replacements:
            # 使用正则表达式匹配完整的标识符（避免部分匹配）
            # 标识符前后必须是非标识符字符
            pattern = r'(?<![\w_])' + re.escape(original) + r'(?![\w_])'
            result = re.sub(pattern, normalized, result)
        
        # 处理$符号引用
        result = SymbolReplacer._replace_dollar_references(result, symbols_metadata, replacements)
        
        return result
    
    @staticmethod
    def _replace_dollar_references(
        content: str,
        symbols_metadata: Dict[str, SymbolMetadata],
        replacements: Dict[str, Tuple[str, str, int]]
    ) -> str:
        """替换$符号引用中的符号名称
        
        Args:
            content: 内容
            symbols_metadata: 符号元数据
            replacements: 已有的替换映射
            
        Returns:
            str: 替换后的内容
        """
        # 匹配$引用：$后跟标识符和点分隔的路径
        # 例如: $gravity.apply_gravity, $self.position, $friction.FrictionManager
        pattern = r'\$([\w_]+(?:\.[\w_]+)*)'
        
        def replace_ref(match):
            ref = match.group(1)  # 不含$的引用路径
            parts = ref.split('.')
            
            # 替换路径中的每个部分
            new_parts = []
            for part in parts:
                if part in replacements:
                    new_parts.append(replacements[part][0])  # 使用规范化名称
                else:
                    new_parts.append(part)
            
            return '$' + '.'.join(new_parts)
        
        return re.sub(pattern, replace_ref, content)
