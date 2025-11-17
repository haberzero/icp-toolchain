from enum import Enum
from turtle import Turtle
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
        self.ast_nodes: Dict[int, AstNode] = {0: AstNode(uid=0, node_type=AstNodeType.DEFAULT)}  # 根节点
        self.state_stack: List[Tuple[BaseState, int]] = [(TopLevelState(0, self.uid_generator, self.ast_nodes), 0)]  # 栈内容：(状态机实例, 栈顶节点uid)
        
        # 暂存的特殊行内容
        self.pending_intent_comment = ""
        self.pending_description = ""
        
        # 跟踪上一个AST节点
        self.last_ast_node: Optional[AstNode] = self.ast_nodes[0]
        self.last_ast_node_uid = 0

        # 状态变量，指示当前token应该被如何处理
        self.is_pass_token_to_state = False
        self.is_new_line_start = False

        # 函数声明时的多行参数定义可能会因为不同开发者的书写习惯带来额外的缩进问题，需要单独处理
        self.func_pending_indent_level = 0
        
        # 延续行状态：需要吸收的DEDENT数量和是否需要创建新代码块
        self.continuation_dedent_to_absorb = 0  # 需要吸收的DEDENT数量
        self.continuation_needs_new_block = False  # 是否需要在吸收完DEDENT后创建新代码块

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

                # 将包括缩进的所有token都交给状态机，给状态机提供多行处理的能力
                if self.is_pass_token_to_state:
                    self._process_token_in_current_state(token)

                # 处理缩进和状态栈
                elif token.type == IbcTokenType.INDENT:
                    self._handle_indent(token)
                elif token.type == IbcTokenType.DEDENT:
                    self._handle_dedent(token)

                # 处理关键字(目前关键字只会在行首出现)
                elif token.type == IbcTokenType.KEYWORDS:
                    self._handle_keyword(token)
                
                # token处在行首，且不是关键字，且并非透传token的状态，则认为是行为描述行的开始
                elif self.is_new_line_start and token.type is not IbcTokenType.KEYWORDS:
                    self.is_new_line_start = False
                    current_state_obj, parent_uid = self.state_stack[-1]
                    state_obj = BehaviorStepState(parent_uid, self.uid_generator, self.ast_nodes)
                    self.state_stack.append((state_obj, parent_uid))
                    self._process_token_in_current_state(token)
                
                # 将token传递给当前状态机处理
                else:
                    self._process_token_in_current_state(token)

                # --- token已经被使用，开始状态机的后处理 ---
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

                # 获取顶部状态机实例
                current_state_obj, _ = self.state_stack[-1]

                # 状态变量的更新
                # 栈顶状态机是否请求了token透传
                if current_state_obj.is_need_pass_in_token():
                    self.is_pass_token_to_state = True
                else:
                    self.is_pass_token_to_state = False
                
                # 当出现了 新行/缩进/退缩进 以外的任何token, 则意味着随后的token不处于行首
                if token.type in (IbcTokenType.NEWLINE, IbcTokenType.INDENT, IbcTokenType.DEDENT):
                    self.is_new_line_start = True
                else:
                    self.is_new_line_start = False
                
                # 检查是否需要弹出状态
                if not current_state_obj.is_need_pop():
                    continue
                else:
                    # 状态机弹出
                    current_state_obj, _ = self.state_stack.pop()
                    
                    # 进行内容暂存处理
                    if isinstance(current_state_obj, DescriptionState):
                        self.pending_description = current_state_obj.get_content()
                    if isinstance(current_state_obj, IntentCommentState):
                        self.pending_intent_comment = current_state_obj.get_content()
                    
                    # 函数声明时的多行参数定义可能会因为不同开发者的书写习惯带来额外的缩进问题，需要单独处理
                    if isinstance(current_state_obj, FuncDeclState):
                        self.func_pending_indent_level = current_state_obj.get_pending_indent_level()
                    
                    # 处理从延续行模式弹出的BehaviorStepState
                    if isinstance(current_state_obj, BehaviorStepState):
                        if current_state_obj.has_entered_continuation_mode():
                            # 获取局部缩进等级
                            local_indent = current_state_obj.get_local_indent_level()
                            
                            # 检查是否需要创建新代码块
                            if isinstance(self.last_ast_node, BehaviorStepNode) and self.last_ast_node.new_block_flag:
                                # 需要创建新代码块
                                if local_indent == 0:
                                    # 局部缩进为0，后续正常INDENT压栈即可
                                    pass
                                elif local_indent == 1:
                                    # 局部缩进为1，需要标记手工压栈
                                    self.continuation_needs_new_block = True
                                elif local_indent > 1:
                                    # 局部缩进>1，需要吸收(local_indent-1)次DEDENT后手工压栈
                                    self.continuation_dedent_to_absorb = local_indent - 1
                                    self.continuation_needs_new_block = True
                            else:
                                # 不需要创建新代码块，吸收所有局部缩进的DEDENT
                                if local_indent > 0:
                                    self.continuation_dedent_to_absorb = local_indent
                
                # 当 func_pending_indent_level == 1 时, 意味着后续内容开始时不再会有indent token, 这里需要一次手动压栈
                if self.func_pending_indent_level == 1:
                    self.func_pending_indent_level = 0
                    if isinstance(self.last_ast_node, FunctionNode):
                        state_obj = FuncContentState(self.last_ast_node.uid, self.uid_generator, self.ast_nodes)
                        self.state_stack.append((state_obj, self.last_ast_node.uid))
                    else:
                        raise ParserError(f"Line {token.line_num}: Parser TOP --- Should not happen, contact dev please")
                
                # 处理延续行后需要手工压栈的情况
                if self.continuation_needs_new_block:
                    self.continuation_needs_new_block = False
                    if isinstance(self.last_ast_node, BehaviorStepNode):
                        state_obj = FuncContentState(self.last_ast_node.uid, self.uid_generator, self.ast_nodes)
                        self.state_stack.append((state_obj, self.last_ast_node.uid))
                    else:
                        raise ParserError(f"Line {token.line_num}: Parser TOP --- continuation_needs_new_block should only be set for BehaviorStepNode")
                
            return self.ast_nodes
        
        except ParserError:
            raise ParserError(f"Line {self.line_num}: Parse error")
    
    def _handle_indent(self, token: Token) -> None:
        """处理缩进"""
        # 根据最新的AST节点判断应该压入的状态
        if isinstance(self.last_ast_node, ClassNode):
            state_obj = ClassContentState(self.last_ast_node.uid, self.uid_generator, self.ast_nodes)
            self.state_stack.append((state_obj, self.last_ast_node.uid))

        elif isinstance(self.last_ast_node, FunctionNode):
            state_obj = FuncContentState(self.last_ast_node.uid, self.uid_generator, self.ast_nodes)
            self.state_stack.append((state_obj, self.last_ast_node.uid))

        elif isinstance(self.last_ast_node, BehaviorStepNode):
            if not isinstance(self.state_stack[-1][0], (FuncContentState, BehaviorStepState)):
                raise ParserError(f"Line {token.line_num}: Behavior step must be inside a function")

            if self.last_ast_node.new_block_flag:
                state_obj = FuncContentState(self.last_ast_node.uid, self.uid_generator, self.ast_nodes)
                self.state_stack.append((state_obj, self.last_ast_node.uid))
            else:
                raise ParserError(f"Line {token.line_num}: Invalid indent, missing colon after behavior step to start a new block")

    def _handle_dedent(self, token: Token) -> None:
        """处理退格"""
        if self.func_pending_indent_level > 1:
            # 此变量大于1意味着状态机刚弹出一个func decl, 在行为行开始前需要额外退缩进
            self.func_pending_indent_level -= 1
            return
        
        # 如果需要吸收DEDENT（延续行弹出后的局部缩进处理）
        if self.continuation_dedent_to_absorb > 0:
            self.continuation_dedent_to_absorb -= 1
            return

        if len(self.state_stack) > 1:  # 不能弹出顶层状态
            self.state_stack.pop()
        else:
            raise ParserError(f"Line {token.line_num}: pop state toplevel, should not happen, contact dev please")

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
            state_obj = ModuleDeclState(parent_uid, self.uid_generator, self.ast_nodes)
        elif token.type == IbcTokenType.KEYWORDS and token.value == "var":
            state_obj = VarDeclState(parent_uid, self.uid_generator, self.ast_nodes)
        elif token.type == IbcTokenType.KEYWORDS and token.value == "description":
            state_obj = DescriptionState(parent_uid, self.uid_generator, self.ast_nodes)
        elif token.type == IbcTokenType.KEYWORDS and token.value == "class":
            state_obj = ClassDeclState(parent_uid, self.uid_generator, self.ast_nodes)
        elif token.type == IbcTokenType.KEYWORDS and token.value == "func":
            state_obj = FuncDeclState(parent_uid, self.uid_generator, self.ast_nodes)
        elif token.type == IbcTokenType.KEYWORDS and token.value == "@":
            state_obj = IntentCommentState(parent_uid, self.uid_generator, self.ast_nodes)
        else:
            raise ParserError(f"Line {token.line_num}: Invalid keyword token'{token.value}', should not happen, contact dev please")
            
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
        current_state_obj.process_token(token)

