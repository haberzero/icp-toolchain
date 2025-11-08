# import sys
# import os
# import tkinter as tk

# from ui.path_selector import PathSelector
# from ui.main_window import MainWindow

# from cfg.proj_cfg_manager import get_instance as get_proj_cfg_manager
# from data_exchange.app_data_manager import get_instance as get_app_data_manager

# from data_exchange.user_data_manager import get_instance as get_user_data_manager

# # UI 模式启动
# def main():
#     proj_cfg_manager = get_proj_cfg_manager()
#     app_data_manager = get_app_data_manager()
#     user_data_manager = get_user_data_manager()

#     root = tk.Tk()
#     main_window = MainWindow(root)
#     root.deiconify()

#     # 路径选择弹窗
#     last_path = app_data_manager.load_last_path()
#     if not last_path:
#         path_selector = PathSelector(root)
#     else:
#         path_selector = PathSelector(root, last_path)
#     root.wait_window(path_selector.window)
#     selected_path = path_selector.get_selected_path()

#     # 未选择路径 退出
#     if not selected_path or not proj_cfg_manager.set_work_dir(selected_path):
#         root.destroy()
#         return

#     proj_cfg_manager.set_work_dir(selected_path)
#     app_data_manager.save_last_path(selected_path)

#     # 更新目录树
#     main_window.populate_tree()

#     root.mainloop()

# if __name__ == "__main__":
#     main()
