import sys
import os
import re
import difflib

from typing import Dict, List, Tuple, Optional, Set, Any
from typedef.ibc_data_types import (
    IbcBaseAstNode, ModuleNode, FunctionNode, VariableNode, BehaviorStepNode, ClassNode,
)
from libs.dir_json_funcs import DirJsonFuncs
from utils.issue_recorder import IbcIssueRecorder


class SymbolRefResolver:
    """
    符号引用解析器
    
    职责：解析IBC代码中以$符号标记的外部符号引用
    
    功能:
    1. 从 ast_dict 中提取所有符号引用（$标记的引用）
    2. 在可见符号树中解析和验证这些符号引用
    3. 提供符号引用的查找和匹配功能
    
    注意：可见符号表的构建由 VisibleSymbolBuilder 负责
    """
    
    def __init__(
        self, 
        ast_dict: Dict[int, IbcBaseAstNode],
        symbols_tree: Dict[str, Any],
        symbols_metadata: Dict[str, Dict[str, Any]],
        ibc_issue_recorder: IbcIssueRecorder,
        proj_root_dict: Dict[str, Any],
        dependent_relation: Dict[str, List[str]],
        current_file_path: str
    ):
        """
        初始化符号引用解析器
        
        Args:
            ast_dict: AST字典
            symbols_tree: 可见符号树（由VisibleSymbolBuilder构建）
            symbols_metadata: 可见符号元数据
            ibc_issue_recorder: 问题记录器
            proj_root_dict: 项目根目录字典
            dependent_relation: 依赖关系
            current_file_path: 当前文件路径
        """
        self.ast_dict = ast_dict
        self.symbols_tree = symbols_tree
        self.symbols_metadata = symbols_metadata
        self.ibc_issue_recorder = ibc_issue_recorder
        self.proj_root_dict = proj_root_dict
        self.dependent_relation = dependent_relation
        self.current_file_path = current_file_path
        
        # 从AST中提取模块引用信息
        self.module_imports = self._extract_module_imports()
        
        # 外部库依赖（从proj_root_dict中获取）
        self.external_library_dependencies = self._extract_external_libraries()
    
    def _extract_module_imports(self) -> Dict[str, str]:
        """从AST中提取所有module声明
        
        Returns:
            Dict[str, str]: {模块别名: 模块完整路径}
            例如: {"ball_entity": "src.ball.ball_entity"}
        """
        module_imports = {}
        
        # 遍历AST，查找ModuleNode
        for uid, node in self.ast_dict.items():
            if isinstance(node, ModuleNode):
                # module节点的identifier存储的是完整路径，如"src.ball.ball_entity"
                full_path = node.identifier
                # 从完整路径提取模块名（最后一部分）
                module_name = full_path.split('.')[-1] if '.' in full_path else full_path
                module_imports[module_name] = full_path
        
        return module_imports
    
    def _extract_external_libraries(self) -> Set[str]:
        """从proj_root_dict中提取外部库依赖
        
        Returns:
            Set[str]: 外部库名称集合
        """
        external_libs = set()
        
        # 检查proj_root_dict中是否有ExternalLibraryDependencies节点
        if "ExternalLibraryDependencies" in self.proj_root_dict:
            ext_deps = self.proj_root_dict["ExternalLibraryDependencies"]
            if isinstance(ext_deps, dict):
                external_libs.update(ext_deps.keys())
        
        return external_libs
    
    def resolve_all_references(self) -> None:
        """解析AST中的所有符号引用并验证"""
        # 遍历AST，查找所有包含符号引用的节点
        for uid, node in self.ast_dict.items():
            self._resolve_node_references(node)
    
    def _resolve_node_references(self, node: IbcBaseAstNode) -> None:
        """解析单个节点中的符号引用
        
        Args:
            node: AST节点
        """
        if isinstance(node, VariableNode):
            # 变量节点的type_ref字段包含符号引用列表
            for ref in node.type_ref:
                self._validate_symbol_reference(ref, node.line_number)
        
        elif isinstance(node, FunctionNode):
            # 函数参数的param_type_refs字段包含符号引用
            for param_name, ref in node.param_type_refs.items():
                self._validate_symbol_reference(ref, node.line_number)
        
        elif isinstance(node, BehaviorStepNode):
            # 行为步骤的symbol_refs字段包含符号引用列表
            for ref in node.symbol_refs:
                self._validate_symbol_reference(ref, node.line_number)
    
    def _validate_symbol_reference(self, ref: str, line_num: int) -> None:
        """验证单个符号引用
        
        Args:
            ref: 符号引用字符串（如"ball_entity.BallEntity"或"self.ball.get_position"）
            line_num: 行号
        """
        if not ref:
            return
        
        # 解析引用路径
        parts = ref.split('.')
        if len(parts) < 2:
            # 引用至少需要两部分：模块名.符号名
            self.ibc_issue_recorder.record_issue(
                message=f"符号引用格式错误，至少需要'模块.符号'的形式: {ref}",
                line_num=line_num,
                line_content=""
            )
            return
        
        # 第一部分是起点（模块名或self）
        start_point = parts[0]
        
        # 如果是self引用，跳过验证（属于内部引用）
        if start_point == "self":
            return
        
        # 验证起点是否在导入的模块中
        if start_point not in self.module_imports:
            # 起点不在导入模块中，尝试模糊匹配
            self._record_module_not_found(start_point, line_num, ref)
            return
        
        # 获取模块的完整路径
        module_full_path = self.module_imports[start_point]
        
        # 检查模块是否是外部库
        if self._is_external_library_module(module_full_path):
            # 外部库引用，认为正确，跳过后续验证
            return
        
        # 内部模块引用，需要在可见符号树中查找
        symbol_path = '.'.join(parts[1:])  # 去掉起点，得到符号路径
        self._validate_internal_symbol(module_full_path, symbol_path, line_num, ref)
    
    def _is_external_library_module(self, module_path: str) -> bool:
        """判断模块是否属于外部库
        
        Args:
            module_path: 模块完整路径（如"numpy.array"）
        
        Returns:
            bool: 是否为外部库
        """
        # 获取模块的顶层包名
        top_level_package = module_path.split('.')[0]
        return top_level_package in self.external_library_dependencies
    
    def _validate_internal_symbol(
        self, 
        module_path: str, 
        symbol_path: str, 
        line_num: int,
        original_ref: str
    ) -> None:
        """验证内部符号引用是否存在于可见符号树中
        
        Args:
            module_path: 模块完整路径（如"src.ball.ball_entity"）
            symbol_path: 符号路径（如"BallEntity.get_position"）
            line_num: 行号
            original_ref: 原始引用字符串
        """
        # 构建在symbols_metadata中的完整路径
        full_symbol_path = f"{module_path}.{symbol_path}"
        
        # 检查符号是否存在
        if full_symbol_path in self.symbols_metadata:
            # 符号存在，验证通过
            return
        
        # 符号不存在，尝试模糊匹配
        self._record_symbol_not_found(full_symbol_path, module_path, line_num, original_ref)
    
    def _record_module_not_found(self, module_name: str, line_num: int, original_ref: str) -> None:
        """记录模块未找到的问题，并尝试模糊匹配
        
        Args:
            module_name: 模块名
            line_num: 行号
            original_ref: 原始引用字符串
        """
        # 收集所有可能的模块名候选
        candidates = []
        
        # 从导入的模块中收集
        candidates.extend(self.module_imports.keys())
        
        # 从外部库中收集
        candidates.extend(self.external_library_dependencies)
        
        # 从依赖文件中收集（提取文件名作为候选）
        if self.current_file_path in self.dependent_relation:
            for dep_path in self.dependent_relation[self.current_file_path]:
                # 提取文件名
                file_name = dep_path.split('/')[-1]
                if file_name not in candidates:
                    candidates.append(file_name)
        
        # 从所有依赖关系中收集文件名（作为补充候选）
        for deps in self.dependent_relation.values():
            for dep_path in deps:
                file_name = dep_path.split('/')[-1]
                if file_name not in candidates:
                    candidates.append(file_name)
        
        # 使用difflib进行模糊匹配
        matches = difflib.get_close_matches(module_name, candidates, n=3, cutoff=0.3)
        
        if matches:
            suggestion = f"你是否想引用: {', '.join(matches)}？"
        else:
            suggestion = "未找到相似的模块名"
        
        message = f"模块引用错误：模块'{module_name}'未在导入列表或依赖关系中找到。{suggestion} 原始引用: {original_ref}"
        
        self.ibc_issue_recorder.record_issue(
            message=message,
            line_num=line_num,
            line_content=""
        )
    
    def _record_symbol_not_found(
        self, 
        full_symbol_path: str, 
        module_path: str,
        line_num: int,
        original_ref: str
    ) -> None:
        """记录符号未找到的问题，并尝试模糊匹配
        
        Args:
            full_symbol_path: 完整符号路径
            module_path: 模块路径
            line_num: 行号
            original_ref: 原始引用字符串
        """
        # 收集该模块下所有可见符号作为候选
        candidates = []
        
        for meta_path, meta in self.symbols_metadata.items():
            # 只收集属于该模块的符号（不包括folder和file）
            if meta_path.startswith(module_path + '.') and meta.get('type') not in ('folder', 'file'):
                # 提取相对于模块的符号路径
                relative_path = meta_path[len(module_path) + 1:]
                candidates.append(relative_path)
        
        # 提取待查找的符号路径（去掉模块前缀）
        symbol_to_find = full_symbol_path[len(module_path) + 1:]
        
        # 使用difflib进行模糊匹配
        matches = difflib.get_close_matches(symbol_to_find, candidates, n=3, cutoff=0.3)
        
        if matches:
            # 构建建议信息，包含符号描述
            suggestions = []
            for match in matches:
                match_full_path = f"{module_path}.{match}"
                meta = self.symbols_metadata.get(match_full_path, {})
                desc = meta.get('description', '无描述')
                suggestions.append(f"{match} ({desc})")
            
            suggestion = f"你是否想引用: {'; '.join(suggestions)}？"
        else:
            suggestion = f"在模块'{module_path}'中未找到相似的符号"
        
        message = f"符号引用错误：符号'{symbol_to_find}'在模块'{module_path}'的可见符号中未找到。{suggestion} 原始引用: {original_ref}"
        
        self.ibc_issue_recorder.record_issue(
            message=message,
            line_num=line_num,
            line_content=""
        )
    