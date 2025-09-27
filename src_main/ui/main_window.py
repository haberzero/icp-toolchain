import tkinter as tk
from tkinter import ttk
import os
from cfg.proj_cfg_manager import get_instance as get_proj_cfg_manager
from data_exchange.user_data_manager import get_instance as get_user_data_manager


class MainWindow:
    def __init__(self, parent):
        self.parent = parent
        self.proj_cfg_manager = get_proj_cfg_manager()
        self.user_data_manager = get_user_data_manager()
        self.create_window()
        self.populate_tree()

    def center_window(self, window, width, height):
        # 获取屏幕尺寸
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        
        # 计算居中位置
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        # 设置窗口位置
        window.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_window(self):
        self.window = self.parent
        self.window.title("项目管理工具")
        
        # 设置窗口大小并居中
        self.center_window(self.window, 1000, 600)

        # 创建主框架
        main_frame = tk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 创建三个区域的框架
        # 左侧目录树框架
        left_frame = tk.Frame(main_frame, width=200)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_frame.pack_propagate(False)

        # 中间文本显示框架
        middle_frame = tk.Frame(main_frame)
        middle_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # 右侧显示框架
        right_frame = tk.Frame(main_frame, width=200)
        right_frame.pack(side=tk.LEFT, fill=tk.Y)
        right_frame.pack_propagate(False)

        # 创建目录树
        left_label = tk.Label(left_frame, text="项目目录结构")
        left_label.pack(anchor=tk.W)

        self.tree = ttk.Treeview(left_frame)
        tree_scrollbar = tk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)

        # 创建中间文本显示区域
        middle_label = tk.Label(middle_frame, text="文件内容")
        middle_label.pack(anchor=tk.W)

        self.text_display = tk.Text(middle_frame, wrap=tk.WORD, state=tk.DISABLED)
        text_scrollbar = tk.Scrollbar(middle_frame, orient=tk.VERTICAL, command=self.text_display.yview)
        self.text_display.configure(yscrollcommand=text_scrollbar.set)

        self.text_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 创建右侧显示区域
        right_label = tk.Label(right_frame, text="信息显示")
        right_label.pack(anchor=tk.W)

        self.info_display = tk.Text(right_frame, wrap=tk.WORD, state=tk.DISABLED)
        info_scrollbar = tk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.info_display.yview)
        self.info_display.configure(yscrollcommand=info_scrollbar.set)

        self.info_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        info_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 创建用户交互区域
        bottom_frame = tk.Frame(self.window, height=150)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(0, 5))
        bottom_frame.pack_propagate(False)

        # 用户输入区域
        input_frame_container = tk.Frame(bottom_frame)
        input_frame_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        input_label = tk.Label(input_frame_container, text="初始需求输入区:")
        input_label.pack(anchor=tk.W, fill=tk.X)  # 让input_label占据整个上方部分

        input_frame = tk.Frame(input_frame_container)
        input_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.user_input = tk.Text(input_frame, wrap=tk.WORD, height=4)
        input_scrollbar = tk.Scrollbar(input_frame, orient=tk.VERTICAL, command=self.user_input.yview)
        self.user_input.configure(yscrollcommand=input_scrollbar.set)

        self.user_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        input_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 按钮区域
        button_frame = tk.Frame(bottom_frame)
        button_frame.config(width=200)
        button_frame.pack(side=tk.RIGHT, fill=tk.Y)
        button_frame.pack_propagate(False)

        # 创建按钮区域容器
        buttons_column1 = tk.Frame(button_frame)
        buttons_column1.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        spacer_label = tk.Label(buttons_column1, text="")
        spacer_label.pack(fill=tk.X, pady=(0, 2)) # 控制与下方按钮的间距

        # 按钮信息列表
        buttons_info = [
            ("按钮1", self.on_button1_click),
            ("按钮2", self.on_button2_click),
            ("按钮3", self.on_button3_click),
            ("按钮4", self.on_button4_click),
        ]

        for text, command in buttons_info:
            btn = tk.Button(
                buttons_column1,
                text=text,
                command=command,
                width=10,
            )
            btn.pack(fill=tk.X, expand=True, pady=1)
        
        # 创建第二列按钮区域容器
        buttons_column2 = tk.Frame(button_frame)
        buttons_column2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        spacer_label2 = tk.Label(buttons_column2, text="")
        spacer_label2.pack(fill=tk.X, pady=(0, 2))  # 控制与下方按钮的间距

        # 第二列按钮信息列表
        buttons_info2 = [
            ("按钮5", self.on_button5_click),
            ("按钮6", self.on_button6_click),
            ("按钮7", self.on_button7_click),
            ("按钮8", self.on_button8_click),
        ]

        for text, command in buttons_info2:
            btn = tk.Button(
                buttons_column2,
                text=text,
                command=command,
                width=10,
            )
            btn.pack(fill=tk.X, expand=True, pady=1)

        # 绑定用户输入事件
        self.user_input.bind('<KeyRelease>', self.on_user_input_change)

    def populate_tree(self):
        # 清空现有项目树
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 获取项目根路径
        root_path = self.proj_cfg_manager.get_work_dir()
        if not root_path or not os.path.exists(root_path):
            return

        # 添加根节点
        root_node = self.tree.insert('', 'end', text=os.path.basename(root_path), values=[root_path])

        # 递归添加子目录和文件
        self.add_nodes(root_node, root_path)

    def add_nodes(self, parent, path):
        try:
            for item in sorted(os.listdir(path)):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    # 添加目录节点
                    node = self.tree.insert(parent, 'end', text=item, values=[item_path])
                    # 递归添加子节点
                    self.add_nodes(node, item_path)
                else:
                    # 添加文件节点
                    self.tree.insert(parent, 'end', text=item, values=[item_path])
        except PermissionError:
            # 处理权限不足的情况
            pass

    def on_tree_select(self, event):
        # 获取选中的项目
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        item_path = self.tree.item(item, 'values')[0]

        # 检查是否为文件
        if os.path.isfile(item_path):
            # 尝试读取并显示文件内容
            self.display_file_content(item_path)
        else:
            # 如果是目录，清空显示
            self.clear_text_display()

    def display_file_content(self, file_path):
        try:
            # 尝试以文本方式读取文件
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # 显示文件内容
            self.text_display.config(state=tk.NORMAL)
            self.text_display.delete(1.0, tk.END)
            self.text_display.insert(1.0, content)
            self.text_display.config(state=tk.DISABLED)
        except (UnicodeDecodeError, PermissionError, FileNotFoundError):
            # 如果文件无法读取为文本，则显示空白
            self.clear_text_display()

    def clear_text_display(self):
        self.text_display.config(state=tk.NORMAL)
        self.text_display.delete(1.0, tk.END)
        self.text_display.config(state=tk.DISABLED)

    def on_user_input_change(self, event=None):
        # 获取用户输入并保存到单例中
        user_input = self.user_input.get(1.0, tk.END)
        self.user_data_manager.set_user_prompt(user_input)

    def on_button1_click(self):
        # 按钮1功能待实现
        pass

    def on_button2_click(self):
        # 按钮2功能待实现
        pass

    def on_button3_click(self):
        # 按钮3功能待实现
        pass

    def on_button4_click(self):
        # 按钮4功能待实现
        pass

    def on_button5_click(self):
        # 按钮5功能待实现
        pass

    def on_button6_click(self):
        # 按钮6功能待实现
        pass

    def on_button7_click(self):
        # 按钮7功能待实现
        pass

    def on_button8_click(self):
        # 按钮8功能待实现
        pass