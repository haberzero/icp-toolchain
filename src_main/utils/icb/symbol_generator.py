import sys
from typing import Dict, Any, List, Optional

class SymbolGenerator:
    @staticmethod
    def generate_symbol_table(ast_node_dict: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        生成符号表，包含最外层和 class 内部的 class/func/var，
        func 只记录 input/output 参数，不记录内部结构。
        """

        root_uid = -1
        # 收集所有目标符号
        symbols = SymbolGenerator._collect_symbols(root_uid, ast_node_dict)
        return symbols

    @staticmethod
    def _collect_symbols(uid: int, ast_node_dict: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        遍历AST并收集所有目标符号（class/func/var/module）
        """
        node = ast_node_dict.get(uid)
        if not node:
            return []

        collected_symbols = []
        
        # 如果当前节点是目标类型，则处理它
        if node.get('type') in ['class', 'func', 'var', 'module']:
            processed_node = SymbolGenerator._process_node(node, ast_node_dict)
            if processed_node:
                collected_symbols.append(processed_node)

        # 遍历所有子节点
        for child_uid in node.get('child_list', []):
            child_symbols = SymbolGenerator._collect_symbols(child_uid, ast_node_dict)
            collected_symbols.extend(child_symbols)

        return collected_symbols

    @staticmethod
    def _process_node(node: Dict[str, Any], ast_node_dict: Dict[int, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        根据节点类型处理单个节点
        """
        node_type = node.get('type')
        
        if node_type == 'func':
            return SymbolGenerator._process_function(node, ast_node_dict)
        elif node_type == 'class':
            return SymbolGenerator._process_class(node, ast_node_dict)
        elif node_type == 'var':
            return SymbolGenerator._process_var(node)
        elif node_type == 'module':
            return SymbolGenerator._process_module(node)
        
        return None

    @staticmethod
    def _process_function(node: Dict[str, Any], ast_node_dict: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
        """处理函数节点，提取input/output参数"""
        input_params = []
        output_params = []

        # 查找函数的子节点中的input和output
        for child_uid in node.get('child_list', []):
            child_node = ast_node_dict.get(child_uid)
            if not child_node:
                continue
                
            if child_node.get('type') == 'input':
                input_params = child_node.get('value', [])
            elif child_node.get('type') == 'output':
                output_params = child_node.get('value', [])

        return {
            'type': 'func',
            'name': node.get('name'),
            'description': node.get('description'),
            'input': input_params,
            'output': output_params,
            'children': []
        }

    @staticmethod
    def _process_class(node: Dict[str, Any], ast_node_dict: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
        """处理类节点，提取inh和内部的var/func"""
        inh_class = None
        var_func_nodes = []

        # 查找类的子节点中的inh和var/func
        for child_uid in node.get('child_list', []):
            child_node = ast_node_dict.get(child_uid)
            if not child_node:
                continue
                
            if child_node.get('type') == 'inh':
                inh_class = child_node.get('value')
            elif child_node.get('type') in ['class', 'func', 'var']:
                # 对于类内部的var/func，我们只需要基本信息
                processed_child = SymbolGenerator._process_node(child_node, ast_node_dict)
                if processed_child:
                    var_func_nodes.append(processed_child)

        return {
            'type': 'class',
            'name': node.get('name'),
            'description': node.get('description'),
            'inh': inh_class,
            'children': var_func_nodes
        }

    @staticmethod
    def _process_var(node: Dict[str, Any]) -> Dict[str, Any]:
        """处理变量节点"""
        return {
            'type': 'var',
            'name': node.get('name'),
            'description': node.get('description'),
            'value': node.get('value')
        }

    @staticmethod
    def _process_module(node: Dict[str, Any]) -> Dict[str, Any]:
        """处理模块节点"""
        return {
            'type': 'module',
            'name': node.get('name'),
            'description': node.get('description'),
            'value': node.get('value')
        }