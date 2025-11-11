"""
AST数据管理器使用示例

演示如何在实际场景中使用 AstDataManager 进行 AST 的保存和加载
"""

import sys
import os

# 添加src_main到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ibc_analyzer.ibc_analyzer import analyze_ibc_code
from data_exchange.ibc_data_manager import get_instance as get_ibc_data_manager


def example_save_and_load_ast():
    """示例：解析IBC代码，保存AST，然后重新加载"""
    
    # 示例IBC代码
    ibc_code = """
module UserManagement: 用户管理模块

class User():
    var username: 用户名
    var email: 电子邮件地址
    
    description: 用户登录功能
    @ 验证用户名和密码，返回登录结果
    func login(username, password):
        检查用户名是否存在 $username$
        验证密码是否正确 $password$
        如果验证成功:
            创建会话
            返回成功
        否则:
            返回失败
    """
    
    print("=" * 60)
    print("示例：解析、保存和加载 AST")
    print("=" * 60)
    
    # 1. 解析IBC代码生成AST
    print("\n1. 解析IBC代码...")
    try:
        ast_dict = analyze_ibc_code(ibc_code)
        print(f"   ✓ 解析成功，生成 {len(ast_dict)} 个AST节点")
    except Exception as e:
        print(f"   ✗ 解析失败: {e}")
        return
    
    # 2. 保存AST到文件
    print("\n2. 保存AST到文件...")
    ast_manager = get_ibc_data_manager()
    
    # 定义保存路径
    save_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "user_management_ast.json"
    )
    
    success = ast_manager.save_ast_to_file(ast_dict, save_path)
    if success:
        print(f"   ✓ AST已保存到: {save_path}")
    else:
        print(f"   ✗ 保存失败")
        return
    
    # 3. 从文件加载AST
    print("\n3. 从文件加载AST...")
    loaded_ast = ast_manager.load_ast_from_file(save_path)
    print(f"   ✓ 成功加载 {len(loaded_ast)} 个节点")
    
    # 4. 验证加载的AST
    print("\n4. 验证加载的AST内容...")
    print(f"   节点总数: {len(loaded_ast)}")
    
    # 遍历并展示部分节点信息
    from typedef.ibc_data_types import (
        ModuleNode, ClassNode, FunctionNode, VariableNode, BehaviorStepNode
    )
    
    for uid, node in loaded_ast.items():
        if isinstance(node, ModuleNode):
            print(f"   - [Module] uid={uid}, identifier='{node.identifier}'")
        elif isinstance(node, ClassNode):
            print(f"   - [Class] uid={uid}, identifier='{node.identifier}'")
        elif isinstance(node, FunctionNode):
            print(f"   - [Function] uid={uid}, identifier='{node.identifier}', params={list(node.params.keys())}")
        elif isinstance(node, VariableNode):
            print(f"   - [Variable] uid={uid}, identifier='{node.identifier}'")
        elif isinstance(node, BehaviorStepNode):
            print(f"   - [BehaviorStep] uid={uid}, content='{node.content[:30]}...'")
    
    # 5. 展示如何通过AST树结构遍历
    print("\n5. 遍历AST树结构...")
    root_node = loaded_ast[0]
    print(f"   根节点 (uid=0) 有 {len(root_node.children_uids)} 个子节点")
    
    def print_tree(ast_dict, uid, indent=0):
        """递归打印AST树"""
        node = ast_dict[uid]
        indent_str = "  " * indent
        
        node_type = type(node).__name__
        identifier = getattr(node, 'identifier', 'N/A')
        
        print(f"{indent_str}├─ [{node_type}] uid={uid}, identifier='{identifier}'")
        
        for child_uid in node.children_uids:
            print_tree(ast_dict, child_uid, indent + 1)
    
    print_tree(loaded_ast, 0)
    
    print("\n" + "=" * 60)
    print("✓ 示例完成！AST持久化功能已成功演示")
    print("=" * 60)


if __name__ == "__main__":
    print("\n开始运行 AST 使用示例...\n")
    
    try:
        example_save_and_load_ast()
    except Exception as e:
        print(f"\n✗ 示例运行失败: {e}")
        import traceback
        traceback.print_exc()
