import sys
import os
import re

from typing import Dict, List, Tuple, Optional, Set, Any
from typedef.ibc_data_types import (
    IbcBaseAstNode, ModuleNode, FunctionNode, VariableNode, BehaviorStepNode, ClassNode,
    FileSymbolTable, SymbolNode, SymbolType
)
from libs.dir_json_funcs import DirJsonFuncs


class SymbolRefResolver:
    """
    符号引用解析器
    
    功能:
    1. 从 ast_dict 中提取所有符号引用
    2. 基于 module 引用构建可见符号表
    3. 在可见符号表中检索和验证符号引用
    """
    
    def __init__(self, proj_root_dict: Dict):
        """
        初始化符号引用解析器
        
        Args:
            proj_root_dict: 项目根目录字典，包含所有文件的结构信息
        """
        self.proj_root_dict = proj_root_dict
        
        # 获取所有有效的文件路径
        print(f"初始化符号引用解析器")
        self.valid_file_paths = set(DirJsonFuncs.get_all_file_paths(proj_root_dict))
        print(f"  有效文件路径数: {len(self.valid_file_paths)}")
        
        # 存储从 ast_dict 中提取的各类引用
        self.module_refs: List[str] = []  # module 引用列表
        self.param_type_refs: List[Tuple[str, str]] = []  # (参数名, 符号引用) 元组列表
        self.var_type_refs: List[Tuple[str, str]] = []  # (变量名, 符号引用) 元组列表
        self.behavior_refs: List[str] = []  # 行为描述中的符号引用列表
        self.class_inherit_refs: List[str] = []  # 类继承中的符号引用列表
        
        # 完整的可用符号表(基于 proj_root_dict 和所有已有的 ibc 文件构建)
        # TODO: 暂时未实现，用占位符表示
        self.full_symbol_table: Dict[str, Any] = {}
        
        # 当前文件的可见符号表(基于 module 引用从完整符号表中提取)
        self.visible_symbol_table: Dict[str, Any] = {}


    def build_full_symbol_table(self) -> Dict[str, Any]:
        """
        构建完整的可用符号表
        
        基于 proj_root_dict 以及所有已有的 ibc 文件进行构建。
        具体逻辑:
        1. 在完整 proj_root_dict 的基础上，删除各个文件自己的内容描述
        2. 在各个文件下再增加树状的，类似于 proj_root_dict 文件结构一样的符号树
        3. 符号树类似于 class -> func 这种构成，结构完全近似于 proj_root_dict
        
        Returns:
            完整的符号表字典
            
        注意: 此方法暂时未实现，只做占位和接口定义
        """
        print(f"开始构建完整可用符号表")
        
        # TODO: 实际实现逻辑
        # 1. 遍历 proj_root_dict 获取所有文件路径
        # 2. 对每个文件，读取对应的 .ibc 文件和符号表文件
        # 3. 将符号表信息组织成树状结构，挂载到文件路径下
        # 4. 删除文件的内容描述字段
        
        # 临时返回空字典
        full_symbol_table = {}
        
        print(f"  完整符号表构建完成(暂未实现)")
        return full_symbol_table

    
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



    def build_visible_symbol_table(self) -> None:
        """
        基于 module 引用构建当前文件的可见符号表
        
        处理流程:
        1. proj_root 本身必然可见，proj_root 下的所有 key(文件/文件夹)都可见
        2. 对每个 module 引用，通过 . 符号分割，从 proj_root 开始逐步索引
        3. 将索引到的所有符号及其子节点加入可见表
        4. 最终可见表只保留被 module 抽取出的部分，proj_root 下的直接子节点不再保留
        
        注意: 此方法依赖于 build_full_symbol_table 的实现
        """
        print(f"开始构建可见符号表")
        
        # TODO: 实际实现逻辑
        # 1. 从 full_symbol_table 中提取 proj_root 节点
        # 2. 遍历所有 module_refs
        # 3. 对每个 module_ref，解析路径并从 full_symbol_table 中提取对应的符号树
        # 4. 将提取的符号树合并到 visible_symbol_table 中
        
        # 临时实现：暂时设置为空
        self.visible_symbol_table = {}
        
        print(f"  可见符号表构建完成(暂未实现)")
    
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
    
    def resolve_symbol_in_visible_table(self, symbol_ref: str) -> Tuple[bool, str]:
        """
        在可见符号表中检索符号引用
        
        基于 . 符号分割的路径，在可见符号表中进行逐级索引
        
        Args:
            symbol_ref: 符号引用字符串
            
        Returns:
            (是否找到, 描述信息) 元组
        """
        if not symbol_ref:
            return False, "符号引用为空"
        
        # 解析路径
        path_parts = self.parse_ref_path(symbol_ref)
        
        if not path_parts:
            return False, f"符号引用解析失败: {symbol_ref}"
        
        # TODO: 实际实现逻辑
        # 1. 从 visible_symbol_table 开始
        # 2. 逐级索引 path_parts
        # 3. 如果某一级不存在，返回 False
        # 4. 如果全部索引成功，返回 True
        
        # 临时实现：总是返回未找到
        return False, f"符号引用检索未实现: {symbol_ref}"
    
    def validate_all_refs(self) -> Dict[str, List[Tuple[bool, str]]]:
        """
        验证所有提取的符号引用
        
        对所有类型的引用进行验证:
        - module 引用(特殊处理，用于构建可见表)
        - 函数参数类型引用
        - 变量类型引用
        - 类继承引用
        - 行为描述引用
        
        Returns:
            包含各类引用验证结果的字典
        """
        print(f"开始验证所有符号引用")
        
        validation_results = {
            "param_type_refs": [],
            "var_type_refs": [],
            "class_inherit_refs": [],
            "behavior_refs": []
        }
        
        # 验证函数参数类型引用
        for param_name, type_ref in self.param_type_refs:
            result = self.resolve_symbol_in_visible_table(type_ref)
            validation_results["param_type_refs"].append((param_name, type_ref, result[0], result[1]))
        
        # 验证变量类型引用
        for var_name, type_ref in self.var_type_refs:
            result = self.resolve_symbol_in_visible_table(type_ref)
            validation_results["var_type_refs"].append((var_name, type_ref, result[0], result[1]))
        
        # 验证类继承引用
        for inherit_ref in self.class_inherit_refs:
            result = self.resolve_symbol_in_visible_table(inherit_ref)
            validation_results["class_inherit_refs"].append((inherit_ref, result[0], result[1]))
        
        # 验证行为描述引用
        for behavior_ref in self.behavior_refs:
            result = self.resolve_symbol_in_visible_table(behavior_ref)
            validation_results["behavior_refs"].append((behavior_ref, result[0], result[1]))
        
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