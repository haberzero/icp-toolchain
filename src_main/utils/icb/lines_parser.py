import sys
from typing import Dict, Any, List, Optional

from libs.diag_handler import DiagHandler, IcbEType, IcbWType


class LinesParser:
    def __init__(self, diag_handler: DiagHandler):
        self.diag_handler = diag_handler
    
    def parse_line(self, line_content: str, node_uid: int) -> Optional[Dict[str, Any]]:
        line_classify_result = self._classify_line(line_content)
        
        # _parse_line检测到语法错误后会返回None
        if line_classify_result == "intent_comment":
            return self._parse_intent_comment(line_content, node_uid)
        elif line_classify_result == "class_declaration":
            return self._parse_class_declaration(line_content, node_uid)
        elif line_classify_result == "function_declaration":
            return self._parse_function_declaration(line_content, node_uid)
        elif line_classify_result == "variable_declaration":
            return self._parse_variable_declaration(line_content, node_uid)
        elif line_classify_result == "behavior_declaration":
            return self._parse_begin_declaration(line_content, node_uid)
        elif line_classify_result == "input_attribute":
            return self._parse_input_attribute(line_content, node_uid)
        elif line_classify_result == "output_attribute":
            return self._parse_output_attribute(line_content, node_uid)
        elif line_classify_result == "description_attribute":
            return self._parse_description_attribute(line_content, node_uid)
        elif line_classify_result == "inh_attribute":
            return self._parse_inh_attribute(line_content, node_uid)
        elif line_classify_result == "behavior_step_with_child":
            return self._parse_behavior_step_with_child(line_content, node_uid)
        elif line_classify_result == "behavior_step":
            return self._parse_behavior_step(line_content, node_uid)
        elif line_classify_result == "pass":
            return self._parse_pass(line_content, node_uid)

        # 目前唯一一个来自line_classify的语法错误检查
        elif line_classify_result == "line_error_unexpected_colon":
            self.diag_handler.set_line_error(node_uid, IcbEType.UNEXPECTED_COLON)
            return None
        else:
            self.diag_handler.set_line_error(node_uid, IcbEType.UNKNOWN_LINE_TYPE)
            return None
    
    def _classify_line(self, line_content: str) -> str:
        # 行分类中不处理更多语法问题，语法问题放在具体的_parser函数中解决
        if line_content.startswith("@"):
            # 不对意图注释进行更多语法限制
            return "intent_comment"

        if ':' in line_content:
            # 提取冒号前的第一个字符串
            first_part = line_content.split(':', 1)[0].strip()

            if first_part == "":
                # 唯一一个由classify处理的语法错误
                return "line_error_unexpected_colon"
            
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
            elif first_word == "begin":
                return "begin_declaration"
            elif first_word == "input":
                return "input_attribute"
            elif first_word == "output":
                return "output_attribute"
            elif first_word == "description":
                return "description_attribute"
            elif first_word == "inh":
                return "inh_attribute"
            else:
                return "behavior_step_with_child"
        else:
            if line_content == "pass":
                return "pass"
            else:
                return "behavior_step"

    # 创建基础节点结构，确保所有键都存在。具体各个key的功能说明可查阅helper.py（后续会放进去，现在还没有）
    # 节点信息会在lines_parser和ast_builder中被进行一些不同处理
    def _create_base_node(self, node_type: str, node_uid: int) -> Dict[str, Any]:
        return {
            'type': node_type,
            'node_uid': node_uid,
            'name': None,
            'value': None,
            'description': None,
            'intent_comment': None,
            'is_block_start': False,
            'special_align': False,
            'parent': None,
            'child_list': [],
            'expected_next': [],
            'expected_child': [],
            'is_ast_node': True
        }

    def gen_root_ast_node(self) -> Dict[str, Any]:
        """生成根AST节点"""
        root = self._create_base_node('root', -1)   # root_node固定uid为-1
        root.update({
            'name': 'root',
            'is_block_start': True,
            'expected_child': ['class', 'func', 'var']
        })
        return root

    # 意图注释
    def _parse_intent_comment(self, line_content: str, node_uid: int) -> Dict[str, Any]:
        # 无格式要求，意图注释本质上是额外提示词
        # 'expected_next': ['NONE'] 意味着不覆盖上一个节点的expected_next。该节点不在expected_体系中处理
        # 不被认为是 attribute，不被认为是ast_node
        node = self._create_base_node('intent_comment', node_uid)
        node.update({
            'value': line_content.lstrip('@').strip(),
            'expected_next': ['NONE'],
            'is_ast_node': False
        })
        return node

    # description 属性解析
    def _parse_description_attribute(self, line_content: str, node_uid: int) -> Optional[Dict[str, Any]]:
        # 格式要求: 'description: 关键字的对外可见描述'
        # description 的内容会被附加在上一个同缩进的node上(但对于非对外关键字无意义)
        parts = line_content.split(':', 1)
        if len(parts) < 2:
            self.diag_handler.set_line_error(node_uid, IcbEType.MISSING_COLON)
            return None
        
        # 'expected_next': ['NONE'] 意味着不覆盖上一个节点的expected_next。该节点不在expected_体系中处理
        # 不被认为是 attribute，不被认为是ast_node
        node = self._create_base_node('description', node_uid)
        node.update({
            'value': parts[1].strip(),
            'expected_next': ['NONE'],
            'is_ast_node': False
        })
        return node
    
    # 类 class 声明
    def _parse_class_declaration(self, line_content: str, node_uid: int) -> Optional[Dict[str, Any]]:
        # 格式要求: 'class 类名:' (冒号后暂时不允许有其他内容)
        colon_split_strs = line_content.split(':', 1) # 只分割第一个冒号
        if len(colon_split_strs) < 2:
            self.diag_handler.set_line_error(node_uid, IcbEType.MISSING_COLON)
            return None
        
        # 检查冒号后是否有多余内容
        if colon_split_strs[1].strip() != "":
            self.diag_handler.set_line_error(node_uid, IcbEType.EXTRA_CONTENT_AFTER_COLON)
            return None
        
        class_components = colon_split_strs[0].strip().split()
        # 检查类名是否存在
        if len(class_components) < 2:
            self.diag_handler.set_line_error(node_uid, IcbEType.MISSING_CLASS_NAME)
            return None
        
        # 检查是否有多余空格及内容
        if len(class_components) > 2:
            self.diag_handler.set_line_error(node_uid, IcbEType.UNEXPECTED_SPACE)
            return None
        
        # 创建类节点
        node = self._create_base_node('class', node_uid)
        node.update({
            'name': class_components[1],
            'is_block_start': True,
            'expected_child': ['inh', 'begin'],
            'expected_next': ['class', 'func', 'var']
        })
        return node
    
    # 函数 func 声明
    def _parse_function_declaration(self, line_content: str, node_uid: int) -> Optional[Dict[str, Any]]:
        # 格式要求: 'func 函数名:' (冒号后暂时不允许有其他内容)
        colon_split_strs = line_content.split(':', 1) # 只分割第一个冒号
        if len(colon_split_strs) < 2:
            self.diag_handler.set_line_error(node_uid, IcbEType.MISSING_COLON)
            return None
        
        # 检查冒号后是否有多余内容
        if colon_split_strs[1].strip() != "":
            self.diag_handler.set_line_error(node_uid, IcbEType.EXTRA_CONTENT_AFTER_COLON)
            return None
        
        func_components = colon_split_strs[0].strip().split()
        # 检查函数名是否存在
        if len(func_components) < 2:
            self.diag_handler.set_line_error(node_uid, IcbEType.MISSING_FUNCTION_NAME)
            return None
        
        # 检查函数名后是否有多余内容
        if len(func_components) > 2:
            self.diag_handler.set_line_error(node_uid, IcbEType.UNEXPECTED_SPACE)
            return None
        
        # 创建函数节点
        node = self._create_base_node('func', node_uid)
        node.update({
            'name': func_components[1],
            'is_block_start': True,
            'expected_child': ['input', 'output', 'begin'],
            'expected_next': ['class', 'func', 'var']
        })
        return node
    
    # 变量 var 声明
    def _parse_variable_declaration(self, line_content: str, node_uid: int) -> Optional[Dict[str, Any]]:
        # 格式要求: 'var 变量名[: 可选的对变量的描述]' 
        parts = line_content.split(':', 1)
        if len(parts) < 2:
            description = None
        else:
            description = parts[1].strip()
        
        var_parts = parts[0].strip().split()
        # 检查变量名是否存在
        if len(var_parts) < 2:
            self.diag_handler.set_line_error(node_uid, IcbEType.MISSING_VAR_NAME)
            return None
        
        # 检查变量名后是否有多余内容
        if len(var_parts) > 2:
            self.diag_handler.set_line_error(node_uid, IcbEType.UNEXPECTED_SPACE)
            return None
        
        # 如果后续没有description声明进行覆盖的话, 默认以变量对自己的功能描述作为对外声明
        # 变量声明的expected_next标记为'NONE' 特殊处理，会使用上一个节点的expected_next
        node = self._create_base_node('var', node_uid)
        node.update({
            'name': var_parts[1],
            'value': description,
            'description': description,
            'expected_next': ['NONE']
        })
        return node
    
    # begin 块声明
    def _parse_begin_declaration(self, line_content: str, node_uid: int) -> Optional[Dict[str, Any]]:
        # 格式要求: 'begin:' (冒号后暂时不允许有其他内容)
        colon_split_strs = line_content.split(':', 1) # 只分割第一个冒号
        if len(colon_split_strs) < 2:
            self.diag_handler.set_line_error(node_uid, IcbEType.MISSING_COLON)
            return None
        
        # 检查冒号后是否有多余内容
        if colon_split_strs[1].strip() != "":
            self.diag_handler.set_line_error(node_uid, IcbEType.EXTRA_CONTENT_AFTER_COLON)
            return None
        
        node = self._create_base_node('begin', node_uid)
        node.update({
            'is_block_start': True,
            'special_align': True,
            'expected_child': ['behavior_step', 'behavior_step_with_child', 'var', 'func', 'class']
        })
        return node
    
    # input 输入变量列表解析
    def _parse_input_attribute(self, line_content: str, node_uid: int) -> Optional[Dict[str, Any]]:
        # 格式要求: 'input: [输入变量列表, 以逗号分隔]'
        parts = line_content.split(':', 1)
        if len(parts) < 2:
            self.diag_handler.set_line_error(node_uid, IcbEType.MISSING_COLON)
            return None
        
        node = self._create_base_node('input', node_uid)
        node.update({
            'value': parts[1].strip().split(','),
            'special_align': True,
            'expected_next': ['output', 'begin']
        })
        return node

    # output 输出变量列表解析
    def _parse_output_attribute(self, line_content: str, node_uid: int) -> Optional[Dict[str, Any]]:
        # 格式要求: 'output: [输出变量列表, 以逗号分隔]'
        parts = line_content.split(':', 1)
        if len(parts) < 2:
            self.diag_handler.set_line_error(node_uid, IcbEType.MISSING_COLON)
            return None
        
        node = self._create_base_node('output', node_uid)
        node.update({
            'value': parts[1].strip().split(','),
            'special_align': True,
            'expected_next': ['begin']
        })
        return node

    # inh属性解析
    def _parse_inh_attribute(self, line_content: str, node_uid: int) -> Optional[Dict[str, Any]]:
        parts = line_content.split(':', 1)
        if len(parts) < 2:
            self.diag_handler.set_line_error(node_uid, IcbEType.MISSING_COLON)
            return None
        
        node = self._create_base_node('inh', node_uid)
        node.update({
            'value': parts[1].strip(),
            'special_align': True,
            'expected_next': ['begin']  # inh后只会再出现begin（不考虑意图注释）
        })
        return node

    # 带有子代码块的行为步骤行
    def _parse_behavior_step_with_child(self, line_content: str, node_uid: int) -> Dict[str, Any]:
        parts = line_content.split(':', 1)
        node = self._create_base_node('behavior_step_with_child', node_uid)
        if parts[1].strip():
            # 子代码块可能在同一行且只有一行，体现为冒号后存在非空白内容，此时禁止进一步换行缩进
            child_content = parts[1].strip()
            node.update({
                'value': line_content,
                'is_block_start': False,
                'expected_child': ['var', 'behavior_step', 'behavior_step_with_child'],
                'expected_next': ['var', 'behavior_step', 'behavior_step_with_child']
            })
        else:
            # 没有同一行子内容时添加expected_child
            node.update({
                'value': line_content,
                'is_block_start': True,
                'expected_child': ['var', 'behavior_step', 'behavior_step_with_child'],
                'expected_next': ['var', 'behavior_step', 'behavior_step_with_child']
            })
        return node
    
    # 常规行为步骤行
    def _parse_behavior_step(self, line_content: str, node_uid: int) -> Dict[str, Any]:
        node = self._create_base_node('behavior_step', node_uid)
        node.update({
            'value': line_content.strip(),
            'expected_next': ['var', 'behavior_step', 'behavior_step_with_child']
        })
        return node
    
    # pass行，规避一些现在懒得做特殊处理的语法问题，统一用pass行处理
    def _parse_pass(self, line_content: str, node_uid: int) -> Dict[str, Any]:
        node = self._create_base_node('pass', node_uid)
        return node