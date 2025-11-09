#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""重构验证测试脚本"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试导入"""
    print("测试1: 检查导入...")
    try:
        from utils.cmd_handler.cmd_handler_ibc_gen import CmdHandlerIbcGen
        print("✓ CmdHandlerIbcGen 导入成功")
        return True
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        return False

def test_class_structure():
    """测试类结构"""
    print("\n测试2: 检查类结构...")
    try:
        from utils.cmd_handler.cmd_handler_ibc_gen import CmdHandlerIbcGen
        
        # 检查关键方法是否存在
        required_methods = [
            '_calculate_file_checksum',
            '_load_file_checksums',
            '_save_file_checksums',
            '_build_and_save_ast',
            '_process_symbol_normalization',
            '_extract_symbols_from_ast',
            '_call_symbol_normalizer_ai',
            '_load_symbols_table',
            '_save_symbols_table',
            '_extract_visible_symbols',
            '_build_available_symbols_text',
            '_init_ai_handler_1',
            '_init_ai_handler_2',
        ]
        
        for method_name in required_methods:
            if hasattr(CmdHandlerIbcGen, method_name):
                print(f"  ✓ 方法 {method_name} 存在")
            else:
                print(f"  ✗ 方法 {method_name} 不存在")
                return False
        
        return True
    except Exception as e:
        print(f"✗ 结构检查失败: {e}")
        return False

def test_prompt_files():
    """测试提示词文件是否存在"""
    print("\n测试3: 检查提示词文件...")
    
    prompt_files = [
        'icp_prompt_sys/9_symbol_normalizer.md',
        'icp_prompt_user/symbol_normalizer_user.md',
    ]
    
    all_exist = True
    for file_path in prompt_files:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        if os.path.exists(full_path):
            print(f"  ✓ 文件存在: {file_path}")
        else:
            print(f"  ✗ 文件不存在: {file_path}")
            all_exist = False
    
    return all_exist

def main():
    """主测试函数"""
    print("=" * 60)
    print("IBC代码生成器重构验证测试")
    print("=" * 60)
    
    results = []
    
    # 运行测试
    results.append(("导入测试", test_imports()))
    results.append(("类结构测试", test_class_structure()))
    results.append(("提示词文件测试", test_prompt_files()))
    
    # 输出结果
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in results:
        status = "通过" if result else "失败"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {test_name}: {status}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("所有测试通过！重构成功完成。")
        return 0
    else:
        print("部分测试失败，请检查相关问题。")
        return 1

if __name__ == '__main__':
    sys.exit(main())
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""重构验证测试脚本"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试导入"""
    print("测试1: 检查导入...")
    try:
        from utils.cmd_handler.cmd_handler_ibc_gen import CmdHandlerIbcGen
        print("✓ CmdHandlerIbcGen 导入成功")
        return True
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        return False

def test_class_structure():
    """测试类结构"""
    print("\n测试2: 检查类结构...")
    try:
        from utils.cmd_handler.cmd_handler_ibc_gen import CmdHandlerIbcGen
        
        # 检查关键方法是否存在
        required_methods = [
            '_calculate_file_checksum',
            '_load_file_checksums',
            '_save_file_checksums',
            '_build_and_save_ast',
            '_process_symbol_normalization',
            '_extract_symbols_from_ast',
            '_call_symbol_normalizer_ai',
            '_load_symbols_table',
            '_save_symbols_table',
            '_extract_visible_symbols',
            '_build_available_symbols_text',
            '_init_ai_handler_1',
            '_init_ai_handler_2',
        ]
        
        for method_name in required_methods:
            if hasattr(CmdHandlerIbcGen, method_name):
                print(f"  ✓ 方法 {method_name} 存在")
            else:
                print(f"  ✗ 方法 {method_name} 不存在")
                return False
        
        return True
    except Exception as e:
        print(f"✗ 结构检查失败: {e}")
        return False

def test_prompt_files():
    """测试提示词文件是否存在"""
    print("\n测试3: 检查提示词文件...")
    
    prompt_files = [
        'icp_prompt_sys/9_symbol_normalizer.md',
        'icp_prompt_user/symbol_normalizer_user.md',
    ]
    
    all_exist = True
    for file_path in prompt_files:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        if os.path.exists(full_path):
            print(f"  ✓ 文件存在: {file_path}")
        else:
            print(f"  ✗ 文件不存在: {file_path}")
            all_exist = False
    
    return all_exist

def main():
    """主测试函数"""
    print("=" * 60)
    print("IBC代码生成器重构验证测试")
    print("=" * 60)
    
    results = []
    
    # 运行测试
    results.append(("导入测试", test_imports()))
    results.append(("类结构测试", test_class_structure()))
    results.append(("提示词文件测试", test_prompt_files()))
    
    # 输出结果
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in results:
        status = "通过" if result else "失败"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {test_name}: {status}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("所有测试通过！重构成功完成。")
        return 0
    else:
        print("部分测试失败，请检查相关问题。")
        return 1

if __name__ == '__main__':
    sys.exit(main())
