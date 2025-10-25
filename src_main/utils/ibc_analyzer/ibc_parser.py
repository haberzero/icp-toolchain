from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from typedef.ibc_data_types import (
    IbcTokenType, Token, AstNode, AstNodeType, 
    ModuleNode, ClassNode, FunctionNode, VariableNode, BehaviorStepNode
)


class ParserState(Enum):
    """解析器状态枚举"""
    TOP_LEVEL = "TOP_LEVEL"  # 顶层状态
    CLASS_CONTENT = "CLASS_CONTENT"  # 类内容状态
    FUNCTION_CONTENT = "FUNCTION_CONTENT"  # 函数内容状态（行为步骤状态）


class ParseError(Exception):
    """解析异常"""
    def __init__(self, line_num: int, message: str):
        self.line_num = line_num
        self.message = message
        super().__init__(f"Line {line_num}: {message}")
    
    def __str__(self):
        return f"ParserError: {self.message}"


class IbcParser:
    """IBC代码解析器"""
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.state_stack: List[Tuple[ParserState, int]] = [(ParserState.TOP_LEVEL, 0)]
        self.ast_nodes: Dict[int, AstNode] = {}
        self.node_counter = 1
        
        # 暂存的特殊行内容
        self.pending_intent_comment = ""
        self.pending_description = ""
        
        # 跟踪上一个AST节点
        self.last_ast_node: Optional[AstNode] = None
        
    def _generate_uid(self) -> int:
        """生成唯一ID"""
        self.node_counter += 1
        return self.node_counter
    
    def _peek_token(self) -> Token:
        """查看当前token"""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(IbcTokenType.EOF, "EOF", -1)
    
    def _consume_token(self) -> Token:
        """消费当前token"""
        token = self._peek_token()
        self.pos += 1
        return token
    
    def _match_token(self, expected_type: IbcTokenType) -> Token:
        """匹配特定类型的token"""
        token = self._peek_token()
        if token.type == expected_type:
            return self._consume_token()
        raise ParseError(token.line_num, f"Expected {expected_type}, but got {token.type}")

    def _take_token_str_until(self, stop_token: IbcTokenType) -> str:
        """从当前位置开始，直到遇到指定token，返回所有token的值。用于获取直到特定token前的总字符串"""
        tokens = []
        while self._peek_token().type != stop_token:
            if self._is_at_end():
                raise ParseError(self._peek_token().line_num, "Unexpected end of file")
            tokens.append(self._consume_token())
        return "".join(token.value for token in tokens)
    
    def _discard_token_until(self, stop_token: IbcTokenType):
        """从当前位置开始，直到遇到指定token，丢弃期间所获取到的所有token"""
        while self._peek_token().type != stop_token:
            if self._is_at_end():
                raise ParseError(self._peek_token().line_num, "Unexpected end of file")
            self._consume_token()
    
    def _is_at_end(self) -> bool:
        """检查是否到达文件末尾"""
        return self._peek_token().type == IbcTokenType.EOF
    
    def _get_current_state(self) -> Tuple[ParserState, int]:
        """获取当前状态"""
        return self.state_stack[-1] if self.state_stack else (ParserState.TOP_LEVEL, 0)
    
    def _push_state(self, state: ParserState, parent_uid: int):
        """压入状态栈"""
        self.state_stack.append((state, parent_uid))
    
    def _pop_state(self) -> Tuple[ParserState, int]:
        """弹出状态栈"""
        if not self.state_stack:
            raise ParseError(self._peek_token().line_num, "State stack is empty")
        return self.state_stack.pop()
    
    def _add_ast_node(self, node: AstNode):
        """添加AST节点"""
        self.ast_nodes[node.uid] = node
        self.last_ast_node = node

        # 没有父节点直接返回
        if node.parent_uid == 0:
            return
        
        # 如果有父节点，向父节点添加子节点
        if node.parent_uid in self.ast_nodes:
            parent_node = self.ast_nodes[node.parent_uid]
            parent_node.add_child(node.uid)
    
    def _handle_indent_dedent(self):
        """处理缩进/退格token，返回是否有缩进变化"""
        token = self._peek_token()
        current_state, parent_uid = self._get_current_state()
        if token.type == IbcTokenType.INDENT:
            self._consume_token()

            # 没有已存在的AST Node, 不允许出现缩进
            if not self.last_ast_node:
                raise ParseError(token.line_num, "Unexpected indent")
            
            # 不允许出现连续的 indent token
            if self._peek_token().type == IbcTokenType.INDENT:
                raise ParseError(token.line_num, "Indent should not repeatedly occur")
            
            # 需要缩进的情况：函数、类或带有new_block_flag的行为步骤
            if isinstance(self.last_ast_node, FunctionNode):
                self._push_state(ParserState.FUNCTION_CONTENT, self.last_ast_node.uid)
                return 
            elif isinstance(self.last_ast_node, BehaviorStepNode) and \
                    getattr(self.last_ast_node, 'new_block_flag', False):
                self._push_state(ParserState.FUNCTION_CONTENT, self.last_ast_node.uid)
                return
            elif isinstance(self.last_ast_node, ClassNode):
                self._push_state(ParserState.CLASS_CONTENT, self.last_ast_node.uid)
                return
            
            else:
                raise ParseError(token.line_num, "Unexpected indent")
            
        elif token.type == IbcTokenType.DEDENT:
            while self._consume_token().type == IbcTokenType.DEDENT:
                self._pop_state()
            return
    
    def _handle_special_lines(self) -> bool:
        """处理特殊行（意图注释、描述），返回是否处理了特殊行"""
        current_token = self._peek_token()
        
        # 处理意图注释
        if current_token.type == IbcTokenType.INTENT_COMMENT:
            # 消费所有token并全部作为意图注释的字符处理，直到换行
            _tmp_str = self._take_token_str_until(IbcTokenType.NEWLINE)

            # 禁止行末冒号
            if _tmp_str.endswith(":"):
                raise ParseError(current_token.line_num, "Intent comment cannot end with colon")
            
            return True

        # 处理描述行
        elif current_token.type == IbcTokenType.KEYWORDS and \
            current_token.value == "description":
            
            self._consume_token()  # 消费 description token
            self._match_token(IbcTokenType.COLON)  # 检测冒号存在性

            # 消费所有剩余token并全部作为对外描述内容的字符处理，直到换行
            _tmp_str = self._take_token_str_until(IbcTokenType.NEWLINE)
            
            # 禁止行末冒号
            if _tmp_str.endswith(":"):
                raise ParseError(current_token.line_num, "Description cannot end with colon")

            return True
            
        return False
    
    def _parse_module_decl(self):
        """解析模块声明"""
        token = self._match_token(IbcTokenType.KEYWORDS)  # 消费 "module" 关键字
        module_name_token = self._match_token(IbcTokenType.IDENTIFIER)  # 消费模块名
        module_name = module_name_token.value

        if self._peek_token().type == IbcTokenType.NEWLINE:
            # 无描述，直接生成节点
            module_node = ModuleNode(
                uid=self._generate_uid(),
                node_type=AstNodeType.MODULE,
                line_number=token.line_num,
                identifier=module_name,
                content=""
            )
            self._add_ast_node(module_node)
            self._consume_token()   # 消费换行符
            return

        elif self._peek_token().type == IbcTokenType.COLON:
            # 消费所有剩余token并全部作为对外描述内容的字符处理，直到换行
            _tmp_token = self._consume_token()
            _tmp_str = _tmp_token.value
            while _tmp_token.type != IbcTokenType.NEWLINE:
                _tmp_str += _tmp_token.value
                _tmp_token = self._consume_token()
            
            # 禁止行末冒号
            if _tmp_str.endswith(":"):
                raise ParseError(token.line_num, "Unexpected colon at the end of line")
            
            module_desc = _tmp_str

            # 生成AST Node
            module_node = ModuleNode(
                uid=self._generate_uid(),
                node_type=AstNodeType.MODULE,
                line_number=token.line_num,
                identifier=module_name,
                content=module_desc
            )
            self._add_ast_node(module_node)
            self._match_token(IbcTokenType.NEWLINE)  # 消费换行符
        
        else:
            raise ParseError(token.line_num, "Unexpected token")
    
    def _parse_class_decl(self):
        """解析类声明"""
        token = self._consume_token()  # 消费 "class" 关键字
        class_name_token = self._match_token(IbcTokenType.IDENTIFIER)  # 类名
        class_name = class_name_token.value
        self._match_token(IbcTokenType.COLON)  # 消费 ":"
        
        # 创建类节点
        _, parent_uid = self._get_current_state()
        class_node = ClassNode(
            uid=self._generate_uid(),
            parent_uid=parent_uid if parent_uid else 0,
            node_type=AstNodeType.CLASS,
            line_number=token.line_num,
            identifier=class_name,
            external_desc=self.pending_description,
            intent_comment=self.pending_intent_comment
        )
        self._add_ast_node(class_node)
        
        # 清空暂存的意图注释以及对外描述
        self.pending_intent_comment = ""
        self.pending_description = ""
        
        self._match_token(IbcTokenType.NEWLINE)  # 消费换行符
    
    def _parse_function_decl(self):
        """解析函数声明"""
        token = self._consume_token()  # 消费 "func"
        func_name_token = self._match_token(IbcTokenType.IDENTIFIER)    # 函数名
        self._match_token(IbcTokenType.LPAREN)  # 消费 "("
        
        # 解析参数列表
        params = {}
        while self._peek_token().type != IbcTokenType.RPAREN:
            # 函数定义时，可能出现为了美观换行编写参数列表。因此忽略过程中的换行以及缩进相关token、直到identifier出现。
            self._discard_token_until(IbcTokenType.IDENTIFIER)
            param_name_token = self._consume_token()
            param_name = param_name_token.value
            param_desc = ""

            # 不合法的多个左括号
            if self._peek_token().type == IbcTokenType.LPAREN:
                raise ParseError(token.line_num, "Unexpected left parenthesis")
            
            # 检查是否有参数描述
            if self._peek_token().type == IbcTokenType.COLON:
                self._consume_token()  # 消费 ":"
                
                # 收集参数描述直到逗号或右括号
                while (self._peek_token().type not in [IbcTokenType.COMMA, IbcTokenType.RPAREN]):
                    if self._peek_token().type == IbcTokenType.EOF:
                        raise ParseError(self._peek_token().line_num, "Unexpected EOF")
                    desc_token = self._consume_token()
                    param_desc += desc_token.value
            
            # 添加参数描述内容到参数字典
            params[param_name] = param_desc.strip()  # strip参数描述
            
            # 如果是逗号，继续下一个参数
            if self._peek_token().type == IbcTokenType.COMMA:
                self._consume_token()  # 消费逗号
        
        self._match_token(IbcTokenType.RPAREN)  # 消费 ")"
        self._match_token(IbcTokenType.COLON)   # 消费 ":"
        
        # 创建函数节点
        _, parent_uid = self._get_current_state()
        func_node = FunctionNode(
            uid=self._generate_uid(),
            parent_uid=parent_uid if parent_uid else 0,
            node_type=AstNodeType.FUNCTION,
            line_number=token.line_num,
            identifier=func_name_token.value,
            intent_comment=self.pending_intent_comment,
            external_desc=self.pending_description,
            params=params
        )
        
        # 清空暂存的对外描述以及意图注释
        self.pending_intent_comment = ""
        self.pending_description = ""
        
        self._add_ast_node(func_node)
        
        self._match_token(IbcTokenType.NEWLINE)  # 消费换行符
    
    def _parse_variable_decl(self):
        """解析变量声明"""
        token = self._consume_token()  # 消费 "var"
        var_name_token = self._match_token(IbcTokenType.IDENTIFIER)  # 变量名
        
        self._match_token(IbcTokenType.COLON)  # 消费 ":"
        
        # 获取变量描述
        var_desc = ""
        # 收集所有剩余token直到换行符
        var_desc = self._take_token_str_until(IbcTokenType.NEWLINE)
        
        # 检查变量描述末尾是否包含不允许的符号
        if var_desc and var_desc[-1] in ":,()":
            raise ParseError(token.line_num, f"Variable description cannot end with these symbols --- ': , ( )'")
        
        # 创建变量节点
        _, parent_uid = self._get_current_state()
        var_node = VariableNode(
            uid=self._generate_uid(),
            parent_uid=parent_uid if parent_uid else 0,
            node_type=AstNodeType.VARIABLE,
            line_number=token.line_num,
            identifier=var_name_token.value,
            content=var_desc.strip(),
            external_desc=var_desc.strip(),
            intent_comment=self.pending_intent_comment
        )
        
        # 清空暂存的意图注释
        self.pending_intent_comment = ""
        
        self._add_ast_node(var_node)
        self._match_token(IbcTokenType.NEWLINE)  # 消费换行符
    
    def _parse_behavior_step(self):
        """解析行为步骤行"""
        # 收集整行内容直到换行符
        line_content = ""
        symbol_refs = []
        new_block_flag = False
        
        # 收集这行的所有token内容直到换行符，过程中记录符号引用
        while self._peek_token().type != IbcTokenType.NEWLINE:
            token = self._consume_token()
            line_content += token.value
            if token.type == IbcTokenType.REF_IDENTIFIER:
                # 记录符号引用
                symbol_refs.append(token.value)

        # 移除可能的行尾冒号，行为描述过程中的行尾冒号意味着新块以及缩进的开始
        line_content = line_content.strip()
        if line_content.endswith(":"):
            line_content = line_content[:-1]
            new_block_flag = True
        
        # 创建行为步骤节点
        _, parent_uid = self._get_current_state()
        behavior_node = BehaviorStepNode(
            uid=self._generate_uid(),
            parent_uid=parent_uid if parent_uid else 0,
            node_type=AstNodeType.BEHAVIOR_STEP,
            line_number=self._peek_token().line_num,
            content=line_content.strip(),
            symbol_refs=symbol_refs,
            new_block_flag=new_block_flag
        )
        
        self._add_ast_node(behavior_node)
        self._match_token(IbcTokenType.NEWLINE)  # 消费换行符
    
    def _handle_normal_line(self):
        """处理常规行, 行首第一个单词被认为是关键字 标点符号不允许出现在行首"""
        token = self._peek_token()
        current_state, _ = self._get_current_state()
        
        # 根据当前状态以及行内首个非缩进token内容决定后续处理方法
        if token.type == IbcTokenType.KEYWORDS and token.value == "module":
            if current_state != ParserState.TOP_LEVEL:
                raise ParseError(token.line_num, "Module declaration only allowed at file top")
            self._parse_module_decl()
            return
        elif token.type == IbcTokenType.KEYWORDS and token.value == "class":
            self._parse_class_decl()
            return
        elif token.type == IbcTokenType.KEYWORDS and token.value == "func":
            self._parse_function_decl()
            return
        elif token.type == IbcTokenType.KEYWORDS and token.value == "var":
            self._parse_variable_decl()
            return
        elif token.type == IbcTokenType.IDENTIFIER:
            if current_state != ParserState.FUNCTION_CONTENT:
                raise ParseError(token.line_num, "behavior step must be inside function")
            self._parse_behavior_step()
        else:
            raise ParseError(token.line_num, "Invalid content at the beginning of the line")
    
    def parse(self) -> Dict[int, AstNode]:
        """执行解析"""
        while not self._is_at_end():
            token = self._peek_token()

            # 如果是换行符，直接消费（所有处理应确保换行符被消费，此分支理论上不应该进入）
            if token.type == IbcTokenType.NEWLINE:
                print(f"Warning: Unexpected newline at line {token.line_num}")
                self._consume_token()
                continue
            
            # 检查并处理缩进，同时处理状态栈
            self._handle_indent_dedent()

            # 处理特殊行（意图注释、对外描述）
            if self._handle_special_lines():
                # 特殊行处理后直接进入下一行
                continue
                
            # 依据当前栈顶状态处理常规行
            self._handle_normal_line()
        
        return self.ast_nodes


def parse_ibc_tokens(tokens: List[Token]) -> Dict[str, Dict[str, Any]]:
    """解析IBC tokens并返回AST字典"""
    parser = IbcParser(tokens)
    ast_nodes = parser.parse()
    
    # 转换为字典格式
    result = {}
    for uid, node in ast_nodes.items():
        result[uid] = node.to_dict()
        
    return result