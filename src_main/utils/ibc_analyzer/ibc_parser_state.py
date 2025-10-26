from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from typedef.ibc_data_types import (
    IbcTokenType, Token, AstNode, AstNodeType, 
    ModuleNode, ClassNode, FunctionNode, VariableNode, BehaviorStepNode
)

from utils.ibc_analyzer.ibc_parser_uid_generator import IbcParserUidGenerator


class ParserState(Enum):
    """解析器状态枚举"""
    BASE_STATE = "BASE_STATE"  # 默认状态，不起作用，仅占位
    TOP_LEVEL = "TOP_LEVEL"  # 顶层状态
    MODULE_DECL = "MODULE_DECL"  # 模块声明解析
    VAR_DECL = "VAR_DECL"  # 变量声明解析
    DESCRIPTION = "DESCRIPTION"  # 对外描述解析
    INTENT_COMMENT = "INTENT_COMMENT"  # 意图注释解析
    CLASS_DECL = "CLASS_DECL"  # 类声明解析
    CLASS_CONTENT = "CLASS_CONTENT"  # 类内容解析, 没有对应状态机, 主要在主循环中处理
    FUNC_DECL = "FUNC_DECL"  # 函数声明解析
    FUNC_CONTENT = "FUNCTION_CONTENT"  # 函数内容解析, 没有对应状态机, 主要在主循环中处理
    BEHAVIOR_STEP = "BEHAVIOR_STEP"  # 行为步骤解析


class BaseState:
    """状态基类"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator):
        self.state_type = ParserState.BASE_STATE
        self.parent_uid = parent_uid
        self.uid_generator = uid_generator
        self.last_token: Optional[Token] = None

    def process_token(self, token: Token, ast_node_dict: Dict[int, AstNode]) -> None:
        self.last_token = token

    def is_pop_state(self) -> bool:
        return False


class TopLevelState(BaseState):
    """顶层状态类"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator):
        super().__init__(parent_uid, uid_generator)
        self.state_type = ParserState.TOP_LEVEL

    def process_token(self, token: Token, ast_node_dict: Dict[int, AstNode]) -> None:
        super().process_token(token, ast_node_dict)
        # 顶层状态不处理token，只在主循环中处理关键字


class ModuleDeclState(BaseState):
    """模块声明状态类"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator):
        super().__init__(parent_uid, uid_generator)
        self.state_type = ParserState.MODULE_DECL
        self.module_name = ""
        self.content = ""
        self.expecting_module_name = True
        self.expecting_colon = False
        self.expecting_content = False

    def process_token(self, token: Token, ast_node_dict: Dict[int, AstNode]) -> None:
        super().process_token(token, ast_node_dict)
        
        if token.type == IbcTokenType.IDENTIFIER and self.expecting_module_name:
            self.module_name = token.value
            self.expecting_module_name = False
            self.expecting_colon = True
        elif token.type == IbcTokenType.COLON and self.expecting_colon:
            self.expecting_colon = False
            self.expecting_content = True
        elif token.type == IbcTokenType.IDENTIFIER and self.expecting_content:
            self.content = token.value
        elif token.type == IbcTokenType.NEWLINE:
            # 模块声明结束，创建节点
            uid = self.uid_generator.gen_uid()
            line_num = self.last_token.line_num if self.last_token else 0
            module_node = ModuleNode(
                uid=uid,
                parent_uid=self.parent_uid,
                node_type=AstNodeType.MODULE,
                line_number=line_num,
                identifier=self.module_name,
                content=self.content
            )
            
            ast_node_dict[uid] = module_node
            if self.parent_uid in ast_node_dict:
                ast_node_dict[self.parent_uid].add_child(uid)
                
    def is_pop_state(self) -> bool:
        return self.last_token is not None and self.last_token.type == IbcTokenType.NEWLINE


class VarDeclState(BaseState):
    """变量声明状态类"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator):
        super().__init__(parent_uid, uid_generator)
        self.state_type = ParserState.VAR_DECL
        self.variables: List[Tuple[str, str]] = []  # [(name, description), ...]
        self.current_var_name = ""
        self.current_var_desc = ""
        self.expecting_var_name = True
        self.expecting_colon = False
        self.expecting_var_desc = False

    def process_token(self, token: Token, ast_node_dict: Dict[int, AstNode]) -> None:
        super().process_token(token, ast_node_dict)
        
        if token.type == IbcTokenType.IDENTIFIER and self.expecting_var_name:
            self.current_var_name = token.value
            self.expecting_var_name = False
            self.expecting_colon = True
        elif token.type == IbcTokenType.COLON and self.expecting_colon:
            self.expecting_colon = False
            self.expecting_var_desc = True
        elif token.type == IbcTokenType.IDENTIFIER and self.expecting_var_desc:
            self.current_var_desc = token.value
            # 添加变量到列表
            self.variables.append((self.current_var_name, self.current_var_desc))
            # 重置状态以处理下一个变量
            self.current_var_name = ""
            self.current_var_desc = ""
            self.expecting_var_name = True
            self.expecting_colon = False
            self.expecting_var_desc = False
        elif token.type == IbcTokenType.COMMA:
            # 添加变量到列表
            if self.current_var_name:
                self.variables.append((self.current_var_name, self.current_var_desc))
            # 重置状态以处理下一个变量
            self.current_var_name = ""
            self.current_var_desc = ""
            self.expecting_var_name = True
            self.expecting_colon = False
            self.expecting_var_desc = False
        elif token.type == IbcTokenType.NEWLINE:
            # 添加最后一个变量（如果没有冒号和描述）
            if self.current_var_name:
                self.variables.append((self.current_var_name, self.current_var_desc))
            # 为每个变量创建节点
            line_num = self.last_token.line_num if self.last_token else 0
            for var_name, var_desc in self.variables:
                uid = self.uid_generator.gen_uid()
                var_node = VariableNode(
                    uid=uid,
                    parent_uid=self.parent_uid,
                    node_type=AstNodeType.VARIABLE,
                    line_number=line_num,
                    identifier=var_name,
                    content=var_desc
                )
                ast_node_dict[uid] = var_node
                if self.parent_uid in ast_node_dict:
                    ast_node_dict[self.parent_uid].add_child(uid)

    def is_pop_state(self) -> bool:
        return self.last_token is not None and self.last_token.type == IbcTokenType.NEWLINE


class DescriptionState(BaseState):
    """描述状态类"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator):
        super().__init__(parent_uid, uid_generator)
        self.state_type = ParserState.DESCRIPTION
        self.content = ""
        self.expecting_colon = True
        self.expecting_content = False

    def process_token(self, token: Token, ast_node_dict: Dict[int, AstNode]) -> None:
        super().process_token(token, ast_node_dict)
        
        if token.type == IbcTokenType.COLON and self.expecting_colon:
            self.expecting_colon = False
            self.expecting_content = True
        elif token.type == IbcTokenType.IDENTIFIER and self.expecting_content:
            if self.content:
                self.content += " " + token.value
            else:
                self.content = token.value
        elif token.type == IbcTokenType.NEWLINE:
            # 描述结束，暂存内容
            pass  # 内容将在关联节点创建时使用

    def is_pop_state(self) -> bool:
        return self.last_token is not None and self.last_token.type == IbcTokenType.NEWLINE

    def get_content(self) -> str:
        return self.content


class IntentCommentState(BaseState):
    """意图注释状态类"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator):
        super().__init__(parent_uid, uid_generator)
        self.state_type = ParserState.INTENT_COMMENT
        self.content = ""

    def process_token(self, token: Token, ast_node_dict: Dict[int, AstNode]) -> None:
        super().process_token(token, ast_node_dict)
        
        if token.type == IbcTokenType.IDENTIFIER:
            if self.content:
                self.content += " " + token.value
            else:
                self.content = token.value

    def is_pop_state(self) -> bool:
        return self.last_token is not None and self.last_token.type == IbcTokenType.NEWLINE

    def get_content(self) -> str:
        return self.content


class ClassDeclState(BaseState):
    """类声明状态类"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator):
        super().__init__(parent_uid, uid_generator)
        self.state_type = ParserState.CLASS_DECL
        self.class_name = ""
        self.parent_class = ""
        self.inheritance_desc = ""
        self.params: Dict[str, str] = {}
        self.expecting_class_name = True
        self.expecting_lparen = False
        self.expecting_param_content = False
        self.expecting_rparen = False
        self.expecting_colon = False

    def process_token(self, token: Token, ast_node_dict: Dict[int, AstNode]) -> None:
        super().process_token(token, ast_node_dict)
        
        if token.type == IbcTokenType.IDENTIFIER and self.expecting_class_name:
            self.class_name = token.value
            self.expecting_class_name = False
            self.expecting_lparen = True
        elif token.type == IbcTokenType.LPAREN and self.expecting_lparen:
            self.expecting_lparen = False
            self.expecting_param_content = True
        elif token.type == IbcTokenType.IDENTIFIER and self.expecting_param_content:
            # 这里需要处理参数，可能是父类名或继承描述
            if not self.parent_class:
                self.parent_class = token.value
            else:
                if self.inheritance_desc:
                    self.inheritance_desc += " " + token.value
                else:
                    self.inheritance_desc = token.value
        elif token.type == IbcTokenType.COMMA and self.expecting_param_content:
            # 参数分隔符
            pass
        elif token.type == IbcTokenType.RPAREN and self.expecting_param_content:
            self.expecting_param_content = False
            self.expecting_colon = True
        elif token.type == IbcTokenType.COLON and self.expecting_colon:
            self.expecting_colon = False
        elif token.type == IbcTokenType.NEWLINE:
            # 类声明结束，创建节点
            uid = self.uid_generator.gen_uid()
            line_num = self.last_token.line_num if self.last_token else 0
            class_node = ClassNode(
                uid=uid,
                parent_uid=self.parent_uid,
                node_type=AstNodeType.CLASS,
                line_number=line_num,
                identifier=self.class_name,
                params=self.params
            )
            
            ast_node_dict[uid] = class_node
            if self.parent_uid in ast_node_dict:
                ast_node_dict[self.parent_uid].add_child(uid)

    def is_pop_state(self) -> bool:
        return self.last_token is not None and self.last_token.type == IbcTokenType.NEWLINE


class FuncDeclState(BaseState):
    """函数声明状态类"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator):
        super().__init__(parent_uid, uid_generator)
        self.state_type = ParserState.FUNC_DECL
        self.func_name = ""
        self.params: Dict[str, str] = {}
        self.current_param_name = ""
        self.current_param_desc = ""
        self.expecting_func_name = True
        self.expecting_lparen = False
        self.expecting_params = False
        self.expecting_param_name = True
        self.expecting_param_colon = False
        self.expecting_param_desc = False
        self.expecting_rparen = False
        self.expecting_colon = False

    def process_token(self, token: Token, ast_node_dict: Dict[int, AstNode]) -> None:
        super().process_token(token, ast_node_dict)
        
        if token.type == IbcTokenType.IDENTIFIER and self.expecting_func_name:
            self.func_name = token.value
            self.expecting_func_name = False
            self.expecting_lparen = True
        elif token.type == IbcTokenType.LPAREN and self.expecting_lparen:
            self.expecting_lparen = False
            self.expecting_params = True
            self.expecting_param_name = True
        elif token.type == IbcTokenType.IDENTIFIER and self.expecting_params and self.expecting_param_name:
            self.current_param_name = token.value
            self.expecting_param_name = False
            self.expecting_param_colon = True
        elif token.type == IbcTokenType.COLON and self.expecting_params and self.expecting_param_colon:
            self.expecting_param_colon = False
            self.expecting_param_desc = True
        elif token.type == IbcTokenType.IDENTIFIER and self.expecting_params and self.expecting_param_desc:
            self.current_param_desc = token.value
            self.params[self.current_param_name] = self.current_param_desc
            self.current_param_name = ""
            self.current_param_desc = ""
            self.expecting_param_name = True
            self.expecting_param_colon = False
            self.expecting_param_desc = False
        elif token.type == IbcTokenType.COMMA and self.expecting_params:
            # 如果有当前参数但没有描述，也要添加
            if self.current_param_name:
                self.params[self.current_param_name] = self.current_param_desc
                self.current_param_name = ""
                self.current_param_desc = ""
            self.expecting_param_name = True
            self.expecting_param_colon = False
            self.expecting_param_desc = False
        elif token.type == IbcTokenType.RPAREN and self.expecting_params:
            # 如果有当前参数但没有描述，也要添加
            if self.current_param_name:
                self.params[self.current_param_name] = self.current_param_desc
            self.expecting_params = False
            self.expecting_rparen = False
            self.expecting_colon = True
        elif token.type == IbcTokenType.COLON and self.expecting_colon:
            self.expecting_colon = False
        elif token.type == IbcTokenType.NEWLINE:
            # 函数声明结束，创建节点
            uid = self.uid_generator.gen_uid()
            line_num = self.last_token.line_num if self.last_token else 0
            func_node = FunctionNode(
                uid=uid,
                parent_uid=self.parent_uid,
                node_type=AstNodeType.FUNCTION,
                line_number=line_num,
                identifier=self.func_name,
                params=self.params
            )
            
            ast_node_dict[uid] = func_node
            if self.parent_uid in ast_node_dict:
                ast_node_dict[self.parent_uid].add_child(uid)

    def is_pop_state(self) -> bool:
        return self.last_token is not None and self.last_token.type == IbcTokenType.NEWLINE


class BehaviorStepState(BaseState):
    """行为步骤状态类"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator):
        super().__init__(parent_uid, uid_generator)
        self.state_type = ParserState.BEHAVIOR_STEP
        self.content = ""
        self.symbol_refs: List[str] = []
        self.new_block_flag = False

    def process_token(self, token: Token, ast_node_dict: Dict[int, AstNode]) -> None:
        super().process_token(token, ast_node_dict)
        
        if token.type == IbcTokenType.REF_IDENTIFIER:
            self.symbol_refs.append(token.value)
        elif token.type == IbcTokenType.IDENTIFIER:
            if self.content:
                self.content += " " + token.value
            else:
                self.content = token.value
        elif token.type == IbcTokenType.COLON:
            self.content += ":"
            self.new_block_flag = True
        elif token.type == IbcTokenType.COMMA:
            self.content += ","
        elif token.type == IbcTokenType.LPAREN:
            self.content += "("
        elif token.type == IbcTokenType.RPAREN:
            self.content += ")"
        elif token.type == IbcTokenType.NEWLINE:
            # 行为步骤结束，创建节点
            uid = self.uid_generator.gen_uid()
            line_num = self.last_token.line_num if self.last_token else 0
            behavior_node = BehaviorStepNode(
                uid=uid,
                parent_uid=self.parent_uid,
                node_type=AstNodeType.BEHAVIOR_STEP,
                line_number=line_num,
                content=self.content,
                symbol_refs=self.symbol_refs,
                new_block_flag=self.new_block_flag
            )
            
            ast_node_dict[uid] = behavior_node
            if self.parent_uid in ast_node_dict:
                ast_node_dict[self.parent_uid].add_child(uid)

    def is_pop_state(self) -> bool:
        return self.last_token is not None and self.last_token.type == IbcTokenType.NEWLINE