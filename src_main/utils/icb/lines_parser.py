import sys
from typing import Dict, Any, List, Optional

from libs.diag_handler import DiagHandler, IcbEType, IcbWType


class LinesParser:
    def __init__(self, diag_handler: DiagHandler):
        self.diag_handler = diag_handler
    
    def parse_line(self, line_content: str, node_uid: int) -> Optional[Dict[str, Any]]:
        """
        解析单行内容并生成对应的节点结构
        Args:
            line_content: 行内容字符串
            node_uid: 节点唯一标识符（行号）
            
        Returns:
            解析后的节点字典，如果解析失败则返回None
        """
        # 1. 对行内容进行分类
        line_classification = self._classify_line(line_content)
        
        # 2. 根据分类结果选择对应的解析方法
        parsing_methods = {
            "intent_comment": self._parse_intent_comment,
            "module_declaration": self._parse_module_declaration,
            "class_declaration": self._parse_class_declaration,
            "function_declaration": self._parse_function_declaration,
            "variable_declaration": self._parse_variable_declaration,
            "begin_declaration": self._parse_begin_declaration,
            "input_attribute": self._parse_input_attribute,
            "output_attribute": self._parse_output_attribute,
            "description_attribute": self._parse_description_attribute,
            "inh_attribute": self._parse_inh_attribute,
            "behavior_step_with_child": self._parse_behavior_step_with_child,
            "behavior_step": self._parse_behavior_step,
            "pass": self._parse_pass
        }
        
        # 3. 如果是正常的行类型，调用对应的解析方法
        if line_classification in parsing_methods:
            return parsing_methods[line_classification](line_content, node_uid)
        
        # 4. 处理各种行分类错误
        error_type_map = {
            "line_error_unexpected_colon": IcbEType.UNEXPECTED_COLON,
            "line_error_keyword_format": IcbEType.KEYWORD_FORMAT_ERROR,
            "line_error_missing_colon": IcbEType.MISSING_COLON
        }
        
        # 5. 根据错误类型设置诊断信息
        if line_classification in error_type_map:
            self.diag_handler.set_line_error(node_uid, error_type_map[line_classification])
        else:
            self.diag_handler.set_line_error(node_uid, IcbEType.UNKNOWN_LINE_TYPE)
            
        # 6. 解析失败返回None
        return None
    
    def _classify_line(self, line_content: str) -> str:
        """
        对行内容进行分类，识别其类型
        Args:
            line_content: 行内容字符串
            
        Returns:
            行的分类结果字符串
        """
        # 意图注释行以@开头
        if line_content.startswith("@"):
            return "intent_comment"

        # 处理包含冒号的行
        if ':' in line_content:
            return self._classify_line_with_colon(line_content)
        else:
            # 处理不包含冒号的行
            return self._classify_line_without_colon(line_content)

    def _classify_line_with_colon(self, line_content: str) -> str:
        """
        对包含冒号的行进行分类
        
        Args:
            line_content: 包含冒号的行内容字符串
            
        Returns:
            行的分类结果字符串
        """
        # 提取冒号前的第一个字符串
        first_part = line_content.split(':', 1)[0].strip()

        # 检查是否是行首冒号错误
        if first_part == "":
            return "line_error_unexpected_colon"
        
        # 获取第一个单词（关键字）
        first_word = first_part.split()[0]
        
        # 定义关键字到分类的映射
        keyword_map = {
            "module": "module_declaration",
            "class": "class_declaration",
            "func": "function_declaration",
            "var": "variable_declaration",
            "begin": "begin_declaration",
            "input": "input_attribute",
            "output": "output_attribute",
            "description": "description_attribute",
            "inh": "inh_attribute"
        }
        
        # 如果第一个词是关键字，直接返回对应的分类
        if first_word in keyword_map:
            return keyword_map[first_word]
            
        # 非关键字但包含冒号的行视为行为步骤（带子节点）
        return "behavior_step_with_child"

    def _classify_line_without_colon(self, line_content: str) -> str:
        """
        对不包含冒号的行进行分类
        Args:
            line_content: 不包含冒号的行内容字符串
            
        Returns:
            行的分类结果字符串
        """
        # 去除首尾空格后按空格分割
        parts = line_content.strip().split()
        
        # 获取第一个单词，如果parts为空则使用整行内容
        first_word = parts[0] if parts else line_content.strip()
        
        # 定义不需要冒号的关键字映射
        keyword_map_no_colon = {
            "pass": "pass"
        }
        
        # 需要冒号但缺少冒号的关键字列表
        keywords_requiring_colon = [
            "module", "class", "func", "var", 
            "begin", "input", "output", "description", "inh"
        ]
        
        # 检查是否是以关键字开头但应该有冒号的行
        if first_word in keywords_requiring_colon:
            return "line_error_missing_colon"
            
        # 检查是否是不需要冒号的特殊关键字
        if first_word in keyword_map_no_colon:
            return keyword_map_no_colon[first_word]
            
        # 默认视为行为步骤
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
            'expected_child': ['module', 'class', 'func', 'var', 'begin']
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

    # module 模块声明
    def _parse_module_declaration(self, line_content: str, node_uid: int) -> Optional[Dict[str, Any]]:
        # 格式要求: 'module 模块名: 模块描述'
        colon_split_strs = line_content.split(':', 1)  # 只分割第一个冒号
        if len(colon_split_strs) < 2:
            self.diag_handler.set_line_error(node_uid, IcbEType.MISSING_COLON)
            return None

        module_components = colon_split_strs[0].strip().split()
        # 检查模块名是否存在
        if len(module_components) < 2:
            self.diag_handler.set_line_error(node_uid, IcbEType.MISSING_MODULE_NAME)
            return None

        # 检查是否有多余空格及内容
        if len(module_components) > 2:
            self.diag_handler.set_line_error(node_uid, IcbEType.UNEXPECTED_SPACE)
            return None

        # 创建模块节点
        node = self._create_base_node('module', node_uid)
        node.update({
            'name': module_components[1],
            'value': colon_split_strs[1].strip(),
            'description': colon_split_strs[1].strip(),
            'expected_next': ['module', 'class', 'func', 'var']
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
            'expected_child': ['description', 'inh', 'begin', 'var', 'func'],  # 添加description支持
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
        
        var_parts = parts[0].strip().split()
        # 检查变量名是否存在
        if len(var_parts) < 2:
            self.diag_handler.set_line_error(node_uid, IcbEType.MISSING_VAR_NAME)
            return None
        
        # 检查变量名后是否有多余内容
        if len(var_parts) > 2:
            self.diag_handler.set_line_error(node_uid, IcbEType.UNEXPECTED_SPACE)
            return None
        
        # 处理变量描述
        description = None
        if len(parts) >= 2:
            description = parts[1].strip() if parts[1].strip() else None
        
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
        
        # 分割逗号分隔的变量列表，并去除每个变量名前后的空格
        raw_variables = parts[1].strip().split(',')
        variables = [var.strip() for var in raw_variables]
        
        node = self._create_base_node('input', node_uid)
        node.update({
            'value': variables,
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
        
        # 分割逗号分隔的变量列表，并去除每个变量名前后的空格
        raw_variables = parts[1].strip().split(',')
        variables = [var.strip() for var in raw_variables]
        
        node = self._create_base_node('output', node_uid)
        node.update({
            'value': variables,
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
        if len(parts) > 1 and parts[1].strip():
            # 子代码块可能在同一行且只有一行，体现为冒号后存在非空白内容，此时禁止进一步换行缩进
            child_content = parts[1].strip()
            node.update({
                'value': parts[0].strip(),  # 只保留冒号前的部分作为value
                'is_block_start': False,  # 同行内容不需要进一步缩进
                'expected_child': [],  # 没有子节点
                'expected_next': ['var', 'behavior_step', 'behavior_step_with_child']
            })
        else:
            # 没有同一行子内容时添加expected_child
            node.update({
                'value': parts[0].strip(),  # 只保留冒号前的部分作为value
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