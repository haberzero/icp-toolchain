import sys
import os
import json
import argparse

# 导入并使用
from src_main.cfg import mccp_dir_content_manager

# 这个文件最主要的作用：从dir_content_manager中读取展平后的目录内容
# 三个generator函数，分别创建mcbc, mcpc, src_main的完整目录结构


class DirGenerator:
    def __init__(self, project_path):
        self.project_path = project_path
        self.dir_content_manager = mccp_dir_content_manager.get_instance()

    def generate_mcbc_dir(self):
        pass

    def generate_mcpc_dir(self):
        pass

    def generate_src_main_dir(self):
        pass