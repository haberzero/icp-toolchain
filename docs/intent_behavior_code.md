# Intent Behavior Code (IBC) 语言参考手册

Intent Behavior Code（意图行为代码，简称 IBC）是一种结合自然语言与缩进结构、关键字机制的伪代码描述语言，是Intent Code Protocol 中的一个重要概念。本手册详细说明 IBC 的语法规则和使用方法。

## 语法总则

IBC 的关键字采用位置敏感设计。除 `self` 外，所有关键字仅在行首位置时生效，出现在其他位置时视为普通文本。

### 1. 模块引用 (module)

语法格式：`module 模块路径[: 描述]`

使用规则：

- 必须位于文件顶部
- 模块路径使用点号分隔，例如 `utils.logger` 对应文件路径 `utils/logger.ibc`
- 路径中不包含文件扩展名
- 引用的模块及其符号在当前文件中全局可见，通过 `$` 符号进行引用

示例：

```Intent Behavior Code
module utils.logger: 日志工具模块

func 初始化应用():
    日志器 = $logger.Logger(配置对象.log_level)
```

### 2. 函数定义 (func)

语法格式：

```Intent Behavior Code
func 函数名(<参数1>, <参数2>, ...):
    函数体描述

func 函数名(
    <参数1>[: 参数描述],
    <参数2>[: 参数描述]):
    函数体描述
```

使用规则：

- 参数描述为可选项
- 当提供参数描述时，由于描述中可能包含逗号，每个参数必须单独占一行
- 函数体需在冒号后换行，并缩进 4 个空格
- 函数体使用自然语言描述功能逻辑

示例：

```Intent Behavior Code
func 计算订单总价(
    商品列表: 包含价格信息的商品对象数组, 
    折扣率: 0到1之间的小数):
    var 总价 = 0
    遍历 商品列表 中的每个 商品:
        总价 = 总价 + 商品.价格
    返回 总价 × 折扣率
```

### 3. 类定义 (class)

语法格式：`class 类名([$父类符号][: 继承描述]):`

使用规则：

- 继承父类时使用 `$` 符号引用，例如 `$模块.类名`
- 顶层类默认为 public 可见性
- 类内成员默认为 public 可见性

示例：

```Intent Behavior Code
class UserManager($BaseManager: 使用公共基类管理生命周期):
    private
    var users: 用户数据字典
    
    public
    func 添加用户(用户名, 密码: 经过哈希处理的密码字符串):
        尝试验证 用户名 和 密码 的格式是否正确
        将用户保存到数据库
        返回 操作结果
```

### 4. 对外描述 (description)

语法格式：`description: 功能描述文本`（单行）或换行缩进（多行）

使用规则：

- 必须出现在函数或类定义之前
- 单行描述直接跟在冒号后，多行描述需换行并缩进
- 该描述主要用于外部引用时的说明，不直接参与当前代码生成

示例：

```Intent Behavior Code
description: 处理用户登录请求，验证凭据并返回认证结果
func 登录(用户名, 密码):
    <具体的功能描述>

description:
    从多个数据源读取配置信息，合并冲突设置，
    并提供热重载功能
class 配置管理器():
    private
    <内部私有成员定义>

    public
    <具体的class内容定义及描述>
```

### 5. 意图注释 (@)

语法格式：`@ 注释内容`（单行）

使用规则：

- 仅用于修饰函数或类定义，必须出现在定义之前
- 当与 `description` 同时使用时，`@` 注释应位于 `description` 和定义之间，独占一行
- 必须保持单行，不支持换行
- 用于提供设计决策、性能考虑、约束条件等补充信息
- 这些信息将在代码生成阶段提供给 AI

示例：

```Intent Behavior Code
description: 用户认证服务
@ 线程安全设计，所有公共方法都必须使用锁机制
class AuthService():
    public
    @ 使用bcrypt进行密码哈希
    func 哈希密码(明文密码):
        返回 哈希结果
```

### 6. 可见性声明 (public/protected/private)

语法格式：`public`、`protected`、`private`

使用规则：

- 仅在类内部使用，不可用于顶层定义
- 声明后的内容不需要额外缩进
- 该声明会影响后续所有符号（函数、变量）的可见性
- 符号定义默认为 public 可见性
- 建议在类中显式划分可见性区域，而非完全依赖默认行为
- 以下划线开头的内部实现方法、缓存变量等建议放在 `private` 区域，对外接口放在 `public` 区域

示例：

```Intent Behavior Code
class DataProcessor():
    private
    // _cache和_validate_data都会被标记为private
    var _cache: 缓存字典
    func _validate_data(数据):
        返回 验证结果

    // 从process_data开始被标记为public
    public
    func process_data(输入数据):
        验证结果 = self._validate_data(输入数据)
        返回 处理后数据 如果 验证结果 否则 None
```

### 7. 变量声明 (var)

语法格式：`var <变量名>[: 描述]`

使用规则：

- 描述为可选项，长度不超过 30 个汉字
- 描述中可使用 `$` 符号标注类型引用
- 不支持赋值语法（如 `var x = 0`）
- 不支持多变量声明（如 `var x, y`）

示例：

```Intent Behavior Code
var userCount: 当前在线用户数量
var logger: 日志实例，类型为 $logger.Logger
var config
```

### 8. 符号引用 ($)

语法格式：`$模块.符号` 或 `$符号`

使用规则：

- 用于在行为描述中引用函数、变量、类等符号
- 引用外部文件的符号必须使用 `$` 前缀，例如 `$logger.Logger`
- 当前文件内的符号在上下文明确时可省略 `$`
- 常见引用格式：`$外部变量名`、`$实例.方法(参数)`、`$文件名.类名.方法名`
- 符号引用以空格或其他符号分隔
- 点号 `.` 是引用的一部分，括号 `()` 不属于引用

示例：

```Intent Behavior Code
module utils.logger
module config.settings

func 初始化应用():
    配置对象 = $settings.load_config("app.json")
    日志器 = $logger.Logger(配置对象.log_level)
    如果 $settings.DEBUG_MODE:
        日志器.set_debug(True)
    返回 配置对象, 日志器

func 处理业务逻辑(
    数据, 
    日志器: 类型为 $logger.Logger):
    验证结果 = $validator.validate_data(数据)
    返回 处理成功 如果 验证结果.is_valid 否则 处理失败
```

### 9. 自引用关键字 (self)

语法格式：`self`

使用规则：

- `self` 是类中的隐式关键字，无需在函数参数中显式声明
- 在类的所有方法中默认可用，用于引用当前实例
- 使用 `self.属性名` 或 `self.方法名()` 访问实例成员
- 仅在类内部有效，不可在顶层函数或脚本代码中使用
- 即使方法参数列表为空，方法体内仍可直接使用 `self`

### 10. 行为描述

行为描述使用通顺、精炼的自然语言来表达程序逻辑。

语法规则：

- 可以出现在函数内部或文件顶层（脚本式代码）
- 行末冒号表示下一行需增加一级缩进
- 行末逗号表示下一行是当前行的延续，可跨多行，缩进可自定义但建议保持一致
- 非行末位置的冒号和逗号不具有语法意义
- 非行首位置的关键字不作为保留字处理

示例：

```Intent Behavior Code
如果 条件1,
    条件2,
    条件3 运行:
    执行操作
    定义列表 = [元素1, 元素2, 元素3]
```

### 11. 人员注释 (//)

人员注释用于为开发者提供说明，这些注释不会传递给 AI 模型。

示例：`// 这是一行注释`

## 语法结构模板

```Intent Behavior Code
module <模块路径>[: 描述]

// 顶层行为（脚本式代码用）
<执行步骤>
$<符号引用>

description: <功能描述>
@ <意图注释>
func <函数名>(<参数>[: 描述], ...):
    var <变量>[: 描述]
    self.<实例属性/方法>  // 类方法中使用
    <执行步骤>
    返回 <结果>

description: <功能描述>
@ <意图注释>
class <类名>([$父类][: 继承描述]):
    private
    var <私有变量>
    
    public
    description: <方法描述>
    func <方法名>(<参数>):
        self.<属性>  // 访问实例成员
        <执行步骤>
        返回 <结果>
```

## 完整代码示例

### 示例1：配置管理器（类定义）

```Intent Behavior Code
module json: 标准JSON解析库
module threading: 线程支持库

description: 线程安全的配置管理器，支持多数据源和热重载
@ 所有公共方法都保证线程安全，使用读写锁优化性能
class ConfigManager():
    private
    var configData: 当前配置数据
    var configPath: 主配置文件路径
    var rwLock: 读写锁对象，类型为 $threading.RLock
    
    func _load_from_file():
        从文件读取配置内容
        解析JSON数据
        返回 解析结果
    
    public
    description: 初始化配置管理器
    func __init__(配置文件路径: 字符串路径，支持相对和绝对路径):
        // 下面的变量/方法引用未写明显式引用，但已经足够明确
        self.configPath = 配置文件路径
        self.rwLock = 创建读写锁()
        self.加载配置()
    
    description: 从文件加载配置数据
    @ 使用JSON格式解析，自动处理编码问题
    func 加载配置():
        获取 self.rwLock 的写锁
        尝试:
            文件内容 = 读取文件(self.configPath)
            self.configData = json.parse(文件内容)
        捕获 异常:
            记录错误 "配置加载失败: " + 异常信息
        最后:
            释放 self.rwLock 的写锁
```

### 示例2：API客户端（类+异步）

```Intent Behavior Code
module requests: HTTP请求库
module logging: 日志记录库

description: 
    通用的REST API客户端，封装了重试机制、
    错误处理和请求日志记录功能
@ 具备异步处理功能
class ApiClient():
    private
    var baseUrl: API服务基础地址
    var timeout: 请求超时时间
    var session: HTTP会话对象，类型为 $requests.Session
    
    public
    description: 发送GET请求到指定接口
    @ 异步函数
    func 获取数据(
        接口路径: 相对路径，不需要包含基础URL, 
        查询参数: 字典形式的查询参数
    ):
        完整URL = self.baseUrl + 接口路径
        重试计数 = 0
        
        当 重试计数 < 3:
            尝试:
                响应 = self.session.get(完整URL, 查询参数)
                如果 响应.状态码 == 200:
                    返回 json.parse(响应.内容)
                否则:
                    记录警告 "API返回错误: " + 响应.状态码
                    抛出异常
            捕获 网络异常:
                重试计数 = 重试计数 + 1
                等待 2的重试计数次方 秒
        
        抛出异常 "请求失败，超过最大重试次数"
```

### 示例3：脚本式代码（顶层行为）

```Intent Behavior Code
module argparse: 命令行参数解析库
module config: 配置文件处理模块
module processor: 数据处理模块

// 顶层行为：直接在模块级别执行
初始化日志系统
设置日志级别为 INFO

解析器 = $argparse.ArgumentParser("数据处理工具")
解析器.添加参数("--input", "输入文件路径")
解析器.添加参数("--output", "输出文件路径")
命令行参数 = 解析器.解析()

如果 命令行参数.config:
    配置数据 = $config.load_config(命令行参数.config)
否则:
    配置数据 = $config.get_default_config()

如果 不存在文件(命令行参数.input):
    记录错误 "输入文件不存在"
    退出程序(1)

输入数据 = 读取文件(命令行参数.input)
处理结果 = $processor.process_data(输入数据, 配置数据)
写入文件(命令行参数.output, 处理结果)
记录信息 "处理完成"
```

## 编码规范

格式要求：

- 统一使用 4 个空格进行缩进
- 冒号后换行必须增加缩进
- 参数列表支持换行对齐
- 类内部推荐显式使用可见性声明来组织成员

长度限制：

- `description` 描述不超过 50 个汉字
- `@` 注释不超过 30 个汉字，且必须单行
- 参数和变量描述不超过 30 个汉字

使用约束：

- 不可在函数体内使用 `@` 注释
- 不可引用未定义的 `$` 符号
- 同一目标不可有多个 `@` 注释
- 冒号后换行必须缩进

## 最佳实践

编写 IBC 代码时，建议遵循以下原则：

1. 遵循实现规划：在多文件项目中，确保每个文件的功能定位与整体规划一致，准确体现文件的职责和调用关系。

2. 符合层级架构：根据分层架构设计（如基础层、业务层、应用层），确保依赖关系合理，上层可依赖下层，避免反向依赖。

3. 保持调用一致性：文件间的调用顺序和数据流转应当清晰明确，确保模块协作逻辑易于理解。

4. 显式声明可见性：在类定义中，根据成员职责合理划分可见性区域，提高代码的可读性和可维护性。
