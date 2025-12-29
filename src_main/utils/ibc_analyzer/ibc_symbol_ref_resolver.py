"""
符号引用解析器 V2

全新设计的符号引用解析器，支持：
1. 多层级module引入粒度（文件夹/文件/类/函数级别）
2. 上下文感知的作用域解析
3. 严格的可见性控制
4. 统一的本地/外部符号处理逻辑

核心概念：
- ImportScope: 描述一个module声明创建的导入作用域
- ReferenceContext: 描述$引用发生时的上下文信息
- ScopeChain: 从当前位置向上追溯的作用域链
"""

import re
import difflib
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set, Any

from typedef.ibc_data_types import (
    IbcBaseAstNode, ModuleNode, FunctionNode, VariableNode, 
    BehaviorStepNode, ClassNode, VisibilityTypes
)
from utils.issue_recorder import IbcIssueRecorder


class ImportDepth(Enum):
    """导入深度枚举"""
    FOLDER = 1      # 文件夹级别: module src.ball
    FILE = 2        # 文件级别: module src.ball.ball_entity
    CLASS = 3       # 类级别: module src.ball.ball_entity.BallEntity
    FUNCTION = 4    # 函数级别: module src.ball.ball_entity.BallEntity.get_position


class ScopeType(Enum):
    """作用域类型"""
    TOP_LEVEL = "top_level"     # 顶层作用域
    CLASS = "class"             # 类作用域
    FUNCTION = "function"       # 函数作用域
    BEHAVIOR = "behavior"       # 行为步骤作用域


@dataclass
class ImportScope:
    """导入作用域
    
    描述一个module声明创建的导入作用域：
    - module_path: 完整模块路径 (如 "src.ball.ball_entity")
    - alias: 模块别名，用于引用时的起始点 (如 "ball_entity")
    - depth: 导入深度
    - exposed_prefix: 用户引用时可以省略的前缀
    """
    module_path: str                    # 完整模块路径
    alias: str                          # 模块别名
    depth: ImportDepth = ImportDepth.FILE
    is_external: bool = False           # 是否是外部库


@dataclass  
class ReferenceContext:
    """引用上下文
    
    描述一个$引用发生时的上下文信息：
    - node_uid: 引用所在节点的UID
    - scope_chain: 作用域链（从内到外）
    - local_symbols: 当前可见的局部符号
    - line_num: 行号
    """
    node_uid: int
    scope_chain: List[Tuple[ScopeType, int]]  # [(作用域类型, 节点UID), ...]
    local_symbols: Dict[str, Dict[str, Any]]  # {符号名: {type, visibility, ...}}
    line_num: int


@dataclass
class ResolvedSymbol:
    """解析后的符号信息"""
    original_ref: str           # 原始引用字符串
    resolved_path: str          # 解析后的完整路径
    symbol_type: str            # 符号类型 (class/func/var)
    source: str                 # 来源 (local/import/external)
    visibility: str             # 可见性
    is_valid: bool              # 是否有效
    error_message: str = ""     # 错误信息


class SymbolRefResolver:
    """
    符号引用解析器
    
    全新重构版本，支持多层级引用和上下文感知的作用域解析。
    
    主要功能：
    1. 解析module声明，构建ImportScope列表
    2. 解析$引用时构建ReferenceContext
    3. 按照优先级和作用域规则验证符号引用
    4. 验证self.xxx引用
    
    解析优先级（从高到低）：
    1. 当前作用域的局部符号（函数参数、局部变量）
    2. 父作用域的符号（class成员等）
    3. 本地文件的顶层符号
    4. 通过module导入的外部符号（后导入优先）
    """
    
    def __init__(
        self, 
        ast_dict: Dict[int, IbcBaseAstNode],
        symbols_tree: Dict[str, Any],
        symbols_metadata: Dict[str, Dict[str, Any]],
        ibc_issue_recorder: IbcIssueRecorder,
        proj_root_dict: Dict[str, Any],
        dependent_relation: Dict[str, List[str]],
        current_file_path: str
    ):
        """
        初始化符号引用解析器
        
        Args:
            ast_dict: AST字典
            symbols_tree: 可见符号树（由VisibleSymbolBuilder构建）
            symbols_metadata: 可见符号元数据
            ibc_issue_recorder: 问题记录器
            proj_root_dict: 项目根目录字典
            dependent_relation: 依赖关系
            current_file_path: 当前文件路径
        """
        self.ast_dict = ast_dict
        self.symbols_tree = symbols_tree
        self.symbols_metadata = symbols_metadata
        self.ibc_issue_recorder = ibc_issue_recorder
        self.proj_root_dict = proj_root_dict
        self.dependent_relation = dependent_relation
        self.current_file_path = current_file_path
        
        # 解析module声明，构建ImportScope列表
        self.import_scopes: List[ImportScope] = self._build_import_scopes()
        
        # 外部库依赖集合
        self.external_libraries: Set[str] = self._extract_external_libraries()
        
        # 本地符号表（当前文件定义的符号）
        self.local_symbols: Dict[str, Dict[str, Any]] = self._extract_local_symbols()
    
    def _build_import_scopes(self) -> List[ImportScope]:
        """从AST中解析所有module声明，构建ImportScope列表"""
        import_scopes = []
        
        for uid, node in self.ast_dict.items():
            if isinstance(node, ModuleNode):
                module_path = node.identifier  # 如 "src.ball.ball_entity"
                
                # 检查是否是外部库
                is_external = self._is_external_library_path(module_path)
                
                # 确定导入深度
                depth = self._determine_import_depth(module_path, is_external)
                
                # 确定别名（模块路径的最后一部分）
                alias = self._extract_alias(module_path, depth)
                
                import_scopes.append(ImportScope(
                    module_path=module_path,
                    alias=alias,
                    depth=depth,
                    is_external=is_external
                ))
        
        return import_scopes
    
    def _determine_import_depth(self, module_path: str, is_external: bool) -> ImportDepth:
        """确定模块导入深度
        
        通过检查模块路径在符号树中的位置来确定深度：
        - 如果路径指向文件夹 -> FOLDER
        - 如果路径指向文件 -> FILE  
        - 如果路径指向类 -> CLASS
        - 如果路径指向函数 -> FUNCTION
        """
        if is_external:
            return ImportDepth.FILE  # 外部库默认文件级别
        
        # 检查路径在symbols_metadata中的类型
        if module_path in self.symbols_metadata:
            meta = self.symbols_metadata[module_path]
            sym_type = meta.get('type', '')
            if sym_type == 'folder':
                return ImportDepth.FOLDER
            elif sym_type == 'file':
                return ImportDepth.FILE
            elif sym_type == 'class':
                return ImportDepth.CLASS
            elif sym_type == 'func':
                return ImportDepth.FUNCTION
        
        # 如果在symbols_metadata中找不到精确匹配，尝试通过proj_root_dict推断
        parts = module_path.split('.')
        
        # 遍历proj_root_dict检查路径能到达的深度
        current = self.proj_root_dict
        file_depth_reached = 0  # 记录到达文件结构的深度
        
        for i, part in enumerate(parts):
            if isinstance(current, dict) and part in current:
                current = current[part]
                file_depth_reached = i + 1
            else:
                # 路径中断，后面的部分是符号（类或函数）
                remaining_parts = len(parts) - file_depth_reached
                if remaining_parts >= 2:
                    # 至少有两层符号路径（如 BallEntity.get_position），推断最后一部分是函数
                    return ImportDepth.FUNCTION
                elif remaining_parts == 1:
                    # 只有一层符号路径，推断是类
                    return ImportDepth.CLASS
                break
        
        # 如果所有parts都在proj_root_dict中找到，判断最后一个节点的类型
        if isinstance(current, str):
            # 字符串节点表示文件
            return ImportDepth.FILE
        elif isinstance(current, dict):
            # 字典节点表示文件夹
            return ImportDepth.FOLDER
        
        # 默认文件级别
        return ImportDepth.FILE
    
    def _extract_alias(self, module_path: str, depth: ImportDepth) -> str:
        """提取模块别名
        
        别名是用户引用时使用的起始点：
        - 文件级别: 取路径最后一部分 (src.ball.ball_entity -> ball_entity)
        - 类级别: 取类名 (src.ball.ball_entity.BallEntity -> BallEntity)
        - 函数级别: 取函数名
        """
        parts = module_path.split('.')
        if parts:
            return parts[-1]
        return module_path
    
    def _is_external_library_path(self, module_path: str) -> bool:
        """判断模块路径是否属于外部库"""
        top_level = module_path.split('.')[0]
        return top_level in self._extract_external_libraries()
    
    def _extract_external_libraries(self) -> Set[str]:
        """从proj_root_dict中提取外部库依赖"""
        external_libs = set()
        
        if "ExternalLibraryDependencies" in self.proj_root_dict:
            ext_deps = self.proj_root_dict["ExternalLibraryDependencies"]
            if isinstance(ext_deps, dict):
                external_libs.update(ext_deps.keys())
        
        return external_libs
    
    def _extract_local_symbols(self) -> Dict[str, Dict[str, Any]]:
        """提取本地符号（当前文件定义的符号）
        
        从symbols_metadata中筛选出有__is_local__标记的符号
        """
        local_symbols = {}
        
        for path, meta in self.symbols_metadata.items():
            if meta.get('__is_local__', False):
                local_symbols[path] = meta
        
        return local_symbols
    
    def resolve_all_references(self) -> None:
        """解析AST中的所有符号引用并验证"""
        for uid, node in self.ast_dict.items():
            self._resolve_node_references(node)
    
    def _resolve_node_references(self, node: IbcBaseAstNode) -> None:
        """解析单个节点中的符号引用"""
        if isinstance(node, VariableNode):
            # 变量节点的type_ref字段包含符号引用列表
            context = self._build_reference_context(node.uid, node.line_number)
            for ref in node.type_ref:
                self._validate_symbol_reference(ref, context)
        
        elif isinstance(node, FunctionNode):
            # 函数参数的param_type_refs字段包含符号引用
            context = self._build_reference_context(node.uid, node.line_number)
            for param_name, ref in node.param_type_refs.items():
                self._validate_symbol_reference(ref, context)
        
        elif isinstance(node, BehaviorStepNode):
            # 行为步骤的symbol_refs字段包含符号引用列表
            context = self._build_reference_context(node.uid, node.line_number)
            for ref in node.symbol_refs:
                self._validate_symbol_reference(ref, context)
            # 验证self引用
            for self_ref in node.self_refs:
                self._validate_self_reference(self_ref, node, context)
    
    def _build_reference_context(self, node_uid: int, line_num: int) -> ReferenceContext:
        """构建引用上下文
        
        从当前节点向上追溯，构建作用域链和可见符号表
        """
        scope_chain = []
        local_symbols = {}
        
        current_uid = node_uid
        visited = set()  # 防止循环
        
        while current_uid in self.ast_dict and current_uid not in visited:
            visited.add(current_uid)
            node = self.ast_dict[current_uid]
            
            if isinstance(node, FunctionNode):
                scope_chain.append((ScopeType.FUNCTION, current_uid))
                # 收集函数参数作为局部符号
                for param_name, param_desc in node.params.items():
                    local_symbols[param_name] = {
                        'type': 'param',
                        'visibility': 'local',
                        'scope': 'function',
                        'uid': current_uid
                    }
                # 收集函数内的局部变量
                for child_uid in node.children_uids:
                    child = self.ast_dict.get(child_uid)
                    if isinstance(child, VariableNode):
                        local_symbols[child.identifier] = {
                            'type': 'var',
                            'visibility': 'local',
                            'scope': 'function',
                            'uid': child_uid
                        }
            
            elif isinstance(node, ClassNode):
                scope_chain.append((ScopeType.CLASS, current_uid))
                # 收集类成员
                for child_uid in node.children_uids:
                    child = self.ast_dict.get(child_uid)
                    if isinstance(child, VariableNode):
                        local_symbols[child.identifier] = {
                            'type': 'var',
                            'visibility': child.visibility.value,
                            'scope': 'class',
                            'uid': child_uid,
                            'class_uid': current_uid
                        }
                    elif isinstance(child, FunctionNode):
                        local_symbols[child.identifier] = {
                            'type': 'func',
                            'visibility': child.visibility.value,
                            'scope': 'class',
                            'uid': child_uid,
                            'class_uid': current_uid
                        }
            
            elif isinstance(node, BehaviorStepNode):
                scope_chain.append((ScopeType.BEHAVIOR, current_uid))
            
            # 向上追溯
            current_uid = node.parent_uid
            if current_uid == 0:
                scope_chain.append((ScopeType.TOP_LEVEL, 0))
                break
        
        return ReferenceContext(
            node_uid=node_uid,
            scope_chain=scope_chain,
            local_symbols=local_symbols,
            line_num=line_num
        )
    
    def _validate_symbol_reference(self, ref: str, context: ReferenceContext) -> None:
        """验证符号引用
        
        解析优先级：
        1. 上下文局部符号（函数参数、局部变量、类成员）
        2. 本地文件顶层符号
        3. 通过module导入的外部符号
        """
        if not ref:
            return
        
        # 解析引用路径
        parts = ref.split('.')
        first_part = parts[0]
        
        # 跳过self引用（由_validate_self_reference处理）
        if first_part == "self":
            return
        
        # 策略1: 检查上下文局部符号
        if first_part in context.local_symbols:
            # 找到局部符号
            local_meta = context.local_symbols[first_part]
            
            # 检查可见性：如果是类成员，需要验证是否可以访问
            if not self._check_local_visibility(local_meta, context):
                self.ibc_issue_recorder.record_issue(
                    message=f"可见性错误：符号'{first_part}'在当前作用域中不可访问（{local_meta.get('visibility', 'unknown')}）",
                    line_num=context.line_num,
                    line_content=""
                )
                return
            
            # 如果是多部分引用，验证子路径
            if len(parts) > 1:
                # 暂时跳过子路径验证，因为需要类型推导
                pass
            return
        
        # 策略2: 检查本地文件顶层符号
        if self._check_local_top_level_symbol(ref, context):
            return
        
        # 策略3: 检查module导入的符号
        if self._check_imported_symbol(ref, context):
            return
        
        # 未找到符号，记录错误
        self._record_symbol_not_found(ref, context)
    
    def _check_local_visibility(self, local_meta: Dict, context: ReferenceContext) -> bool:
        """检查局部符号的可见性
        
        规则：
        - local/public: 始终可访问
        - private: 只有在同一个类内的代码才能访问
        - protected: 只有在同一个类及其子类内才能访问（暂时视为同private）
        """
        visibility = local_meta.get('visibility', 'public')
        scope = local_meta.get('scope', '')
        
        if visibility in ('public', 'local'):
            return True
        
        if visibility in ('private', 'protected'):
            # 需要检查当前代码是否在同一个类内
            class_uid = local_meta.get('class_uid')
            if class_uid is None:
                return True
            
            # 检查context.scope_chain中是否包含该class
            for scope_type, uid in context.scope_chain:
                if scope_type == ScopeType.CLASS and uid == class_uid:
                    return True
            
            return False
        
        return True
    
    def _check_local_top_level_symbol(self, ref: str, context: ReferenceContext) -> bool:
        """检查是否是本地文件的顶层符号
        
        支持的引用格式：
        1. 单个符号名: $ClassName 或 $func_name
        2. 完整路径: $ClassName.method
        """
        parts = ref.split('.')
        first_part = parts[0]
        
        # 检查符号树的根节点
        if first_part in self.symbols_tree:
            # 检查是否是本地符号
            if first_part in self.local_symbols:
                return True
            # 即使不在local_symbols中，也检查symbols_metadata
            for path, meta in self.local_symbols.items():
                if path == first_part or path.split('.')[0] == first_part:
                    return True
        
        # 检查完整路径在本地符号中
        full_path = '.'.join(parts)
        if full_path in self.local_symbols:
            return True
        
        # 检查是否是本地符号的子符号
        for local_path in self.local_symbols:
            # 检查是否匹配最后一部分
            local_parts = local_path.split('.')
            if local_parts[-1] == first_part:
                return True
            # 检查是否是完整路径匹配
            if local_path == full_path or local_path.endswith('.' + full_path):
                return True
        
        return False
    
    def _check_imported_symbol(self, ref: str, context: ReferenceContext) -> bool:
        """检查是否是通过module导入的符号
        
        按照导入顺序（后导入优先）检查各个ImportScope
        """
        parts = ref.split('.')
        first_part = parts[0]
        
        # 反向遍历import_scopes（后导入优先）
        for import_scope in reversed(self.import_scopes):
            # 检查是否匹配别名
            if first_part == import_scope.alias:
                # 外部库引用，默认有效
                if import_scope.is_external:
                    return True
                
                # 内部模块引用，验证完整路径
                if len(parts) == 1:
                    # 只引用了别名本身，检查是否有效
                    return self._validate_module_alias_only(import_scope)
                else:
                    # 引用了别名下的符号
                    return self._validate_imported_symbol_path(import_scope, parts[1:], context)
        
        return False
    
    def _validate_module_alias_only(self, import_scope: ImportScope) -> bool:
        """验证只引用别名本身的情况
        
        如 $ball_entity（没有后续路径）
        - 如果导入的是文件，通常不允许直接引用文件名
        - 如果导入的是类，则可以直接引用类名
        """
        if import_scope.depth == ImportDepth.CLASS:
            return True
        elif import_scope.depth == ImportDepth.FUNCTION:
            return True
        else:
            # 文件或文件夹级别，检查是否有同名的类
            module_path = import_scope.module_path
            alias = import_scope.alias
            
            # 检查是否存在 module_path.alias 这样的类
            full_class_path = f"{module_path}.{alias}"
            if full_class_path in self.symbols_metadata:
                meta = self.symbols_metadata[full_class_path]
                if meta.get('type') in ('class', 'func', 'var'):
                    return True
            
            return False
    
    def _validate_imported_symbol_path(
        self, 
        import_scope: ImportScope, 
        remaining_parts: List[str],
        context: ReferenceContext
    ) -> bool:
        """验证导入符号的路径
        
        Args:
            import_scope: 导入作用域
            remaining_parts: 除别名外的剩余路径部分
            context: 引用上下文
        """
        module_path = import_scope.module_path
        symbol_path = '.'.join(remaining_parts)
        
        # 构建完整的符号路径
        full_path = f"{module_path}.{symbol_path}"
        
        # 策略1: 检查是否存在于symbols_metadata中（精确匹配）
        if full_path in self.symbols_metadata:
            meta = self.symbols_metadata[full_path]
            # 检查可见性
            visibility = meta.get('visibility', 'public')
            if visibility == 'private':
                self.ibc_issue_recorder.record_issue(
                    message=f"可见性错误：符号'{symbol_path}'是私有的，无法从外部访问",
                    line_num=context.line_num,
                    line_content=""
                )
                return False
            return True
        
        # 策略2: 尝试在符号树中查找（树形结构遍历）
        if self._check_symbol_in_tree(module_path, remaining_parts):
            return True
        
        # 策略3: 尝试以别名为起点在符号树中查找
        # 这是为了处理类级别导入的情况：module X.Y.Z.ClassName
        # 当引用 $ClassName.method 时，在树中直接查找 ClassName.method
        if import_scope.depth in (ImportDepth.CLASS, ImportDepth.FUNCTION):
            alias_tree_path = [import_scope.alias] + remaining_parts
            if self._check_symbol_path_in_tree(alias_tree_path):
                return True
        
        # 策略4: 模糊匹配（可能是嵌套的类/函数）
        for meta_path in self.symbols_metadata:
            if meta_path.startswith(module_path + '.'):
                relative = meta_path[len(module_path) + 1:]
                # 匹配完整路径或末尾匹配
                if relative == symbol_path:
                    return True
                # 匹配第一个部分（对于深层嵌套的情况）
                if relative.startswith(symbol_path + '.') or relative.endswith('.' + symbol_path):
                    return True
                # 匹配第一级符号
                if remaining_parts and relative.split('.')[0] == remaining_parts[0]:
                    return True
        
        # 策略5: 检查第一部分是否是导入路径下的子符号（如 physics.apply_force 中的 physics）
        if remaining_parts:
            first_part = remaining_parts[0]
            # 检查 module_path.first_part 是否存在
            check_path = f"{module_path}.{first_part}"
            if check_path in self.symbols_metadata:
                return True
            # 检查树中是否有这个符号
            if self._check_symbol_in_tree(module_path, [first_part]):
                return True
        
        # 策略6: 递归检查多层路径（如 physics.apply_force 或 physics.PhysicsEngine.apply_force）
        if len(remaining_parts) >= 2:
            # 尝试在符号树中查找多层路径
            if self._check_multi_level_path(module_path, remaining_parts):
                return True
        
        return False
    
    def _check_multi_level_path(self, base_path: str, path_parts: List[str]) -> bool:
        """检查多层路径是否存在
        
        对于类似 $engine.physics.apply_force 的引用：
        - base_path = "src.engine"
        - path_parts = ["physics", "apply_force"]
        
        需要检查 src.engine.physics.apply_force 或 src.engine.physics.*.apply_force
        """
        # 构建完整路径并在符号树中查找
        full_path_parts = base_path.split('.') + path_parts
        
        # 在符号树中按顺序查找
        current = self.symbols_tree
        for part in full_path_parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                # 找不到直接路径，尝试在当前节点的子节点中查找
                if isinstance(current, dict):
                    found = False
                    for key, value in current.items():
                        if isinstance(value, dict) and part in value:
                            current = value[part]
                            found = True
                            break
                    if not found:
                        return False
                else:
                    return False
        
        return True
    
    def _check_symbol_path_in_tree(self, path_parts: List[str]) -> bool:
        """从符号树根开始检查路径是否存在
        
        递归搜索符号树中是否包含给定的路径
        """
        def search_in_dict(d: Dict, parts: List[str], start_idx: int) -> bool:
            if start_idx >= len(parts):
                return True
            
            target = parts[start_idx]
            if not isinstance(d, dict):
                return False
            
            # 直接匹配
            if target in d:
                if start_idx == len(parts) - 1:
                    return True
                return search_in_dict(d[target], parts, start_idx + 1)
            
            # 递归搜索子节点
            for key, value in d.items():
                if isinstance(value, dict):
                    if search_in_dict(value, parts, start_idx):
                        return True
            
            return False
        
        return search_in_dict(self.symbols_tree, path_parts, 0)
    
    def _check_symbol_in_tree(self, base_path: str, path_parts: List[str]) -> bool:
        """在符号树中检查路径是否存在
        
        Args:
            base_path: 基础路径（如 src.ball.ball_entity）
            path_parts: 需要查找的路径部分列表
        
        Returns:
            bool: 路径是否存在
        """
        # 将base_path转换为部分列表
        base_parts = base_path.split('.')
        
        # 从符号树根开始遍历
        current = self.symbols_tree
        
        # 先导航到base_path
        for part in base_parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False
        
        # 然后检查path_parts
        for part in path_parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False
        
        return True
    
    def _record_symbol_not_found(self, ref: str, context: ReferenceContext) -> None:
        """记录符号未找到的错误，并提供建议"""
        parts = ref.split('.')
        first_part = parts[0]
        
        # 收集候选符号
        candidates = []
        
        # 从局部符号收集
        candidates.extend(context.local_symbols.keys())
        
        # 从本地符号收集
        for path in self.local_symbols:
            name = path.split('.')[-1]
            if name not in candidates:
                candidates.append(name)
        
        # 从导入的模块收集
        for import_scope in self.import_scopes:
            if import_scope.alias not in candidates:
                candidates.append(import_scope.alias)
        
        # 模糊匹配
        matches = difflib.get_close_matches(first_part, candidates, n=3, cutoff=0.3)
        
        if matches:
            suggestion = f"你是否想引用: {', '.join(matches)}？"
        else:
            suggestion = "未找到相似的符号"
        
        # 确定错误类型
        if len(parts) == 1:
            message = f"符号引用错误：符号'{ref}'未找到。{suggestion}"
        else:
            # 检查第一部分是否是有效的模块别名
            is_module = any(s.alias == first_part for s in self.import_scopes)
            if is_module:
                message = f"符号引用错误：在模块'{first_part}'中未找到符号'{'.'.join(parts[1:])}'。{suggestion}"
            else:
                message = f"符号引用错误：'{first_part}'不是有效的模块或本地符号。{suggestion}"
        
        self.ibc_issue_recorder.record_issue(
            message=message,
            line_num=context.line_num,
            line_content=""
        )
    
    def _validate_self_reference(
        self, 
        ref: str, 
        node: BehaviorStepNode, 
        context: ReferenceContext
    ) -> None:
        """验证self引用（self.xxx格式）
        
        self引用只能在类的方法内使用，且只能访问：
        1. 类的成员变量
        2. 类的方法
        3. 父类的可访问成员（如果有继承）
        """
        if not ref:
            return
        
        parts = ref.split('.')
        first_part = parts[0]  # self后面的第一个部分
        
        # 检查是否在类的上下文中
        class_uid = None
        for scope_type, uid in context.scope_chain:
            if scope_type == ScopeType.CLASS:
                class_uid = uid
                break
        
        if class_uid is None:
            self.ibc_issue_recorder.record_issue(
                message=f"self引用错误：self只能在类的方法内使用",
                line_num=context.line_num,
                line_content=""
            )
            return
        
        # 获取类节点
        class_node = self.ast_dict.get(class_uid)
        if not isinstance(class_node, ClassNode):
            return
        
        # 构建类的成员符号表
        class_members = {}
        for child_uid in class_node.children_uids:
            child = self.ast_dict.get(child_uid)
            if isinstance(child, VariableNode):
                class_members[child.identifier] = {
                    'type': 'var',
                    'visibility': child.visibility.value
                }
            elif isinstance(child, FunctionNode):
                class_members[child.identifier] = {
                    'type': 'func',
                    'visibility': child.visibility.value
                }
        
        # 还要收集函数内的参数和局部变量（可以通过self引用的）
        func_uid = None
        for scope_type, uid in context.scope_chain:
            if scope_type == ScopeType.FUNCTION:
                func_uid = uid
                break
        
        if func_uid:
            func_node = self.ast_dict.get(func_uid)
            if isinstance(func_node, FunctionNode):
                # 函数参数
                for param_name in func_node.params:
                    class_members[param_name] = {
                        'type': 'param',
                        'visibility': 'local'
                    }
                # 函数局部变量
                for child_uid in func_node.children_uids:
                    child = self.ast_dict.get(child_uid)
                    if isinstance(child, VariableNode):
                        class_members[child.identifier] = {
                            'type': 'var',
                            'visibility': 'local'
                        }
        
        # 验证first_part是否在类成员中
        if first_part not in class_members:
            # 模糊匹配建议
            matches = difflib.get_close_matches(first_part, class_members.keys(), n=3, cutoff=0.3)
            if matches:
                suggestion = f"你是否想引用: {', '.join(matches)}？"
            else:
                suggestion = "在当前类中未找到相似的成员"
            
            self.ibc_issue_recorder.record_issue(
                message=f"self引用错误：类'{class_node.identifier}'中不存在成员'{first_part}'。{suggestion}",
                line_num=context.line_num,
                line_content=""
            )
            return
        
        # 如果引用的是嵌套路径（如self.ball.get_position），只验证第一层
        # 更深层的验证需要类型推导，暂时跳过
