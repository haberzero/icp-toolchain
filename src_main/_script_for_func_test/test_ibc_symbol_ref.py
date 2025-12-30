"""符号引用解析器综合测试脚本

测试覆盖范围：
1. 本地符号管理：合并、优先级、空表处理、特殊标记验证
2. 外部符号引用：$引用语法、模块检测、外部库、多模块、无效格式
3. self引用验证：正确/错误引用、作用域可见性
4. 本地符号的$引用：本地符号引用、前后差异对比
5. 符号自引用：函数递归（$引用）、类方法递归（self引用）、类$引用自身成员
6. 作用域隔离：private成员访问控制
7. Module层次引用：文件夹级别、深层文件夹、类级别、函数级别
8. 边界条件：参数类型、混合引用、无导入检测
"""
import sys
import os

# 添加项目根目录到系统路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.ibc_analyzer.ibc_visible_symbol_builder import VisibleSymbolBuilder
from utils.ibc_analyzer.ibc_analyzer import analyze_ibc_content
from utils.ibc_analyzer.ibc_symbol_ref_resolver import SymbolRefResolver
from utils.issue_recorder import IbcIssueRecorder
from typedef.cmd_data_types import Colors
from typedef.ibc_data_types import ClassMetadata, FunctionMetadata, VariableMetadata


# ===========================
# 测试辅助函数
# ===========================

def create_test_metadata(meta_type: str, **kwargs):
    """创建测试用的符号元数据对象
    
    Args:
        meta_type: 类型 - 'class', 'function', 'variable'
        **kwargs: 元数据属性
    
    Returns:
        SymbolMetadata对象
    """
    if meta_type == "class":
        return ClassMetadata(
            type="class",
            visibility=kwargs.get("visibility", "public"),
            description=kwargs.get("description", ""),
            normalized_name=kwargs.get("normalized_name", ""),
            __is_local__=kwargs.get("__is_local__", False),
            __local_file__=kwargs.get("__local_file__", "")
        )
    elif meta_type == "function":
        return FunctionMetadata(
            type="func",
            visibility=kwargs.get("visibility", "public"),
            description=kwargs.get("description", ""),
            parameters=kwargs.get("parameters", {}),
            normalized_name=kwargs.get("normalized_name", ""),
            __is_local__=kwargs.get("__is_local__", False),
            __local_file__=kwargs.get("__local_file__", "")
        )
    elif meta_type == "variable":
        return VariableMetadata(
            type="var",
            visibility=kwargs.get("visibility", "public"),
            description=kwargs.get("description", ""),
            scope=kwargs.get("scope", "unknown"),
            normalized_name=kwargs.get("normalized_name", ""),
            __is_local__=kwargs.get("__is_local__", False),
            __local_file__=kwargs.get("__local_file__", "")
        )
    else:
        raise ValueError(f"不支持的类型: {meta_type}")

def run_test(
    test_name: str,
    ibc_content: str,
    symbols_tree: dict = None,
    symbols_metadata: dict = None,
    proj_root_dict: dict = None,
    dependent_relation: dict = None,
    current_file_path: str = "src/test",
    include_local_symbols: bool = True,
    expected_issues: int = 0,
    expected_issue_keywords: list = None
) -> bool:
    """运行单个测试用例
    
    Args:
        test_name: 测试名称
        ibc_content: IBC代码内容
        symbols_tree: 外部可见符号树
        symbols_metadata: 外部符号元数据
        proj_root_dict: 项目根目录字典
        dependent_relation: 依赖关系
        current_file_path: 当前文件路径
        include_local_symbols: 是否包含本地符号
        expected_issues: 预期的问题数量
        expected_issue_keywords: 预期问题消息中包含的关键词列表
    
    Returns:
        bool: 测试是否通过
    """
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试: {test_name}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")
    
    if symbols_tree is None:
        symbols_tree = {}
    if symbols_metadata is None:
        symbols_metadata = {}
    if proj_root_dict is None:
        proj_root_dict = {"src": {"test": "测试模块"}}
    if dependent_relation is None:
        dependent_relation = {current_file_path: []}
    
    # 解析IBC代码
    issue_recorder = IbcIssueRecorder()
    ast_dict, local_symbols_tree, local_symbols_metadata = analyze_ibc_content(ibc_content, issue_recorder)
    
    if not ast_dict:
        print(f"{Colors.FAIL}IBC代码解析失败{Colors.ENDC}")
        return False
    
    # 构建可见符号树
    builder = VisibleSymbolBuilder(proj_root_dict)
    
    # 准备依赖符号表
    dependency_symbol_tables = {}
    for dep_path in dependent_relation.get(current_file_path, []):
        dep_key = dep_path.replace('/', '.')
        if dep_key in symbols_tree or any(k.startswith(dep_key) for k in symbols_metadata):
            # 添加每个匹配的依赖，不要break
            dependency_symbol_tables[dep_path] = (symbols_tree, symbols_metadata)
    
    if dependency_symbol_tables:
        visible_symbols_tree, visible_symbols_metadata = builder.build_visible_symbol_tree(
            current_file_path=current_file_path,
            dependency_symbol_tables=dependency_symbol_tables,
            include_local_symbols=include_local_symbols,
            local_symbols_tree=local_symbols_tree if include_local_symbols else None,
            local_symbols_metadata=local_symbols_metadata if include_local_symbols else None
        )
    else:
        visible_symbols_tree, visible_symbols_metadata = builder.build_visible_symbol_tree(
            current_file_path=current_file_path,
            dependency_symbol_tables={},
            include_local_symbols=include_local_symbols,
            local_symbols_tree=local_symbols_tree if include_local_symbols else None,
            local_symbols_metadata=local_symbols_metadata if include_local_symbols else None
        )
    
    # 创建解析器
    issue_recorder.clear()
    resolver = SymbolRefResolver(
        ast_dict=ast_dict,
        symbols_tree=visible_symbols_tree,
        symbols_metadata=visible_symbols_metadata,
        ibc_issue_recorder=issue_recorder,
        proj_root_dict=proj_root_dict,
        dependent_relation=dependent_relation,
        current_file_path=current_file_path
    )
    
    # 解析所有引用
    resolver.resolve_all_references()
    
    # 检查结果
    issues = issue_recorder.get_issues()
    actual_issues = len(issues)
    
    print(f"  预期问题数: {expected_issues}")
    print(f"  实际问题数: {actual_issues}")
    
    if issues:
        print(f"  问题列表:")
        for issue in issues:
            print(f"    - {issue.message}")
    
    # 验证问题数量
    if actual_issues != expected_issues:
        print(f"{Colors.FAIL}✗ 测试失败: 问题数量不匹配{Colors.ENDC}")
        return False
    
    # 验证问题关键词
    if expected_issue_keywords:
        for keyword in expected_issue_keywords:
            found = any(keyword in issue.message for issue in issues)
            if not found:
                print(f"{Colors.FAIL}✗ 测试失败: 未找到预期的关键词 '{keyword}'{Colors.ENDC}")
                return False
    
    print(f"{Colors.OKGREEN}✓ 测试通过{Colors.ENDC}")
    return True


# ===========================
# 1. 本地符号管理测试
# ===========================

def test_local_symbol_merge_and_empty():
    """测试1.1: 本地符号合并（包括空符号表场景）"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试1.1: 本地符号合并（含空表）{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")
    
    proj_root_dict = {"src": {"test": "测试模块"}}
    builder = VisibleSymbolBuilder(proj_root_dict)
    dependency_symbol_tables = {
        "src/dep_module": (
            {"DepClass": {}},
            {"DepClass": create_test_metadata("class", visibility="public", description="依赖类", normalized_name="DepClass")}
        )
    }
    
    # 场景1: 包含本地符号
    local_symbols_tree = {
        "LocalClass": {"local_method": {}},
        "local_func": {}
    }
    local_symbols_metadata = {
        "LocalClass": create_test_metadata("class", visibility="public", description="本地类", normalized_name="LocalClass"),
        "LocalClass.local_method": create_test_metadata("function", visibility="public", description="本地方法", normalized_name="local_method"),
        "local_func": create_test_metadata("function", visibility="public", description="本地函数", normalized_name="local_func")
    }
    
    symbols_tree, symbols_metadata = builder.build_visible_symbol_tree(
        current_file_path="src/test",
        dependency_symbol_tables=dependency_symbol_tables,
        include_local_symbols=True,
        local_symbols_tree=local_symbols_tree,
        local_symbols_metadata=local_symbols_metadata
    )
    
    assert "LocalClass" in symbols_tree, "本地类应该在符号树中"
    assert "local_func" in symbols_tree, "本地函数应该在符号树中"
    assert symbols_metadata["LocalClass"].__is_local__ == True, "本地符号应该有 __is_local__ 标记"
    assert symbols_metadata["LocalClass"].__local_file__ == "src/test", "本地符号应该有文件路径标记"
    
    # 场景2: 空本地符号表
    symbols_tree2, _ = builder.build_visible_symbol_tree(
        current_file_path="src/test",
        dependency_symbol_tables=dependency_symbol_tables,
        include_local_symbols=True,
        local_symbols_tree={},
        local_symbols_metadata={}
    )
    assert "src" in symbols_tree2, "空本地符号时应该有依赖符号"
    
    print(f"{Colors.OKGREEN}✓ 测试通过{Colors.ENDC}")
    return True


def test_local_symbol_priority():
    """测试1.2: 本地符号优先级（重名处理）"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试1.2: 本地符号优先级{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")
    
    proj_root_dict = {"src": {"test": "测试模块"}}
    builder = VisibleSymbolBuilder(proj_root_dict)
    
    dependency_symbol_tables = {
        "src/dep_module": (
            {"SharedName": {}},
            {"SharedName": create_test_metadata("class", visibility="public", description="依赖模块的类", normalized_name="SharedNameFromDep")}
        )
    }
    
    local_symbols_tree = {"SharedName": {}}
    local_symbols_metadata = {
        "SharedName": create_test_metadata("class", visibility="public", description="本地模块的类", normalized_name="SharedNameLocal")
    }
    
    symbols_tree, symbols_metadata = builder.build_visible_symbol_tree(
        current_file_path="src/test",
        dependency_symbol_tables=dependency_symbol_tables,
        include_local_symbols=True,
        local_symbols_tree=local_symbols_tree,
        local_symbols_metadata=local_symbols_metadata
    )
    
    assert "SharedName" in symbols_metadata, "SharedName 应该存在"
    assert symbols_metadata["SharedName"].__is_local__ == True, "SharedName 应该是本地符号"
    assert symbols_metadata["SharedName"].normalized_name == "SharedNameLocal", "应该使用本地符号的规范化名称"
    
    print(f"{Colors.OKGREEN}✓ 测试通过{Colors.ENDC}")
    return True


# ===========================
# 2. 外部符号引用测试（$引用）
# ===========================

def test_external_reference_multi_modules():
    """测试2.1: 外部符号引用（多模块）"""
    ibc_content = """module src.ball.ball_entity: 球体实体模块
module src.shape.shape_base: 形状基类模块

description: 测试类
class TestClass():
    var ball: 球体实例，类型为 $ball_entity.BallEntity
    var shape: 形状实例，类型为 $shape_base.ShapeBase
"""
    
    symbols_tree = {
        "src": {
            "ball": {
                "ball_entity": {
                    "BallEntity": {}
                }
            },
            "shape": {
                "shape_base": {
                    "ShapeBase": {}
                }
            }
        }
    }
    
    symbols_metadata = {
        "src.ball.ball_entity.BallEntity": create_test_metadata("class", visibility="public"),
        "src.shape.shape_base.ShapeBase": create_test_metadata("class", visibility="public")
    }
    
    proj_root_dict = {
        "src": {
            "ball": {"ball_entity": "球体实体文件"},
            "shape": {"shape_base": "形状基类文件"}
        }
    }
    
    return run_test(
        test_name="2.1 外部符号引用（多模块）",
        ibc_content=ibc_content,
        symbols_tree=symbols_tree,
        symbols_metadata=symbols_metadata,
        proj_root_dict=proj_root_dict,
        dependent_relation={"src/test": ["src/ball/ball_entity", "src/shape/shape_base"]},
        expected_issues=0
    )


def test_module_not_found():
    """测试2.2: 模块未找到检测"""
    ibc_content = """module src.ball.ball_entity: 球体实体模块

description: 测试类
class TestClass():
    var shape: 形状，类型为 $heptagon_shape.HeptagonShape
"""
    
    proj_root_dict = {
        "src": {
            "ball": {"ball_entity": "球体实体文件"},
            "heptagon": {"heptagon_shape": "七边形文件"}
        }
    }
    
    return run_test(
        test_name="2.2 模块未找到检测",
        ibc_content=ibc_content,
        proj_root_dict=proj_root_dict,
        expected_issues=1,
        expected_issue_keywords=["heptagon_shape"]
    )


def test_external_library_reference():
    """测试2.3: 外部库引用"""
    ibc_content = """module numpy: 数值计算库

description: 测试类
class TestClass():
    var data: 数组，类型为 $numpy.ndarray
"""
    
    proj_root_dict = {
        "ExternalLibraryDependencies": {
            "numpy": "数值计算库"
        }
    }
    
    return run_test(
        test_name="2.3 外部库引用",
        ibc_content=ibc_content,
        proj_root_dict=proj_root_dict,
        expected_issues=0
    )


def test_no_import_reference():
    """测试2.4: 无导入时的引用检测"""
    ibc_content = """description: 测试类
class TestClass():
    var data: 数据，类型为 $ball_entity.BallEntity
"""
    
    proj_root_dict = {
        "src": {
            "ball": {"ball_entity": "球体实体文件"}
        }
    }
    
    return run_test(
        test_name="2.4 无导入时的引用检测",
        ibc_content=ibc_content,
        proj_root_dict=proj_root_dict,
        expected_issues=1,
        expected_issue_keywords=["ball_entity"]
    )


# ===========================
# 3. self引用验证测试
# ===========================

def test_self_reference_valid():
    """测试3.1: 有效的self引用"""
    ibc_content = """
description: self引用测试

class TestClass():
    var internal_data: 内部数据
    var ball: 球体对象
    
    func test_method():
        数据 = self.internal_data
        结果 = self.ball.get_position()
"""
    return run_test(
        test_name="3.1 有效的self引用",
        ibc_content=ibc_content,
        expected_issues=0
    )


def test_self_reference_invalid():
    """测试3.2: 无效的self引用"""
    ibc_content = """
description: 无效self引用测试

class TestClass():
    var internal_data: 内部数据
    
    func test_method():
        数据 = self.nonexistent_var
"""
    return run_test(
        test_name="3.2 无效的self引用",
        ibc_content=ibc_content,
        expected_issues=1,
        expected_issue_keywords=["nonexistent_var"]
    )


def test_scope_visibility_across_methods():
    """测试3.3: 跨方法的作用域可见性"""
    ibc_content = """
description: 作用域可见性测试

class TestClass():
    var class_var: 类变量
    
    func method_a(param_a: 参数A):
        var local_var_a: 局部变量A
        数据1 = self.class_var
        数据2 = self.param_a
        数据3 = self.local_var_a
    
    func method_b():
        数据 = self.local_var_a
"""
    return run_test(
        test_name="3.3 跨方法作用域可见性",
        ibc_content=ibc_content,
        expected_issues=1,
        expected_issue_keywords=["local_var_a"]
    )


# ===========================
# 4. 本地符号的$引用测试
# ===========================

def test_local_symbol_dollar_reference():
    """测试4.1: 本地符号的$引用"""
    ibc_content = """
description: 本地符号引用测试

class Ball():
    var position_x: 横坐标
    var position_y: 纵坐标
    
    func update_position(delta_x: float, delta_y: float):
        新x = $Ball.position_x + delta_x
        新y = $Ball.position_y + delta_y
"""
    return run_test(
        test_name="4.1 本地符号$引用",
        ibc_content=ibc_content,
        expected_issues=0
    )


def test_local_symbol_reference_before_after():
    """测试4.2: 包含本地符号前后的差异对比"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试4.2: 包含本地符号前后的差异对比{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")
    
    ibc_content = """
description: 测试本地符号引用

class Ball():
    var position_x: float
    var position_y: float
    
    func update_position(delta_x: float, delta_y: float):
        新x = $Ball.position_x + delta_x
        新y = $Ball.position_y + delta_y
        调用 $Ball.set_position(新x, 新y)
    
    func set_position(x: float, y: float):
        self.position_x = x
        self.position_y = y
"""
    
    issue_recorder = IbcIssueRecorder()
    ast_dict, symbols_tree, symbols_metadata = analyze_ibc_content(ibc_content, issue_recorder)
    
    if not ast_dict:
        print(f"{Colors.FAIL}IBC代码解析失败{Colors.ENDC}")
        return False
    
    proj_root_dict = {"src": {"test": "测试模块"}}
    builder = VisibleSymbolBuilder(proj_root_dict)
    
    # 不包含本地符号
    visible_symbols_tree_no_local, visible_symbols_metadata_no_local = builder.build_visible_symbol_tree(
        current_file_path="src/test",
        dependency_symbol_tables={},
        include_local_symbols=False
    )
    
    issue_recorder.clear()
    ref_resolver_no_local = SymbolRefResolver(
        ast_dict=ast_dict,
        symbols_tree=visible_symbols_tree_no_local,
        symbols_metadata=visible_symbols_metadata_no_local,
        ibc_issue_recorder=issue_recorder,
        proj_root_dict=proj_root_dict,
        dependent_relation={},
        current_file_path="src/test"
    )
    ref_resolver_no_local.resolve_all_references()
    issues_no_local = issue_recorder.get_issues()
    
    # 包含本地符号
    visible_symbols_tree_with_local, visible_symbols_metadata_with_local = builder.build_visible_symbol_tree(
        current_file_path="src/test",
        dependency_symbol_tables={},
        include_local_symbols=True,
        local_symbols_tree=symbols_tree,
        local_symbols_metadata=symbols_metadata
    )
    
    issue_recorder.clear()
    ref_resolver_with_local = SymbolRefResolver(
        ast_dict=ast_dict,
        symbols_tree=visible_symbols_tree_with_local,
        symbols_metadata=visible_symbols_metadata_with_local,
        ibc_issue_recorder=issue_recorder,
        proj_root_dict=proj_root_dict,
        dependent_relation={},
        current_file_path="src/test"
    )
    ref_resolver_with_local.resolve_all_references()
    issues_with_local = issue_recorder.get_issues()
    
    # 验证：不包含本地符号时应该有错误，包含后应该减少或消除
    assert len(issues_no_local) > 0, "不包含本地符号时应该有错误"
    assert len(issues_with_local) < len(issues_no_local), "包含本地符号后问题应该减少"
    
    print(f"{Colors.OKGREEN}✓ 测试通过: 问题数从 {len(issues_no_local)} 减少到 {len(issues_with_local)}{Colors.ENDC}")
    return True


# ===========================
# 5. 符号自引用测试
# ===========================

def test_recursive_function_with_dollar_reference():
    """测试5.1: 函数递归调用（$单个符号名引用）"""
    ibc_content = """
description: 递归函数测试

class MathUtils():
    func factorial(n: int):
        如果 n <= 1:
            返回 1
        否则:
            返回 n * $factorial(n - 1)
    
    func fibonacci(n: int):
        如果 n <= 1:
            返回 n
        否则:
            返回 $fibonacci(n - 1) + $fibonacci(n - 2)
"""
    return run_test(
        test_name="5.1 函数递归调用（$引用）",
        ibc_content=ibc_content,
        expected_issues=0
    )


def test_class_method_self_recursive():
    """测试5.2: 类方法self递归调用"""
    ibc_content = """
description: 类方法递归调用测试

class TreeNode():
    var value: 节点值
    var left: 左子节点
    var right: 右子节点
    
    func calculate_height():
        如果 self.left 为空 且 self.right 为空:
            返回 1
        否则:
            左高度 = self.left.calculate_height()
            右高度 = self.right.calculate_height()
            返回 1 + max(左高度, 右高度)
"""
    return run_test(
        test_name="5.2 类方法self递归调用",
        ibc_content=ibc_content,
        expected_issues=0
    )


def test_class_self_reference_with_dollar():
    """测试5.3: 类中使用$引用访问自身的方法和属性"""
    ibc_content = """
description: 类中使用$引用自身

class Calculator():
    var result: 计算结果
    var history: 历史记录列表
    
    func add(a: float, b: float):
        self.result = a + b
        调用 $Calculator.save_to_history(self.result)
        返回 self.result
    
    func save_to_history(value: float):
        将 value 添加到 self.history
    
    func get_result():
        返回 $Calculator.result
"""
    return run_test(
        test_name="5.3 类中$引用自身成员",
        ibc_content=ibc_content,
        expected_issues=0
    )


def test_local_var_dollar_reference():
    """测试5.4: 函数局部变量的$引用"""
    ibc_content = """
description: 局部变量引用测试

class DataProcessor():
    func process_data(input_data: 输入数据):
        var temp_result: 临时结果
        var final_result: 最终结果
        
        temp_result = 处理(input_data)
        final_result = 转换($temp_result)
        返回 $final_result
"""
    return run_test(
        test_name="5.4 函数局部变量$引用",
        ibc_content=ibc_content,
        expected_issues=0
    )


def test_single_symbol_ambiguity():
    """测试5.5: 单个符号引用的歧义性处理"""
    ibc_content = """
description: 符号歧义性测试

class ClassA():
    func process():
        执行 A 的处理

class ClassB():
    func process():
        调用 $process()
        执行 B 的处理
"""
    return run_test(
        test_name="5.5 单符号引用歧义性",
        ibc_content=ibc_content,
        expected_issues=0
    )


# ===========================
# 6. 作用域隔离测试
# ===========================

def test_private_member_access_same_class():
    """测试6.1: 同一类内访问private成员（应该允许）"""
    ibc_content = """
description: private成员访问测试

class DataProcessor():
    private
    var _cache: 内部缓存
    
    func _validate(data: 数据):
        返回 验证结果
    
    public
    func process(data: 数据):
        验证 = self._validate(data)
        缓存 = self._cache
        返回 处理结果
"""
    return run_test(
        test_name="6.1 同一类内访问private成员",
        ibc_content=ibc_content,
        expected_issues=0
    )


# ===========================
# 7. Module层次引用测试
# ===========================

def test_module_folder_level_import():
    """测试7.1: 文件夹级别的module引入"""
    ibc_content = """module src.ball: 球体模块文件夹

description: 测试文件夹级别引用
class TestClass():
    var entity: 球体实体，类型为 $ball.ball_entity.BallEntity
"""
    
    symbols_tree = {
        "src": {
            "ball": {
                "ball_entity": {
                    "BallEntity": {"get_position": {}}
                },
                "ball_physics": {
                    "BallPhysics": {}
                }
            }
        }
    }
    
    symbols_metadata = {
        "src.ball": {"type": "folder", "visibility": "public"},
        "src.ball.ball_entity": {"type": "file", "visibility": "public"},
        "src.ball.ball_entity.BallEntity": create_test_metadata("class", visibility="public"),
        "src.ball.ball_entity.BallEntity.get_position": create_test_metadata("function", visibility="public"),
        "src.ball.ball_physics": {"type": "file", "visibility": "public"},
        "src.ball.ball_physics.BallPhysics": create_test_metadata("class", visibility="public")
    }
    
    proj_root_dict = {
        "src": {
            "ball": {
                "ball_entity": "球体实体文件",
                "ball_physics": "球体物理文件"
            }
        }
    }
    
    return run_test(
        test_name="7.1 文件夹级别module引入",
        ibc_content=ibc_content,
        symbols_tree=symbols_tree,
        symbols_metadata=symbols_metadata,
        proj_root_dict=proj_root_dict,
        dependent_relation={"src/test": ["src/ball"]},
        expected_issues=0
    )


def test_module_deep_folder_import():
    """测试7.2: 深层文件夹结构的module引入"""
    ibc_content = """module src.engine.physics: 物理引擎核心模块

description: 测试深层文件夹引用
class TestClass():
    var core: 物理核心，类型为 $physics.core.PhysicsCore
    var collision: 碰撞检测器，类型为 $physics.collision.detector.CollisionDetector
"""
    
    symbols_tree = {
        "src": {
            "engine": {
                "physics": {
                    "core": {
                        "PhysicsCore": {}
                    },
                    "collision": {
                        "detector": {
                            "CollisionDetector": {}
                        }
                    }
                }
            }
        }
    }
    
    symbols_metadata = {
        "src.engine.physics": {"type": "folder", "visibility": "public"},
        "src.engine.physics.core": {"type": "file", "visibility": "public"},
        "src.engine.physics.core.PhysicsCore": create_test_metadata("class", visibility="public"),
        "src.engine.physics.collision": {"type": "folder", "visibility": "public"},
        "src.engine.physics.collision.detector": {"type": "file", "visibility": "public"},
        "src.engine.physics.collision.detector.CollisionDetector": create_test_metadata("class", visibility="public")
    }
    
    proj_root_dict = {
        "src": {
            "engine": {
                "physics": {
                    "core": "物理核心文件",
                    "collision": {
                        "detector": "碰撞检测器文件"
                    }
                }
            }
        }
    }
    
    return run_test(
        test_name="7.2 深层文件夹结构module引入",
        ibc_content=ibc_content,
        symbols_tree=symbols_tree,
        symbols_metadata=symbols_metadata,
        proj_root_dict=proj_root_dict,
        dependent_relation={"src/test": ["src/engine/physics"]},
        expected_issues=0
    )


def test_module_class_level_import():
    """测试7.3: 类级别的module引入"""
    ibc_content = """module src.ball.ball_entity.BallEntity: 球体实体类

description: 测试类级别引用
class TestClass():
    var entity: 球体实例，类型为 $BallEntity
    
    func get_ball_position():
        位置 = $BallEntity.get_position()
        返回 位置
"""
    
    symbols_tree = {
        "src": {
            "ball": {
                "ball_entity": {
                    "BallEntity": {
                        "get_position": {},
                        "set_position": {}
                    }
                }
            }
        }
    }
    
    symbols_metadata = {
        "src.ball.ball_entity": {"type": "file", "visibility": "public"},
        "src.ball.ball_entity.BallEntity": create_test_metadata("class", visibility="public"),
        "src.ball.ball_entity.BallEntity.get_position": create_test_metadata("function", visibility="public"),
        "src.ball.ball_entity.BallEntity.set_position": create_test_metadata("function", visibility="public")
    }
    
    proj_root_dict = {
        "src": {
            "ball": {
                "ball_entity": "球体实体文件"
            }
        }
    }
    
    return run_test(
        test_name="7.3 类级别module引入",
        ibc_content=ibc_content,
        symbols_tree=symbols_tree,
        symbols_metadata=symbols_metadata,
        proj_root_dict=proj_root_dict,
        dependent_relation={"src/test": ["src/ball/ball_entity"]},
        expected_issues=0
    )


def test_module_function_level_import():
    """测试7.4: 函数级别的module引入"""
    ibc_content = """module src.utils.math_helper.calculate_distance: 距离计算函数

description: 测试函数级别引用
class TestClass():
    func test_distance():
        距离 = $calculate_distance(点A, 点B)
        返回 距离
"""
    
    symbols_tree = {
        "src": {
            "utils": {
                "math_helper": {
                    "calculate_distance": {},
                    "calculate_angle": {}
                }
            }
        }
    }
    
    symbols_metadata = {
        "src.utils.math_helper": {"type": "file", "visibility": "public"},
        "src.utils.math_helper.calculate_distance": create_test_metadata("function", visibility="public"),
        "src.utils.math_helper.calculate_angle": create_test_metadata("function", visibility="public")
    }
    
    proj_root_dict = {
        "src": {
            "utils": {
                "math_helper": "数学辅助函数文件"
            }
        }
    }
    
    return run_test(
        test_name="7.4 函数级别module引入",
        ibc_content=ibc_content,
        symbols_tree=symbols_tree,
        symbols_metadata=symbols_metadata,
        proj_root_dict=proj_root_dict,
        dependent_relation={"src/test": ["src/utils/math_helper"]},
        expected_issues=0
    )


def test_module_multi_level_mixed():
    """测试7.5: 多层级混合引入"""
    ibc_content = """module src.engine: 引擎文件夹
module src.ball.ball_entity.BallEntity: 球体类
module numpy: 数值计算库

description: 测试多层级混合引用
class TestClass():
    var ball: 球体实例，类型为 $BallEntity
    var physics: 物理引擎，类型为 $engine.physics.PhysicsEngine
    var data: 数据数组，类型为 $numpy.ndarray
    
    func process():
        位置 = $BallEntity.get_position()
        物理处理 = $engine.physics.PhysicsEngine.apply_force(self.ball)
"""
    
    symbols_tree = {
        "src": {
            "engine": {
                "physics": {
                    "PhysicsEngine": {"apply_force": {}}
                }
            },
            "ball": {
                "ball_entity": {
                    "BallEntity": {"get_position": {}}
                }
            }
        }
    }
    
    symbols_metadata = {
        "src.engine": {"type": "folder", "visibility": "public"},
        "src.engine.physics": {"type": "file", "visibility": "public"},
        "src.engine.physics.PhysicsEngine": create_test_metadata("class", visibility="public"),
        "src.engine.physics.PhysicsEngine.apply_force": create_test_metadata("function", visibility="public"),
        "src.ball.ball_entity.BallEntity": create_test_metadata("class", visibility="public"),
        "src.ball.ball_entity.BallEntity.get_position": create_test_metadata("function", visibility="public")
    }
    
    proj_root_dict = {
        "ExternalLibraryDependencies": {"numpy": "数值计算库"},
        "src": {
            "engine": {"physics": "物理引擎文件"},
            "ball": {"ball_entity": "球体实体文件"}
        }
    }
    
    return run_test(
        test_name="7.5 多层级混合引入",
        ibc_content=ibc_content,
        symbols_tree=symbols_tree,
        symbols_metadata=symbols_metadata,
        proj_root_dict=proj_root_dict,
        dependent_relation={"src/test": ["src/engine", "src/ball/ball_entity"]},
        expected_issues=0
    )


def test_module_wrong_level_reference():
    """测试7.6: 错误层级引用检测"""
    # 引入的是文件夹级别，但尝试直接引用该文件夹下不存在的符号
    ibc_content = """module src.ball: 球体模块文件夹

description: 测试错误层级引用
class TestClass():
    var entity: 类型为 $ball.NonExistentClass
"""
    
    symbols_tree = {
        "src": {
            "ball": {
                "ball_entity": {
                    "BallEntity": {}
                }
            }
        }
    }
    
    symbols_metadata = {
        "src.ball": {"type": "folder", "visibility": "public"},
        "src.ball.ball_entity": {"type": "file", "visibility": "public"},
        "src.ball.ball_entity.BallEntity": create_test_metadata("class", visibility="public")
    }
    
    proj_root_dict = {
        "src": {
            "ball": {"ball_entity": "球体实体文件"}
        }
    }
    
    return run_test(
        test_name="7.6 错误层级引用检测",
        ibc_content=ibc_content,
        symbols_tree=symbols_tree,
        symbols_metadata=symbols_metadata,
        proj_root_dict=proj_root_dict,
        dependent_relation={"src/test": ["src/ball"]},
        expected_issues=1,
        expected_issue_keywords=["NonExistentClass"]
    )


# ===========================
# 8. 边界条件测试
# ===========================

def test_mixed_references():
    """测试8.1: 混合引用（外部+本地+self）"""
    ibc_content = """module numpy: 数值计算库
module src.ball.ball_entity: 球体实体模块

description: 测试类
class TestClass():
    var data: 数组，类型为 $numpy.ndarray
    var ball: 球体实例，类型为 $ball_entity.BallEntity
    var local_cache: 本地缓存
    
    func process_ball(球体参数: 球体对象):
        数据 = self.data
        球体 = self.ball
        缓存 = self.local_cache
        处理 $TestClass.local_cache
"""
    
    symbols_tree = {
        "src": {
            "ball": {
                "ball_entity": {
                    "BallEntity": {}
                }
            }
        }
    }
    
    symbols_metadata = {
        "src.ball.ball_entity.BallEntity": create_test_metadata("class", visibility="public")
    }
    
    proj_root_dict = {
        "ExternalLibraryDependencies": {"numpy": "数值计算库"},
        "src": {
            "ball": {"ball_entity": "球体实体文件"}
        }
    }
    
    return run_test(
        test_name="8.1 混合引用",
        ibc_content=ibc_content,
        symbols_tree=symbols_tree,
        symbols_metadata=symbols_metadata,
        proj_root_dict=proj_root_dict,
        dependent_relation={"src/test": ["src/ball/ball_entity"]},
        expected_issues=0
    )


def test_cross_file_dependency_workflow():
    """测试8.2: 跨文件依赖工作流（BallEntity -> GameManager）"""
    ibc_content = """
class GameManager():
    var ball: $ball.BallEntity类型的球体对象
    
    func update():
        使用$ball.BallEntity.get_position获取位置
        调用$ball.BallEntity.set_velocity设置速度
"""
    
    # 模拟 ball 模块的符号（从另一个文件加载）
    symbols_tree = {
        "ball": {
            "BallEntity": {
                "position": None,
                "velocity": None,
                "get_position": None,
                "set_velocity": None
            }
        }
    }
    symbols_metadata = {
        "ball.BallEntity": create_test_metadata("class", description="球体实体"),
        "ball.BallEntity.position": create_test_metadata("variable", scope="field", description="球体位置"),
        "ball.BallEntity.velocity": create_test_metadata("variable", scope="field", description="球体速度"),
        "ball.BallEntity.get_position": create_test_metadata("function", description="获取位置"),
        "ball.BallEntity.set_velocity": create_test_metadata("function", parameters={"速度值": ""}, description="设置速度")
    }
    
    proj_root_dict = {
        "src": {
            "ball": "球体模块",
            "game": "游戏模块"
        }
    }
    dependent_relation = {"src/game": ["src/ball"]}
    
    return run_test(
        test_name="8.2 跨文件依赖工作流（BallEntity -> GameManager）",
        ibc_content=ibc_content,
        symbols_tree=symbols_tree,
        symbols_metadata=symbols_metadata,
        proj_root_dict=proj_root_dict,
        dependent_relation=dependent_relation,
        current_file_path="src/game",
        expected_issues=0
    )


# ===========================
# 运行所有测试
# ===========================

def run_all_tests():
    """运行所有测试"""
    print(f"\n{Colors.OKBLUE}{'='*70}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}符号引用解析器综合测试{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*70}{Colors.ENDC}\n")
    
    test_results = []
    
    try:
        # 1. 本地符号管理测试
        print(f"\n{Colors.OKBLUE}{'#'*70}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}# 1. 本地符号管理测试{Colors.ENDC}")
        print(f"{Colors.OKBLUE}{'#'*70}{Colors.ENDC}")
        test_results.append(("1.1 本地符号合并（含空表）", test_local_symbol_merge_and_empty()))
        test_results.append(("1.2 本地符号优先级", test_local_symbol_priority()))
        
        # 2. 外部符号引用测试
        print(f"\n{Colors.OKBLUE}{'#'*70}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}# 2. 外部符号引用测试（$引用）{Colors.ENDC}")
        print(f"{Colors.OKBLUE}{'#'*70}{Colors.ENDC}")
        test_results.append(("2.1 多模块引用", test_external_reference_multi_modules()))
        test_results.append(("2.2 模块未找到检测", test_module_not_found()))
        test_results.append(("2.3 外部库引用", test_external_library_reference()))
        test_results.append(("2.4 无导入引用检测", test_no_import_reference()))
        
        # 3. self引用验证测试
        print(f"\n{Colors.OKBLUE}{'#'*70}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}# 3. self引用验证测试{Colors.ENDC}")
        print(f"{Colors.OKBLUE}{'#'*70}{Colors.ENDC}")
        test_results.append(("3.1 有效self引用", test_self_reference_valid()))
        test_results.append(("3.2 无效self引用", test_self_reference_invalid()))
        test_results.append(("3.3 跨方法作用域可见性", test_scope_visibility_across_methods()))
        
        # 4. 本地符号的$引用测试
        print(f"\n{Colors.OKBLUE}{'#'*70}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}# 4. 本地符号的$引用测试{Colors.ENDC}")
        print(f"{Colors.OKBLUE}{'#'*70}{Colors.ENDC}")
        test_results.append(("4.1 本地符号$引用", test_local_symbol_dollar_reference()))
        test_results.append(("4.2 本地符号前后对比", test_local_symbol_reference_before_after()))
        
        # 5. 符号自引用测试
        print(f"\n{Colors.OKBLUE}{'#'*70}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}# 5. 符号自引用测试{Colors.ENDC}")
        print(f"{Colors.OKBLUE}{'#'*70}{Colors.ENDC}")
        test_results.append(("5.1 函数递归$引用", test_recursive_function_with_dollar_reference()))
        test_results.append(("5.2 类方法self递归", test_class_method_self_recursive()))
        test_results.append(("5.3 类$引用自身成员", test_class_self_reference_with_dollar()))
        test_results.append(("5.4 局部变量$引用", test_local_var_dollar_reference()))
        test_results.append(("5.5 单符号歧义性", test_single_symbol_ambiguity()))
        
        # 6. 作用域隔离测试
        print(f"\n{Colors.OKBLUE}{'#'*70}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}# 6. 作用域隔离测试{Colors.ENDC}")
        print(f"{Colors.OKBLUE}{'#'*70}{Colors.ENDC}")
        test_results.append(("6.1 同类内访问private成员", test_private_member_access_same_class()))
        
        # 7. Module层次引用测试
        print(f"\n{Colors.OKBLUE}{'#'*70}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}# 7. Module层次引用测试{Colors.ENDC}")
        print(f"{Colors.OKBLUE}{'#'*70}{Colors.ENDC}")
        test_results.append(("7.1 文件夹级别module引入", test_module_folder_level_import()))
        test_results.append(("7.2 深层文件夹结构", test_module_deep_folder_import()))
        test_results.append(("7.3 类级别module引入", test_module_class_level_import()))
        test_results.append(("7.4 函数级别module引入", test_module_function_level_import()))
        test_results.append(("7.5 多层级混合引入", test_module_multi_level_mixed()))
        test_results.append(("7.6 错误层级引用检测", test_module_wrong_level_reference()))
        
        # 8. 边界条件测试
        print(f"\n{Colors.OKBLUE}{'#'*70}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}# 8. 边界条件测试{Colors.ENDC}")
        print(f"{Colors.OKBLUE}{'#'*70}{Colors.ENDC}")
        test_results.append(("8.1 混合引用", test_mixed_references()))
        test_results.append(("8.2 跨文件依赖工作流", test_cross_file_dependency_workflow()))
        
        # 测试汇总
        print(f"\n{Colors.OKBLUE}{'='*70}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}测试汇总{Colors.ENDC}")
        print(f"{Colors.OKBLUE}{'='*70}{Colors.ENDC}")
        
        passed = sum(1 for _, result in test_results if result)
        failed = len(test_results) - passed
        
        for test_name, result in test_results:
            status = f"{Colors.OKGREEN}✓ 通过{Colors.ENDC}" if result else f"{Colors.FAIL}✗ 失败{Colors.ENDC}"
            print(f"{test_name}: {status}")
        
        print(f"\n总计: {passed} 通过, {failed} 失败")
        
        if failed == 0:
            print(f"{Colors.OKGREEN}{'='*70}{Colors.ENDC}")
            print(f"{Colors.OKGREEN}所有测试通过! ({passed}/{len(test_results)}){Colors.ENDC}")
            print(f"{Colors.OKGREEN}{'='*70}{Colors.ENDC}\n")
            return True
        else:
            print(f"{Colors.WARNING}有 {failed} 个测试失败{Colors.ENDC}\n")
            return False
        
    except Exception as e:
        print(f"\n{Colors.FAIL}❌ 测试出错: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
