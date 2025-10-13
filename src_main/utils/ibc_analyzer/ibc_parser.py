from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from typedef.ibc_data_types import IbcKeywords, IbcTokenType, Token, AstNodeType, \
    AstNode, ModuleNode, ClassNode, FunctionNode, VariableNode, BehaviorStepNode


class ParseError(Exception):
    """解析器异常"""
    def __init__(self, message: str, line_number: int = 0):
        self.message = message
        self.line_number = line_number
        super().__init__(self.message)
    
    def __str__(self):
        if self.line_number:
            return f"ParseError at line {self.line_number}: {self.message}"
        return f"ParseError: {self.message}"


class ParserState(Enum):
    """解析器状态枚举"""
    TOP_LEVEL = "TOP_LEVEL"  # 顶层状态
    CLASS_CONTENT = "CLASS_CONTENT"  # 类内容状态
    FUNCTION_CONTENT = "FUNCTION_CONTENT"  # 函数内容状态（行为步骤状态）
    CLASS_DECL = "CLASS_DECL"  # 类定义解析状态
    FUNCTION_DECL = "FUNCTION_DECL"  # 函数定义解析状态
    VARIABLE_DECL = "VARIABLE_DECL"  # 变量定义解析状态
    MODULE_DECL = "MODULE_DECL"  # 模块应用解析状态


class Parser:
    """IBC语法解析器"""
    def __init__(self, tokens: List[Token]):
        self.tokens: List[Token] = tokens
        self.current_token_index = 0
        self.ast_nodes: Dict[str, AstNode] = {}
        self.node_counter = 0
        
        # 状态栈，用于处理缩进和嵌套结构
        self.state_stack: List[Tuple[ParserState, str]] = []  # (状态, 父节点UID)
        
        # 特殊行内容缓存（description和intent comment）
        self.pending_description = ""
        self.pending_intent_comment = ""
        
    def _generate_node_uid(self) -> str:
        """生成唯一的节点ID"""
        self.node_counter += 1
        return f"node_{self.node_counter}"
    
    def _peek_token(self, offset: int = 0) -> Token:
        """查看下一个token但不移动指针"""
        index = self.current_token_index + offset
        if index < len(self.tokens):
            return self.tokens[index]
        return Token(IbcTokenType.EOF, "EOF", 0)
    
    def _consume_token(self) -> Token:
        """消费当前token并移动到下一个"""
        if self.current_token_index < len(self.tokens):
            token = self.tokens[self.current_token_index]
            self.current_token_index += 1
            return token
        return Token(IbcTokenType.EOF, "EOF", 0)
    
    def _match_token(self, expected_type: IbcTokenType) -> Token:
        """匹配期望类型的token"""
        token = self._peek_token()
        if token.type == expected_type:
            return self._consume_token()
        raise ParseError(f"Expected {expected_type} but got {token.type}", token.line_num)
    
    def _match_optional_token(self, expected_type: IbcTokenType) -> Optional[Token]:
        """可选地匹配token"""
        token = self._peek_token()
        if token.type == expected_type:
            return self._consume_token()
        return None
    
    def _collect_until_newline(self) -> str:
        """收集直到换行符的所有内容"""
        content_parts = []
        while self._peek_token().type not in [IbcTokenType.NEWLINE, IbcTokenType.EOF]:
            token = self._consume_token()
            content_parts.append(token.value)
        return "".join(content_parts)
    
    def _apply_pending_attributes(self, node: AstNode) -> None:
        """将挂起的属性（description和intent_comment）应用到节点"""
        if isinstance(node, (ClassNode, FunctionNode)):
            node.external_desc = self.pending_description
            node.intent_comment = self.pending_intent_comment
            self.pending_description = ""
            self.pending_intent_comment = ""
        else:
            self.pending_description = ""
            self.pending_intent_comment = ""
            raise ParseError("Unexpected Node, intent comment should be applied to class or function")
    
    def _parse_module_decl(self, line_num: int) -> ModuleNode:
        """解析模块声明"""
        identifier_token = self._match_token(IbcTokenType.IDENTIFIER)
        
        content = ""
        if self._match_optional_token(IbcTokenType.COLON):
            content = self._collect_until_newline().strip()
        else:
            self._match_optional_token(IbcTokenType.NEWLINE)
        
        node = ModuleNode(
            uid=self._generate_node_uid(),
            node_type=AstNodeType.MODULE,
            line_number=line_num,
            identifier=identifier_token.value,
            content=content
        )
        
        self.ast_nodes[node.uid] = node
        return node
    
    def _parse_var_decl(self, line_num: int) -> VariableNode:
        """解析变量声明"""
        # 收集变量声明内容
        content = self._collect_until_newline().strip()
        
        # 简单解析变量名和描述（以冒号分隔）
        if ':' in content:
            var_parts = content.split(':', 1)
            identifier = var_parts[0].strip()
            external_desc = var_parts[1].strip()
        else:
            identifier = content
            external_desc = ""
        
        node = VariableNode(
            uid=self._generate_node_uid(),
            node_type=AstNodeType.VARIABLE,
            line_number=line_num,
            identifier=identifier,
            content=content,
            external_desc=external_desc
        )
        
        self.ast_nodes[node.uid] = node
        return node
    
    def _parse_func_decl(self, line_num: int) -> FunctionNode:
        """解析函数声明"""
        func_name_token = self._match_token(IbcTokenType.IDENTIFIER)
        
        # 解析参数列表
        self._match_token(IbcTokenType.LPAREN)
        
        params = {}
        # 解析参数直到右括号
        while self._peek_token().type != IbcTokenType.RPAREN:
            param_token = self._consume_token()
            if param_token.type == IbcTokenType.IDENTIFIER:
                param_name = param_token.value
                # 检查是否有参数描述
                if self._match_optional_token(IbcTokenType.COLON):
                    # 收集参数描述直到逗号或右括号
                    desc_parts = []
                    while self._peek_token().type not in [IbcTokenType.COMMA, IbcTokenType.RPAREN, IbcTokenType.EOF]:
                        desc_token = self._consume_token()
                        desc_parts.append(desc_token.value)
                    param_desc = "".join(desc_parts).strip()
                    params[param_name] = param_desc
                else:
                    params[param_name] = ""
                    
                # 如果是逗号，继续下一个参数
                if self._peek_token().type == IbcTokenType.COMMA:
                    self._consume_token()  # 消费逗号
                    
        self._match_token(IbcTokenType.RPAREN)
        self._match_token(IbcTokenType.COLON)
        self._match_token(IbcTokenType.NEWLINE)
        
        node = FunctionNode(
            uid=self._generate_node_uid(),
            node_type=AstNodeType.FUNCTION,
            line_number=line_num,
            identifier=func_name_token.value,
            params=params
        )
        
        self._apply_pending_attributes(node)
        self.ast_nodes[node.uid] = node
        return node
    
    def _parse_class_decl(self, line_num: int) -> ClassNode:
        """解析类声明"""
        class_name_token = self._match_token(IbcTokenType.IDENTIFIER)
        
        # 解析继承关系
        self._match_token(IbcTokenType.LPAREN)
        
        inherit_info = ""
        # 收集继承信息直到右括号
        while self._peek_token().type != IbcTokenType.RPAREN:
            inherit_token = self._consume_token()
            inherit_info += inherit_token.value
            
        self._match_token(IbcTokenType.RPAREN)
        self._match_token(IbcTokenType.COLON)
        self._match_token(IbcTokenType.NEWLINE)
        
        node = ClassNode(
            uid=self._generate_node_uid(),
            node_type=AstNodeType.CLASS,
            line_number=line_num,
            identifier=class_name_token.value,
            params={"inherit": inherit_info.strip()} if inherit_info.strip() else {}
        )
        
        self._apply_pending_attributes(node)
        self.ast_nodes[node.uid] = node
        return node
    
    def _parse_behavior_step(self, line_num: int) -> BehaviorStepNode:
        """解析行为步骤"""
        # 收集整行内容作为行为步骤
        content_parts = []
        while self._peek_token().type not in [IbcTokenType.NEWLINE, IbcTokenType.EOF]:
            token = self._consume_token()
            content_parts.append(token.value)
        content = "".join(content_parts).strip()
        
        # 解析符号引用（$xxx$格式）
        symbol_refs = {}
        parts = content.split('$')
        if len(parts) > 1 and len(parts) % 2 == 1:  # 包含成对的$符号
            for i in range(1, len(parts), 2):
                if parts[i].strip():  # 非空白引用
                    symbol_refs[f"ref_{i//2}"] = parts[i].strip()
        
        node = BehaviorStepNode(
            uid=self._generate_node_uid(),
            node_type=AstNodeType.BEHAVIOR_STEP,
            line_number=line_num,
            content=content,
            symbol_refs=symbol_refs
        )
        
        self.ast_nodes[node.uid] = node
        return node
    
    def _handle_indent(self) -> None:
        """处理缩进"""
        # 获取当前状态和父节点
        if self.state_stack:
            current_state, parent_uid = self.state_stack[-1]
            
            # 根据当前状态决定如何处理缩进
            if current_state == ParserState.TOP_LEVEL:
                # 顶层状态下缩进进入类或函数内容状态
                pass
            elif current_state in [ParserState.CLASS_CONTENT, ParserState.FUNCTION_CONTENT]:
                # 已经在内容状态下再次缩进，可能是嵌套的类或函数
                pass
                
        # 压入新的缩进层级
        self._consume_token()  # 消费INDENT token
    
    def _handle_dedent(self) -> None:
        """处理退格"""
        # 弹出状态栈直到匹配的缩进层级
        if self.state_stack:
            self.state_stack.pop()
            
        self._consume_token()  # 消费DEDENT token
    
    def _handle_special_lines(self) -> bool:
        """处理特殊行（description和intent comment）
        返回True表示处理了特殊行，False表示不是特殊行"""
        token = self._peek_token()
        
        if token.type == IbcTokenType.KEYWORDS and token.value == IbcKeywords.DESCRIPTION.value:
            self._consume_token()  # 消费description关键字
            self._match_token(IbcTokenType.COLON)
            self.pending_description = self._collect_until_newline().strip()
            self._match_optional_token(IbcTokenType.NEWLINE)
            return True
            
        elif token.type == IbcTokenType.INTENT_COMMENT:
            self._consume_token()  # 消费@符号
            self.pending_intent_comment = self._collect_until_newline().strip()
            self._match_optional_token(IbcTokenType.NEWLINE)
            return True
            
        return False
    
    def _handle_keyword_line(self) -> Optional[AstNode]:
        """处理关键字行，返回创建的节点"""
        token = self._peek_token()
        if token.type != IbcTokenType.KEYWORDS:
            return None
            
        self._consume_token()  # 消费关键字
        
        if token.value == IbcKeywords.MODULE.value:
            return self._parse_module_decl(token.line_num)
        elif token.value == IbcKeywords.FUNC.value:
            return self._parse_func_decl(token.line_num)
        elif token.value == IbcKeywords.CLASS.value:
            return self._parse_class_decl(token.line_num)
        elif token.value == IbcKeywords.VAR.value:
            return self._parse_var_decl(token.line_num)
        else:
            # 未知关键字，收集整行内容
            content = self._collect_until_newline()
            self._match_optional_token(IbcTokenType.NEWLINE)
            return None
    
    def _handle_behavior_step(self, parent_uid: str) -> BehaviorStepNode:
        """处理行为步骤"""
        token = self._peek_token()
        node = self._parse_behavior_step(token.line_num)
        node.parent_uid = parent_uid
        self.ast_nodes[node.uid] = node
        
        # 更新父节点的子节点列表
        if parent_uid in self.ast_nodes:
            self.ast_nodes[parent_uid].add_child(node.uid)
            
        self._match_optional_token(IbcTokenType.NEWLINE)
        return node
    
    def parse(self) -> Dict[str, AstNode]:
        """执行语法解析，返回AST节点字典"""
        try:
            # 初始化状态为顶层状态
            self.state_stack.append((ParserState.TOP_LEVEL, ""))
            
            while self.current_token_index < len(self.tokens):
                token = self._peek_token()
                
                if token.type == IbcTokenType.EOF:
                    break
                    
                # 处特殊行（description和intent comment）
                if self._handle_special_lines():
                    continue
                
                # 处理缩进和退格
                if token.type == IbcTokenType.INDENT:
                    self._handle_indent()
                    continue
                elif token.type == IbcTokenType.DEDENT:
                    self._handle_dedent()
                    continue
                
                # 获取当前状态
                current_state, parent_uid = self.state_stack[-1] if self.state_stack else (ParserState.TOP_LEVEL, "")
                
                # 根据当前状态处理不同的token
                if token.type == IbcTokenType.KEYWORDS:
                    node = self._handle_keyword_line()
                    if node:
                        # 设置父节点关系
                        if parent_uid and parent_uid in self.ast_nodes:
                            node.parent_uid = parent_uid
                            self.ast_nodes[parent_uid].add_child(node.uid)
                        
                        # 根据节点类型更新状态
                        if isinstance(node, ClassNode):
                            self.state_stack.append((ParserState.CLASS_CONTENT, node.uid))
                        elif isinstance(node, FunctionNode):
                            self.state_stack.append((ParserState.FUNCTION_CONTENT, node.uid))
                            
                elif token.type == IbcTokenType.INTENT_COMMENT:
                    # 行首的意图注释已经被_handle_special_lines处理
                    # 这里处理其他位置的意图注释（作为行为步骤）
                    self._consume_token()  # 消费@符号
                    node = self._parse_behavior_step(token.line_num)
                    if parent_uid and parent_uid in self.ast_nodes:
                        node.parent_uid = parent_uid
                        self.ast_nodes[parent_uid].add_child(node.uid)
                    self.ast_nodes[node.uid] = node
                    self._match_optional_token(IbcTokenType.NEWLINE)
                    
                elif token.type == IbcTokenType.NEWLINE:
                    self._consume_token()  # 消费换行符
                    
                else:
                    # 普通的行为步骤
                    if current_state in [ParserState.CLASS_CONTENT, ParserState.FUNCTION_CONTENT]:
                        self._handle_behavior_step(parent_uid)
                    else:
                        # 顶层状态下的非关键字行，跳过
                        self._collect_until_newline()
                        self._match_optional_token(IbcTokenType.NEWLINE)
            
            return self.ast_nodes
            
        except ParseError as e:
            print(e)
            return {}
        except Exception as e:
            print(f"!!! Unexpected parsing error: {e}")
            return {}


def parse_ibc_tokens(tokens: List[Token]) -> Dict[str, Dict[str, Any]]:
    """解析IBC tokens并返回AST字典"""
    parser = Parser(tokens)
    nodes = parser.parse()
    
    # 转换为字典格式
    result = {}
    for uid, node in nodes.items():
        result[uid] = node.to_dict()
    
    return result