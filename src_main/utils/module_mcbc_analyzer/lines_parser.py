import sys
from typing import Dict, Any, List, Optional

class LinesParser:
    def __init__(self):
        self.expected_next_types: List[str] = []
    
    def parse_line(self, line_content: str, line_num: int) -> Optional[Dict[str, Any]]:
        # 使用行类型分类器确定行类型
        line_type = self._classify_line(line_content)
        
        # 根据分类结果调用对应的解析方法
        if line_type == "intent_comment":
            return self._parse_intent_comment(line_content, line_num)
        elif line_type == "class_declaration":
            return self._parse_class_declaration(line_content, line_num)
        elif line_type == "function_declaration":
            return self._parse_function_declaration(line_content, line_num)
        elif line_type == "variable_declaration":
            return self._parse_variable_declaration(line_content, line_num)
        elif line_type == "behavior_declaration":
            return self._parse_behavior_declaration(line_content, line_num)
        elif line_type == "attribute":
            return self._parse_attribute(line_content, line_num)
        elif line_type == "behavior_step_with_children":
            return self._parse_behavior_step_with_children(line_content, line_num)
        elif line_type == "behavior_step":
            return self._parse_behavior_step(line_content, line_num)
        else:
            print(f"Syntax Error on line {line_num}: Unknown line type. Line content: '{line_content}'", 
                file=sys.stderr)
            return None

    def _classify_line(self, line_content: str) -> str:
        """分类器：根据行内容判断行类型"""
        # 首先检查意图注释
        if line_content.startswith("@"):
            return "intent_comment"
        
        # 检查是否有冒号分隔符
        if ':' in line_content:
            # 提取冒号前的第一个字符串
            first_part = line_content.split(':', 1)[0].strip()
            if not first_part:
                return "behavior_step_with_children"
            
            # 检查第一个字符串是否是关键词
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

    def _create_base_node(self, node_type: str, line_num: int) -> Dict[str, Any]:
        """创建基础节点结构，确保所有键都存在"""
        return {
            'type': node_type,
            'value': None,
            'line_num': line_num,
            'name': None,
            'description': None,
            'intent': None,
            'is_block_start': False,
            'children': [],
            'attributes': None,
            'parent': None,
            'expected_next_types': [],
            'is_ast_node': True  # 默认为AST节点，特殊类型会覆盖
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
    
    def _parse_intent_comment(self, line_content: str, line_num: int) -> Dict[str, Any]:
        """解析意图注释（@开头的行）"""
        node = self._create_base_node('intent_comment', line_num)
        node.update({
            'value': line_content.lstrip('@').strip(),
            'is_ast_node': False,
            'expected_next_types': ['class', 'func', 'var', 'behavior']
        })
        return node
    
    def _parse_class_declaration(self, line_content: str, line_num: int) -> Optional[Dict[str, Any]]:
        """解析类声明"""
        # 提取冒号前的部分
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
    
    def _parse_function_declaration(self, line_content: str, line_num: int) -> Optional[Dict[str, Any]]:
        """解析函数声明"""
        # 提取冒号前的部分
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
    
    def _parse_variable_declaration(self, line_content: str, line_num: int) -> Optional[Dict[str, Any]]:
        """解析变量声明"""
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
    
    def _parse_behavior_declaration(self, line_content: str, line_num: int) -> Dict[str, Any]:
        """解析行为声明"""
        node = self._create_base_node('behavior', line_num)
        node.update({
            'is_block_start': True,
            'expected_next_types': ['behavior_step']
        })
        return node
    
    def _parse_attribute(self, line_content: str, line_num: int) -> Optional[Dict[str, Any]]:
        """解析属性行（input/output/description/inh）"""
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
    
    def _parse_behavior_step(self, line_content: str, line_num: int) -> Dict[str, Any]:
        """解析普通行为步骤"""
        node = self._create_base_node('behavior_step', line_num)
        node.update({
            'value': line_content.strip(),
            'expected_next_types': ['behavior_step']
        })
        return node
    
    def _parse_behavior_step_with_children(self, line_content: str, line_num: int) -> Dict[str, Any]:
        """解析带有子节点的行为步骤"""
        parts = line_content.split(':', 1)
        behavior_desc = parts[0].strip()
        child_content = parts[1].strip() if len(parts) > 1 else ""

        node = self._create_base_node('behavior_step', line_num)
        node.update({
            'value': behavior_desc,
            'is_block_start': True,
            'expected_next_types': ['behavior_step']
        })

        if child_content:
            child_node = self._create_base_node('behavior_step', line_num)
            child_node.update({
                'value': child_content,
                'parent': node
            })
            node['children'].append(child_node)

        return node