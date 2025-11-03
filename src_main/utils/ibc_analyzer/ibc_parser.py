from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from typedef.ibc_data_types import (
    IbcTokenType, Token, AstNode, AstNodeType, 
    ModuleNode, ClassNode, FunctionNode, VariableNode, BehaviorStepNode
)

from utils.ibc_analyzer.ibc_parser_state import (
    ParserState, BaseState, TopLevelState, ModuleDeclState, 
    VarDeclState, DescriptionState, ClassContentState, FuncContentState,
    ClassDeclState, FuncDeclState, BehaviorStepState, IntentCommentState
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
        self.line_num = 0
        # 修改state_stack为直接存储状态机实例，而不是ParserState枚举
        self.state_stack: List[Tuple[BaseState, int]] = [(TopLevelState(0, self.uid_generator), 0)]  # 栈内容：(状态机实例, 栈顶节点uid)
        self.ast_nodes: Dict[int, AstNode] = {0: AstNode(uid=0, node_type=AstNodeType.DEFAULT)}  # 根节点
        
        # 暂存的特殊行内容
        self.pending_intent_comment = ""
        self.pending_description = ""
        
        # 跟踪上一个AST节点
        self.last_ast_node: Optional[AstNode] = self.ast_nodes[0]
        self.last_ast_node_uid = 0

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
        try:
            while not self._is_at_end():
                token = self._consume_token()
                self.line_num = token.line_num
                # 处理缩进变化（目前逻辑有缺陷，应该统一给状态机逻辑处理，以提高统一性并且增强灵活性。现在的实现纯为了偷懒）
                if token.type == IbcTokenType.INDENT:
                    self._handle_indent()
                    continue
                elif token.type == IbcTokenType.DEDENT:
                    self._handle_dedent()
                    continue

                # 处理关键字。注意所有行包括行为步骤行都有起始的关键字，步骤行的关键字由Lexer自动添加
                if token.type == IbcTokenType.KEYWORDS:
                    self._handle_keyword(token)
                    continue
                
                # 将token传递给当前状态机处理
                self._process_token_in_current_state(token)
                
                # 检查是否需要弹出状态
                current_state_obj, _ = self.state_stack[-1]
                if not current_state_obj.is_need_pop():
                    continue
                self.state_stack.pop()
                
                # 如果是描述暂存内容
                if isinstance(current_state_obj, DescriptionState):
                    self.pending_description = current_state_obj.get_content()
                if isinstance(current_state_obj, IntentCommentState):
                    self.pending_intent_comment = current_state_obj.get_content()
                
            return self.ast_nodes
        
        except ParserError:
            raise ParserError(f"Line {self.line_num}: Parse error")
    
    def _handle_indent(self) -> None:
        """处理缩进"""
        # 根据最新的AST节点判断应该压入的状态
        token = self._peek_token()
        if isinstance(self.last_ast_node, ClassNode):
            state_obj = ClassContentState(self.last_ast_node.uid, self.uid_generator)
            self.state_stack.append((state_obj, self.last_ast_node.uid))

        elif isinstance(self.last_ast_node, FunctionNode):
            state_obj = FuncContentState(self.last_ast_node.uid, self.uid_generator)
            self.state_stack.append((state_obj, self.last_ast_node.uid))

        elif isinstance(self.last_ast_node, BehaviorStepNode):
            if not isinstance(self.state_stack[-1][0], (FuncContentState, BehaviorStepState)):
                raise ParserError(f"Line {token.line_num}: Behavior step must be inside a function")

            if self.last_ast_node.new_block_flag:
                state_obj = FuncContentState(self.last_ast_node.uid, self.uid_generator)
                self.state_stack.append((state_obj, self.last_ast_node.uid))
            else:
                raise ParserError(f"Line {token.line_num}: Invalid indent, missing colon after behavior step to start a new block")

    def _handle_dedent(self) -> None:
        """处理退格"""
        token = self._peek_token()
        if len(self.state_stack) > 1:  # 不能弹出顶层状态
            self.state_stack.pop()
        else:
            raise ParserError(f"Line {token.line_num}: pop state toplevel, check your code please")

    def _handle_keyword(self, token: Token) -> None:
        """处理关键字"""
        current_state_obj, parent_uid = self.state_stack[-1]
        current_state_type = current_state_obj.state_type
        
        # 检查关键字在当前位置是否合法
        if token.value == "module" and current_state_type != ParserState.TOP_LEVEL:
            raise ParserError(f"Line {token.line_num}: 'module' keyword only allowed at top level")
        
        # 根据关键字类型压入相应的状态
        state_obj = None
        if token.type == IbcTokenType.KEYWORDS and token.value == "module":
            state_obj = ModuleDeclState(parent_uid, self.uid_generator)
        elif token.type == IbcTokenType.KEYWORDS and token.value == "var":
            state_obj = VarDeclState(parent_uid, self.uid_generator)
        elif token.type == IbcTokenType.KEYWORDS and token.value == "description":
            state_obj = DescriptionState(parent_uid, self.uid_generator)
        elif token.type == IbcTokenType.KEYWORDS and token.value == "class":
            state_obj = ClassDeclState(parent_uid, self.uid_generator)
        elif token.type == IbcTokenType.KEYWORDS and token.value == "func":
            state_obj = FuncDeclState(parent_uid, self.uid_generator)
        elif token.type == IbcTokenType.KEYWORDS and token.value == "behavior":
            state_obj = BehaviorStepState(parent_uid, self.uid_generator)
        elif token.type == IbcTokenType.KEYWORDS and token.value == "@":
            state_obj = IntentCommentState(parent_uid, self.uid_generator)
        else:
            raise ParserError(f"Line {token.line_num}: Invalid keyword token'{token.value}', check your code please")
            
        if state_obj:
            self.state_stack.append((state_obj, parent_uid))
    
    def _process_token_in_current_state(self, token: Token) -> None:
        """将token传递给当前状态机处理"""
        if not self.state_stack:
            raise ParserError(f"Line {token.line_num}: No state in stack")
            
        # 获取栈顶的状态机实例
        current_state_obj, parent_uid = self.state_stack[-1]
        
        # 状态机实例处理token
        # TODO: 现在的process_token方法 不应该传递进去ast_nodes，这个变量应该在状态机实例创建时就被传递，以后改一下
        current_state_obj.process_token(token, self.ast_nodes)

        # 检查是否存在uid的更新
        current_uid = self.uid_generator.get_current_uid()
        if current_uid > self.last_ast_node_uid:
            self.last_ast_node_uid = current_uid
            self.last_ast_node = self.ast_nodes[current_uid]
            # 如果是类声明或函数声明节点，附加对外描述和意图注释
            if isinstance(self.last_ast_node, (ClassNode, FunctionNode)):
                self.last_ast_node.external_desc = self.pending_description
                self.last_ast_node.intent_comment = self.pending_intent_comment
                self.pending_description = ""
                self.pending_intent_comment = ""
            else:
                self.pending_description = ""
                self.pending_intent_comment = ""
