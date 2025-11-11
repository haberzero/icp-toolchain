import json
import sys
import os

# 正确添加src_main目录到sys.path，以便能够导入libs中的模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from libs.dir_json_funcs import DirJsonFuncs

def test_detect_circular_dependencies():
    """测试循环依赖检测功能"""
    print("测试 detect_circular_dependencies 函数...")
    
    # 测试用例1: 存在循环依赖
    dependencies_with_cycle = {
        "src/controllers/PhysicsEngine": [
            "src/models/Ball",
            "src/models/Heptagon",
            "src/controllers/CollisionDetector"
        ],
        "src/controllers/CollisionDetector": [
            "src/models/Ball",
            "src/models/Heptagon"
        ],
        "src/services/Renderer": [
            "src/models/Ball",
            "src/models/Heptagon",
            "src/views/SimulationLoop"
        ],
        "src/views/SimulationLoop": [
            "src/controllers/PhysicsEngine",
            "src/services/Renderer"
        ]
    }
    
    cycles = DirJsonFuncs.detect_circular_dependencies(dependencies_with_cycle)
    assert len(cycles) > 0, "应该检测到循环依赖"
    print(f"  ✓ 成功检测到循环依赖: {cycles}")
    
    # 测试用例2: 无循环依赖
    dependencies_without_cycle = {
        "src/controllers/PhysicsEngine": [
            "src/models/Ball",
            "src/models/Heptagon",
            "src/controllers/CollisionDetector"
        ],
        "src/controllers/CollisionDetector": [
            "src/models/Ball",
            "src/models/Heptagon"
        ],
        "src/services/Renderer": [
            "src/models/Ball",
            "src/models/Heptagon"
        ],
        "src/views/SimulationLoop": [
            "src/controllers/PhysicsEngine"
        ],
        "src/models/Ball": [],
        "src/models/Heptagon": []
    }
    
    cycles = DirJsonFuncs.detect_circular_dependencies(dependencies_without_cycle)
    assert len(cycles) == 0, "不应该检测到循环依赖"
    print("  ✓ 成功确认无循环依赖")

def test_ensure_all_files_in_dependent_relation():
    """测试确保所有文件在依赖关系中"""
    print("测试 ensure_all_files_in_dependent_relation 函数...")
    
    # 测试用例: 包含文件但缺少依赖关系条目的JSON
    json_content = {
        "proj_root": {
            "src": {
                "models": {
                    "Heptagon": "管理正七边形几何属性与边界检测",
                    "Ball": "封装球体物理状态与自转渲染逻辑"
                },
                "controllers": {
                    "PhysicsEngine": "实现重力、摩擦与碰撞响应算法",
                    "CollisionDetector": "处理球-球、球-边界的碰撞判定"
                },
                "services": {
                    "Renderer": "使用tkinter绘制场景与动态刷新画面"
                },
                "views": {
                    "SimulationLoop": "控制主循环与时间步长更新"
                }
            },
            "config": {}
        },
        "dependent_relation": {
            "src/controllers/PhysicsEngine": [
                "src/models/Ball",
                "src/models/Heptagon",
                "src/controllers/CollisionDetector"
            ]
        }
    }
    
    # 检查修改前的dependent_relation大小
    original_size = len(json_content["dependent_relation"])
    
    # 执行函数
    modified = DirJsonFuncs.ensure_all_files_in_dependent_relation(json_content)
    
    # 验证结果
    assert modified, "应该对JSON内容进行了修改"
    assert len(json_content["dependent_relation"]) > original_size, "dependent_relation应该增加了条目"
    
    # 验证所有文件都有对应的依赖关系条目
    expected_files = {
        "src/models/Heptagon",
        "src/models/Ball",
        "src/controllers/PhysicsEngine",
        "src/controllers/CollisionDetector",
        "src/services/Renderer",
        "src/views/SimulationLoop"
    }
    
    actual_files = set(json_content["dependent_relation"].keys())
    assert expected_files.issubset(actual_files), "所有文件都应该在dependent_relation中有条目"
    print("  ✓ 成功为缺失的文件添加了依赖关系条目")


def test_build_file_creation_order():
    """测试文件创建顺序构建功能"""
    print("测试 build_file_creation_order 函数...")
    
    dependencies = {
        "src/controllers/PhysicsEngine": [
            "src/models/Ball",
            "src/models/Heptagon",
            "src/controllers/CollisionDetector"
        ],
        "src/controllers/CollisionDetector": [
            "src/models/Ball",
            "src/models/Heptagon"
        ],
        "src/services/Renderer": [
            "src/models/Ball",
            "src/models/Heptagon"
        ],
        "src/views/SimulationLoop": [
            "src/controllers/PhysicsEngine"
        ],
        "src/models/Ball": [],
        "src/models/Heptagon": []
    }
    
    order = DirJsonFuncs.build_file_creation_order(dependencies)
    assert len(order) == len(dependencies), "创建顺序应该包含所有文件"
    
    # 验证规则2: has_in_no_out (Ball, Heptagon) 在 has_in_has_out (CollisionDetector, PhysicsEngine) 之前
    ball_index = order.index("src/models/Ball")
    heptagon_index = order.index("src/models/Heptagon")
    collision_detector_index = order.index("src/controllers/CollisionDetector")
    physics_engine_index = order.index("src/controllers/PhysicsEngine")
    
    assert collision_detector_index > ball_index, "CollisionDetector应该在Ball之后"
    assert collision_detector_index > heptagon_index, "CollisionDetector应该在Heptagon之后"
    assert physics_engine_index > collision_detector_index, "PhysicsEngine应该在CollisionDetector之后"
    
    # 验证规则4: no_in_has_out (Renderer, SimulationLoop) 在最后
    renderer_index = order.index("src/services/Renderer")
    simulation_loop_index = order.index("src/views/SimulationLoop")
    
    assert renderer_index > physics_engine_index, "Renderer应该在PhysicsEngine之后"
    assert simulation_loop_index > physics_engine_index, "SimulationLoop应该在PhysicsEngine之后"
    
    print("  ✓ 成功构建了正确的文件创建顺序")
    print(f"  创建顺序: {order}")

def test_topological_sort():
    """测试拓扑排序功能"""
    print("测试 topological_sort 函数...")
    
    dependencies = {
        "A": ["B", "C"],
        "B": ["D"],
        "C": ["D"],
        "D": []
    }
    
    files = ["A", "B", "C", "D"]
    sorted_files = DirJsonFuncs._topological_sort(dependencies, files)
    
    # 验证排序结果
    assert len(sorted_files) == 4, "排序结果应该包含所有文件"
    assert sorted_files[-1] == "A", "A依赖其他文件，应该排在最后"
    assert sorted_files[0] == "D", "D没有依赖，应该排在最前"
    
    # B和C依赖D，应该在D之后
    d_index = sorted_files.index("D")
    b_index = sorted_files.index("B")
    c_index = sorted_files.index("C")
    assert b_index > d_index, "B应该在D之后"
    assert c_index > d_index, "C应该在D之后"
    
    print("  ✓ 成功完成了拓扑排序")
    print(f"  排序结果: {sorted_files}")

def test_compare_structure():
    """测试结构比较功能"""
    print("测试 compare_structure 函数...")
    
    # 测试用例1: 相同结构
    old_structure = {
        "src": {
            "models": {},
            "controllers": {}
        },
        "config": {}
    }
    
    new_structure = {
        "src": {
            "models": {
                "Ball": "封装球体物理状态与自转渲染逻辑"
            },
            "controllers": {}
        },
        "config": {}
    }
    
    result = DirJsonFuncs.compare_structure(old_structure, new_structure)
    assert result, "结构应该匹配"
    print("  ✓ 成功比较了结构一致性")
    
    # 测试用例2: 不同结构
    different_structure = {
        "src": {
            "models": {},
            "views": {}  # 原来是controllers，现在是views
        },
        "config": {}
    }
    
    result = DirJsonFuncs.compare_structure(old_structure, different_structure)
    assert not result, "结构应该不匹配"
    print("  ✓ 成功检测到结构不一致")

def test_collect_paths():
    """测试路径收集功能"""
    print("测试 collect_paths 函数...")
    
    proj_root = {
        "src": {
            "models": {
                "Heptagon": "管理正七边形几何属性与边界检测",
                "Ball": "封装球体物理状态与自转渲染逻辑"
            },
            "controllers": {
                "PhysicsEngine": "实现重力、摩擦与碰撞响应算法"
            }
        },
        "config": {
            "settings": "应用程序配置"
        }
    }
    
    paths = DirJsonFuncs._collect_paths(proj_root)
    expected_paths = {
        "src/models/Heptagon",
        "src/models/Ball",
        "src/controllers/PhysicsEngine",
        "config/settings"
    }
    
    assert paths == expected_paths, f"收集的路径应该匹配预期: {expected_paths}"
    print("  ✓ 成功收集了所有文件路径")
    print(f"  收集到的路径: {paths}")

def test_validate_dependent_paths():
    """测试依赖路径验证功能"""
    print("测试 validate_dependent_paths 函数...")
    
    proj_root = {
        "src": {
            "models": {
                "Heptagon": "管理正七边形几何属性与边界检测",
                "Ball": "封装球体物理状态与自转渲染逻辑"
            },
            "controllers": {
                "PhysicsEngine": "实现重力、摩擦与碰撞响应算法"
            }
        }
    }
    
    # 测试用例1: 有效的依赖关系
    valid_dependent_relation = {
        "src/controllers/PhysicsEngine": [
            "src/models/Ball",
            "src/models/Heptagon"
        ]
    }
    
    result = DirJsonFuncs.validate_dependent_paths(valid_dependent_relation, proj_root)
    assert result, "依赖路径应该有效"
    print("  ✓ 成功验证了有效的依赖路径")
    
    # 测试用例2: 无效的依赖关系
    invalid_dependent_relation = {
        "src/controllers/PhysicsEngine": [
            "src/models/NonExistentFile"  # 不存在的文件
        ]
    }
    
    result = DirJsonFuncs.validate_dependent_paths(invalid_dependent_relation, proj_root)
    assert not result, "依赖路径应该无效"
    print("  ✓ 成功检测到无效的依赖路径")

def test_check_new_nodes_are_strings():
    """测试检查新节点是否为字符串功能"""
    print("测试 check_new_nodes_are_strings 函数...")
    
    # 测试用例1: 所有新节点都是字符串（正确情况）
    valid_node = {
        "src": {
            "models": {
                "Ball": "封装球体物理状态与自转渲染逻辑",
                "Heptagon": "管理正七边形几何属性与边界检测"
            },
            "controllers": {
                "PhysicsEngine": "实现重力、摩擦与碰撞响应算法"
            }
        }
    }
    
    result = DirJsonFuncs.check_new_nodes_are_strings(valid_node)
    assert result, "所有新节点都是字符串，应该返回True"
    print("  ✓ 成功验证了所有节点都是字符串")
    
    # 测试用例2: 包含非字符串叶子节点（错误情况）
    invalid_node = {
        "src": {
            "models": {
                "Ball": 123,  # 数字类型，不是字符串
                "Heptagon": "管理正七边形几何属性与边界检测"
            }
        }
    }
    
    result = DirJsonFuncs.check_new_nodes_are_strings(invalid_node)
    assert not result, "包含非字符串叶子节点，应该返回False"
    print("  ✓ 成功检测到非字符串节点")
    
    # 测试用例3: 包含嵌套字典但叶子节点都是字符串（正确情况）
    nested_valid_node = {
        "src": {
            "models": {
                "Ball": "封装球体物理状态与自转渲染逻辑"
            },
            "controllers": {
                "PhysicsEngine": "实现重力、摩擦与碰撞响应算法"
            }
        },
        "config": {
            "settings": "应用程序配置"
        }
    }
    
    result = DirJsonFuncs.check_new_nodes_are_strings(nested_valid_node)
    assert result, "所有叶子节点都是字符串，应该返回True"
    print("  ✓ 成功验证了嵌套结构中所有节点都是字符串")

if __name__ == "__main__":
    print("\n开始测试 DirJsonFuncs 类的所有功能...\n")
    
    try:
        test_detect_circular_dependencies()
        print()
        
        test_ensure_all_files_in_dependent_relation()
        print()
        
        test_build_file_creation_order()
        print()
        
        test_topological_sort()
        print()
        
        test_compare_structure()
        print()
        
        test_collect_paths()
        print()
        
        test_validate_dependent_paths()
        print()
        
        test_check_new_nodes_are_strings()
        print()
        
        print("=" * 50)
        print("所有测试通过！✓")
        print("=" * 50)
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()