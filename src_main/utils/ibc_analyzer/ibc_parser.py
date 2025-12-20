from enum import Enum
from typing import List, Dict, Any, Optional, Tuple, Callable
from typedef.ibc_data_types import (
    IbcTokenType, Token, IbcBaseAstNode, AstNodeType, 
    ModuleNode, ClassNode, FunctionNode, VariableNode, BehaviorStepNode,
    VisibilityTypes
)
from typedef.exception_types import IbcParserError

from utils.ibc_analyzer.ibc_parser_state import (
    ParserState, BaseState, TopLevelState, ModuleDeclState, 
    VarDeclState, DescriptionState, ClassContentState, FuncContentState,
    ClassDeclState, FuncDeclState, BehaviorStepState, IntentCommentState,
    VisibilityDeclState
)

from utils.ibc_analyzer.ibc_parser_uid_generator import IbcParserUidGenerator


# TODO: 目前设计模式不完善，后处理也许应该整合到整个状态处理逻辑里，不应该零散分布。
class ParserMainState(Enum):
    """Parser主循环状态枚举"""
    PASS_THROUGH_MODE = "PASS_THROUGH_MODE"  # token透传模式
    INDENT_PROCESSING = "INDENT_PROCESSING"  # 缩进处理
    DEDENT_PROCESSING = "DEDENT_PROCESSING"  # 退缩进处理
    KEYWORD_PROCESSING = "KEYWORD_PROCESSING"  # 关键字处理
    BEHAVIOR_START = "BEHAVIOR_START"  # 行为步骤开始
    NORMAL_PROCESSING = "NORMAL_PROCESSING"  # 常规处理


class IbcParser:
    """IBC代码解析器"""
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.uid_generator = IbcParserUidGenerator()
        self.line_num = 0
        # 修改state_stack为直接存储状态机实例，而不是ParserState枚举
        self.ast_nodes: Dict[int, IbcBaseAstNode] = {0: IbcBaseAstNode(uid=0, node_type=AstNodeType.DEFAULT)}  # 根节点
        self.state_stack: List[Tuple[BaseState, int]] = [(TopLevelState(0, self.uid_generator, self.ast_nodes), 0)]  # 栈内容：(状态机实例, 栈顶节点uid)
        
        # 暂存的特殊行内容
        self.pending_intent_comment = ""
        self.pending_description = ""
        
        # 跟踪上一个AST节点
        self.last_ast_node: Optional[IbcBaseAstNode] = self.ast_nodes[0]
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

    def _determine_main_state(self, token: Token) -> ParserMainState:
        """根据token和当前状态，决定处理模式"""
        # 优先级最高：token透传模式
        if self.is_pass_token_to_state:
            return ParserMainState.PASS_THROUGH_MODE
        
        # 处理缩进
        if token.type == IbcTokenType.INDENT:
            return ParserMainState.INDENT_PROCESSING
        
        # 处理退缩进
        if token.type == IbcTokenType.DEDENT:
            return ParserMainState.DEDENT_PROCESSING
        
        # 处理关键字
        if token.type == IbcTokenType.KEYWORDS:
            return ParserMainState.KEYWORD_PROCESSING
        
        # token处在行首，且不是关键字、不是NEWLINE，则认为是行为描述行的开始
        if self.is_new_line_start and token.type not in (IbcTokenType.KEYWORDS, IbcTokenType.NEWLINE):
            return ParserMainState.BEHAVIOR_START
        
        # 其他情况，常规处理
        return ParserMainState.NORMAL_PROCESSING
    
    def _execute_token_processing(self, token: Token, main_state: ParserMainState) -> None:
        """执行token处理逻辑"""
        if main_state == ParserMainState.PASS_THROUGH_MODE:
            self._process_token_in_current_state(token)
        
        elif main_state == ParserMainState.INDENT_PROCESSING:
            self._handle_indent(token)
        
        elif main_state == ParserMainState.DEDENT_PROCESSING:
            self._handle_dedent(token)
        
        elif main_state == ParserMainState.KEYWORD_PROCESSING:
            self._handle_keyword(token)
        
        elif main_state == ParserMainState.BEHAVIOR_START:
            self._handle_behavior_start(token)
        
        elif main_state == ParserMainState.NORMAL_PROCESSING:
            self._process_token_in_current_state(token)
    
    def _post_process_token(self, token: Token) -> None:
        """处理token后的后处理逻辑"""
        # 检查是否存在uid的更新
        current_uid = self.uid_generator.get_current_uid()
        if current_uid > self.last_ast_node_uid:
            self._update_last_ast_node(current_uid)
        
        # 获取顶部状态机实例
        current_state_obj, _ = self.state_stack[-1]
        
        # 更新token透传标志
        self._update_pass_token_flag(current_state_obj)
        
        # 更新行首标志
        self._update_new_line_flag(token)
        
        # 检查是否需要弹出状态
        if current_state_obj.is_need_pop():
            self._handle_state_pop(current_state_obj, token)
    
    def _update_last_ast_node(self, current_uid: int) -> None:
        """更新最后AST节点并附加描述信息和可见性"""
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
        
        # 统一处理可见性
        self._apply_visibility_to_node(self.last_ast_node)
    
    def _apply_visibility_to_node(self, node: IbcBaseAstNode) -> None:
        """为节点附加可见性"""
        # 处理类节点的可见性
        if isinstance(node, ClassNode):
            # 递归查找父节点，确定是顶层类、类内类还是函数内类
            parent_context = self._find_parent_context(node.parent_uid)
            
            if parent_context == 'top':
                # 顶层类，必须是public
                node.visibility = VisibilityTypes.PUBLIC
            elif parent_context == 'class':
                # 类内类，使用当前类内可见性
                for state_obj, _ in reversed(self.state_stack):
                    if isinstance(state_obj, ClassContentState):
                        node.visibility = state_obj.get_current_visibility()
                        break
            elif parent_context == 'func':
                # 函数内类，必须是private
                node.visibility = VisibilityTypes.PRIVATE
        
        # 处理函数节点的可见性
        elif isinstance(node, FunctionNode):
            # 递归查找父节点，确定是顶层函数、类内函数还是函数内函数
            parent_context = self._find_parent_context(node.parent_uid)
            
            if parent_context == 'top':
                # 顶层函数，默认public
                node.visibility = VisibilityTypes.PUBLIC
            elif parent_context == 'class':
                # 类内函数，使用当前类内可见性
                for state_obj, _ in reversed(self.state_stack):
                    if isinstance(state_obj, ClassContentState):
                        node.visibility = state_obj.get_current_visibility()
                        break
            elif parent_context == 'func':
                # 函数内函数，必须是private
                node.visibility = VisibilityTypes.PRIVATE
        
        # 处理变量节点的可见性
        elif isinstance(node, VariableNode):
            # 变量只能在类内定义，使用当前类内可见性
            for state_obj, _ in reversed(self.state_stack):
                if isinstance(state_obj, ClassContentState):
                    node.visibility = state_obj.get_current_visibility()
                    break
    
    def _find_parent_context(self, parent_uid: int) -> str:
        """
        递归查找父节点上下文，返回 'top', 'class', 或 'func'
        
        查找规则：
        - 向上递归查找父节点
        - 如果遇到函数节点，返回 'func'
        - 如果遇到类节点，继续向上递归
        - 如果递归到根节点（uid=0），返回 'top' 或 'class'
        """
        current_uid = parent_uid
        
        while current_uid != 0:
            parent_node = self.ast_nodes.get(current_uid)
            
            if parent_node is None:
                # 找不到父节点，返回top
                return 'top'
            
            if isinstance(parent_node, FunctionNode):
                # 遇到函数节点，说明是函数内定义
                return 'func'
            elif isinstance(parent_node, ClassNode):
                # 遇到类节点，继续向上递归
                current_uid = parent_node.parent_uid
            else:
                # 遇到其他节点（如BehaviorStepNode），继续向上
                current_uid = parent_node.parent_uid
        
        # 递归到根节点，检查是否在类内
        # 通过检查parent_uid是否指向一个类节点
        if parent_uid != 0:
            immediate_parent = self.ast_nodes.get(parent_uid)
            if isinstance(immediate_parent, ClassNode):
                return 'class'
        
        return 'top'
    
    def _update_pass_token_flag(self, current_state_obj: BaseState) -> None:
        """更新token透传标志"""
        self.is_pass_token_to_state = current_state_obj.is_need_pass_in_token()
    
    def _update_new_line_flag(self, token: Token) -> None:
        """更新行首标志"""
        if token.type == IbcTokenType.NEWLINE:
            self.is_new_line_start = True
        elif token.type in (IbcTokenType.INDENT, IbcTokenType.DEDENT):
            # INDENT和DEDENT不改变行首状态，因为它们只是缩进标记
            # 真正的内容token会在后续出现
            pass
        else:
            self.is_new_line_start = False
    
    def _handle_state_pop(self, current_state_obj: BaseState, token: Token) -> None:
        """处理状态机弹出逻辑"""
        # 弹出状态机
        self.state_stack.pop()
        
        # 进行内容暂存处理
        if isinstance(current_state_obj, DescriptionState):
            self.pending_description = current_state_obj.get_content()
        
        if isinstance(current_state_obj, IntentCommentState):
            self.pending_intent_comment = current_state_obj.get_content()
        
        # 处理可见性声明弹出，更新ClassContentState的当前可见性
        if isinstance(current_state_obj, VisibilityDeclState):
            if self.state_stack:  # 确保栈不为空
                parent_state_obj, _ = self.state_stack[-1]
                if isinstance(parent_state_obj, ClassContentState):
                    visibility = current_state_obj.get_visibility_type()
                    parent_state_obj.set_current_visibility(visibility)
        
        # 函数声明时的多行参数定义可能会因为不同开发者的书写习惯带来额外的缩进问题，需要单独处理
        if isinstance(current_state_obj, FuncDeclState):
            self.func_pending_indent_level = current_state_obj.get_pending_indent_level()
        
        # 处理从延续行模式弹出的BehaviorStepState
        if isinstance(current_state_obj, BehaviorStepState):
            self._handle_behavior_continuation_pop(current_state_obj)
    
    def _handle_behavior_continuation_pop(self, behavior_state: BehaviorStepState) -> None:
        """处理行为步骤延续行弹出逻辑"""
        if not behavior_state.has_entered_continuation_mode():
            return
        
        # 获取局部缩进等级
        local_indent = behavior_state.get_local_indent_level()
        
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
    
    def _handle_post_pop_actions(self, token: Token) -> None:
        """处理状态机弹出后的额外动作"""
        # 当 func_pending_indent_level == 1 时, 意味着后续内容开始时不再会有indent token, 这里需要一次手动压栈
        if self.func_pending_indent_level == 1:
            self.func_pending_indent_level = 0
            if isinstance(self.last_ast_node, FunctionNode):
                state_obj = FuncContentState(self.last_ast_node.uid, self.uid_generator, self.ast_nodes)
                self.state_stack.append((state_obj, self.last_ast_node.uid))
            else:
                raise IbcParserError(
                    message="Parser TOP --- Should not happen, contact dev please",
                    line_num=token.line_num
                )
        
        # 处理延续行后需要手工压栈的情况
        if self.continuation_needs_new_block:
            self.continuation_needs_new_block = False
            if isinstance(self.last_ast_node, BehaviorStepNode):
                state_obj = FuncContentState(self.last_ast_node.uid, self.uid_generator, self.ast_nodes)
                self.state_stack.append((state_obj, self.last_ast_node.uid))
            else:
                raise IbcParserError(
                    message="Parser TOP --- continuation_needs_new_block should only be set for BehaviorStepNode",
                    line_num=token.line_num
                )
    
    def _handle_behavior_start(self, token: Token) -> None:
        """处理行为步骤开始"""
        self.is_new_line_start = False
        current_state_obj, parent_uid = self.state_stack[-1]
        state_obj = BehaviorStepState(parent_uid, self.uid_generator, self.ast_nodes)
        self.state_stack.append((state_obj, parent_uid))
        self._process_token_in_current_state(token)
    
    def parse(self) -> Dict[int, IbcBaseAstNode]:
        """执行解析"""
        while not self._is_at_end():
            token = self._consume_token()
            self.line_num = token.line_num

            # 阶段1：决定当前token应该被如何处理
            main_state = self._determine_main_state(token)
            
            # 阶段2：执行token处理
            self._execute_token_processing(token, main_state)
            
            # 阶段3：token后处理
            self._post_process_token(token)
            
            # 阶段4：处理状态机弹出后的额外动作
            self._handle_post_pop_actions(token)
            
        return self.ast_nodes
    
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
            # 行为步骤后的缩进：允许在函数内或顶层
            current_state_obj = self.state_stack[-1][0]
            # 允许在FuncContentState、TopLevelState或BehaviorStepState中
            if not isinstance(current_state_obj, (FuncContentState, TopLevelState, BehaviorStepState)):
                raise IbcParserError(
                    message="Behavior step can only be inside a function or at top level",
                    line_num=token.line_num
                )

            if self.last_ast_node.new_block_flag:
                # 根据当前状态决定压入的父节点
                if isinstance(current_state_obj, TopLevelState):
                    # 顶层行为步骤后的代码块，父节点是当前behavior节点
                    state_obj = TopLevelState(self.last_ast_node.uid, self.uid_generator, self.ast_nodes)
                else:
                    # 函数内的行为步骤后的代码块
                    state_obj = FuncContentState(self.last_ast_node.uid, self.uid_generator, self.ast_nodes)
                self.state_stack.append((state_obj, self.last_ast_node.uid))
            else:
                raise IbcParserError(
                    message="Invalid indent, missing colon after behavior step to start a new block",
                    line_num=token.line_num
                )

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
            raise IbcParserError(
                message="pop state toplevel, should not happen, contact dev please",
                line_num=token.line_num
            )

    def _handle_keyword(self, token: Token) -> None:
        """处理关键字"""
        current_state_obj, parent_uid = self.state_stack[-1]
        current_state_type = current_state_obj.state_type
        
        # 检查关键字在当前位置是否合法
        if token.value == "module" and current_state_type != ParserState.TOP_LEVEL:
            raise IbcParserError(
                message="'module' keyword only allowed at top level",
                line_num=token.line_num
            )
        
        # 可见性关键字只允许在类内容中使用
        if token.value in ("public", "protected", "private"):
            if current_state_type != ParserState.CLASS_CONTENT:
                raise IbcParserError(
                    message=f"Visibility keyword '{token.value}' only allowed inside class definition",
                    line_num=token.line_num
                )
        
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
        elif token.type == IbcTokenType.KEYWORDS and token.value in ("public", "protected", "private"):
            state_obj = VisibilityDeclState(parent_uid, self.uid_generator, self.ast_nodes)
            state_obj.set_visibility_keyword(token.value)
        else:
            raise IbcParserError(
                message=f"Invalid keyword token'{token.value}', should not happen, contact dev please",
                line_num=token.line_num
            )
            
        if state_obj:
            self.state_stack.append((state_obj, parent_uid))
    
    def _process_token_in_current_state(self, token: Token) -> None:
        """将token传递给当前状态机处理"""
        if not self.state_stack:
            raise IbcParserError(
                message="No state in stack",
                line_num=token.line_num
            )
            
        # 获取栈顶的状态机实例
        current_state_obj, parent_uid = self.state_stack[-1]
        
        # 状态机实例处理token
        current_state_obj.process_token(token)

