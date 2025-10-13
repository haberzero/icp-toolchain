import sys
import os

# 正确添加src_main目录到sys.path，以便能够导入libs中的模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.ibc_analyzer.ibc_parser import parse_ibc_code

def test_simple_module():
    """测试简单模块解析"""
    print("测试 simple_module 函数...")
    
    code = """module requests: Python第三方HTTP请求库
module threading: 系统线程库
module utils"""
    
    ast = parse_ibc_code(code)
    assert len(ast) > 0, "AST节点数量应该大于0"
    
    print(f"  ✓ 成功解析简单模块，共 {len(ast)} 个节点")
    return True

def test_function_with_params():
    """测试带参数的函数"""
    print("测试 function_with_params 函数...")
    
    code = """\
func 计算订单总价(商品列表: 包含价格信息的商品对象数组, 折扣率: 0到1之间的小数):
    初始化 总价 = 0
    遍历 商品列表 中的每个 商品:
        总价 = 总价 + 商品.价格
    总价 = 总价 × 折扣率
    返回 总价"""
    
    ast = parse_ibc_code(code)
    assert len(ast) > 0, "AST节点数量应该大于0"
    
    print(f"  ✓ 成功解析带参数的函数，共 {len(ast)} 个节点")
    return True

def test_class_with_inheritance():
    """测试带继承的类"""
    print("测试 class_with_inheritance 函数...")
    
    code = """class UserManager(BaseManager: 使用公共基类管理生命周期):
    var users: 用户数据字典
    var dbConnection: 数据库连接对象
    
    func 添加用户(用户名, 密码: 经过哈希处理的密码字符串):
        验证 用户名 和 密码 格式
        创建新用户对象
        将用户保存到数据库
        返回 操作结果"""
    
    ast = parse_ibc_code(code)
    assert len(ast) > 0, "AST节点数量应该大于0"
    
    print(f"  ✓ 成功解析带继承的类，共 {len(ast)} 个节点")
    return True

def test_description_and_intent():
    """测试描述和意图注释"""
    print("测试 description_and_intent 函数...")
    
    code = """description: 处理用户登录请求，验证凭据并返回认证结果
@ 线程安全设计，所有公共方法都内置锁机制
class AuthService():"""
    
    ast = parse_ibc_code(code)
    assert len(ast) > 0, "AST节点数量应该大于0"
    
    print(f"  ✓ 成功解析描述和意图注释，共 {len(ast)} 个节点")
    return True

def main():
    """主测试函数"""
    print("开始测试 IBC 解析器...\n")
    
    try:
        test_results = []
        
        test_results.append(("简单模块", test_simple_module()))
        print()
        
        test_results.append(("带参数的函数", test_function_with_params()))
        print()
        
        test_results.append(("带继承的类", test_class_with_inheritance()))
        print()
        
        test_results.append(("描述和意图注释", test_description_and_intent()))
        print()
        
        print("测试结果汇总")
        print("=" * 40)
        
        passed = 0
        failed = 0
        
        for test_name, result in test_results:
            status = "✓ 通过" if result else "❌ 失败"
            print(f"{test_name:20} {status}")
            if result:
                passed += 1
            else:
                failed += 1
        
        print(f"\n总计: {passed} 通过, {failed} 失败")
        
        if failed == 0:
            print("🎉 所有测试通过！")
        else:
            print(f"⚠️  有 {failed} 个测试失败")
            
        return failed == 0
        
    except Exception as e:
        print(f"测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)