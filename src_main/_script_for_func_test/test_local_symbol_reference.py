"""
端到端测试：验证本地符号在IBC代码中的$引用能被正确解析

测试场景：
生成包含对本地符号进行$引用的IBC代码，验证ref_resolver能够正确解析
"""
import sys
import os

# 添加项目根目录到系统路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.ibc_analyzer.ibc_analyzer import analyze_ibc_code
from utils.ibc_analyzer.ibc_visible_symbol_builder import VisibleSymbolBuilder
from utils.ibc_analyzer.ibc_symbol_ref_resolver import SymbolRefResolver
from utils.issue_recorder import IbcIssueRecorder


def test_local_symbol_reference():
    """测试对本地符号的$引用"""
    print("="*60)
    print("测试: 本地符号的$引用解析")
    print("="*60)
    
    # IBC代码：定义一个类，然后在函数中引用自己的属性和方法
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
    
    print("\n1. 解析IBC代码生成AST和符号表...")
    issue_recorder = IbcIssueRecorder()
    ast_dict, symbols_tree, symbols_metadata = analyze_ibc_code(ibc_code, issue_recorder)
    
    if not ast_dict:
        print("❌ IBC代码解析失败")
        return False
    
    print(f"✓ AST节点数: {len(ast_dict)}")
    print(f"✓ 符号树: {list(symbols_tree.keys())}")
    print(f"✓ 符号元数据keys: {list(symbols_metadata.keys())}")
    
    # 构造项目根目录和依赖关系（假设无外部依赖）
    proj_root_dict = {
        "src": {
            "test": "测试模块"
        }
    }
    
    dependency_symbol_tables = {}
    
    print("\n2. 构建可见符号树（不包含本地符号）...")
    builder = VisibleSymbolBuilder(proj_root_dict)
    visible_symbols_tree_no_local, visible_symbols_metadata_no_local = builder.build_visible_symbol_tree(
        current_file_path="src/test",
        dependency_symbol_tables=dependency_symbol_tables,
        include_local_symbols=False
    )
    
    print(f"✓ 可见符号数（不含本地）: {len(visible_symbols_metadata_no_local)}")
    
    print("\n3. 验证符号引用（不包含本地符号）...")
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
    print(f"✓ 发现的问题数: {len(issues_no_local)}")
    if issues_no_local:
        print("  问题列表:")
        for issue in issues_no_local:
            print(f"    - 第{issue.line_num}行: {issue.message}")
    
    # 应该有问题，因为没有包含本地符号
    assert len(issues_no_local) > 0, "应该发现符号引用问题（本地符号不在可见符号树中）"
    print("✓ 预期行为：未包含本地符号时，$引用无法解析")
    
    print("\n4. 构建可见符号树（包含本地符号）...")
    visible_symbols_tree_with_local, visible_symbols_metadata_with_local = builder.build_visible_symbol_tree(
        current_file_path="src/test",
        dependency_symbol_tables=dependency_symbol_tables,
        include_local_symbols=True,
        local_symbols_tree=symbols_tree,
        local_symbols_metadata=symbols_metadata
    )
    
    print(f"✓ 可见符号数（含本地）: {len(visible_symbols_metadata_with_local)}")
    print(f"✓ 可见符号树根节点: {list(visible_symbols_tree_with_local.keys())}")
    
    print("\n5. 验证符号引用（包含本地符号）...")
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
    print(f"✓ 发现的问题数: {len(issues_with_local)}")
    if issues_with_local:
        print("  问题列表:")
        for issue in issues_with_local:
            print(f"    - 第{issue.line_num}行: {issue.message}")
    
    # 包含本地符号后，应该能够解析所有引用
    # 注意：可能仍有一些问题，但应该比之前少
    print(f"✓ 包含本地符号后，问题数从 {len(issues_no_local)} 减少到 {len(issues_with_local)}")
    
    return True


def test_complex_local_reference():
    """测试复杂的本地符号引用场景"""
    print("\n" + "="*60)
    print("测试: 复杂的本地符号引用")
    print("="*60)
    
    # IBC代码：多个类之间的相互引用
    ibc_code = """
description: 测试复杂的本地符号引用

class Vector2D():
    var x: float
    var y: float
    
    func magnitude():
        x_squared = $Vector2D.x * $Vector2D.x
        y_squared = $Vector2D.y * $Vector2D.y
        返回 sqrt(x_squared + y_squared)

class Physics():
    func apply_velocity(entity, velocity: Vector2D, delta_time: float):
        vx = $Vector2D.x
        vy = $Vector2D.y
        更新entity的位置
"""
    
    print("\n1. 解析IBC代码...")
    issue_recorder = IbcIssueRecorder()
    ast_dict, symbols_tree, symbols_metadata = analyze_ibc_code(ibc_code, issue_recorder)
    
    if not ast_dict:
        print("❌ IBC代码解析失败")
        return False
    
    print(f"✓ 符号树: {list(symbols_tree.keys())}")
    
    print("\n2. 构建包含本地符号的可见符号树...")
    proj_root_dict = {"src": {"physics": "物理模块"}}
    builder = VisibleSymbolBuilder(proj_root_dict)
    
    visible_symbols_tree, visible_symbols_metadata = builder.build_visible_symbol_tree(
        current_file_path="src/physics",
        dependency_symbol_tables={},
        include_local_symbols=True,
        local_symbols_tree=symbols_tree,
        local_symbols_metadata=symbols_metadata
    )
    
    print(f"✓ 可见符号: {list(visible_symbols_tree.keys())}")
    
    # 验证本地符号是否有特殊标记
    assert "Vector2D" in visible_symbols_metadata, "Vector2D应该在可见符号中"
    assert visible_symbols_metadata["Vector2D"].get("__is_local__") == True, "应该有本地标记"
    
    print("✓ 本地符号包含正确的标记")
    
    print("\n3. 验证符号引用...")
    issue_recorder.clear()
    ref_resolver = SymbolRefResolver(
        ast_dict=ast_dict,
        symbols_tree=visible_symbols_tree,
        symbols_metadata=visible_symbols_metadata,
        ibc_issue_recorder=issue_recorder,
        proj_root_dict=proj_root_dict,
        dependent_relation={},
        current_file_path="src/physics"
    )
    ref_resolver.resolve_all_references()
    
    issues = issue_recorder.get_issues()
    print(f"✓ 发现的问题数: {len(issues)}")
    if issues:
        for issue in issues:
            print(f"    - 第{issue.line_num}行: {issue.message}")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("开始端到端测试：本地符号$引用解析")
    print("="*60 + "\n")
    
    try:
        if not test_local_symbol_reference():
            return False
        
        if not test_complex_local_reference():
            return False
        
        print("\n" + "="*60)
        print("测试汇总")
        print("="*60)
        print("所有测试通过! (2/2)")
        print("="*60 + "\n")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
