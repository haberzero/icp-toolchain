"""
IBC代码重建模块

负责从AST重建IBC代码字符串
"""
from typing import Dict, List
from typedef.ibc_data_types import (
    IbcBaseAstNode, AstNodeType, ModuleNode, ClassNode, 
    FunctionNode, VariableNode, BehaviorStepNode
)


class IbcCodeReconstructor:
    """IBC代码重建器，从AST重建IBC代码字符串"""
    
    def __init__(self, ast_dict: Dict[int, IbcBaseAstNode]):
        """
        初始化IBC代码重建器
        
        Args:
            ast_dict: AST节点字典
        """
        self.ast_dict = ast_dict
        self.indent_level = 0
        self.lines: List[str] = []
    
    def reconstruct(self) -> str:
        """
        从AST重建IBC代码
        
        Returns:
            str: 重建的IBC代码字符串
        """
        self.lines = []
        self.indent_level = 0
        
        # 从根节点开始遍历
        root_node = self.ast_dict.get(0)
        if not root_node:
            return ""
        
        # 处理根节点的所有子节点
        for child_uid in root_node.children_uids:
            self._reconstruct_node(child_uid)
        
        return '\n'.join(self.lines)
    
    def _reconstruct_node(self, uid: int) -> None:
        """
        递归重建单个节点
        
        Args:
            uid: 节点UID
        """
        node = self.ast_dict.get(uid)
        if not node:
            return
        
        if isinstance(node, ModuleNode):
            self._reconstruct_module(node)
        elif isinstance(node, ClassNode):
            self._reconstruct_class(node)
        elif isinstance(node, FunctionNode):
            self._reconstruct_function(node)
        elif isinstance(node, VariableNode):
            self._reconstruct_variable(node)
        elif isinstance(node, BehaviorStepNode):
            self._reconstruct_behavior_step(node)
    
    def _reconstruct_module(self, node: ModuleNode) -> None:
        """重建module声明"""
        if node.content:
            self.lines.append(f"module {node.identifier}: {node.content}")
        else:
            self.lines.append(f"module {node.identifier}")
    
    def _reconstruct_class(self, node: ClassNode) -> None:
        """重建class定义"""
        # 添加description（如果存在）
        if node.external_desc:
            self._add_description(node.external_desc)
        
        # 添加意图注释（如果存在）
        if node.intent_comment:
            self._add_intent_comment(node.intent_comment)
        
        # 构建class声明
        indent = self._get_indent()
        if node.inh_params:
            # 有继承参数
            inh_str = ", ".join([f"{k}: {v}" if v else k for k, v in node.inh_params.items()])
            self.lines.append(f"{indent}class {node.identifier}({inh_str}):")
        else:
            self.lines.append(f"{indent}class {node.identifier}():")
        
        # 处理子节点
        self.indent_level += 1
        for child_uid in node.children_uids:
            self._reconstruct_node(child_uid)
        self.indent_level -= 1
        
        # 类定义后添加空行
        self.lines.append("")
    
    def _reconstruct_function(self, node: FunctionNode) -> None:
        """重建function定义"""
        # 添加description（如果存在）
        if node.external_desc:
            self._add_description(node.external_desc)
        
        # 添加意图注释（如果存在）
        if node.intent_comment:
            self._add_intent_comment(node.intent_comment)
        
        # 构建func声明
        indent = self._get_indent()
        if node.params:
            # 有参数描述，需要多行格式
            params_list = []
            for param_name, param_desc in node.params.items():
                if param_desc:
                    params_list.append(f"{param_name}: {param_desc}")
                else:
                    params_list.append(param_name)
            
            # 检查是否需要换行
            if any(node.params.values()):
                # 有描述，使用多行格式
                self.lines.append(f"{indent}func {node.identifier}(")
                for i, param_str in enumerate(params_list):
                    if i < len(params_list) - 1:
                        self.lines.append(f"{indent}    {param_str},")
                    else:
                        self.lines.append(f"{indent}    {param_str}")
                self.lines.append(f"{indent}):")
            else:
                # 无描述，单行格式
                params_str = ", ".join(params_list)
                self.lines.append(f"{indent}func {node.identifier}({params_str}):")
        else:
            self.lines.append(f"{indent}func {node.identifier}():")
        
        # 处理子节点
        self.indent_level += 1
        for child_uid in node.children_uids:
            self._reconstruct_node(child_uid)
        self.indent_level -= 1
        
        # 函数定义后添加空行（仅在顶层时）
        if self.indent_level == 0:
            self.lines.append("")
    
    def _reconstruct_variable(self, node: VariableNode) -> None:
        """重建variable声明"""
        indent = self._get_indent()
        if node.content:
            self.lines.append(f"{indent}var {node.identifier}: {node.content}")
        else:
            self.lines.append(f"{indent}var {node.identifier}")
    
    def _reconstruct_behavior_step(self, node: BehaviorStepNode) -> None:
        """重建behavior step"""
        indent = self._get_indent()
        
        # 处理new_block_flag
        if node.new_block_flag:
            # 这是一个新代码块的开始，增加缩进
            content_lines = node.content.split('\n')
            for line in content_lines:
                if line.strip():
                    self.lines.append(f"{indent}{line}")
            
            # 处理子节点
            self.indent_level += 1
            for child_uid in node.children_uids:
                self._reconstruct_node(child_uid)
            self.indent_level -= 1
        else:
            # 普通行为描述行
            content_lines = node.content.split('\n')
            for line in content_lines:
                if line.strip():
                    self.lines.append(f"{indent}{line}")
            
            # 处理子节点（不增加缩进）
            for child_uid in node.children_uids:
                self._reconstruct_node(child_uid)
    
    def _add_description(self, desc: str) -> None:
        """添加description"""
        indent = self._get_indent()
        desc_lines = desc.strip().split('\n')
        if len(desc_lines) == 1:
            # 单行描述
            self.lines.append(f"{indent}description: {desc_lines[0]}")
        else:
            # 多行描述
            self.lines.append(f"{indent}description:")
            for line in desc_lines:
                self.lines.append(f"{indent}    {line}")
    
    def _add_intent_comment(self, comment: str) -> None:
        """添加意图注释"""
        indent = self._get_indent()
        self.lines.append(f"{indent}@ {comment}")
    
    def _get_indent(self) -> str:
        """获取当前缩进字符串"""
        return "    " * self.indent_level
