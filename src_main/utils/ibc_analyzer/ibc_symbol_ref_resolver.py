import sys
import os
import re
import difflib

from typing import Dict, List, Tuple, Optional, Set, Any
from typedef.ibc_data_types import (
    IbcBaseAstNode, ModuleNode, FunctionNode, VariableNode, BehaviorStepNode, ClassNode,
)
from libs.dir_json_funcs import DirJsonFuncs



# matches = difflib.get_close_matches(target, candidates, n=3, cutoff=0.3)


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
    
    def __init__(self, visible_symbol_tree: Dict[str, Any]):
        """
        初始化符号引用解析器
        
        Args:
            visible_symbol_tree: 可见符号树（由VisibleSymbolBuilder构建）
        """
        print(f"初始化符号引用解析器")
        self.visible_symbol_tree = visible_symbol_tree
        
        # 存储从 ast_dict 中提取的各类引用
        self.module_refs: List[str] = []  # module 引用列表
        self.param_type_refs: List[Tuple[str, str]] = []  # (参数名, 符号引用) 元组列表
        self.var_type_refs: List[Tuple[str, str]] = []  # (变量名, 符号引用) 元组列表
        self.behavior_refs: List[str] = []  # 行为描述中的符号引用列表
        self.class_inherit_refs: List[str] = []  # 类继承中的符号引用列表


    def set_visible_symbol_tree(self, visible_symbol_tree: Dict[str, Any]) -> None:
        """
        设置/更新可见符号树
        
        Args:
            visible_symbol_tree: 新的可见符号树
        """
        self.visible_symbol_tree = visible_symbol_tree
        print(f"可见符号树已更新")

    
    def extract_all_refs_from_ast_dict(self, ast_dict: Dict[int, IbcBaseAstNode]) -> None:
        """
        从 AST 字典中提取所有符号引用
        
        遍历 ast_dict，从各类节点中提取:
        - module 引用
        - 函数参数类型引用
        - 变量类型引用
        - 类继承引用
        - 行为描述中的符号引用
        
        Args:
            ast_dict: AST 节点字典
        """
        print(f"开始从 AST 中提取符号引用")
        
        # 清空之前的引用记录
        self.module_refs.clear()
        self.param_type_refs.clear()
        self.var_type_refs.clear()
        self.class_inherit_refs.clear()
        self.behavior_refs.clear()
        
        for uid, ast_node in ast_dict.items():
            if isinstance(ast_node, ModuleNode):
                self._extract_module_refs(ast_node)
            elif isinstance(ast_node, ClassNode):
                self._extract_class_refs(ast_node)
            elif isinstance(ast_node, FunctionNode):
                self._extract_function_refs(ast_node)
            elif isinstance(ast_node, VariableNode):
                self._extract_variable_refs(ast_node)
            elif isinstance(ast_node, BehaviorStepNode):
                self._extract_behavior_refs(ast_node)
        
        print(f"  module 引用数: {len(self.module_refs)}")
        print(f"  函数参数类型引用数: {len(self.param_type_refs)}")
        print(f"  变量类型引用数: {len(self.var_type_refs)}")
        print(f"  类继承引用数: {len(self.class_inherit_refs)}")
        print(f"  行为描述引用数: {len(self.behavior_refs)}")
    
    def _extract_module_refs(self, module_node: ModuleNode) -> None:
        """
        提取 module 节点中的引用
        
        Args:
            module_node: module 节点
        """
        if module_node.identifier:
            self.module_refs.append(module_node.identifier)
    
    def _extract_class_refs(self, class_node: ClassNode) -> None:
        """
        提取 class 节点中的继承引用
        
        Args:
            class_node: class 节点
        """
        # 从 inh_params 字典中提取父类符号引用
        for param_key, param_value in class_node.inh_params.items():
            # param_key 可能是父类的符号引用
            if param_key:
                self.class_inherit_refs.append(param_key)
    
    def _extract_function_refs(self, function_node: FunctionNode) -> None:
        """
        提取 function 节点中的参数类型引用
        
        Args:
            function_node: function 节点
        """
        # 从 param_type_refs 字典中提取符号引用
        for param_name, type_ref in function_node.param_type_refs.items():
            if type_ref:
                self.param_type_refs.append((param_name, type_ref))
    
    def _extract_variable_refs(self, variable_node: VariableNode) -> None:
        """
        提取 variable 节点中的类型引用
        
        Args:
            variable_node: variable 节点
        """
        # 从 type_ref 字段中提取符号引用
        if variable_node.type_ref:
            self.var_type_refs.append((variable_node.identifier, variable_node.type_ref))
    
    def _extract_behavior_refs(self, behavior_node: BehaviorStepNode) -> None:
        """
        提取 behavior 节点中的符号引用
        
        Args:
            behavior_node: behavior 节点
        """
        # 从 symbol_refs 列表中提取符号引用
        for symbol_ref in behavior_node.symbol_refs:
            if symbol_ref:
                self.behavior_refs.append(symbol_ref)



    def resolve_module_ref(self, module_ref: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        解析module引用，在可见符号树中查找对应的模块/文件
        
        Args:
            module_ref: module引用字符串，如 "src.ball.ball_entity"
            
        Returns:
            Tuple[bool, Optional[Dict], str]: 
                - 是否找到
                - 找到的符号节点（如果找到）
                - 描述信息
        """
        if not module_ref:
            return False, None, "module引用为空"
        
        # 解析路径
        path_parts = self.parse_ref_path(module_ref)
        if not path_parts:
            return False, None, f"module引用解析失败: {module_ref}"
        
        # 在可见符号树中逐级查找
        current_node = self.visible_symbol_tree
        for part in path_parts:
            if isinstance(current_node, dict) and part in current_node:
                current_node = current_node[part]
            else:
                return False, None, f"找不到路径: {module_ref} (在 {part} 处断开)"
        
        return True, current_node, f"成功找到: {module_ref}"
    
    def parse_ref_path(self, symbol_ref: str) -> List[str]:
        """
        解析符号引用路径，将其按 . 分割成路径组件列表
        
        Args:
            symbol_ref: 符号引用字符串，如 "module.submodule.Class.method"
            
        Returns:
            路径组件列表，如 ["module", "submodule", "Class", "method"]
        """
        if not symbol_ref:
            return []
        
        # 按 . 分割
        parts = symbol_ref.split('.')
        
        # 过滤空字符串
        return [part.strip() for part in parts if part.strip()]
    
    def resolve_symbol_in_visible_tree(self, symbol_ref: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        在可见符号树中检索符号引用
        
        基于 . 符号分割的路径，在可见符号树中进行逐级索引
        
        Args:
            symbol_ref: 符号引用字符串，如 "ball_entity.BallEntity.get_position"
            
        Returns:
            Tuple[bool, Optional[Dict], str]:
                - 是否找到
                - 找到的符号节点（如果找到）
                - 描述信息
        """
        if not symbol_ref:
            return False, None, "符号引用为空"
        
        # 解析路径
        path_parts = self.parse_ref_path(symbol_ref)
        
        if not path_parts:
            return False, None, f"符号引用解析失败: {symbol_ref}"
        
        # 在可见符号树中逐级查找
        current_node = self.visible_symbol_tree
        path_traveled = []
        
        for part in path_parts:
            path_traveled.append(part)
            
            if isinstance(current_node, dict) and part in current_node:
                current_node = current_node[part]
            else:
                # 尝试模糊匹配
                if isinstance(current_node, dict):
                    # 查找相似的键
                    available_keys = [k for k in current_node.keys() if not k.startswith('_')]
                    if available_keys:
                        matches = difflib.get_close_matches(part, available_keys, n=3, cutoff=0.6)
                        if matches:
                            suggestion = f"找不到 '{part}'，可能是: {', '.join(matches)}"
                        else:
                            suggestion = f"找不到 '{part}'，可用选项: {', '.join(available_keys[:5])}"
                    else:
                        suggestion = f"找不到 '{part}'，该节点下无可用符号"
                else:
                    suggestion = f"'{'.'.join(path_traveled[:-1])}' 不是容器节点"
                
                return False, None, f"符号 {symbol_ref} 查找失败: {suggestion}"
        
        # 检查最终节点是否是符号节点
        if isinstance(current_node, dict) and '_symbol_type' in current_node:
            symbol_type = current_node.get('_symbol_type', 'unknown')
            visibility = current_node.get('_visibility', 'unknown')
            description = current_node.get('_description', '')
            return True, current_node, f"找到符号: {symbol_ref} ({symbol_type}, {visibility}): {description}"
        elif isinstance(current_node, dict):
            # 找到的是容器节点（目录/文件）
            return True, current_node, f"找到容器节点: {symbol_ref}"
        else:
            return False, None, f"符号 {symbol_ref} 指向的不是有效节点"
    
    def validate_all_refs(self) -> Dict[str, List[Tuple]]:
        """
        验证所有提取的符号引用
        
        对所有类型的引用进行验证:
        - module 引用（验证module路径是否存在）
        - 函数参数类型引用
        - 变量类型引用
        - 类继承引用
        - 行为描述引用
        
        Returns:
            包含各类引用验证结果的字典
        """
        print(f"开始验证所有符号引用")
        
        validation_results = {
            "module_refs": [],
            "param_type_refs": [],
            "var_type_refs": [],
            "class_inherit_refs": [],
            "behavior_refs": []
        }
        
        # 验证module引用
        for module_ref in self.module_refs:
            found, node, msg = self.resolve_module_ref(module_ref)
            validation_results["module_refs"].append((module_ref, found, msg))
        
        # 验证函数参数类型引用
        for param_name, type_ref in self.param_type_refs:
            found, node, msg = self.resolve_symbol_in_visible_tree(type_ref)
            validation_results["param_type_refs"].append((param_name, type_ref, found, msg))
        
        # 验证变量类型引用
        for var_name, type_ref in self.var_type_refs:
            found, node, msg = self.resolve_symbol_in_visible_tree(type_ref)
            validation_results["var_type_refs"].append((var_name, type_ref, found, msg))
        
        # 验证类继承引用
        for inherit_ref in self.class_inherit_refs:
            found, node, msg = self.resolve_symbol_in_visible_tree(inherit_ref)
            validation_results["class_inherit_refs"].append((inherit_ref, found, msg))
        
        # 验证行为描述引用
        for behavior_ref in self.behavior_refs:
            found, node, msg = self.resolve_symbol_in_visible_tree(behavior_ref)
            validation_results["behavior_refs"].append((behavior_ref, found, msg))
        
        print(f"  符号引用验证完成")
        return validation_results
    
    def get_module_refs(self) -> List[str]:
        """获取所有 module 引用"""
        return self.module_refs.copy()
    
    def get_param_type_refs(self) -> List[Tuple[str, str]]:
        """获取所有函数参数类型引用"""
        return self.param_type_refs.copy()
    
    def get_var_type_refs(self) -> List[Tuple[str, str]]:
        """获取所有变量类型引用"""
        return self.var_type_refs.copy()
    
    def get_class_inherit_refs(self) -> List[str]:
        """获取所有类继承引用"""
        return self.class_inherit_refs.copy()
    
    def get_behavior_refs(self) -> List[str]:
        """获取所有行为描述引用"""
        return self.behavior_refs.copy()