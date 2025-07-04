import os
import json
import argparse

# 此文件后面全部重构，应该去调用cfg文件里的manager来进行操作

# def create_structure(data, base_path):
#     """递归生成文件夹和文件"""
#     for name, value in data.items():
#         current_path = os.path.join(base_path, name)
#         if value is None:
#             # 创建文件（值为null时视为文件）
#             with open(current_path, 'w', encoding='utf-8') as f:
#                 pass  # 创建空文件
#             print(f"创建文件: {current_path}")
#         elif isinstance(value, dict):
#             # 创建文件夹（值为字典时视为文件夹）
#             os.makedirs(current_path, exist_ok=True)
#             print(f"创建文件夹: {current_path}")
#             # 递归处理子目录
#             create_structure(value, current_path)

# def main():
#     # 解析命令行参数（指定JSON文件路径和目标生成路径）
#     parser = argparse.ArgumentParser(description='根据JSON生成文件夹结构')
#     parser.add_argument('--json_path', type=str, required=True, help='JSON文件路径')
#     parser.add_argument('--target_dir', type=str, default='.', help='目标生成目录（默认当前目录）')
#     args = parser.parse_args()

#     # 读取JSON文件
#     with open(args.json_path, 'r', encoding='utf-8') as f:
#         structure_data = json.load(f)

#     # 确保目标目录存在
#     os.makedirs(args.target_dir, exist_ok=True)
    
#     # 开始生成结构
#     create_structure(structure_data, args.target_dir)
#     print("文件夹结构生成完成！")

# if __name__ == '__main__':
#     main()