"""
局部符号和符号引用解析器综合测试脚本

测试覆盖范围：
1. 本地符号管理：合并、优先级、空表处理、特殊标记验证
2. 外部符号引用：$引用语法、模块检测、外部库、多模块、无效格式
3. self引用验证：正确/错误引用、作用域可见性
4. 本地符号的$引用：本地符号引用、前后差异对比
5. 边界条件：参数类型、混合引用、无导入检测
"""
import sys
import os

# 添加项目根目录到系统路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.ibc_analyzer.ibc_visible_symbol_builder import VisibleSymbolBuilder
from utils.ibc_analyzer.ibc_analyzer import analyze_ibc_code
from utils.ibc_analyzer.ibc_symbol_ref_resolver import SymbolRefResolver
from utils.issue_recorder import IbcIssueRecorder
from typedef.cmd_data_types import Colors


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
            {"DepClass": {"type": "class", "visibility": "public", "description": "依赖类", "normalized_name": "DepClass"}}
        )
    }
    
    # 场景1: 包含本地符号
    local_symbols_tree = {
        "LocalClass": {"local_method": {}},
        "local_func": {}
    }
    local_symbols_metadata = {
        "LocalClass": {"type": "class", "visibility": "public", "description": "本地类", "normalized_name": "LocalClass"},
        "LocalClass.local_method": {"type": "function", "visibility": "public", "description": "本地方法", "normalized_name": "local_method"},
        "local_func": {"type": "function", "visibility": "public", "description": "本地函数", "normalized_name": "local_func"}
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
    assert symbols_metadata["LocalClass"]["__is_local__"] == True, "本地符号应该有 __is_local__ 标记"
    assert symbols_metadata["LocalClass"]["__local_file__"] == "src/test", "本地符号应该有文件路径标记"
    
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
            {"SharedName": {"type": "class", "visibility": "public", "description": "依赖模块的类", "normalized_name": "SharedNameFromDep"}}
        )
    }
    
    local_symbols_tree = {"SharedName": {}}
    local_symbols_metadata = {
        "SharedName": {"type": "class", "visibility": "public", "description": "本地模块的类", "normalized_name": "SharedNameLocal"}
    }
    
    symbols_tree, symbols_metadata = builder.build_visible_symbol_tree(
        current_file_path="src/test",
        dependency_symbol_tables=dependency_symbol_tables,
        include_local_symbols=True,
        local_symbols_tree=local_symbols_tree,
        local_symbols_metadata=local_symbols_metadata
    )
    
    assert "SharedName" in symbols_metadata, "SharedName 应该存在"
    assert symbols_metadata["SharedName"]["__is_local__"] == True, "SharedName 应该是本地符号"
    assert symbols_metadata["SharedName"]["normalized_name"] == "SharedNameLocal", "应该使用本地符号的规范化名称"
    
    print(f"{Colors.OKGREEN}✓ 测试通过{Colors.ENDC}")
    return True


# ===========================
# 2. 外部符号引用测试（$引用）
# ===========================

def test_external_reference_multi_modules():
    """测试2.1: 外部符号引用（单模块和多模块）"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试2.1: 外部符号引用（多模块）{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")
    
    ibc_code = """module src.ball.ball_entity: 球体实体模块
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
        "src.ball.ball_entity.BallEntity": {"type": "class", "visibility": "public"},
        "src.shape.shape_base.ShapeBase": {"type": "class", "visibility": "public"}
    }
    
    proj_root_dict = {
        "src": {
            "ball": {
                "ball_entity": "球体实体文件"
            },
            "shape": {
                "shape_base": "形状基类文件"
            }
        }
    }
    
    dependent_relation = {"src/test": ["src/ball/ball_entity", "src/shape/shape_base"]}
    
    issue_recorder = IbcIssueRecorder()
    ast_dict, _, _ = analyze_ibc_code(ibc_code, issue_recorder)
    
    if not ast_dict:
        print(f"{Colors.FAIL}AST解析失败{Colors.ENDC}")
        return False
    
    resolver = SymbolRefResolver(
        ast_dict=ast_dict,
        symbols_tree=symbols_tree,
        symbols_metadata=symbols_metadata,
        ibc_issue_recorder=issue_recorder,
        proj_root_dict=proj_root_dict,
        dependent_relation=dependent_relation,
        current_file_path="src/test"
    )
    
    resolver.resolve_all_references()
    
    if issue_recorder.has_issues():
        print(f"{Colors.FAIL}测试失败: 多模块引用不应该报错{Colors.ENDC}")
        for issue in issue_recorder.get_issues():
            print(f"  - {issue.message}")
        return False
    
    print(f"{Colors.OKGREEN}✓ 测试通过{Colors.ENDC}")
    return True


def test_module_not_found_and_invalid_format():
    """测试2.2: 模块未找到检测和无效引用格式"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试2.2: 模块未找到和无效格式{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")
    
    ibc_code = """module src.ball.ball_entity: 球体实体模块

description: 测试类
class TestClass():
    var shape: 七边形实例，类型为 $heptagon_shape.HeptagonShape
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
        "src.ball.ball_entity.BallEntity": {"type": "class", "visibility": "public"}
    }
    
    proj_root_dict = {
        "src": {
            "ball": {
                "ball_entity": "球体实体文件"
            },
            "heptagon": {
                "heptagon_shape": "七边形文件"
            }
        }
    }
    
    dependent_relation = {
        "src/test": ["src/ball/ball_entity"],
        "src/other": ["src/heptagon/heptagon_shape"]
    }
    
    issue_recorder = IbcIssueRecorder()
    ast_dict, _, _ = analyze_ibc_code(ibc_code, issue_recorder)
    
    if not ast_dict:
        print(f"{Colors.FAIL}AST解析失败{Colors.ENDC}")
        return False
    
    resolver = SymbolRefResolver(
        ast_dict=ast_dict,
        symbols_tree=symbols_tree,
        symbols_metadata=symbols_metadata,
        ibc_issue_recorder=issue_recorder,
        proj_root_dict=proj_root_dict,
        dependent_relation=dependent_relation,
        current_file_path="src/test"
    )
    
    resolver.resolve_all_references()
    
    if not issue_recorder.has_issues():
        print(f"{Colors.FAIL}测试失败: 应该检测到模块未找到{Colors.ENDC}")
        return False
    
    # 场景2: 无效引用格式
    ibc_code2 = """module src.ball.ball_entity: 球体实体模块

description: 测试类
class TestClass():
    var invalid: 无效引用，类型为 $BallEntity
"""
    
    issue_recorder2 = IbcIssueRecorder()
    ast_dict2, _, _ = analyze_ibc_code(ibc_code2, issue_recorder2)
    
    if ast_dict2:
        resolver2 = SymbolRefResolver(
            ast_dict=ast_dict2,
            symbols_tree=symbols_tree,
            symbols_metadata=symbols_metadata,
            ibc_issue_recorder=issue_recorder2,
            proj_root_dict=proj_root_dict,
            dependent_relation=dependent_relation,
            current_file_path="src/test"
        )
        resolver2.resolve_all_references()
        
        if not issue_recorder2.has_issues():
            print(f"{Colors.FAIL}测试失败: 应该检测到引用格式错误{Colors.ENDC}")
            return False
    
    print(f"{Colors.OKGREEN}✓ 测试通过{Colors.ENDC}")
    return True


def test_external_library_reference():
    """测试2.3: 外部库引用和无导入检测"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试2.3: 外部库引用和无导入检测{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")
    
    # 场景1: 外部库引用
    ibc_code = """module numpy: 数值计算库

description: 测试类
class TestClass():
    var data: 数组，类型为 $numpy.ndarray
"""
    
    proj_root_dict = {
        "ExternalLibraryDependencies": {
            "numpy": "数值计算库"
        }
    }
    
    issue_recorder = IbcIssueRecorder()
    ast_dict, _, _ = analyze_ibc_code(ibc_code, issue_recorder)
    
    if not ast_dict:
        print(f"{Colors.FAIL}AST解析失败{Colors.ENDC}")
        return False
    
    resolver = SymbolRefResolver(
        ast_dict=ast_dict,
        symbols_tree={},
        symbols_metadata={},
        ibc_issue_recorder=issue_recorder,
        proj_root_dict=proj_root_dict,
        dependent_relation={"src/test": []},
        current_file_path="src/test"
    )
    
    resolver.resolve_all_references()
    
    if issue_recorder.has_issues():
        print(f"{Colors.FAIL}测试失败: 外部库引用不应该报错{Colors.ENDC}")
        return False
    
    # 场景2: 没有模块导入的情况
    ibc_code2 = """description: 测试类
class TestClass():
    var data: 数据，类型为 $ball_entity.BallEntity
"""
    
    proj_root_dict2 = {
        "src": {
            "ball": {
                "ball_entity": "球体实体文件"
            }
        }
    }
    
    issue_recorder2 = IbcIssueRecorder()
    ast_dict2, _, _ = analyze_ibc_code(ibc_code2, issue_recorder2)
    
    if ast_dict2:
        resolver2 = SymbolRefResolver(
            ast_dict=ast_dict2,
            symbols_tree={},
            symbols_metadata={},
            ibc_issue_recorder=issue_recorder2,
            proj_root_dict=proj_root_dict2,
            dependent_relation={"src/test": []},
            current_file_path="src/test"
        )
        resolver2.resolve_all_references()
        
        if not issue_recorder2.has_issues():
            print(f"{Colors.FAIL}测试失败: 应该检测到模块未导入{Colors.ENDC}")
            return False
    
    print(f"{Colors.OKGREEN}✓ 测试通过{Colors.ENDC}")
    return True


# ===========================
# 3. self引用验证测试
# ===========================

def test_self_reference_valid_and_invalid():
    """测试3.1: class中self引用（正确和错误场景）"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试3.1: self引用（正确/错误）{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")
    
    # 场景1: 正确self引用
    ibc_code1 = """description: 测试类
class TestClass():
    var internal_data: 内部数据
    var ball: 球体对象
    
    func test_method():
        数据 = self.internal_data
        结果 = self.ball.get_position()
"""
    
    issue_recorder1 = IbcIssueRecorder()
    ast_dict1, _, _ = analyze_ibc_code(ibc_code1, issue_recorder1)
    
    if ast_dict1:
        resolver1 = SymbolRefResolver(
            ast_dict=ast_dict1,
            symbols_tree={},
            symbols_metadata={},
            ibc_issue_recorder=issue_recorder1,
            proj_root_dict={},
            dependent_relation={"src/test": []},
            current_file_path="src/test"
        )
        resolver1.resolve_all_references()
        
        if issue_recorder1.has_issues():
            print(f"{Colors.FAIL}测试失败: 正确self引用不应该报错{Colors.ENDC}")
            return False
    
    # 场景2: 错误的self引用
    ibc_code2 = """description: 测试类
class TestClass():
    var internal_data: 内部数据
    
    func test_method():
        # invalid_var在类中未定义
        数据 = self.invalid_var
"""
    
    issue_recorder2 = IbcIssueRecorder()
    ast_dict2, _, _ = analyze_ibc_code(ibc_code2, issue_recorder2)
    
    if ast_dict2:
        resolver2 = SymbolRefResolver(
            ast_dict=ast_dict2,
            symbols_tree={},
            symbols_metadata={},
            ibc_issue_recorder=issue_recorder2,
            proj_root_dict={},
            dependent_relation={"src/test": []},
            current_file_path="src/test"
        )
        resolver2.resolve_all_references()
        
        if not issue_recorder2.has_issues():
            print(f"{Colors.FAIL}测试失败: 应该检测到self引用错误{Colors.ENDC}")
            return False
    
    print(f"{Colors.OKGREEN}✓ 测试通过{Colors.ENDC}")
    return True


def test_scope_visibility():
    """测试3.2: 作用域可见性（局部变量作用域隔离）"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试3.2: 作用域可见性{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")
    
    ibc_code = """description: 测试类
class TestClass():
    var class_var: 类变量
    
    func method_a(param_a: 参数A):
        var local_var_a: 局部变量A
        数据1 = self.class_var
        数据2 = self.param_a
        数据3 = self.local_var_a
    
    func method_b():
        # 不应该能访问method_a的局部变量
        数据 = self.local_var_a
"""
    
    symbols_tree = {}
    symbols_metadata = {}
    proj_root_dict = {}
    dependent_relation = {"src/test": []}
    
    issue_recorder = IbcIssueRecorder()
    ast_dict, _, _ = analyze_ibc_code(ibc_code, issue_recorder)
    
    if not ast_dict:
        print(f"{Colors.FAIL}AST解析失败{Colors.ENDC}")
        return False
    
    resolver = SymbolRefResolver(
        ast_dict=ast_dict,
        symbols_tree=symbols_tree,
        symbols_metadata=symbols_metadata,
        ibc_issue_recorder=issue_recorder,
        proj_root_dict=proj_root_dict,
        dependent_relation=dependent_relation,
        current_file_path="src/test"
    )
    
    resolver.resolve_all_references()
    
    if issue_recorder.has_issues():
        issues = issue_recorder.get_issues()
        has_local_var_error = any("local_var_a" in issue.message for issue in issues)
        if has_local_var_error:
            print(f"{Colors.OKGREEN}✓ 测试通过: 正确检测到跨作用域访问错误{Colors.ENDC}")
            return True
        else:
            print(f"{Colors.FAIL}测试失败: 未检测到local_var_a的作用域错误{Colors.ENDC}")
            return False
    else:
        print(f"{Colors.FAIL}测试失败: 应该检测到作用域访问错误{Colors.ENDC}")
        return False


# ===========================
# 4. 本地符号的$引用测试
# ===========================

def test_local_symbol_dollar_reference():
    """测试4.1: 本地符号的$引用"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试4.1: 本地符号的$引用{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")
    
    ibc_code = """
description: 测试本地符号引用

class Ball():
    var position_x: float
    var position_y: float
    
    func update_position(delta_x: float, delta_y: float):
        新x = $Ball.position_x + delta_x
        新y = $Ball.position_y + delta_y
"""
    
    issue_recorder = IbcIssueRecorder()
    ast_dict, symbols_tree, symbols_metadata = analyze_ibc_code(ibc_code, issue_recorder)
    
    if not ast_dict:
        print(f"{Colors.FAIL}IBC代码解析失败{Colors.ENDC}")
        return False
    
    # 构建包含本地符号的可见符号树
    proj_root_dict = {"src": {"test": "测试模块"}}
    builder = VisibleSymbolBuilder(proj_root_dict)
    
    visible_symbols_tree, visible_symbols_metadata = builder.build_visible_symbol_tree(
        current_file_path="src/test",
        dependency_symbol_tables={},
        include_local_symbols=True,
        local_symbols_tree=symbols_tree,
        local_symbols_metadata=symbols_metadata
    )
    
    # 验证符号引用
    issue_recorder.clear()
    ref_resolver = SymbolRefResolver(
        ast_dict=ast_dict,
        symbols_tree=visible_symbols_tree,
        symbols_metadata=visible_symbols_metadata,
        ibc_issue_recorder=issue_recorder,
        proj_root_dict=proj_root_dict,
        dependent_relation={},
        current_file_path="src/test"
    )
    ref_resolver.resolve_all_references()
    
    issues = issue_recorder.get_issues()
    if issues:
        print(f"{Colors.FAIL}测试失败: 本地符号$引用不应该报错{Colors.ENDC}")
        for issue in issues:
            print(f"  - {issue.message}")
        return False
    
    print(f"{Colors.OKGREEN}✓ 测试通过{Colors.ENDC}")
    return True


def test_local_symbol_reference_before_after():
    """测试4.2: 包含本地符号前后的差异对比"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试4.2: 包含本地符号前后的差异对比{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")
    
    ibc_code = """
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
    ast_dict, symbols_tree, symbols_metadata = analyze_ibc_code(ibc_code, issue_recorder)
    
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
# 5. 边界条件和错误处理测试
# ===========================

def test_mixed_external_internal_and_params():
    """测试5.1: 混合引用（外部+内部+参数类型）"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试5.1: 混合引用{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")
    
    ibc_code = """module numpy: 数值计算库
module src.ball.ball_entity: 球体实体模块

description: 测试类
class TestClass():
    var data: 数组，类型为 $numpy.ndarray
    var ball: 球体实例，类型为 $ball_entity.BallEntity
    
    func process_ball(球体参数: 球体对象，类型为 $ball_entity.BallEntity):
        处理球体逻辑
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
        "src.ball.ball_entity.BallEntity": {"type": "class", "visibility": "public"}
    }
    
    proj_root_dict = {
        "ExternalLibraryDependencies": {
            "numpy": "数值计算库"
        },
        "src": {
            "ball": {
                "ball_entity": "球体实体文件"
            }
        }
    }
    
    dependent_relation = {"src/test": ["src/ball/ball_entity"]}
    
    issue_recorder = IbcIssueRecorder()
    ast_dict, _, _ = analyze_ibc_code(ibc_code, issue_recorder)
    
    if not ast_dict:
        print(f"{Colors.FAIL}AST解析失败{Colors.ENDC}")
        return False
    
    resolver = SymbolRefResolver(
        ast_dict=ast_dict,
        symbols_tree=symbols_tree,
        symbols_metadata=symbols_metadata,
        ibc_issue_recorder=issue_recorder,
        proj_root_dict=proj_root_dict,
        dependent_relation=dependent_relation,
        current_file_path="src/test"
    )
    
    resolver.resolve_all_references()
    
    if issue_recorder.has_issues():
        print(f"{Colors.FAIL}测试失败: 混合引用不应该报错{Colors.ENDC}")
        for issue in issue_recorder.get_issues():
            print(f"  - {issue.message}")
        return False
    
    print(f"{Colors.OKGREEN}✓ 测试通过{Colors.ENDC}")
    return True


def run_all_tests():
    """运行所有测试"""
    print(f"\n{Colors.OKBLUE}{'='*70}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}局部符号和符号引用解析器综合测试{Colors.ENDC}")
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
        test_results.append(("2.2 模块未找到和无效格式", test_module_not_found_and_invalid_format()))
        test_results.append(("2.3 外部库引用和无导入", test_external_library_reference()))
        
        # 3. self引用验证测试
        print(f"\n{Colors.OKBLUE}{'#'*70}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}# 3. self引用验证测试{Colors.ENDC}")
        print(f"{Colors.OKBLUE}{'#'*70}{Colors.ENDC}")
        test_results.append(("3.1 self引用（正确/错误）", test_self_reference_valid_and_invalid()))
        test_results.append(("3.2 作用域可见性", test_scope_visibility()))
        
        # 4. 本地符号的$引用测试
        print(f"\n{Colors.OKBLUE}{'#'*70}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}# 4. 本地符号的$引用测试{Colors.ENDC}")
        print(f"{Colors.OKBLUE}{'#'*70}{Colors.ENDC}")
        test_results.append(("4.1 本地符号$引用", test_local_symbol_dollar_reference()))
        test_results.append(("4.2 包含本地符号前后对比", test_local_symbol_reference_before_after()))
        
        # 5. 边界条件测试
        print(f"\n{Colors.OKBLUE}{'#'*70}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}# 5. 边界条件和错误处理测试{Colors.ENDC}")
        print(f"{Colors.OKBLUE}{'#'*70}{Colors.ENDC}")
        test_results.append(("5.1 混合引用", test_mixed_external_internal_and_params()))
        
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
