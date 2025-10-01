import sys
import os

# 正确添加src_main目录到sys.path，以便能够导入utils.icb中的模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.icb.icb_analyzer import IcbAnalyzer

def create_test_icb_file(file_path, content):
    """创建测试用的ICB文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def test_basic_icb_analysis():
    """测试基本的ICB文件分析功能"""
    print("测试基本的ICB文件分析功能...")
    
    # 创建一个简单的测试ICB文件
    test_content = """class Ball:
description: 球体类，用于表示和管理球体的物理状态
inh: object

    var position: 球心坐标(x, y)
    
    var velocity: 速度向量(vx, vy)
    
    var radius: 球的半径
    
    func __init__:
    description: 初始化球体
    input: x: float, y: float, vx: float, vy: float, radius: float
    output: None
    behavior:
        设置position为(x, y)
        设置velocity为(vx, vy)
        设置radius为radius
    
    func update_position:
    description: 根据速度更新球的位置
    input: dt: float (时间步长)
    output: None
    behavior:
        position.x += velocity.x * dt
        position.y += velocity.y * dt

func check_collision:
description: 检查两个球体是否发生碰撞
input: ball1: Ball, ball2: Ball
output: bool (是否碰撞)
behavior:
    计算两球心之间的距离
    如果距离小于两球半径之和:
        返回True
    否则:
        返回False
"""
    
    test_file = "test_basic.icb"
    create_test_icb_file(test_file, test_content)
    
    # 创建分析器并分析文件
    analyzer = IcbAnalyzer()
    result = analyzer._file_analysis(test_file)
    
    # 验证结果
    assert result == True, "基本ICB文件分析应该成功"
    print("  ✓ 基本ICB文件分析成功")
    
    # 清理测试文件
    os.remove(test_file)

def test_icb_with_syntax_errors():
    """测试包含语法错误的ICB文件分析"""
    print("测试包含语法错误的ICB文件分析...")
    
    # 创建一个包含语法错误的ICB文件（使用了tab字符）
    test_content = """class Ball:
description: 球体类，用于表示和管理球体的物理状态
inh: object

	var position: 球心坐标(x, y)  # 使用tab缩进，应该报错
	
    var velocity: 速度向量(vx, vy)
"""
    
    test_file = "test_syntax_error.icb"
    create_test_icb_file(test_file, test_content)
    
    # 创建分析器并分析文件
    analyzer = IcbAnalyzer()
    result = analyzer._file_analysis(test_file)
    
    # 对于包含语法错误的文件，我们期望分析仍然成功（但会记录错误）
    # 因为错误处理在诊断处理器中进行
    assert result == True, "即使有语法错误，分析也应该继续进行"
    print("  ✓ 包含语法错误的ICB文件分析处理正确")
    
    # 清理测试文件
    os.remove(test_file)

def test_empty_icb_file():
    """测试空ICB文件分析"""
    print("测试空ICB文件分析...")
    
    # 创建一个空的ICB文件
    test_content = ""
    
    test_file = "test_empty.icb"
    create_test_icb_file(test_file, test_content)
    
    # 创建分析器并分析文件
    analyzer = IcbAnalyzer()
    result = analyzer._file_analysis(test_file)
    
    # 空文件应该分析失败
    assert result == False, "空ICB文件分析应该失败"
    print("  ✓ 空ICB文件分析正确处理")
    
    # 清理测试文件
    os.remove(test_file)

def test_icb_with_indentation_errors():
    """测试包含缩进错误的ICB文件分析"""
    print("测试包含缩进错误的ICB文件分析...")
    
    # 创建一个包含缩进错误的ICB文件（跳级缩进）
    test_content = """class Ball:
description: 球体类，用于表示和管理球体的物理状态
inh: object

        var position: 球心坐标(x, y)  # 跳级缩进，应该报错
        
    var velocity: 速度向量(vx, vy)
"""
    
    test_file = "test_indent_error.icb"
    create_test_icb_file(test_file, test_content)
    
    # 创建分析器并分析文件
    analyzer = IcbAnalyzer()
    result = analyzer._file_analysis(test_file)
    
    # 分析应该继续进行，即使有错误
    assert result == True, "即使有缩进错误，分析也应该继续进行"
    print("  ✓ 包含缩进错误的ICB文件分析处理正确")
    
    # 清理测试文件
    os.remove(test_file)

def test_complex_icb_structure():
    """测试复杂的ICB结构分析"""
    print("测试复杂的ICB结构分析...")
    
    # 创建一个复杂的ICB文件
    test_content = """@ 球体物理引擎模块
class PhysicsEngine:
description: 物理引擎类，处理球体运动和碰撞检测
inh: object

    var balls: 存储所有球体的列表
    
    var gravity: 重力加速度
    
    func __init__:
    description: 初始化物理引擎
    input: gravity: float
    output: None
    behavior:
        初始化balls为空列表
        设置gravity值
    
    func add_ball:
    description: 添加球体到物理引擎
    input: ball: Ball
    output: None
    behavior:
        将ball添加到balls列表中
    
    func update:
    description: 更新所有球体的状态
    input: dt: float (时间步长)
    output: None
    behavior:
        对每个ball在balls中:
            如果ball不是静态的:
                应用重力加速度到ball的速度
                更新ball的位置使用dt时间步长
                检查ball与边界碰撞并处理
        
        对每对ball1, ball2在balls中:
            如果ball1和ball2碰撞:
                处理碰撞响应

@ 碰撞处理模块
func resolve_collision:
description: 处理两个球体之间的碰撞
input: ball1: Ball, ball2: Ball
output: None
behavior:
    计算碰撞法线方向
    分解ball1和ball2的速度到法线和切线方向
    交换法线方向的速度分量
    应用弹性系数调整速度
"""
    
    test_file = "test_complex.icb"
    create_test_icb_file(test_file, test_content)
    
    # 创建分析器并分析文件
    analyzer = IcbAnalyzer()
    result = analyzer._file_analysis(test_file)
    
    # 复杂结构应该分析成功
    assert result == True, "复杂ICB结构分析应该成功"
    print("  ✓ 复杂ICB结构分析成功")
    
    # 清理测试文件
    os.remove(test_file)

def main():
    """主测试函数"""
    print("开始测试ICB Analyzer功能...")
    print("=" * 50)
    
    try:
        test_basic_icb_analysis()
        test_icb_with_syntax_errors()
        test_empty_icb_file()
        test_icb_with_indentation_errors()
        test_complex_icb_structure()
        
        print("=" * 50)
        print("所有测试通过!")
        
    except Exception as e:
        print(f"测试失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()