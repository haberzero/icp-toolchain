import sys
from typing import Dict, Any, List, Optional

from src_main.cfg.mccp_config_manager import g_mccp_config_manager
from src_main.lib.diag_handler import DiagHandler, EType, WType


class LinesParser:
    def __init__(self):
        pass
    
    def parse_line(self, line_content: str, line_num: int) -> Optional[Dict[str, Any]]:
        line_classify_result, error_table = self._classify_line(line_content)
        
        if line_classify_result == "intent_comment":
            return self._parse_intent_comment(line_content, line_num)
        elif line_classify_result == "class_declaration":
            return self._parse_class_declaration(line_content, line_num)
        elif line_classify_result == "function_declaration":
            return self._parse_function_declaration(line_content, line_num)
        elif line_classify_result == "variable_declaration":
            return self._parse_variable_declaration(line_content, line_num)
        elif line_classify_result == "behavior_declaration":
            return self._parse_behavior_declaration(line_content, line_num)
        elif line_classify_result == "attribute":
            return self._parse_attribute(line_content, line_num)
        elif line_classify_result == "behavior_step_with_children":
            return self._parse_behavior_step_with_children(line_content, line_num)
        elif line_classify_result == "behavior_step":
            return self._parse_behavior_step(line_content, line_num)
        
        # 错误处理，LinesParser 只负责处理单独一行内的错误，其它错误由AstBuilder处理
        elif line_classify_result == "line_error_unexpected_colon":
            print(f"Syntax Error on line {line_num}: Unexpected colon at the beginning of the line. Line content: '{line_content}'", 
                file=sys.stderr)
            return None

        else:
            # 其实根据设想，准确来讲这个地方不应该直接抛出错误，而是记录当前行数然后丢给建议器去维修的
            print(f"Syntax Error on line {line_num}: Unknown line type. Line content: '{line_content}'", 
                file=sys.stderr)
            return None

    def _classify_line(self, line_content: str) -> str:
        # 首先处理意图注释，意图注释后的空行检查暂时不做，必要性不高。或者后面修错误处理的时候一并修了
        if line_content.startswith("@"):
            return "intent_comment"
        
        # 一行里面有多个冒号的情况可能也得单独考虑，现在来看大概率会出现在行为描述中，应该由建议器处理把后一个冒号删掉或者变成合理的块代码
        # 检查是否有冒号符号，然后判断对应行类型。没有冒号的行统一直接判断成行为描述行
        if ':' in line_content:
            # 提取冒号前的第一个字符串
            first_part = line_content.split(':', 1)[0].strip()

            if first_part == "":
                print()
                return "line_error_unexpected_colon"
            
            # 检查第一个字符串是否是关键词
            # 这里还差一些语法检查，比如说class或者func之后的冒号后面不应该再有任何内容。晚上回去修
            first_word = first_part.split()[0]
            if first_word == "class":
                return "class_declaration"
            elif first_word == "func":
                return "function_declaration"
            elif first_word == "var":
                return "variable_declaration"
            elif first_word == "behavior":
                return "behavior_declaration"
            elif first_word in ["input", "output", "description", "inh"]:
                return "attribute"
            else:
                return "behavior_step_with_children"
        else:
            return "behavior_step"

    # 创建基础节点结构，确保所有键都存在。具体各个key的功能说明可查阅helper.py（后续会放进去，现在还没有）
    def _create_base_node(self, node_type: str, line_num: int) -> Dict[str, Any]:
        return {
            'type': node_type,
            'line_num': line_num,
            'name': None,
            'value': None,
            'description': None,
            'intent_comment': None,
            'is_block_start': False,
            'parent': None,
            'children': [],
            'attributes': None,
            'one_line_child_content': None,
            'expected_next_types': [],
            'is_ast_node': False
        }

    def gen_root_ast_node(self) -> Dict[str, Any]:
        """生成根AST节点"""
        root = self._create_base_node('root', 0)
        root.update({
            'name': 'root',
            'description': 'root',
            'expected_next_types': ['class', 'func', 'var'],
            'is_ast_node': True
        })
        return root
    
    # 意图注释
    def _parse_intent_comment(self, line_content: str, line_num: int) -> Dict[str, Any]:
        node = self._create_base_node('intent_comment', line_num)
        node.update({
            'value': line_content.lstrip('@').strip(),
            'is_ast_node': False,
            'expected_next_types': ['class', 'func', 'var', 'behavior']
        })
        return node
    
    # 类声明
    def _parse_class_declaration(self, line_content: str, line_num: int) -> Optional[Dict[str, Any]]:
        class_part = line_content.split(':', 1)[0].strip()
        parts = class_part.split()
        
        if len(parts) < 2:
            print(f"Syntax Error on line {line_num}: Expected class name. Line content: '{line_content}'", 
                file=sys.stderr)
            return None
        
        node = self._create_base_node('class', line_num)
        node.update({
            'name': parts[1],
            'is_block_start': True,
            'expected_next_types': ['inh', 'var', 'func', 'description']
        })
        return node
    
    # 函数声明
    def _parse_function_declaration(self, line_content: str, line_num: int) -> Optional[Dict[str, Any]]:
        func_part = line_content.split(':', 1)[0].strip()
        parts = func_part.split()
        
        if len(parts) < 2:
            print(f"Syntax Error on line {line_num}: Expected function name. Line content: '{line_content}'", 
                file=sys.stderr)
            return None
        
        node = self._create_base_node('func', line_num)
        node.update({
            'name': parts[1],
            'is_block_start': True,
            'expected_next_types': ['input', 'output', 'description', 'behavior']
        })
        return node
    
    # 变量声明
    def _parse_variable_declaration(self, line_content: str, line_num: int) -> Optional[Dict[str, Any]]:
        parts = line_content.split(':', 1)
        if len(parts) < 2:
            print(f"Syntax Error on line {line_num}: Expected ':' in variable declaration. Line content: '{line_content}'", 
                file=sys.stderr)
            return None
        
        var_part = parts[0].strip()
        var_parts = var_part.split()
        if len(var_parts) < 2:
            print(f"Syntax Error on line {line_num}: Expected variable name. Line content: '{line_content}'", 
                file=sys.stderr)
            return None
        
        node = self._create_base_node('var', line_num)
        node.update({
            'name': var_parts[1],
            'description': parts[1].strip(),
            'expected_next_types': ['behavior_step', 'var', 'func']
        })
        return node
    
    # 行为块起始关键字
    def _parse_behavior_declaration(self, line_content: str, line_num: int) -> Dict[str, Any]:
        node = self._create_base_node('behavior', line_num)
        node.update({
            'is_block_start': True,
            'expected_next_types': ['behavior_step']
        })
        return node
    
    # 解析属性行 (input/output/description/inh)
    def _parse_attribute(self, line_content: str, line_num: int) -> Optional[Dict[str, Any]]:
        parts = line_content.split(':', 1)
        if len(parts) < 2:
            print(f"Syntax Error on line {line_num}: Expected ':' in attribute. Line content: '{line_content}'", 
                file=sys.stderr)
            return None
        
        keyword = parts[0].strip()
        node = self._create_base_node(keyword, line_num)
        node.update({
            'value': parts[1].strip(),
            'is_ast_node': False,
            'expected_next_types': (
                ['input', 'output', 'description', 'behavior'] 
                if keyword in ['input', 'output'] 
                else ['var', 'func']
            )
        })
        return node
    
    # 带有子代码块的行为步骤行，子代码块可能在同一行且只有一行，体现为len(parts) > 1
    def _parse_behavior_step_with_children(self, line_content: str, line_num: int) -> Dict[str, Any]:
        parts = line_content.split(':', 1)
        behavior_desc = parts[0].strip()

        node = self._create_base_node('behavior_step', line_num)
        node.update({
            'value': behavior_desc,
            'is_block_start': True,
            'expected_next_types': ['behavior_step']
        })

        if len(parts) > 1:
            child_content = parts[1].strip()
            node.update({
                'is_block_start': False,
                'one_line_child_content': child_content
            })

        return node
    
    # 常规行为步骤行
    def _parse_behavior_step(self, line_content: str, line_num: int) -> Dict[str, Any]:
        node = self._create_base_node('behavior_step', line_num)
        node.update({
            'value': line_content.strip(),
            'expected_next_types': ['behavior_step']
        })
        return node