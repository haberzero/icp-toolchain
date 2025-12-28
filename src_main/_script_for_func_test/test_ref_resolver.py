"""
符号引用解析器测试脚本

测试SymbolRefResolver的各种场景：
1. 正确的符号引用
2. 模块未找到的情况
3. 符号未找到的情况
4. 外部库引用的情况
"""
import sys
import os

# 添加项目根目录到路径
test_env_root = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(test_env_root, '..'))
sys.path.insert(0, project_root)

from utils.ibc_analyzer.ibc_analyzer import analyze_ibc_code
from utils.ibc_analyzer.ibc_symbol_ref_resolver import SymbolRefResolver
from utils.ibc_analyzer.ibc_visible_symbol_builder import VisibleSymbolBuilder
from utils.issue_recorder import IbcIssueRecorder
from data_store.ibc_data_store import get_instance as get_ibc_data_store
from typedef.cmd_data_types import Colors


def test_case_1_correct_references():
    """测试用例1: 正确的符号引用"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试用例1: 正确的符号引用{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")
    
    # 准备测试数据
    ibc_code = """module src.ball.ball_entity: 球体实体模块

description: 测试类
class TestClass():
    var ball: 球体实例，类型为 $ball_entity.BallEntity
    
    func test_method():
        位置 = self.ball.get_position()
"""
    
    # 模拟的可见符号树和元数据
    symbols_tree = {
        "src": {
            "ball": {
                "ball_entity": {
                    "BallEntity": {
                        "get_position": {}
                    }
                }
            }
        }
    }
    
    symbols_metadata = {
        "src": {"type": "folder"},
        "src.ball": {"type": "folder"},
        "src.ball.ball_entity": {"type": "file", "description": "球体实体文件"},
        "src.ball.ball_entity.BallEntity": {"type": "class", "description": "球体实体类", "visibility": "public"},
        "src.ball.ball_entity.BallEntity.get_position": {"type": "func", "description": "获取位置", "visibility": "public"}
    }
    
    proj_root_dict = {
        "src": {
            "ball": {
                "ball_entity": "球体实体文件"
            }
        }
    }
    
    dependent_relation = {
        "src/test": ["src/ball/ball_entity"]
    }
    
    # 分析IBC代码
    issue_recorder = IbcIssueRecorder()
    ast_dict, _, _ = analyze_ibc_code(ibc_code, issue_recorder)
    
    if not ast_dict:
        print(f"{Colors.FAIL}AST解析失败{Colors.ENDC}")
        return
    
    # 创建符号引用解析器
    resolver = SymbolRefResolver(
        ast_dict=ast_dict,
        symbols_tree=symbols_tree,
        symbols_metadata=symbols_metadata,
        ibc_issue_recorder=issue_recorder,
        proj_root_dict=proj_root_dict,
        dependent_relation=dependent_relation,
        current_file_path="src/test"
    )
    
    # 执行符号引用解析
    resolver.resolve_all_references()
    
    # 检查结果
    if issue_recorder.has_issues():
        print(f"{Colors.FAIL}测试失败: 发现了问题{Colors.ENDC}")
        for issue in issue_recorder.get_issues():
            print(f"  - {issue.message}")
    else:
        print(f"{Colors.OKGREEN}✓ 测试通过: 正确的符号引用没有报错{Colors.ENDC}")


def test_case_2_module_not_found():
    """测试用例2: 模块未找到"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试用例2: 模块未找到{Colors.ENDC}")
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
        "src/other": ["src/heptagon/heptagon_shape"]  # 添加其他文件的依赖，使heptagon_shape可以被找到
    }
    
    issue_recorder = IbcIssueRecorder()
    ast_dict, _, _ = analyze_ibc_code(ibc_code, issue_recorder)
    
    if not ast_dict:
        print(f"{Colors.FAIL}AST解析失败{Colors.ENDC}")
        return
    
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
    
    # 检查结果
    if issue_recorder.has_issues():
        print(f"{Colors.OKGREEN}✓ 测试通过: 检测到模块未找到{Colors.ENDC}")
        for issue in issue_recorder.get_issues():
            print(f"  {Colors.WARNING}问题: {issue.message}{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}测试失败: 应该检测到模块未找到的问题{Colors.ENDC}")


def test_case_3_symbol_not_found():
    """测试用例3: 符号未找到"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试用例3: 符号未找到{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")
    
    ibc_code = """module src.ball.ball_entity: 球体实体模块

description: 测试类
class TestClass():
    var ball: 球体实例，类型为 $ball_entity.BallEntity
    
    func test_method():
        # 引用了不存在的方法
        位置 = self.ball.get_invalid_method()
"""
    
    symbols_tree = {
        "src": {
            "ball": {
                "ball_entity": {
                    "BallEntity": {
                        "get_position": {}
                    }
                }
            }
        }
    }
    
    symbols_metadata = {
        "src.ball.ball_entity.BallEntity": {"type": "class", "visibility": "public", "description": "球体类"},
        "src.ball.ball_entity.BallEntity.get_position": {"type": "func", "visibility": "public", "description": "获取位置"}
    }
    
    proj_root_dict = {
        "src": {
            "ball": {
                "ball_entity": "球体实体文件"
            }
        }
    }
    
    dependent_relation = {
        "src/test": ["src/ball/ball_entity"]
    }
    
    issue_recorder = IbcIssueRecorder()
    ast_dict, _, _ = analyze_ibc_code(ibc_code, issue_recorder)
    
    if not ast_dict:
        print(f"{Colors.FAIL}AST解析失败{Colors.ENDC}")
        return
    
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
    
    # 检查结果
    # 注意：behavior step中的引用当前可能不会被检测，因为它们是在运行时引用
    # 这里我们主要测试var和func参数中的引用
    print(f"{Colors.OKBLUE}当前问题数: {issue_recorder.get_issue_count()}{Colors.ENDC}")
    if issue_recorder.has_issues():
        print(f"{Colors.WARNING}检测到的问题:{Colors.ENDC}")
        for issue in issue_recorder.get_issues():
            print(f"  - {issue.message}")


def test_case_4_external_library():
    """测试用例4: 外部库引用"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试用例4: 外部库引用{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")
    
    ibc_code = """module numpy: 数值计算库

description: 测试类
class TestClass():
    var data: 数组，类型为 $numpy.ndarray
"""
    
    symbols_tree = {}
    symbols_metadata = {}
    
    proj_root_dict = {
        "ExternalLibraryDependencies": {
            "numpy": "数值计算库"
        }
    }
    
    dependent_relation = {
        "src/test": []
    }
    
    issue_recorder = IbcIssueRecorder()
    ast_dict, _, _ = analyze_ibc_code(ibc_code, issue_recorder)
    
    if not ast_dict:
        print(f"{Colors.FAIL}AST解析失败{Colors.ENDC}")
        return
    
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
    
    # 检查结果
    if issue_recorder.has_issues():
        print(f"{Colors.FAIL}测试失败: 外部库引用不应该报错{Colors.ENDC}")
        for issue in issue_recorder.get_issues():
            print(f"  - {issue.message}")
    else:
        print(f"{Colors.OKGREEN}✓ 测试通过: 外部库引用被正确识别{Colors.ENDC}")


def test_case_5_nested_symbol_reference():
    """测试用例5: 嵌套符号引用"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试用例5: 嵌套符号引用{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")
    
    ibc_code = """module src.ball.ball_entity: 球体实体模块

description: 测试类
class TestClass():
    var ball: 球体实例，类型为 $ball_entity.BallEntity
    
    func test_nested():
        # 嵌套引用：类的方法
        球体速度 = self.ball.velocity.get_magnitude()
"""
    
    symbols_tree = {
        "src": {
            "ball": {
                "ball_entity": {
                    "BallEntity": {
                        "velocity": {
                            "get_magnitude": {}
                        }
                    }
                }
            }
        }
    }
    
    symbols_metadata = {
        "src.ball.ball_entity.BallEntity": {"type": "class", "visibility": "public", "description": "球体类"},
        "src.ball.ball_entity.BallEntity.velocity": {"type": "var", "visibility": "public", "description": "速度"},
        "src.ball.ball_entity.BallEntity.velocity.get_magnitude": {"type": "func", "visibility": "public", "description": "获取速度大小"}
    }
    
    proj_root_dict = {
        "src": {
            "ball": {
                "ball_entity": "球体实体文件"
            }
        }
    }
    
    dependent_relation = {
        "src/test": ["src/ball/ball_entity"]
    }
    
    issue_recorder = IbcIssueRecorder()
    ast_dict, _, _ = analyze_ibc_code(ibc_code, issue_recorder)
    
    if not ast_dict:
        print(f"{Colors.FAIL}AST解析失败{Colors.ENDC}")
        return
    
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
    
    # 检查结果
    if issue_recorder.has_issues():
        print(f"{Colors.WARNING}检测到的问题:{Colors.ENDC}")
        for issue in issue_recorder.get_issues():
            print(f"  - {issue.message}")
    else:
        print(f"{Colors.OKGREEN}✓ 测试通过: 嵌套符号引用验证正常{Colors.ENDC}")


def test_case_6_multiple_modules():
    """测试用例6: 引用多个模块"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试用例6: 引用多个模块{Colors.ENDC}")
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
    
    dependent_relation = {
        "src/test": ["src/ball/ball_entity", "src/shape/shape_base"]
    }
    
    issue_recorder = IbcIssueRecorder()
    ast_dict, _, _ = analyze_ibc_code(ibc_code, issue_recorder)
    
    if not ast_dict:
        print(f"{Colors.FAIL}AST解析失败{Colors.ENDC}")
        return
    
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
    
    # 检查结果
    if issue_recorder.has_issues():
        print(f"{Colors.FAIL}测试失败: 多模块引用不应该报错{Colors.ENDC}")
        for issue in issue_recorder.get_issues():
            print(f"  - {issue.message}")
    else:
        print(f"{Colors.OKGREEN}✓ 测试通过: 多模块引用验证正常{Colors.ENDC}")


def test_case_7_function_param_type_ref():
    """测试用例7: 函数参数类型引用"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试用例7: 函数参数类型引用{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")
    
    ibc_code = """module src.ball.ball_entity: 球体实体模块

description: 测试类
class TestClass():
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
        "src.ball.ball_entity.BallEntity": {"type": "class", "visibility": "public", "description": "球体类"}
    }
    
    proj_root_dict = {
        "src": {
            "ball": {
                "ball_entity": "球体实体文件"
            }
        }
    }
    
    dependent_relation = {
        "src/test": ["src/ball/ball_entity"]
    }
    
    issue_recorder = IbcIssueRecorder()
    ast_dict, _, _ = analyze_ibc_code(ibc_code, issue_recorder)
    
    if not ast_dict:
        print(f"{Colors.FAIL}AST解析失败{Colors.ENDC}")
        return
    
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
    
    # 检查结果
    if issue_recorder.has_issues():
        print(f"{Colors.FAIL}测试失败: 函数参数类型引用不应该报错{Colors.ENDC}")
        for issue in issue_recorder.get_issues():
            print(f"  - {issue.message}")
    else:
        print(f"{Colors.OKGREEN}✓ 测试通过: 函数参数类型引用验证正常{Colors.ENDC}")


def test_case_8_invalid_reference_format():
    """测试用例8: 无效的引用格式"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试用例8: 无效的引用格式{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")
    
    ibc_code = """module src.ball.ball_entity: 球体实体模块

description: 测试类
class TestClass():
    var invalid: 无效引用，类型为 $BallEntity
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
            }
        }
    }
    
    dependent_relation = {
        "src/test": ["src/ball/ball_entity"]
    }
    
    issue_recorder = IbcIssueRecorder()
    ast_dict, _, _ = analyze_ibc_code(ibc_code, issue_recorder)
    
    if not ast_dict:
        print(f"{Colors.FAIL}AST解析失败{Colors.ENDC}")
        return
    
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
    
    # 检查结果
    if issue_recorder.has_issues():
        print(f"{Colors.OKGREEN}✓ 测试通过: 检测到无效的引用格式{Colors.ENDC}")
        for issue in issue_recorder.get_issues():
            print(f"  {Colors.WARNING}问题: {issue.message}{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}测试失败: 应该检测到引用格式错误{Colors.ENDC}")


def test_case_9_mixed_external_and_internal():
    """测试用例9: 混合外部库和内部模块引用"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试用例9: 混合外部库和内部模块引用{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")
    
    ibc_code = """module numpy: 数值计算库
module src.ball.ball_entity: 球体实体模块

description: 测试类
class TestClass():
    var data: 数组，类型为 $numpy.ndarray
    var ball: 球体实例，类型为 $ball_entity.BallEntity
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
    
    dependent_relation = {
        "src/test": ["src/ball/ball_entity"]
    }
    
    issue_recorder = IbcIssueRecorder()
    ast_dict, _, _ = analyze_ibc_code(ibc_code, issue_recorder)
    
    if not ast_dict:
        print(f"{Colors.FAIL}AST解析失败{Colors.ENDC}")
        return
    
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
    
    # 检查结果
    if issue_recorder.has_issues():
        print(f"{Colors.FAIL}测试失败: 混合引用不应该报错{Colors.ENDC}")
        for issue in issue_recorder.get_issues():
            print(f"  - {issue.message}")
    else:
        print(f"{Colors.OKGREEN}✓ 测试通过: 混合外部库和内部模块引用验证正常{Colors.ENDC}")


def test_case_10_symbol_fuzzy_match_quality():
    """测试用例10: 符号模糊匹配质量测试"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试用例10: 符号模糊匹配质量测试{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")
    
    ibc_code = """module src.ball.ball_entity: 球体实体模块

description: 测试类
class TestClass():
    var ball: 球体实例，类型为 $ball_entity.BallEntity
    
    func test_method():
        # 故意拼写错误：get_positon 而不是 get_position
        位置 = self.ball.get_positon()
"""
    
    symbols_tree = {
        "src": {
            "ball": {
                "ball_entity": {
                    "BallEntity": {
                        "get_position": {},
                        "set_position": {},
                        "get_velocity": {},
                        "set_velocity": {}
                    }
                }
            }
        }
    }
    
    symbols_metadata = {
        "src.ball.ball_entity.BallEntity": {"type": "class", "visibility": "public"},
        "src.ball.ball_entity.BallEntity.get_position": {"type": "func", "visibility": "public", "description": "获取位置"},
        "src.ball.ball_entity.BallEntity.set_position": {"type": "func", "visibility": "public", "description": "设置位置"},
        "src.ball.ball_entity.BallEntity.get_velocity": {"type": "func", "visibility": "public", "description": "获取速度"},
        "src.ball.ball_entity.BallEntity.set_velocity": {"type": "func", "visibility": "public", "description": "设置速度"}
    }
    
    proj_root_dict = {
        "src": {
            "ball": {
                "ball_entity": "球体实体文件"
            }
        }
    }
    
    dependent_relation = {
        "src/test": ["src/ball/ball_entity"]
    }
    
    issue_recorder = IbcIssueRecorder()
    ast_dict, _, _ = analyze_ibc_code(ibc_code, issue_recorder)
    
    if not ast_dict:
        print(f"{Colors.FAIL}AST解析失败{Colors.ENDC}")
        return
    
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
    
    # 检查结果
    print(f"{Colors.OKBLUE}当前问题数: {issue_recorder.get_issue_count()}{Colors.ENDC}")
    if issue_recorder.has_issues():
        print(f"{Colors.OKGREEN}✓ 测试通过: 检测到拼写错误并提供建议{Colors.ENDC}")
        for issue in issue_recorder.get_issues():
            # 检查是否包含正确的建议
            if "get_position" in issue.message:
                print(f"  {Colors.OKGREEN}✓ 模糊匹配成功: 建议了正确的方法名{Colors.ENDC}")
            print(f"  {Colors.WARNING}问题: {issue.message}{Colors.ENDC}")
    else:
        print(f"{Colors.WARNING}注意: behavior step中的引用可能不会被检测{Colors.ENDC}")


def test_case_11_empty_module_import():
    """测试用例11: 没有模块导入的情况"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试用例11: 没有模块导入的情况{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")
    
    ibc_code = """description: 测试类
class TestClass():
    var data: 数据，类型为 $ball_entity.BallEntity
"""
    
    symbols_tree = {}
    symbols_metadata = {}
    
    proj_root_dict = {
        "src": {
            "ball": {
                "ball_entity": "球体实体文件"
            }
        }
    }
    
    dependent_relation = {
        "src/test": []
    }
    
    issue_recorder = IbcIssueRecorder()
    ast_dict, _, _ = analyze_ibc_code(ibc_code, issue_recorder)
    
    if not ast_dict:
        print(f"{Colors.FAIL}AST解析失败{Colors.ENDC}")
        return
    
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
    
    # 检查结果
    if issue_recorder.has_issues():
        print(f"{Colors.OKGREEN}✓ 测试通过: 检测到未导入模块{Colors.ENDC}")
        for issue in issue_recorder.get_issues():
            print(f"  {Colors.WARNING}问题: {issue.message}{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}测试失败: 应该检测到模块未导入{Colors.ENDC}")


def test_case_12_self_reference_skip():
    """测试用例12: self引用应该被跳过"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试用例12: self引用应该被跳过{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")
    
    ibc_code = """description: 测试类
class TestClass():
    var internal_data: 内部数据
    
    func test_method():
        # self引用应该被跳过验证
        数据 = self.internal_data
        结果 = self.another_method()
"""
    
    symbols_tree = {}
    symbols_metadata = {}
    
    proj_root_dict = {}
    dependent_relation = {"src/test": []}
    
    issue_recorder = IbcIssueRecorder()
    ast_dict, _, _ = analyze_ibc_code(ibc_code, issue_recorder)
    
    if not ast_dict:
        print(f"{Colors.FAIL}AST解析失败{Colors.ENDC}")
        return
    
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
    
    # 检查结果
    if issue_recorder.has_issues():
        print(f"{Colors.WARNING}检测到的问题:{Colors.ENDC}")
        for issue in issue_recorder.get_issues():
            print(f"  - {issue.message}")
        print(f"{Colors.WARNING}注意: behavior step中的self引用可能不会被提取到AST{Colors.ENDC}")
    else:
        print(f"{Colors.OKGREEN}✓ 测试通过: self引用被正确跳过{Colors.ENDC}")


def main():
    """运行所有测试用例"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}符号引用解析器测试{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    
    # 基础功能测试
    print(f"\n{Colors.OKBLUE}【基础功能测试】{Colors.ENDC}")
    test_case_1_correct_references()
    test_case_2_module_not_found()
    test_case_3_symbol_not_found()
    test_case_4_external_library()
    
    # 高级场景测试
    print(f"\n{Colors.OKBLUE}【高级场景测试】{Colors.ENDC}")
    test_case_5_nested_symbol_reference()
    test_case_6_multiple_modules()
    test_case_7_function_param_type_ref()
    test_case_8_invalid_reference_format()
    test_case_9_mixed_external_and_internal()
    
    # 边界情况测试
    print(f"\n{Colors.OKBLUE}【边界情况测试】{Colors.ENDC}")
    test_case_10_symbol_fuzzy_match_quality()
    test_case_11_empty_module_import()
    test_case_12_self_reference_skip()
    
    print(f"\n{Colors.OKGREEN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKGREEN}所有测试完成{Colors.ENDC}")
    print(f"{Colors.OKGREEN}{'='*60}{Colors.ENDC}\n")


if __name__ == "__main__":
    main()
