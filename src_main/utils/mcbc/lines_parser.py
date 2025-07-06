import sys
from typing import Dict, Any, List, Optional

from src_main.cfg.mccp_config_manager import g_mccp_config_manager
from src_main.lib.diag_handler import DiagHandler, EType, WType

# TODO: 在未来 expected_next_type这个属性应该进行一定的重构，现在这种状态属于纯手动维护，必然会为未来开发带来困难。
# 更主要的一点在于，对于不同的target lang来说，语法行为应该有不同的限制。比如python允许函数和类的嵌套定义，但C中不会进行函数的嵌套
# 目前的困难是：mccp不是编程语言，目前评估也不适合去编写“上下文无关文法 —— 也即CFG”。我需要自定义递归下降的结构，保持灵活性和可变性

class LinesParser:
    def __init__(self, diag_handler: DiagHandler):
        self.diag_handler = diag_handler
    
    def parse_line(self, line_content: str, line_num: int) -> Optional[Dict[str, Any]]:
        line_classify_result = self._classify_line(line_content)
        
        # _parse_line检测到语法错误后会返回None
        if line_classify_result == "intent_comment":
            return self._parse_intent_comment(line_content, line_num)
        elif line_classify_result == "class_declaration":
            return self._parse_class_declaration(line_content, line_num)
        elif line_classify_result == "function_declaration":
            return self._parse_function_declaration(line_content, line_num)
        elif line_classify_result == "variable_declaration":
            return self._parse_variable_declaration(line_content, line_num)
        elif line_classify_result == "behavior_declaration":
            return self._parse_begin_declaration(line_content, line_num)
        elif line_classify_result == "attribute":
            return self._parse_attribute(line_content, line_num)
        elif line_classify_result == "behavior_step_with_children":
            return self._parse_behavior_step_with_child(line_content, line_num)
        elif line_classify_result == "behavior_step":
            return self._parse_behavior_step(line_content, line_num)

        # 目前唯一一个来自line_classify的语法错误检查
        elif line_classify_result == "line_error_unexpected_colon":
            self.diag_handler.set_line_error(line_num, EType.UNEXPECTED_COLON)
            return None
        else:
            self.diag_handler.set_line_error(line_num, EType.UNKNOWN_LINE_TYPE)
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
            'expected_next': [],
            'expected_child': [],
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
        # 无格式要求，意图注释本质上是提示词
        node = self._create_base_node('intent_comment', line_num)
        node.update({
            'value': line_content.lstrip('@').strip(),
            'is_ast_node': False,
            'expected_next_types': ['class', 'func', 'var', 'behavior', 'behavior_step_with_child']
        })
        return node
    
    # 类声明
    def _parse_class_declaration(self, line_content: str, line_num: int) -> Optional[Dict[str, Any]]:
        # 格式要求: 'class 类名:' (冒号后不允许有其他内容)
        colon_split_strs = line_content.split(':', 1) # 只分割第一个冒号
        if len(colon_split_strs) < 2:
            self.diag_handler.set_line_error(line_num, EType.MISSING_COLON)
            return None
        
        # 检查冒号后是否有多余内容
        if colon_split_strs[1].strip() != "":
            self.diag_handler.set_line_error(line_num, EType.EXTRA_CONTENT_AFTER_COLON)
            return None
        
        class_components = colon_split_strs[0].strip().split()
        # 检查类名是否存在
        if len(class_components) < 2:
            self.diag_handler.set_line_error(line_num, EType.MISSING_CLASS_NAME)
            return None
        
        # 检查是否有多余空格及内容
        if len(class_components) > 2:
            self.diag_handler.set_line_error(line_num, EType.UNEXPECTED_SPACE)
            return None
        
        # 创建类节点
        node = self._create_base_node('class', line_num)
        node.update({
            'name': class_components[1],
            'is_block_start': False,  # 修改为False
            'expected_next': ['inh', 'begin']  # 新增begin关键字要求
        })
        return node
    
    # 函数声明
    def _parse_function_declaration(self, line_content: str, line_num: int) -> Optional[Dict[str, Any]]:
        # 格式要求: 'func 函数名:' (冒号后不允许有其他内容)
        colon_split_strs = line_content.split(':', 1) # 只分割第一个冒号
        if len(colon_split_strs) < 2:
            self.diag_handler.set_line_error(line_num, EType.MISSING_COLON)
            return None
        
        # 检查冒号后是否有多余内容
        if colon_split_strs[1].strip() != "":
            self.diag_handler.set_line_error(line_num, EType.EXTRA_CONTENT_AFTER_COLON)
            return None
        
        func_components = colon_split_strs[0].strip().split()
        # 检查函数名是否存在
        if len(func_components) < 2:
            self.diag_handler.set_line_error(line_num, EType.MISSING_FUNCTION_NAME)
            return None
        
        # 检查函数名后是否有多余内容
        if len(func_components) > 2:
            self.diag_handler.set_line_error(line_num, EType.UNEXPECTED_SPACE)
            return None
        
        # 创建函数节点（注意，func关键字不被认为是块起始, 'behavior' 才是）
        node = self._create_base_node('func', line_num)
        node.update({
            'name': func_components[1],
            'is_block_start': False,
            'expected_next': ['input', 'output', 'description', 'begin']
        })
        return node
    
    # 变量声明
    def _parse_variable_declaration(self, line_content: str, line_num: int) -> Optional[Dict[str, Any]]:
        # 格式要求: 'var 变量名[: 可选的对变量的描述]' 
        parts = line_content.split(':', 1)
        if len(parts) < 2:
            description = None
        else:
            description = parts[1].strip()
        
        var_parts = parts[0].strip().split()
        # 检查变量名是否存在
        if len(var_parts) < 2:
            self.diag_handler.set_line_error(line_num, EType.MISSING_VAR_NAME)
            return None
        
        # 检查变量名后是否有多余内容
        if len(var_parts) > 2:
            self.diag_handler.set_line_error(line_num, EType.UNEXPECTED_SPACE)
            return None
        
        node = self._create_base_node('var', line_num)
        node.update({
            'name': var_parts[1],
            'value': description,
            'description': description,
            'expected_next_types': ['behavior_step', 'behavior_step_with_child', 'var', 'func']
        })
        return node
    
    # 行为块起始关键字
    def _parse_begin_declaration(self, line_content: str, line_num: int) -> Optional[Dict[str, Any]]:
        # 检查行末尾是否有冒号
        if not line_content.endswith(':'):
            self.diag_handler.set_line_error(line_num, EType.MISSING_COLON)
            return None
        
        node = self._create_base_node('begin', line_num)
        node.update({
            'is_block_start': True,
            'expected_child': ['behavior_step', 'behavior_step_with_child', 'var', 'func']  # 使用expected_child
        })
        return node
    
    # Input属性解析
    def _parse_input_attribute(self, line_content: str, line_num: int) -> Optional[Dict[str, Any]]:
        parts = line_content.split(':', 1)
        if len(parts) < 2:
            self.diag_handler.set_line_error(line_num, EType.MISSING_COLON)
            return None
        
        node = self._create_base_node('input', line_num)
        node.update({
            'value': parts[1].strip(),
            'is_ast_node': False,
            'expected_next': ['input', 'output', 'description', 'begin']
        })
        return node
    
    # Output属性解析
    def _parse_output_attribute(self, line_content: str, line_num: int) -> Optional[Dict[str, Any]]:
        parts = line_content.split(':', 1)
        if len(parts) < 2:
            self.diag_handler.set_line_error(line_num, EType.MISSING_COLON)
            return None
        
        node = self._create_base_node('output', line_num)
        node.update({
            'value': parts[1].strip(),
            'is_ast_node': False,
            'expected_next': ['input', 'output', 'description', 'begin']
        })
        return node
    
    # Description属性解析
    def _parse_description_attribute(self, line_content: str, line_num: int) -> Optional[Dict[str, Any]]:
        parts = line_content.split(':', 1)
        if len(parts) < 2:
            self.diag_handler.set_line_error(line_num, EType.MISSING_COLON)
            return None
        
        node = self._create_base_node('description', line_num)
        node.update({
            'value': parts[1].strip(),
            'is_ast_node': False,
            'expected_next': ['var', 'func', 'begin']
        })
        return node
    
    # Inh属性解析
    def _parse_inh_attribute(self, line_content: str, line_num: int) -> Optional[Dict[str, Any]]:
        parts = line_content.split(':', 1)
        if len(parts) < 2:
            self.diag_handler.set_line_error(line_num, EType.MISSING_COLON)
            return None
        
        node = self._create_base_node('inh', line_num)
        node.update({
            'value': parts[1].strip(),
            'is_ast_node': False,
            'expected_next': ['begin']  # inh后必须跟begin
        })
        return node
    
    # 带有子代码块的行为步骤行，子代码块可能在同一行且只有一行，体现为len(parts) > 1
    def _parse_behavior_step_with_child(self, line_content: str, line_num: int) -> Dict[str, Any]:
        parts = line_content.split(':', 1)
        behavior_desc = parts[0].strip()

        node = self._create_base_node('behavior_step_with_child', line_num)
        # 如果子行为块直接在同一行就不必要再进行进一步缩进
        if len(parts) > 1:
            child_content = parts[1].strip()
            node.update({
                'value': behavior_desc,
                'is_block_start': False,
                'one_line_child_content': child_content,
                'expected_next': ['behavior_step', 'behavior_step_with_child', 'var']
            })
        else:
            # 没有同一行子内容时添加expected_child
            node.update({
                'value': behavior_desc,
                'is_block_start': True,
                'expected_child': ['var', 'behavior_step'],
                'expected_next': ['behavior_step', 'behavior_step_with_child', 'var']
            })
        return node
    
    # 常规行为步骤行
    def _parse_behavior_step(self, line_content: str, line_num: int) -> Dict[str, Any]:
        node = self._create_base_node('behavior_step', line_num)
        node.update({
            'value': line_content.strip(),
            'expected_next': ['behavior_step', 'behavior_step_with_child', 'var']
        })
        return node
