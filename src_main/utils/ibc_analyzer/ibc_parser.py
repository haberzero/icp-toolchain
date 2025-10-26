from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from typedef.ibc_data_types import (
    IbcTokenType, Token, AstNode, AstNodeType, 
    ModuleNode, ClassNode, FunctionNode, VariableNode, BehaviorStepNode
)

from utils.ibc_analyzer.ibc_parser_state import (
    ParserState, BaseState, TopLevelState, ModuleDeclState, 
    VarDeclState, DescriptionState, IntentCommentState, 
    ClassDeclState, FuncDeclState, BehaviorStepState
)
from utils.ibc_analyzer.ibc_parser_uid_generator import IbcParserUidGenerator


class ParserError(Exception):
    """词法分析器异常"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
    
    def __str__(self):
        return f"ParserError: {self.message}"


class IbcParser:
    """IBC代码解析器"""
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.uid_generator = IbcParserUidGenerator()
        self.state_stack: List[Tuple[ParserState, int]] = [(ParserState.TOP_LEVEL, 0)]  # 栈内容：(状态, 栈顶节点uid)
        self.ast_nodes: Dict[int, AstNode] = {0: AstNode(uid=0, node_type=AstNodeType.DEFAULT)}  # 根节点
        
        # 暂存的特殊行内容
        self.pending_intent_comment = ""
        self.pending_description = ""
        
        # 跟踪上一个AST节点
        self.last_ast_node: Optional[AstNode] = self.ast_nodes[0]

    def _peek_token(self) -> Token:
        """查看当前token"""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(IbcTokenType.EOF, "", -1)
    
    def _consume_token(self) -> Token:
        """消费当前token"""
        token = self._peek_token()
        self.pos += 1
        return token
    
    def _is_at_end(self) -> bool:
        """检查是否到达文件末尾"""
        return self._peek_token().type == IbcTokenType.EOF
    
    def parse(self) -> Dict[int, AstNode]:
        """执行解析"""
        while not self._is_at_end():
            token = self._peek_token()
            
            # 处理缩进变化
            if token.type == IbcTokenType.INDENT:
                self._handle_indent()
                self._consume_token()
                continue
            elif token.type == IbcTokenType.DEDENT:
                self._handle_dedent()
                self._consume_token()
                continue
            
            # 处理关键字
            if token.type == IbcTokenType.KEYWORDS:
                self._handle_keyword(token)
                self._consume_token()
                continue
                
            # 将token传递给当前状态机处理
            self._process_token_in_current_state(token)
            self._consume_token()
            
        return self.ast_nodes
    
    def _handle_indent(self) -> None:
        """处理缩进"""
        # 根据最新的AST节点判断应该压入的状态
        if isinstance(self.last_ast_node, ClassNode):
            self.state_stack.append((ParserState.CLASS_CONTENT, self.last_ast_node.uid))

        elif isinstance(self.last_ast_node, FunctionNode):
            self.state_stack.append((ParserState.FUNC_CONTENT, self.last_ast_node.uid))

        elif isinstance(self.last_ast_node, BehaviorStepNode):
            if self.state_stack[-1] is not ParserState.FUNC_CONTENT:  # 行为步骤块
                raise ParserError("Line {token.line_num}: Behavior step must be inside a function")

            if self.last_ast_node.new_block_flag:
                self.state_stack.append((ParserState.FUNC_CONTENT, self.last_ast_node.uid))
            else:
                raise ParserError("Line {token.line_num}: Invalid indent, missing colon after behavior step to start a new block")

    def _handle_dedent(self) -> None:
        """处理退格"""
        if len(self.state_stack) > 1:  # 不能弹出顶层状态
            self.state_stack.pop()
        else:
            raise ParserError("Line {token.line_num}: pop state toplevel, check your code please")

    def _handle_keyword(self, token: Token) -> None:
        """处理关键字"""
        current_state, parent_uid = self.state_stack[-1]
        
        # 检查关键字在当前位置是否合法
        if token.value == "module" and current_state != ParserState.TOP_LEVEL:
            raise ParserError(f"Line {token.line_num}: 'module' keyword only allowed at top level")
        
        # 根据关键字类型压入相应的状态机
        if token.type == IbcTokenType.KEYWORDS and token.value == "module":
            state_obj = ModuleDeclState(parent_uid, self.uid_generator)
            self.state_stack.append((ParserState.MODULE_DECL, parent_uid))
        elif token.type == IbcTokenType.KEYWORDS and token.value == "var":
            state_obj = VarDeclState(parent_uid, self.uid_generator)
            self.state_stack.append((ParserState.VAR_DECL, parent_uid))
        elif token.type == IbcTokenType.KEYWORDS and token.value == "description":
            state_obj = DescriptionState(parent_uid, self.uid_generator)
            self.state_stack.append((ParserState.DESCRIPTION, parent_uid))
        elif token.type == IbcTokenType.KEYWORDS and token.value == "class":
            state_obj = ClassDeclState(parent_uid, self.uid_generator)
            self.state_stack.append((ParserState.CLASS_DECL, parent_uid))
        elif token.type == IbcTokenType.KEYWORDS and token.value == "func":
            state_obj = FuncDeclState(parent_uid, self.uid_generator)
            self.state_stack.append((ParserState.FUNC_DECL, parent_uid))
        elif token.type == IbcTokenType.INTENT_COMMENT:
            state_obj = IntentCommentState(parent_uid, self.uid_generator)
            self.state_stack.append((ParserState.INTENT_COMMENT, parent_uid))
    
    def _process_token_in_current_state(self, token: Token) -> None:
        """将token传递给当前状态机处理"""
        if not self.state_stack:
            raise ParserError(f"Line {token.line_num}: No state in stack")
            
        current_state_type, parent_uid = self.state_stack[-1]
        
        # 创建对应的状态对象
        state_obj = self._create_state_object(current_state_type, parent_uid)
        
        # 处理token
        state_obj.process_token(token, self.ast_nodes)
        
        # 更新last_ast_node
        # 查找最新添加的节点
        if self.ast_nodes:
            max_uid = max(self.ast_nodes.keys())
            self.last_ast_node = self.ast_nodes[max_uid]
        
        # 检查是否需要弹出状态
        if state_obj.is_pop_state():
            popped_state = self.state_stack.pop()
            
            # 如果是描述或意图注释状态，暂存内容
            if popped_state[0] == ParserState.DESCRIPTION and isinstance(state_obj, DescriptionState):
                self.pending_description = state_obj.get_content()
            elif popped_state[0] == ParserState.INTENT_COMMENT and isinstance(state_obj, IntentCommentState):
                self.pending_intent_comment = state_obj.get_content()
    
    def _create_state_object(self, state_type: ParserState, parent_uid: int) -> BaseState:
        """创建状态对象"""
        if state_type == ParserState.TOP_LEVEL:
            return TopLevelState(parent_uid, self.uid_generator)
        elif state_type == ParserState.MODULE_DECL:
            return ModuleDeclState(parent_uid, self.uid_generator)
        elif state_type == ParserState.VAR_DECL:
            return VarDeclState(parent_uid, self.uid_generator)
        elif state_type == ParserState.DESCRIPTION:
            return DescriptionState(parent_uid, self.uid_generator)
        elif state_type == ParserState.INTENT_COMMENT:
            return IntentCommentState(parent_uid, self.uid_generator)
        elif state_type == ParserState.CLASS_DECL:
            return ClassDeclState(parent_uid, self.uid_generator)
        elif state_type == ParserState.FUNC_DECL:
            return FuncDeclState(parent_uid, self.uid_generator)
        elif state_type == ParserState.BEHAVIOR_STEP:
            return BehaviorStepState(parent_uid, self.uid_generator)
        else:
            # 默认返回顶层状态
            return TopLevelState(parent_uid, self.uid_generator)