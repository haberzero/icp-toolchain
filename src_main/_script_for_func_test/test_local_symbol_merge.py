"""
测试本地符号合并到可见符号树的功能

测试场景：
1. 验证本地符号能正确合并到可见符号树
2. 验证本地符号的元数据包含特殊标记 '__is_local__': True
3. 验证本地符号与依赖符号重名时，本地符号优先
4. 验证符号引用解析能正确识别本地符号
"""
import sys
import os

# 添加项目根目录到系统路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.ibc_analyzer.ibc_visible_symbol_builder import VisibleSymbolBuilder


def test_local_symbol_merge():
    """测试本地符号合并功能"""
    print("="*60)
    print("测试1: 本地符号合并到可见符号树")
    print("="*60)
    
    # 构造项目根目录字典
    proj_root_dict = {
        "src": {
            "test": "测试模块"
        }
    }
    
    # 创建可见符号构建器
    builder = VisibleSymbolBuilder(proj_root_dict)
    
    # 构造依赖符号表（来自其他文件）
    dependency_symbol_tables = {
        "src/dep_module": (
            {
                "DepClass": {}
            },
            {
                "DepClass": {
                    "type": "class",
                    "visibility": "public",
                    "description": "依赖类",
                    "normalized_name": "DepClass"
                }
            }
        )
    }
    
    # 构造本地符号表（当前文件自己的符号）
    local_symbols_tree = {
        "LocalClass": {
            "local_method": {}
        },
        "local_func": {}
    }
    
    local_symbols_metadata = {
        "LocalClass": {
            "type": "class",
            "visibility": "public",
            "description": "本地类",
            "normalized_name": "LocalClass"
        },
        "LocalClass.local_method": {
            "type": "function",
            "visibility": "public",
            "description": "本地方法",
            "normalized_name": "local_method"
        },
        "local_func": {
            "type": "function",
            "visibility": "public",
            "description": "本地函数",
            "normalized_name": "local_func"
        }
    }
    
    # 不包含本地符号的情况
    print("\n1.1 不包含本地符号的可见符号树：")
    symbols_tree1, symbols_metadata1 = builder.build_visible_symbol_tree(
        current_file_path="src/test",
        dependency_symbol_tables=dependency_symbol_tables,
        include_local_symbols=False
    )
    
    print(f"\n符号树结构: {list(symbols_tree1.keys())}")
    print(f"符号元数据keys: {list(symbols_metadata1.keys())}")
    
    # 包含本地符号的情况
    print("\n1.2 包含本地符号的可见符号树：")
    symbols_tree2, symbols_metadata2 = builder.build_visible_symbol_tree(
        current_file_path="src/test",
        dependency_symbol_tables=dependency_symbol_tables,
        include_local_symbols=True,
        local_symbols_tree=local_symbols_tree,
        local_symbols_metadata=local_symbols_metadata
    )
    
    print(f"\n符号树结构: {list(symbols_tree2.keys())}")
    print(f"符号元数据keys: {list(symbols_metadata2.keys())}")
    
    # 验证本地符号是否正确添加
    assert "LocalClass" in symbols_tree2, "本地类应该在符号树中"
    assert "local_func" in symbols_tree2, "本地函数应该在符号树中"
    
    # 验证本地符号的元数据是否包含特殊标记
    assert symbols_metadata2["LocalClass"]["__is_local__"] == True, "本地符号应该有 __is_local__ 标记"
    assert symbols_metadata2["LocalClass"]["__local_file__"] == "src/test", "本地符号应该有文件路径标记"
    
    print("\n✓ 本地符号合并成功")
    print(f"  - 本地符号数量: {len(local_symbols_tree)}")
    print(f"  - 本地符号包含 __is_local__ 标记: {symbols_metadata2['LocalClass']['__is_local__']}")
    

def test_local_symbol_priority():
    """测试本地符号优先级（与依赖符号重名时）"""
    print("\n" + "="*60)
    print("测试2: 本地符号与依赖符号重名，本地符号优先")
    print("="*60)
    
    proj_root_dict = {"src": {"test": "测试模块"}}
    builder = VisibleSymbolBuilder(proj_root_dict)
    
    # 依赖符号表中有一个 SharedName 类
    dependency_symbol_tables = {
        "src/dep_module": (
            {
                "SharedName": {}
            },
            {
                "SharedName": {
                    "type": "class",
                    "visibility": "public",
                    "description": "依赖模块中的共享名称类",
                    "normalized_name": "SharedNameFromDep"
                }
            }
        )
    }
    
    # 本地符号表中也有一个 SharedName 类
    local_symbols_tree = {
        "SharedName": {}
    }
    
    local_symbols_metadata = {
        "SharedName": {
            "type": "class",
            "visibility": "public",
            "description": "本地模块中的共享名称类",
            "normalized_name": "SharedNameLocal"
        }
    }
    
    # 构建包含本地符号的可见符号树
    symbols_tree, symbols_metadata = builder.build_visible_symbol_tree(
        current_file_path="src/test",
        dependency_symbol_tables=dependency_symbol_tables,
        include_local_symbols=True,
        local_symbols_tree=local_symbols_tree,
        local_symbols_metadata=local_symbols_metadata
    )
    
    # 验证本地符号优先
    assert "SharedName" in symbols_metadata, "SharedName 应该存在"
    assert symbols_metadata["SharedName"]["__is_local__"] == True, "SharedName 应该是本地符号"
    assert symbols_metadata["SharedName"]["normalized_name"] == "SharedNameLocal", "应该使用本地符号的规范化名称"
    
    print("\n✓ 本地符号优先级测试通过")
    print(f"  - 重名符号: SharedName")
    print(f"  - 规范化名称: {symbols_metadata['SharedName']['normalized_name']}")
    print(f"  - __is_local__: {symbols_metadata['SharedName']['__is_local__']}")


def test_empty_local_symbols():
    """测试空本地符号表的情况"""
    print("\n" + "="*60)
    print("测试3: 空本地符号表")
    print("="*60)
    
    proj_root_dict = {"src": {"test": "测试模块"}}
    builder = VisibleSymbolBuilder(proj_root_dict)
    
    dependency_symbol_tables = {
        "src/dep_module": (
            {"DepClass": {}},
            {"DepClass": {"type": "class", "visibility": "public"}}
        )
    }
    
    # 本地符号为空
    local_symbols_tree = {}
    local_symbols_metadata = {}
    
    symbols_tree, symbols_metadata = builder.build_visible_symbol_tree(
        current_file_path="src/test",
        dependency_symbol_tables=dependency_symbol_tables,
        include_local_symbols=True,
        local_symbols_tree=local_symbols_tree,
        local_symbols_metadata=local_symbols_metadata
    )
    
    # 验证只有依赖符号
    assert "src" in symbols_tree, "应该有依赖符号"
    
    print("\n✓ 空本地符号表测试通过")
    print(f"  - 符号树keys: {list(symbols_tree.keys())}")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("开始测试本地符号合并功能")
    print("="*60 + "\n")
    
    try:
        test_local_symbol_merge()
        test_local_symbol_priority()
        test_empty_local_symbols()
        
        print("\n" + "="*60)
        print("测试汇总")
        print("="*60)
        print("所有测试通过! (3/3)")
        print("="*60 + "\n")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
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
