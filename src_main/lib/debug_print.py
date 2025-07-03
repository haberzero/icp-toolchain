# 定义全局变量，控制打印级别
PRINT_LEVEL = 2  # 可以在文件开头修改这个值

# 定义打印级别和对应的颜色
LEVELS = {
    0: {"name": "ERROR", "color": "\033[91m"},  # 红色
    1: {"name": "WARNING", "color": "\033[93m"},  # 黄色
    2: {"name": "INFO", "color": "\033[94m"},  # 蓝色
    3: {"name": "DEBUG", "color": "\033[92m"}  # 绿色
}

ERROR_T = 0
WARNING_T = 1
INFO_T = 2
DEBUG_T = 3

# 自定义条件打印函数
def DEBUG_PRINT(level, *args, **kwargs):
    # ANSI 转义序列，用于重置颜色
    RESET_COLOR = "\033[0m"
    if level <= PRINT_LEVEL:
        level_info = LEVELS.get(level, {"name": "UNKNOWN", "color": "\033[0m"})
        prefix = f"{level_info['color']}[{level_info['name']}] {RESET_COLOR}"
        print(prefix, *args, **kwargs)

# 使用示例
if __name__ == "__main__":
    DEBUG_PRINT(0, "这是一个错误信息")
    DEBUG_PRINT(1, "这是一个警告信息")
    DEBUG_PRINT(2, "这是一个普通信息")
    DEBUG_PRINT(3, "这是一个调试信息")