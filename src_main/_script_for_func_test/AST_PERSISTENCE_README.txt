================================================================================
AST 持久化功能说明
================================================================================

概述：
------
本功能实现了 AstNode 及其派生类的完整序列化和反序列化，可以将整个 AST 
(Dict[int, AstNode]) 保存到 JSON 文件，并从文件中重建完整的 AST 结构。

主要文件：
----------
1. typedef/ibc_data_types.py
   - 为所有 AstNode 类添加了 from_dict() 静态方法
   - 保留原有的 to_dict() 方法

2. data_exchange/ibc_data_manager.py (新增)
   - AstDataManager 类：单例模式的 AST 数据管理器
   - save_ast_to_file(): 保存 AST 到 JSON 文件
   - load_ast_from_file(): 从 JSON 文件加载 AST

核心功能：
----------
1. 序列化（保存）
   - 将 Dict[int, AstNode] 转换为 JSON 格式
   - 自动添加 _class_type 字段以标识节点类型
   - 保持树形结构（parent_uid, children_uids）

2. 反序列化（加载）
   - 从 JSON 文件读取数据
   - 根据 _class_type 自动创建正确的节点类型
   - 完整重建 AST 树结构

使用方法：
----------

1. 保存 AST 到文件：

    from data_exchange.ibc_data_manager import get_instance as get_ibc_data_manager
    
    # 获取管理器实例
    ast_manager = get_ibc_data_manager()
    
    # 保存 AST（ast_dict 是 Dict[int, AstNode]）
    success = ast_manager.save_ast_to_file(ast_dict, "path/to/save.json")

2. 从文件加载 AST：

    from data_exchange.ibc_data_manager import get_instance as get_ibc_data_manager
    
    # 获取管理器实例
    ast_manager = get_ibc_data_manager()
    
    # 加载 AST
    ast_dict = ast_manager.load_ast_from_file("path/to/save.json")
    # ast_dict 现在是完整的 Dict[int, AstNode]

3. 与 IBC 解析器集成使用：

    from utils.ibc_analyzer.ibc_analyzer import analyze_ibc_code
    from data_exchange.ibc_data_manager import get_instance as get_ibc_data_manager
    
    # 解析 IBC 代码
    ibc_code = "..."
    ast_dict = analyze_ibc_code(ibc_code)
    
    # 保存 AST
    ast_manager = get_ibc_data_manager()
    ast_manager.save_ast_to_file(ast_dict, "my_ast.json")
    
    # 稍后加载
    loaded_ast = ast_manager.load_ast_from_file("my_ast.json")

存储格式：
----------
JSON 文件以 uid 为 key，节点数据为 value：

{
  "0": {
    "uid": 0,
    "parent_uid": 0,
    "children_uids": [1, 2],
    "node_type": "DEFAULT",
    "line_number": 0,
    "_class_type": "AstNode"
  },
  "1": {
    "uid": 1,
    "parent_uid": 0,
    "children_uids": [],
    "node_type": "MODULE",
    "line_number": 2,
    "identifier": "ModuleName",
    "content": "模块描述",
    "_class_type": "ModuleNode"
  },
  ...
}

测试文件：
----------
1. test_ibc_data_manager.py
   - 基础功能测试
   - 测试所有节点类型的序列化和反序列化
   - 验证数据完整性

2. example_ast_usage.py
   - 实际使用示例
   - 演示如何与 IBC 解析器集成
   - 展示 AST 树遍历

节点类型映射：
--------------
- AstNode -> "AstNode"
- ModuleNode -> "ModuleNode"
- ClassNode -> "ClassNode"
- FunctionNode -> "FunctionNode"
- VariableNode -> "VariableNode"
- BehaviorStepNode -> "BehaviorStepNode"

每个节点都保留了完整的属性信息，包括：
- 基础属性：uid, parent_uid, children_uids, node_type, line_number
- 特定属性：identifier, content, params, external_desc, intent_comment 等

优势：
------
1. 逻辑清晰：遵循现有的持久化文件存取模式（单例模式 + JSON）
2. 类型安全：反序列化时自动创建正确的节点类型
3. 结构完整：保留完整的树形结构关系
4. 易于使用：简单的 API 接口
5. 可扩展：未来新增节点类型只需添加相应的 from_dict() 方法

注意事项：
----------
1. 确保保存和加载使用相同的节点类型定义
2. JSON 文件中的 uid 会被转换为整数
3. 枚举类型（如 node_type）会自动转换
4. 字典和列表类型会保持原有结构

================================================================================
