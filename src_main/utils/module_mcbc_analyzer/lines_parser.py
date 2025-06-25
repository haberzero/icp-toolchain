import sys
from typing import Dict, Any, List, Optional

class LinesParser:
    def __init__(self):
        self.expected_next_types: List[str] = []
    
    def parse_line(self, line_content: str, line_num: int) -> Optional[Dict[str, Any]]:
        # 首先检查处理意图注释，意图注释必须单独一行放置否则不会起效
        if line_content.startswith("@"):
            return self._parse_intent_comment(line_content, line_num)
        
        # 如果行中出现了':'则会被split，需要进一步区分
        parts = line_content.split(':')
        if len(parts) > 1:
            # 例: "func myFunc:", parts[0] == "func myFunc", parts[0].split()[0] == "func"
            keyword = parts[0].split()[0]
            if keyword in ["class", "func", "var", "behavior"]:
                # 这里最好不要这样子，我后续应该统一这几个_parse函数的接口形式，统一使用line_content
                # 另外，现在这几个函数不整齐，明天换一个形式。用一个分类函数返回分类结果，此处的函数仅作switch处理调用明确的_parse函数
                return self._parse_keyword_with_colon(keyword, parts, line_num)
            elif keyword in ["input", "output", "description", "inh"]:
                parsed_attribute = self._parse_attribute(parts, line_num, keyword)
                if parsed_attribute:
                    parsed_attribute['is_ast_node'] = False
                return parsed_attribute
            else:
                # 分支语句，循环语句，都是不具备关键词但是具有':'符号的，含有子代码块的行为语句
                parsed_behavior = self._parse_behavior_code_with_children(line_content, line_num)
                if parsed_behavior:
                    parsed_behavior['is_ast_node'] = True
                return parsed_behavior
        # 行内未出现':'直接被认为是行为语句，其它两种注释都已经被剔除
        else:
            parsed_behavior_code = self._parse_behavior_code(line_content, line_num)
            return parsed_behavior_code

    # ast_builder初始化时向其提供root_node
    def gen_root_ast_node(self) -> Dict[str, Any]:
        return {
            'type': 'root',
            'value': None,
            'line_num': 0,
            'name': 'root',
            'description': 'root',
            'intent': None,
            'is_block_start': False,
            'children': [],
            'attributes': None,
            'parent': None,
            'expected_next_types': ['class', 'func', 'var'],
            'is_ast_node': True
        }
    
    def _parse_intent_comment(self, line_content: str, line_num: int) -> Dict[str, Any]:
        comment_text = line_content.lstrip('@').strip()
        return {
            'type': 'intent_comment',
            'value': comment_text,
            'line_num': line_num,
            'name': None,
            'description': None,
            'intent': None,
            'is_block_start': False,
            'children': [],
            'attributes': None,
            'parent': None,
            # 这里还不太对，input那些 包括带有子代码块的行为描述行也需要
            'expected_next_types': ['class', 'func', 'var', 'behavior'],
            'is_ast_node': False
        }
    
    def _parse_keyword_with_colon(self, keyword: str, parts: List[str], line_num: int) -> Optional[Dict[str, Any]]:
        if keyword == "class":
            parsed_class = self._parse_class_declaration(parts, line_num)
            if parsed_class:
                parsed_class['is_ast_node'] = True
            return parsed_class
        elif keyword == "func":
            parsed_func = self._parse_function_declaration(parts, line_num)
            if parsed_func:
                parsed_func['is_ast_node'] = True
            return parsed_func
        elif keyword == "var":
            parsed_var = self._parse_variable_declaration(parts, line_num)
            if parsed_var:
                parsed_var['is_ast_node'] = True
            return parsed_var
        elif keyword == "behavior":
            parsed_behavior = self._parse_behavior_declaration(line_num)
            if parsed_behavior:
                parsed_behavior['is_ast_node'] = True
            return parsed_behavior
        
        else:
            print(f"Syntax Error on line {line_num}: Unknown keyword '{keyword}' with colon. Line content: '{parts[0]}'", file=sys.stderr)
            return None
    
    def _parse_class_declaration(self, parts: List[str], line_num: int) -> Optional[Dict[str, Any]]:
        class_parts = parts[0].split()
        if len(class_parts) < 2:
            print(f"Syntax Error on line {line_num}: Expected a class name after 'class'. Line content: '{parts[0]}'", file=sys.stderr)
            return None
        
        class_name = class_parts[1].strip()
        return {
            'type': 'class',
            'name': class_name,
            'line_num': line_num,
            'description': None,
            'intent': None,
            'is_block_start': True,
            'children': [],
            'attributes': None,
            'parent': None,
            'expected_next_types': ['inh', 'var', 'func', 'description']
        }
    
    def _parse_function_declaration(self, parts: List[str], line_num: int) -> Optional[Dict[str, Any]]:
        func_parts = parts[0].split()
        if len(func_parts) < 2:
            print(f"Syntax Error on line {line_num}: Expected a function name after 'func'. Line content: '{parts[0]}'", file=sys.stderr)
            return None
            
        func_name = func_parts[1].strip()
        return {
            'type': 'func',
            'name': func_name,
            'line_num': line_num,
            'description': None,
            'intent': None,
            'is_block_start': True,
            'children': [],
            'attributes': None,
            'parent': None,
            'expected_next_types': ['input', 'output', 'description', 'behavior']
        }
    
    def _parse_variable_declaration(self, parts: List[str], line_num: int) -> Optional[Dict[str, Any]]:
        var_parts = parts[0].split()
        if len(var_parts) < 2:
            print(f"Syntax Error on line {line_num}: Expected a variable name after 'var'. Line content: '{parts[0]}'", file=sys.stderr)
            return None
        
        var_name = var_parts[1].strip()
        description = parts[1].strip()
        return {
            'type': 'var',
            'name': var_name,
            'description': description,
            'line_num': line_num,
            'intent': None,
            'is_block_start': False,
            'children': [],
            'attributes': None,
            'parent': None,
            'expected_next_types': ['behavior_step', 'var', 'func']
        }
    
    def _parse_attribute(self, parts: List[str], line_num: int, keyword: str) -> Optional[Dict[str, Any]]:
        if len(parts) != 2:
            print(f"Syntax Error on line {line_num}: Expected exactly one ':' but found {len(parts) - 1} for attribute '{keyword}'. Line content: '{parts[0]}'", file=sys.stderr)
            return None

        value = parts[1].strip()
        return {
            # 这个地方最好一定程度明文处理
            'type': keyword,
            'value': value,
            'line_num': line_num,
            'name': None,
            'description': None,
            'intent': None,
            'is_block_start': False,
            'children': [],
            'attributes': None,
            'parent': None,
            'expected_next_types': ['input', 'output', 'description', 'behavior'] if keyword in ['input', 'output'] else ['var', 'func']
        }
    
    def _parse_behavior_declaration(self, line_num: int) -> Optional[Dict[str, Any]]:
        return {
            'type': 'behavior',
            'line_num': line_num,
            'name': None,
            'description': None,
            'intent': None,
            'is_block_start': True,
            'children': [],
            'attributes': None,
            'parent': None,
            'expected_next_types': ['behavior_step']
        }
    
    def _parse_behavior_code(self, line_content: str, line_num: int) -> Dict[str, Any]:
        return {
            'type': 'behavior_step',
            'value': line_content,
            'line_num': line_num,
            'name': None,
            'description': None,
            'intent': None,
            'is_block_start': False,
            'children': [],
            'attributes': None,
            'parent': None,
            'expected_next_types': ['behavior_step']
        }
    
    def _parse_behavior_code_with_children(self, line_content: str, line_num: int) -> Dict[str, Any]:
        parts = line_content.split(':', 1)
        behavior_description = parts[0].strip()
        child_content = parts[1].strip() if len(parts) > 1 else ""

        behavior_node = {
            'type': 'behavior_step',
            'value': behavior_description,
            'line_num': line_num,
            'name': None,
            'description': None,
            'intent': None,
            'is_block_start': True,
            'children': [],
            'attributes': None,
            'parent': None,
            'expected_next_types': ['behavior_step']
        }

        if child_content:
            child_node = {
                'type': 'behavior_step',
                'value': child_content,
                'line_num': line_num,
                'name': None,
                'description': None,
                'intent': None,
                'is_block_start': False,
                'children': [],
                'attributes': None,
                'parent': behavior_node,
                'expected_next_types': ['behavior_step']
            }
            behavior_node['children'].append(child_node)

        return behavior_node
