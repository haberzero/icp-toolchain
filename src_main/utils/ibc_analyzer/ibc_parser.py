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
    CLASS_DECL = "CLASS_DECL"  # 类定义解析状态
    FUNCTION_DECL = "FUNCTION_DECL"  # 函数定义解析状态
    VARIABLE_DECL = "VARIABLE_DECL"  # 变量定义解析状态
    MODULE_DECL = "MODULE_DECL"  # 模块应用解析状态


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
        self.state_stack: List[Tuple[ParserState, Optional[int]]] = [(ParserState.TOP_LEVEL, None)]
        self.ast_nodes: Dict[int, AstNode] = {}
        self.node_counter = 1
        
        # 用于暂存特殊行内容
        self.pending_intent_comment = ""
        self.pending_description = ""
        
        # 用于跟踪上一个AST节点
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
    
    def _is_at_end(self) -> bool:
        """检查是否到达文件末尾"""
        return self._peek_token().type == IbcTokenType.EOF
    
    def _get_current_state(self) -> Tuple[ParserState, Optional[int]]:
        """获取当前状态"""
        return self.state_stack[-1] if self.state_stack else (ParserState.TOP_LEVEL, None)
    
    def _push_state(self, state: ParserState, parent_uid: Optional[int] = None):
        """压入状态栈"""
        self.state_stack.append((state, parent_uid))
    
    def _pop_state(self) -> Tuple[ParserState, Optional[int]]:
        """弹出状态栈"""
        if not self.state_stack:
            raise ParseError(self._peek_token().line_num, "State stack is empty")
        return self.state_stack.pop()
    
    def _add_ast_node(self, node: AstNode):
        """添加AST节点"""
        self.ast_nodes[node.uid] = node
        self.last_ast_node = node

        # 没有父节点直接返回
        if not node.parent_uid:
            return
        
        # 如果有父节点，向父节点添加子节点
        if node.parent_uid in self.ast_nodes:
            parent_node = self.ast_nodes[node.parent_uid]
            parent_node.add_child(node.uid)
    
    def _handle_indent_dedent(self) -> bool:
        """处理缩进/退格token，返回是否有缩进变化"""
        token = self._peek_token()
        current_state, parent_uid = self._get_current_state()
        
        if token.type == IbcTokenType.INDENT:
            self._consume_token()
            
            # 检查上一个节点是否需要缩进
            if self.last_ast_node:
                # 需要缩进的情况：函数、类或带有new_block_flag的行为步骤
                if ((isinstance(self.last_ast_node, (FunctionNode, ClassNode))) or
                    (isinstance(self.last_ast_node, BehaviorStepNode) and 
                     getattr(self.last_ast_node, 'new_block_flag', False))):
                    # 正确的缩进，无需报错
                    pass
                else:
                    raise ParseError(token.line_num, "Unexpected indent")
            
            return True
            
        elif token.type == IbcTokenType.DEDENT:
            self._consume_token()
            
            # 出栈直到匹配正确的缩进级别
            if len(self.state_stack) > 1:
                self._pop_state()
            
            return True
            
        return False
    
    def _handle_special_lines(self) -> bool:
        """处理特殊行（意图注释、描述），返回是否处理了特殊行"""
        token = self._peek_token()
        
        # 处理意图注释
        if token.type == IbcTokenType.INTENT_COMMENT:
            self.pending_intent_comment = self._consume_token().value
            # 消费换行符
            self._match_token(IbcTokenType.NEWLINE)
            return True
            
        # 处理描述行
        if (token.type == IbcTokenType.KEYWORDS and 
            token.value == "description" and
            self._get_token_by_index(offset=2).type == IbcTokenType.COLON):  # 查看 "description" ":" 的模式
            self._consume_token()  # 消费 "description"
            self._match_token(IbcTokenType.COLON)  # 消费 ":"
            
            # 获取描述内容
            content_token = self._consume_token()  # 消费描述内容
            if content_token.type == IbcTokenType.IDENTIFIER:
                self.pending_description = content_token.value
            else:
                self.pending_description = ""
                
            # 消费换行符
            self._match_token(IbcTokenType.NEWLINE)
            return True
            
        return False
    
    def _get_token_by_index(self, offset: int = 0) -> Token:
        """查看指定index位置的token"""
        if self.pos + offset < len(self.tokens):
            return self.tokens[self.pos + offset]
        return Token(IbcTokenType.EOF, "EOF", -1)
    
    def _parse_module_decl(self):
        """解析模块声明"""
        token = self._consume_token()  # 消费 "module"
        module_name_token = self._consume_token()  # 模块名
        
        if module_name_token.type != IbcTokenType.IDENTIFIER:
            raise ParseError(module_name_token.line_num, "Expected module name")
            
        self._match_token(IbcTokenType.COLON)  # 消费 ":"
        
        # 获取模块描述
        desc_token = self._consume_token()
        module_desc = ""
        if desc_token.type == IbcTokenType.IDENTIFIER:
            module_desc = desc_token.value
            
        # 创建模块节点
        module_node = ModuleNode(
            uid=self._generate_uid(),
            node_type=AstNodeType.MODULE,
            line_number=token.line_num,
            identifier=module_name_token.value,
            content=module_desc
        )
        
        self._add_ast_node(module_node)
        self._match_token(IbcTokenType.NEWLINE)  # 消费换行符
    
    def _parse_class_decl(self):
        """解析类声明"""
        token = self._consume_token()  # 消费 "class"
        class_name_token = self._consume_token()  # 类名
        
        if class_name_token.type != IbcTokenType.IDENTIFIER:
            raise ParseError(class_name_token.line_num, "Expected class name")
            
        self._match_token(IbcTokenType.COLON)  # 消费 ":"
        
        # 创建类节点
        _, parent_uid = self._get_current_state()
        class_node = ClassNode(
            uid=self._generate_uid(),
            parent_uid=parent_uid if parent_uid else 0,
            node_type=AstNodeType.CLASS,
            line_number=token.line_num,
            identifier=class_name_token.value,
            intent_comment=self.pending_intent_comment
        )
        
        # 清空暂存的意图注释
        self.pending_intent_comment = ""
        
        self._add_ast_node(class_node)
        
        # 压入类内容状态
        self._push_state(ParserState.CLASS_CONTENT, class_node.uid)
        self._match_token(IbcTokenType.NEWLINE)  # 消费换行符
    
    def _parse_function_decl(self):
        """解析函数声明"""
        token = self._consume_token()  # 消费 "func"
        func_name_token = self._consume_token()  # 函数名
        
        if func_name_token.type != IbcTokenType.IDENTIFIER:
            raise ParseError(func_name_token.line_num, "Expected function name")
            
        self._match_token(IbcTokenType.COLON)  # 消费 ":"
        
        # 创建函数节点
        _, parent_uid = self._get_current_state()
        func_node = FunctionNode(
            uid=self._generate_uid(),
            parent_uid=parent_uid if parent_uid else 0,
            node_type=AstNodeType.FUNCTION,
            line_number=token.line_num,
            identifier=func_name_token.value,
            intent_comment=self.pending_intent_comment,
            external_desc=self.pending_description
        )
        
        # 清空暂存的内容
        self.pending_intent_comment = ""
        self.pending_description = ""
        
        self._add_ast_node(func_node)
        
        # 压入函数内容状态
        self._push_state(ParserState.FUNCTION_CONTENT, func_node.uid)
        self._match_token(IbcTokenType.NEWLINE)  # 消费换行符
    
    def _parse_variable_decl(self):
        """解析变量声明"""
        token = self._consume_token()  # 消费 "var"
        var_name_token = self._consume_token()  # 变量名
        
        if var_name_token.type != IbcTokenType.IDENTIFIER:
            raise ParseError(var_name_token.line_num, "Expected variable name")
            
        self._match_token(IbcTokenType.COLON)  # 消费 ":"
        
        # 获取变量描述
        desc_token = self._consume_token()
        var_desc = ""
        if desc_token.type == IbcTokenType.IDENTIFIER:
            var_desc = desc_token.value
            
        # 创建变量节点
        _, parent_uid = self._get_current_state()
        var_node = VariableNode(
            uid=self._generate_uid(),
            parent_uid=parent_uid if parent_uid else 0,
            node_type=AstNodeType.VARIABLE,
            line_number=token.line_num,
            identifier=var_name_token.value,
            external_desc=var_desc,
            intent_comment=self.pending_intent_comment
        )
        
        # 清空暂存的意图注释
        self.pending_intent_comment = ""
        
        self._add_ast_node(var_node)
        self._match_token(IbcTokenType.NEWLINE)  # 消费换行符
    
    def _parse_behavior_step(self):
        """解析行为步骤"""
        # 收集整行内容直到换行符
        line_content = ""
        symbol_refs = {}
        new_block_flag = False
        
        # 收集这行的所有token直到换行符
        while not self._is_at_end() and self._peek_token().type != IbcTokenType.NEWLINE:
            token = self._consume_token()
            if token.type == IbcTokenType.REF_IDENTIFIER:
                # 记录符号引用
                ref_id = f"ref_{len(symbol_refs)}"
                symbol_refs[ref_id] = token.value
                line_content += f"${token.value}$"
            elif token.type == IbcTokenType.COLON:
                # 检查冒号是否在行末
                if (self._peek_token().type == IbcTokenType.NEWLINE or 
                    (self._peek_token().type == IbcTokenType.EOF)):
                    new_block_flag = True
                    line_content += ":"
                else:
                    line_content += token.value
            else:
                line_content += token.value
        
        # 移除可能的行尾冒号（如果它是新块标记）
        if new_block_flag and line_content.endswith(":"):
            line_content = line_content[:-1]
        
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
        
        # 如果有新的代码块，压入状态
        if new_block_flag:
            self._push_state(ParserState.FUNCTION_CONTENT, behavior_node.uid)
            
        self._match_token(IbcTokenType.NEWLINE)  # 消费换行符
    
    def _handle_keyword_declarations(self) -> bool:
        """处理关键字声明，返回是否处理了关键字"""
        token = self._peek_token()
        
        if token.type != IbcTokenType.KEYWORDS:
            return False
            
        current_state, _ = self._get_current_state()
        
        # 根据当前状态和关键字类型决定如何处理
        if token.value == "module":
            if current_state != ParserState.TOP_LEVEL:
                raise ParseError(token.line_num, "Module declaration only allowed at top level")
            self._parse_module_decl()
            return True
        elif token.value == "class":
            self._parse_class_decl()
            return True
        elif token.value == "func":
            self._parse_function_decl()
            return True
        elif token.value == "var":
            self._parse_variable_decl()
            return True
            
        return False
    
    def parse(self) -> Dict[int, AstNode]:
        """执行解析"""
        while not self._is_at_end():
            token = self._peek_token()
            
            # 如果是文件结束符，退出循环
            if token.type == IbcTokenType.EOF:
                break
                
            # 如果是换行符，直接消费
            if token.type == IbcTokenType.NEWLINE:
                self._consume_token()
                continue
            
            # 处理缩进/退格
            if self._handle_indent_dedent():
                continue
                
            # 处理特殊行（意图注释、描述）
            if self._handle_special_lines():
                continue
                
            # 处理关键字声明
            if self._handle_keyword_declarations():
                continue
                
            # 默认处理为行为步骤
            self._parse_behavior_step()
        
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