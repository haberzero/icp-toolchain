"""
测试新重构的 SymbolRefResolver
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from typing import Dict
from typedef.ibc_data_types import (
    IbcBaseAstNode, ModuleNode, FunctionNode, VariableNode, BehaviorStepNode, ClassNode,
    AstNodeType
)
from utils.ibc_analyzer.ibc_symbol_ref_resolver import SymbolRefResolver


def test_extract_refs():
    """测试从AST中提取各类符号引用"""
    print("=" * 60)
    print("测试新重构的 SymbolRefResolver - 符号引用提取功能")
    print("=" * 60)
    
    # 1. 构造测试用的proj_root_dict结构
    proj_root_dict = {
        "utils": {
            "logger": "日志工具模块",
            "validator": "数据验证模块"
        },
        "config": {
            "settings": "配置管理模块"
        },
        "database": {
            "connection": {
                "pool": "数据库连接池"
            }
        },
        "main": "主入口程序"
    }
    
    # 2. 构造测试用的AST
    ast_dict = {
        0: IbcBaseAstNode(uid=0, node_type=AstNodeType.DEFAULT),
        
        # Module节点
        1: ModuleNode(uid=1, parent_uid=0, node_type=AstNodeType.MODULE,
                        identifier="utils.logger", content="日志工具模块"),
        2: ModuleNode(uid=2, parent_uid=0, node_type=AstNodeType.MODULE,
                        identifier="config.settings", content="配置管理模块"),
        3: ModuleNode(uid=3, parent_uid=0, node_type=AstNodeType.MODULE,
                        identifier="database.connection.pool", content="数据库连接池"),
        
        # Class节点（带继承）
        4: ClassNode(uid=4, parent_uid=0, node_type=AstNodeType.CLASS,
                        identifier="UserManager",
                        inh_params={"BaseManager": "使用公共基类管理生命周期"}),
        
        # Function节点（带参数类型引用）
        5: FunctionNode(uid=5, parent_uid=4, node_type=AstNodeType.FUNCTION,
                        identifier="处理业务逻辑",
                        params={"数据": "", "日志器": "由外部传入实例，其类型为 logger.Logger"},
                        param_type_refs={"日志器": "logger.Logger"}),
        
        # Variable节点（带类型引用）
        6: VariableNode(uid=6, parent_uid=4, node_type=AstNodeType.VARIABLE,
                        identifier="logger",
                        content="日志实例",
                        type_ref="logger.Logger"),
        7: VariableNode(uid=7, parent_uid=4, node_type=AstNodeType.VARIABLE,
                        identifier="dbConnection",
                        content="数据库连接对象",
                        type_ref="database.connection.Connection"),
        
        # Behavior节点（带符号引用）
        8: BehaviorStepNode(uid=8, parent_uid=5, node_type=AstNodeType.BEHAVIOR_STEP,
                            content="配置对象 = settings.load_config('app.json')",
                            symbol_refs=["settings.load_config"]),
        9: BehaviorStepNode(uid=9, parent_uid=5, node_type=AstNodeType.BEHAVIOR_STEP,
                            content="日志器 = logger.Logger(配置对象.log_level)",
                            symbol_refs=["logger.Logger", "config.DEBUG_MODE"]),
    }
    
    # 3. 创建解析器
    resolver = SymbolRefResolver(proj_root_dict)
    
    # 4. 测试提取功能
    print("\n--- 第1步: 提取所有符号引用 ---")
    resolver.extract_all_refs_from_ast_dict(ast_dict)
    
    # 5. 打印提取结果
    print("\n--- 第2步: 查看提取结果 ---")
    
    print("\nModule引用:")
    for ref in resolver.get_module_refs():
        print(f"  - {ref}")
    
    print("\n函数参数类型引用:")
    for param_name, type_ref in resolver.get_param_type_refs():
        print(f"  - {param_name}: {type_ref}")
    
    print("\n变量类型引用:")
    for var_name, type_ref in resolver.get_var_type_refs():
        print(f"  - {var_name}: {type_ref}")
    
    print("\n类继承引用:")
    for inherit_ref in resolver.get_class_inherit_refs():
        print(f"  - {inherit_ref}")
    
    print("\n行为描述符号引用:")
    for behavior_ref in resolver.get_behavior_refs():
        print(f"  - {behavior_ref}")
    
    # 6. 测试路径解析
    print("\n--- 第3步: 测试路径解析 ---")
    test_paths = [
        "logger.Logger",
        "config.settings.load_config",
        "database.connection.pool.ConnectionPool",
        "single_symbol"
    ]
    
    for path in test_paths:
        parts = resolver.parse_ref_path(path)
        print(f"  {path} -> {parts}")
    
    # 7. 测试符号表构建(暂未实现，只是调用接口)
    print("\n--- 第4步: 测试符号表构建(暂未实现) ---")
    full_table = resolver.build_full_symbol_table()
    print(f"  完整符号表: {full_table}")
    
    resolver.build_visible_symbol_table()
    print(f"  可见符号表: {resolver.visible_symbol_table}")
    
    # 8. 测试符号验证(暂未实现，只是调用接口)
    print("\n--- 第5步: 测试符号验证(暂未实现) ---")
    validation_results = resolver.validate_all_refs()
    
    print("\n参数类型引用验证:")
    for param_name, type_ref, is_valid, msg in validation_results['param_type_refs']:
        status = "✓" if is_valid else "✗"
        print(f"  {status} {param_name}: {type_ref} -> {msg}")
    
    print("\n变量类型引用验证:")
    for var_name, type_ref, is_valid, msg in validation_results['var_type_refs']:
        status = "✓" if is_valid else "✗"
        print(f"  {status} {var_name}: {type_ref} -> {msg}")
    
    print("\n类继承引用验证:")
    for inherit_ref, is_valid, msg in validation_results['class_inherit_refs']:
        status = "✓" if is_valid else "✗"
        print(f"  {status} {inherit_ref} -> {msg}")
    
    print("\n行为符号引用验证:")
    for behavior_ref, is_valid, msg in validation_results['behavior_refs']:
        status = "✓" if is_valid else "✗"
        print(f"  {status} {behavior_ref} -> {msg}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    test_extract_refs()
