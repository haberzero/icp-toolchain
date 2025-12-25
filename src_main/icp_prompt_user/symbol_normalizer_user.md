# 符号命名规范化

请你根据以下信息，将从IBC文件AST中提取的自然语言符号转换为符合编程规范的标识符。

## 文件信息

目标编程语言：

TARGET_LANGUAGE_PLACEHOLDER

文件路径：

FILE_PATH_PLACEHOLDER

文件上下文：

CONTEXT_INFO_PLACEHOLDER

## 待规范化的符号列表

以下是从当前文件的AST中提取的自然语言符号，每个符号包含其类型和描述信息。

**符号路径说明**：
- 顶层符号（类、全局函数、全局变量）：直接使用符号名
- 类成员（方法、字段）：使用 `类名.成员名` 格式
- 嵌套符号：使用点号连接的完整路径

**符号列表**：

AST_SYMBOLS_PLACEHOLDER

## 任务要求

请为上述每个符号提供**规范化的标识符名称**：

- 必须符合标准编程语言标识符规范
- 字母或下划线开头
- 仅包含字母、数字、下划线
- 根据目标编程语言的命名习惯进行标识符规范化
- 保留原始符号的核心语义
- 避免使用编程语言保留关键字

**输出JSON格式要求**：

1. JSON的 **key 必须与符号列表中的符号路径完全一致**
   - 如果符号是 `UserManager.add_user`，则 key 必须是 `"UserManager.add_user"`
   - 如果符号是 `calculateTotal`，则 key 必须是 `"calculateTotal"`
2. JSON的 **value 是规范化后的标识符**（不包含路径，只是名称本身）
3. 必须为每个输入符号提供对应的规范化名称

**示例**：
如果符号列表包含：
```
- UserManager (class, 描述: 用户管理器)
- UserManager.添加用户 (func, 描述: 添加新用户)
- 计算总价 (func, 描述: 计算订单总价)
```

你应该输出：
```json
{
  "UserManager": "UserManager",
  "UserManager.添加用户": "add_user",
  "计算总价": "calculate_total"
}
```

注意事项：

- 确保输出的是有效的JSON格式
- 外层key必须与输入的自然语言符号名完全一致
- 每个符号都必须有对应的输出
- 规范化名称必须符合目标语言的标识符规范
- 不要包含任何额外的字段或注释
