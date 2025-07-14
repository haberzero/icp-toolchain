import os
import time
from threading import Thread
from queue import Queue
from src_main.lib.file_reader.file_operator import FileOperator
from PyQt5.QtCore import pyqtSignal, QObject

class TreeBuilder(QObject):
    update_signal = pyqtSignal(list)
    timeout_signal = pyqtSignal()

    def __init__(self, root_path, max_depth=5, file_ops=None):
        super().__init__()
        self.root_path = os.path.abspath(root_path)
        self.max_depth = max_depth
        self.file_ops = file_ops if file_ops else FileOperator(root_path)
        self.ignore_list = [os.path.abspath(p) for entry in self.file_ops.read_ignore_list() for p in entry.get('ignore_info', [])]
        self.nodes = []
        self.path_to_uid = {}
        self.stopped = False
        self.uid_to_node = {}
        self.thread: Thread | None = None  # 添加这一行，显式声明 thread 属性及其类型
    def _generate_uid(self, path):
        """生成稳定UID（路径的MD5前16位）"""
        import hashlib
        return hashlib.md5(path.encode('utf-8')).hexdigest()[:16]

    def _build_tree_thread(self):
        start_time = time.time()
        # 初始化根节点
        root_uid = self._generate_uid(self.root_path)
        self.path_to_uid[self.root_path] = root_uid
        self.nodes.append({
            "uid": root_uid,
            "name": os.path.basename(self.root_path),
            "path": self.root_path,
            "type": "folder",
            "parent_uid": None,  # 根节点无父节点
            "children_uids": []
        })
        self.uid_to_node[root_uid] = self.nodes[-1]  # 根节点加入映射

        # 广度优先遍历
        from collections import deque
        queue = deque([(self.root_path, 0)])  # (当前路径, 当前深度)

        while queue and not self.stopped:
            current_path, depth = queue.popleft()
            
            if depth >= self.max_depth and self.max_depth != 0:
                continue

            # 检查是否超时（每次处理目录前判断）
            if (time.time() - start_time) > 10:
                break

            try:
                entries = os.listdir(current_path)
            except PermissionError:
                continue

            for entry in entries:
                # 检查是否超时（每次处理文件/目录前判断）
                if (time.time() - start_time) > 10:
                    break
                full_path = os.path.join(current_path, entry)
                # 过滤忽略项/隐藏文件/符号链接
                if any(full_path.startswith(ignore) for ignore in self.ignore_list) or \
                    entry.startswith('.') or os.path.islink(full_path):
                    continue

                # 生成节点
                uid = self._generate_uid(full_path)
                node_type = "folder" if os.path.isdir(full_path) else "file"
                parent_uid = self.path_to_uid[current_path]

                # 记录节点
                self.path_to_uid[full_path] = uid
                self.nodes.append({
                    "uid": uid,
                    "name": entry,
                    "path": full_path,
                    "type": node_type,
                    "parent_uid": parent_uid,
                    "children_uids": [] if node_type == "folder" else None
                })
                self.uid_to_node[uid] = self.nodes[-1]  # 新节点加入映射

                # 更新父节点的 children_uids（通过 uid_to_node 快速查找）
                parent_node = self.uid_to_node.get(parent_uid)
                if parent_node:
                    parent_node["children_uids"].append(uid)

                # 文件夹加入队列继续遍历
                if node_type == "folder":
                    queue.append((full_path, depth + 1))

        self.update_signal.emit(self.nodes)  # 发送节点列表

    # 新增：启动目录树构建的入口方法
    def build_tree(self):
        """启动后台线程执行目录树构建"""
        self.thread = Thread(target=self._build_tree_thread)  # 保存线程引用以便后续管理
        self.thread.start()

    def stop(self):
        self.stopped = True

