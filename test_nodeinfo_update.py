#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试NodeInfo结构体更新后的功能
"""

import os
import sys
import tempfile
import shutil

from src_main.cfg.mccp_dir_content_manager import MccpDirContentManager

def test_nodeinfo_features():
    """测试NodeInfo的新功能"""
    
    # 创建临时目录进行测试
    temp_dir = tempfile.mkdtemp()
    print(f"使用临时目录: {temp_dir}")
    
    try:
        # 创建管理器实例
        manager = MccpDirContentManager(temp_dir)
        
        # 创建测试目录结构
        print("\n=== 创建测试目录结构 ===")
        manager.create_directory("src")
        manager.create_directory("src/utils")
        manager.create_directory("src/models")
        manager.create_file("src/main.py")
        manager.create_file("src/utils/helper.py")
        manager.create_file("src/models/user.py")
        manager.create_file("README.md")
        
        print("目录结构创建完成")
        
        # 测试list_directory的新功能
        print("\n=== 测试list_directory的parent和child_list字段 ===")
        root_items = manager.list_directory("")
        for item in root_items:
            print(f"名称: {item.name}")
            print(f"  路径: {item.path}")
            print(f"  是否目录: {item.is_directory}")
            print(f"  父节点: {item.parent}")
            print(f"  子节点: {item.child_list}")
            print()
        
        # 测试src目录的内容
        print("=== 测试src目录的内容 ===")
        src_items = manager.list_directory("src")
        for item in src_items:
            print(f"名称: {item.name}")
            print(f"  路径: {item.path}")
            print(f"  是否目录: {item.is_directory}")
            print(f"  父节点: {item.parent}")
            print(f"  子节点: {item.child_list}")
            print()
        
        # 测试get_node_info方法
        print("=== 测试get_node_info方法 ===")
        src_info = manager.get_node_info("src")
        if src_info:
            print(f"src节点信息:")
            print(f"  名称: {src_info.name}")
            print(f"  路径: {src_info.path}")
            print(f"  是否目录: {src_info.is_directory}")
            print(f"  父节点: {src_info.parent}")
            print(f"  子节点: {src_info.child_list}")
        
        # 测试get_descendants方法
        print("\n=== 测试get_descendants方法 ===")
        descendants = manager.get_descendants("src")
        print(f"src目录的所有子孙节点:")
        for desc in descendants:
            print(f"  {desc.path} ({'目录' if desc.is_directory else '文件'})")
        
        # 测试get_ancestors方法
        print("\n=== 测试get_ancestors方法 ===")
        ancestors = manager.get_ancestors("src/utils/helper.py")
        print(f"src/utils/helper.py的祖先节点:")
        for ancestor in ancestors:
            print(f"  {ancestor}")
        
        # 测试get_parent_info方法
        print("\n=== 测试get_parent_info方法 ===")
        parent_info = manager.get_parent_info("src/utils/helper.py")
        if parent_info:
            print(f"src/utils/helper.py的父节点信息:")
            print(f"  名称: {parent_info.name}")
            print(f"  路径: {parent_info.path}")
            print(f"  子节点: {parent_info.child_list}")
        
        # 测试get_all_paths的新功能
        print("\n=== 测试get_all_paths的parent和child_list字段 ===")
        all_paths = manager.get_all_paths()
        for node in all_paths:
            print(f"路径: {node.path}")
            print(f"  名称: {node.name}")
            print(f"  是否目录: {node.is_directory}")
            print(f"  父节点: {node.parent}")
            print(f"  子节点: {node.child_list}")
            print()
        
        print("✅ 所有测试完成")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"清理临时目录: {temp_dir}")

if __name__ == "__main__":
    test_nodeinfo_features()
