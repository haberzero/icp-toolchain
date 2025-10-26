class IbcParserUidGenerator:
    def __init__(self):
        self.uid = 0    # AST Node uid
    
    def peek_uid(self) -> int:
        """获取下一个编号，但不改变编号"""
        return self.uid + 1

    def gen_uid(self) -> int:
        """获取下一个可用的编号"""
        self.uid += 1   # 从1开始，0被认为是root
        return self.uid
    
    def get_current_uid(self) -> int:
        """获取当前编号"""
        return self.uid