import sys
import os
import json
import argparse

# 导入并使用
from src_main.cfg import mccp_dir_content_manager

# 这个文件最主要的作用：从dir_content_manager中读取展平后的目录内容
# 三个generator函数，分别创建mcbc, mcpc, src_main的完整目录结构


class DirGenerator:
    def __init__(self, project_root):
        self.project_root = project_root
        self.dir_content_manager = mccp_dir_content_manager.get_instance()

    def generate_mcbc_dir(self):
        init_flag = self.dir_content_manager.is_initialized()
        if not init_flag:
            print("目录内容管理器未初始化，请检查代码逻辑。")
            return
        
        flat_path_dict = self.dir_content_manager.get_flat_path_dict()
        mcbc_dir = os.path.join(self.project_root, 'mcbc')
        if not os.path.exists(mcbc_dir):
            os.makedirs(mcbc_dir)
        
        for path, type_info in flat_path_dict.items():
            # 将路径最开头的proj_root替换为mcbc目录
            new_path = os.path.join(mcbc_dir, path.replace(self.project_root, ''))
            if type_info == 'dir':
                if not os.path.exists(new_path):
                    os.makedirs(new_path)
            elif type_info == 'file':
                if not os.path.exists(os.path.dirname(new_path)):
                    print("错误：理论来说所有文件的父目录都应该存在。")

                # 检查文件名是否有后缀，如果有后缀按照后缀名创建，如果没有后缀则创建*.mcbc文件
                if '.' in os.path.basename(new_path):
                    with open(new_path, 'w') as f:
                        f.write('')
                else:
                    with open(new_path + '.mcbc', 'w') as f:
                        f.write('')