import argparse
import os
import sys
import tkinter as tk

from app.icp_cmd_cli import IcpCmdCli
from data_store.app_data_store import get_instance as get_app_data_store
from data_store.user_data_store import get_instance as get_user_data_store
from run_time_cfg.proj_run_time_cfg import \
    get_instance as get_proj_run_time_cfg
from ui.path_selector import PathSelector


# CMD 模式启动
def main():
    parser = argparse.ArgumentParser(description='CMD模式启动')
    parser.add_argument('--work_dir', type=str, help='工作目录路径')
    parser.add_argument('--requirements', type=str, help='直接提供的需求内容')
    args = parser.parse_args()
    
    app_data_store = get_app_data_store()
    proj_run_time_cfg = get_proj_run_time_cfg()
    user_data_store = get_user_data_store()
    
    root = None
    
    # 配置icp项目目标工作目录
    if args.work_dir:
        work_dir = args.work_dir

    else:
        root = tk.Tk()
        last_path = app_data_store.load_last_path()
        if not last_path:
            path_selector = PathSelector(root)
        else:
            path_selector = PathSelector(root, last_path)
        root.wait_window(path_selector.window)
        work_dir = path_selector.get_selected_path()

        if not work_dir:
            print("未选择有效路径，程序退出")
            root.destroy()
            return

    proj_run_time_cfg.set_work_dir_path(work_dir)
    if not os.path.exists(work_dir):
        print(f"错误: 无法设置工作目录为 {work_dir}")
        if root:
            root.destroy()
        return

    app_data_store.save_last_path(work_dir)
    if root:
        root.destroy()
    
    if args.requirements:
        user_data_store.set_user_prompt(args.requirements)
        return
    else:
        requirement_file = os.path.join(work_dir, 'requirements.md')
        if os.path.exists(requirement_file):
            with open(requirement_file, 'r', encoding='utf-8') as f:
                requirement_content = f.read()
            user_data_store.set_user_prompt(requirement_content)

    cmd_interface = IcpCmdCli()
    cmd_interface.start_cli()

if __name__ == "__main__":
    main()
