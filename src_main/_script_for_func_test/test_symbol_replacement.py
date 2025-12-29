"""
测试符号替换功能

该脚本测试 IbcFuncs.replace_symbols_with_normalized_names 方法
验证IBC代码中的符号能否正确替换为规范化名称
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from libs.ibc_funcs import IbcFuncs
from utils.ibc_analyzer.ibc_analyzer import analyze_ibc_code
from typedef.cmd_data_types import Colors


def test_simple_function_replacement():
    """测试简单函数符号替换"""
    print("\n测试 simple_function_replacement 函数...")
    
    # 原始IBC代码
    ibc_content = """description: 实现重力对球体运动状态的影响逻辑
@ 独立处理Y轴方向速度变化，与边界碰撞和摩擦模块协同工作
func apply_gravity(球实例, 时间步长):
    var 重力常数 = 9.81
    
    // 根据重力加速度更新球的垂直速度
    更新后的垂直速度 = 球实例.速度.y + 重力常数 × 时间步长
    
    // 应用新的垂直速度到球的位置上
    新位置.y = 球实例.位置.y + 更新后的垂直速度 × 时间步长
    
    // 将更新后的位置和速度写回球对象
    球实例.速度.y = 更新后的垂直速度
    球实例.位置.y = 新位置.y
"""
    
    try:
        # 解析生成AST
        ast_dict, _, _ = analyze_ibc_code(ibc_content)
        if not ast_dict:
            print("  ❌ 测试失败: AST生成失败")
            return False
        
        # 构造模拟的符号元数据
        symbols_metadata = {
            "gravity.apply_gravity": {
                "type": "func",
                "normalized_name": "apply_gravity",
                "parameters": {
                    "球实例": "",
                    "时间步长": ""
                }
            },
            "gravity.apply_gravity.球实例": {
                "type": "param",
                "normalized_name": "ball_instance"
            },
            "gravity.apply_gravity.时间步长": {
                "type": "param",
                "normalized_name": "time_step"
            },
            "gravity.apply_gravity.重力常数": {
                "type": "var",
                "normalized_name": "gravity_constant"
            },
            "gravity.apply_gravity.更新后的垂直速度": {
                "type": "var",
                "normalized_name": "updated_vertical_velocity"
            },
            "gravity.apply_gravity.新位置": {
                "type": "var",
                "normalized_name": "new_position"
            }
        }
        
        # 执行替换
        result = IbcFuncs.replace_symbols_with_normalized_names(
            ibc_content=ibc_content,
            ast_dict=ast_dict,
            symbols_metadata=symbols_metadata,
            current_file_name="gravity"
        )
        
        # 检查关键替换
        assert "apply_gravity" in result and "apply_gravity(ball_instance, time_step)" in result, "函数名和参数名替换失败"
        assert "gravity_constant" in result, "局部变量 gravity_constant 替换失败"
        assert "updated_vertical_velocity" in result, "局部变量 updated_vertical_velocity 替换失败"
        assert "new_position" in result, "局部变量 new_position 替换失败"
        assert "球实例" not in result.split("//")[0], "原始参数名未替换"  # 排除注释
        
        print("  ✓ 简单函数符号替换测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_class_with_methods():
    """测试类和方法符号替换"""
    print("\n测试 class_with_methods 函数...")
    
    ibc_content = """class FrictionManager():
    private
    var friction_coefficient: 摩擦系数常量
    
    public
    func __init__(摩擦系数):
        self.friction_coefficient = 摩擦系数
    
    func apply_friction(球对象, 时间间隔):
        计算后速度 = self.calculate_energy_loss(球对象.velocity, 时间间隔)
        球对象.velocity = 计算后速度
"""
    
    try:
        # 解析AST
        ast_dict, _, _ = analyze_ibc_code(ibc_content)
        if not ast_dict:
            print("  ❌ 测试失败: AST生成失败")
            return False
        
        # 符号元数据
        symbols_metadata = {
            "friction.FrictionManager": {
                "type": "class",
                "normalized_name": "FrictionManager"
            },
            "friction.FrictionManager.friction_coefficient": {
                "type": "var",
                "normalized_name": "friction_coefficient"
            },
            "friction.FrictionManager.__init__": {
                "type": "func",
                "normalized_name": "__init__"
            },
            "friction.FrictionManager.__init__.摩擦系数": {
                "type": "param",
                "normalized_name": "friction_coef"
            },
            "friction.FrictionManager.apply_friction": {
                "type": "func",
                "normalized_name": "apply_friction"
            },
            "friction.FrictionManager.apply_friction.球对象": {
                "type": "param",
                "normalized_name": "ball_obj"
            },
            "friction.FrictionManager.apply_friction.时间间隔": {
                "type": "param",
                "normalized_name": "time_interval"
            },
            "friction.FrictionManager.apply_friction.计算后速度": {
                "type": "var",
                "normalized_name": "calculated_velocity"
            }
        }
        
        # 执行替换
        result = IbcFuncs.replace_symbols_with_normalized_names(
            ibc_content=ibc_content,
            ast_dict=ast_dict,
            symbols_metadata=symbols_metadata,
            current_file_name="friction"
        )
        
        # 验证
        assert "FrictionManager" in result, "类名替换失败"
        assert "friction_coefficient" in result, "成员变量替换失败"
        assert "__init__(friction_coef)" in result, "构造函数参数替换失败"
        assert "apply_friction(ball_obj, time_interval)" in result, "方法参数替换失败"
        assert "calculated_velocity" in result, "局部变量替换失败"
        
        print("  ✓ 类和方法符号替换测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dollar_reference_replacement():
    """测试$符号引用替换"""
    print("\n测试 dollar_reference_replacement 函数...")
    
    ibc_content = """module src.physics.gravity
module src.physics.friction

func update_ball():
    应用重力 = $gravity.apply_gravity(self, 时间步长)
    摩擦管理器 = $friction.FrictionManager(0.5)
    新速度 = 摩擦管理器.apply_friction(self.velocity)
"""
    
    try:
        # 解析AST
        ast_dict, _, _ = analyze_ibc_code(ibc_content)
        if not ast_dict:
            print("  ❌ 测试失败: AST生成失败")
            return False
        
        # 符号元数据（模拟规范化后的外部符号）
        symbols_metadata = {
            "ball.update_ball": {
                "type": "func",
                "normalized_name": "update_ball"
            },
            "ball.update_ball.时间步长": {
                "type": "var",
                "normalized_name": "time_step"
            },
            "ball.update_ball.应用重力": {
                "type": "var",
                "normalized_name": "apply_gravity_result"
            },
            "ball.update_ball.摩擦管理器": {
                "type": "var",
                "normalized_name": "friction_manager"
            },
            "ball.update_ball.新速度": {
                "type": "var",
                "normalized_name": "new_velocity"
            },
            # 注意：$引用中的符号在metadata中不需要前缀
            "gravity.apply_gravity": {
                "type": "func",
                "normalized_name": "apply_gravity"
            },
            "friction.FrictionManager": {
                "type": "class",
                "normalized_name": "FrictionManager"
            }
        }
        
        # 执行替换
        result = IbcFuncs.replace_symbols_with_normalized_names(
            ibc_content=ibc_content,
            ast_dict=ast_dict,
            symbols_metadata=symbols_metadata,
            current_file_name="ball"
        )
        
        # 验证
        assert "update_ball" in result, "函数名替换失败"
        assert "time_step" in result, "参数名替换失败"
        assert "apply_gravity_result" in result, "局部变量1替换失败"
        assert "friction_manager" in result, "局部变量2替换失败"
        assert "new_velocity" in result, "局部变量3替换失败"
        assert "$gravity.apply_gravity" in result, "$引用未保留"
        assert "$friction.FrictionManager" in result, "$引用未保留"
        
        print("  ✓ $符号引用替换测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("开始测试 Intent Behavior Code 符号替换功能...")
    print("=" * 60)
    
    try:
        test_results = []
        
        test_results.append(("简单函数符号替换", test_simple_function_replacement()))
        print()
        
        test_results.append(("类和方法符号替换", test_class_with_methods()))
        print()
        
        test_results.append(("$符号引用替换", test_dollar_reference_replacement()))
        print()
        
        print("=" * 60)
        print("测试结果汇总")
        print("=" * 60)
        
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
            print("=" * 60)
            print("所有测试通过！✓")
            print("=" * 60)
            return True
        else:
            print(f"⚠️  有 {failed} 个测试失败")
            return False
            
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
