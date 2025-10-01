import sys
from typing import List, Dict, Any, Optional
from utils.icb.lines_parser import LinesParser


class SymbolGenerator:
    @staticmethod
    def generate_symbol_table(ast_node_dict: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        生成符号表，包含最外层和 class 内部的 class/func/var，
        func 只记录 input/output 参数，不记录内部结构。
        """

        root_uid = -1
        result = SymbolGenerator._process_node(root_uid, ast_node_dict, parent_type='root')
        return result if result else []

    @staticmethod
    def _process_node(uid: int, ast_node_dict: Dict[int, Dict[str, Any]], parent_type: str) -> Optional[List[Dict[str, Any]]]:
        node = ast_node_dict.get(uid)
        if not node:
            return None

        current_type = node.get('type')

        # 当前节点是否为目标类型（class/func/var）
        is_target_type = current_type in ['class', 'func', 'var']

        # 是否允许处理子节点（只有 root/class/func 允许继续处理子节点）
        allow_children = current_type in ['root', 'class', 'func']

        collected = []
        children_data = []

        if allow_children:
            for child_uid in node.get('child_list', []):
                child_result = SymbolGenerator._process_node(child_uid, ast_node_dict, parent_type=current_type)
                if child_result:
                    children_data.extend(child_result)

        # 处理函数参数
        if current_type == 'func':
            input_params = []
            output_params = []

            for child in children_data:
                if child['type'] == 'input':
                    input_params = child['value']
                elif child['type'] == 'output':
                    output_params = child['value']

            func_node = {
                'type': 'func',
                'name': node.get('name'),
                'description': node.get('description'),
                'input': input_params,
                'output': output_params,
                'children': []
            }

            collected.append(func_node)

        # 处理类继承关键字
        elif current_type == 'class':
            inh_class = None
            var_func_nodes = []

            for child in children_data:
                if child['type'] == 'inh':
                    inh_class = child['value']
                elif child['type'] in ['class', 'func', 'var']:
                    var_func_nodes.append(child)

            class_node = {
                'type': 'class',
                'name': node.get('name'),
                'description': node.get('description'),
                'inh': inh_class,
                'children': var_func_nodes
            }

            collected.append(class_node)

        # 处理变量
        elif current_type == 'var':
            var_node = {
                'type': 'var',
                'name': node.get('name'),
                'description': node.get('description'),
                'value': node.get('value')
            }

            collected.append(var_node)

        # 如果当前节点不是目标类型，但允许处理子节点，则返回子节点结果
        elif not is_target_type and allow_children:
            collected = children_data

        return collected if collected else None
    