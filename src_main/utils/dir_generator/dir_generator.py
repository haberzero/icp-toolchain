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
        self.config_json_path = os.path.join(self.project_root, ".mccp_config/mccp_config.json")
        self.config_json_path = os.path.normpath(self.config_json_path)
        self.config_json_content = json.load(open(self.config_json_path, 'r', encoding='utf-8'))
        self.target_suffix = self.config_json_content["targetSuffix"]

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
            curr_path = os.path.join(mcbc_dir, path.replace('proj_root/', ''))
            if type_info == 'dir':
                if not os.path.exists(curr_path):
                    os.makedirs(curr_path)
            elif type_info == 'file':
                if not os.path.exists(os.path.dirname(curr_path)):
                    print("错误：理论来说所有文件的父目录都应该存在。")

                # 仅在文件不存在时创建文件
                if not os.path.exists(curr_path):
                    # 检查文件名是否有后缀，如果有后缀按照后缀名创建，如果没有后缀则创建*.mcbc文件
                    if '.' in os.path.basename(curr_path):
                        with open(curr_path, 'w') as f:
                            f.write('')
                    else:
                        with open(curr_path + '.mcbc', 'w') as f:
                            f.write('')

    def generate_src_main_dir(self):
        init_flag = self.dir_content_manager.is_initialized()
        if not init_flag:
            print("目录内容管理器未初始化，请检查代码逻辑。")
            return
        
        # 获取src_main的展平路径字典
        flat_path_dict = self.dir_content_manager.get_flat_path_dict()
        src_main_dir = os.path.join(self.project_root, 'src_main')
        if not os.path.exists(src_main_dir):
            os.makedirs(src_main_dir)
        
        for path, type_info in flat_path_dict.items():
            # 构造实际路径，将proj_root/src_main替换为实际的src_main目录
            curr_path = os.path.join(src_main_dir, path.replace('proj_root/', ''))
            
            if type_info == 'dir':
                if not os.path.exists(curr_path):
                    os.makedirs(curr_path)
            elif type_info == 'file':
                # 确保父目录存在
                parent_dir = os.path.dirname(curr_path)
                if not os.path.exists(parent_dir):
                    os.makedirs(parent_dir)
                
                # 仅在文件不存在时创建文件
                if not os.path.exists(curr_path):
                    # 检查文件名是否有后缀，如果有后缀按照后缀名创建，如果没有后缀则根据目标语言创建
                    if '.' in os.path.basename(curr_path):
                        with open(curr_path, 'w') as f:
                            f.write('')
                    else:
                        with open(curr_path + self.target_suffix, 'w') as f:
                            f.write('')
