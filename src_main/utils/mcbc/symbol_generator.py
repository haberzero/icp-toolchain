# file: symbol_generator.py

import sys
from typing import List, Dict, Any, Optional
from lines_parser import LinesParser


class symbolGenerator:
    @staticmethod
    def generate_symbol_table(ast_node_dict: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        生成符号表，包含所有class、func、var节点，构成树状结构。

        参数:
            ast_node_dict (Dict[int, Dict[str, Any]]): AST节点字典，键为node_uid。

        返回:
            List[Dict[str, Any]]: 符号表的根节点列表（通常是单个根节点的子节点）。
        """
        root_uid = -1  # 根节点的node_uid固定为-1
        result = symbolGenerator._process_node(root_uid, ast_node_dict)
        return result if result is not None else []

    @staticmethod
    def _process_node(uid: int, ast_node_dict: Dict[int, Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """
        递归处理指定UID的节点，收集目标类型的子节点。

        参数:
            uid (int): 当前处理的节点UID。
            ast_node_dict (Dict[int, Dict[str, Any]]): AST节点字典。

        返回:
            Optional[List[Dict[str, Any]]]: 处理后的目标类型节点列表。
        """
        node = ast_node_dict.get(uid)
        if not node:
            return None

        current_type = node.get('type')

        # 如果当前节点是目标类型，构建该节点及其children
        if current_type in ['class', 'func', 'var']:
            children = []
            for child_uid in node.get('child_list', []):
                result = symbolGenerator._process_node(child_uid, ast_node_dict)
                if result:
                    children.extend(result)

            symbol_node = {
                'type': current_type,
                'name': node.get('name'),
                'value': node.get('value'),
                'description': node.get('description'),
                'children': children
            }

            return [symbol_node]

        else:
            # 非目标类型节点，处理其子节点，并合并结果
            collected = []
            for child_uid in node.get('child_list', []):
                result = symbolGenerator._process_node(child_uid, ast_node_dict)
                if result:
                    collected.extend(result)
            return collected if collected else None