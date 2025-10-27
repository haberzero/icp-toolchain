#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试脚本入口文件
开发者可以通过修改变量来选择运行特定的测试脚本
"""

import sys
import os

# 添加项目路径到sys.path
sys.path.append(os.path.join(os.path.dirname(__file__)))

# 测试开关变量，设置为1表示运行对应测试，设置为0表示跳过
RUN_DIR_JSON_FUNCS_TEST = 0  # 目录JSON功能测试
RUN_IBC_LEXER_TEST = 0       # IBC词法分析器测试
RUN_IBC_PARSER_TEST = 1      # IBC解析器测试

def run_dir_json_funcs_test():
    """运行目录JSON功能测试"""
    print("开始运行目录JSON功能测试...")
    try:
        from _script_for_func_test.test_dir_json_funcs import main as dir_json_test_main
        dir_json_test_main()
        print("目录JSON功能测试完成!")
    except Exception as e:
        print(f"目录JSON功能测试出错: {e}")
        import traceback
        traceback.print_exc()

def run_ibc_lexer_test():
    """运行IBC词法分析器测试"""
    print("开始运行IBC词法分析器测试...")
    try:
        from _script_for_func_test.test_ibc_lexer import main as ibc_lexer_test_main
        ibc_lexer_test_main()
        print("IBC词法分析器测试完成!")
    except Exception as e:
        print(f"IBC词法分析器测试出错: {e}")
        import traceback
        traceback.print_exc()

def run_ibc_parser_test():
    """运行IBC解析器测试"""
    print("开始运行IBC解析器测试...")
    try:
        from _script_for_func_test.test_ibc_parser import main as ibc_parser_test_main
        ibc_parser_test_main()
        print("IBC解析器测试完成!")
    except Exception as e:
        print(f"IBC解析器测试出错: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    print("ICP工具链 - 功能测试入口")
    print("=" * 40)
    
    test_executed = False
    
    if RUN_DIR_JSON_FUNCS_TEST:
        run_dir_json_funcs_test()
        test_executed = True
    
    if RUN_IBC_LEXER_TEST:
        run_ibc_lexer_test()
        test_executed = True
        
    if RUN_IBC_PARSER_TEST:
        run_ibc_parser_test()
        test_executed = True
    
    if not test_executed:
        print("未选择任何测试，请修改变量设置后重试。")
    
    print("=" * 40)
    print("测试运行结束")

if __name__ == "__main__":
    main()