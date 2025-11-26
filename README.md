# Intent Code Protocol Toolchain

本仓库是一个实现 Intent Code Protocol 所定义的工程结构的具体命令行工具。可用于从最初始的编程需求开始，逐步生成一个符合ICP规范的完整的代码工程

## 版本定义以及仓库状态

v0.0.1 - 初始版本，demo状态，仅包含一个基本可用的命令行应用以及相关的命令执行器

目前该项目的代码仍处于最初期的demo状态，无法保证绝对稳定运行，也不会承诺特定功能的持续存在

## 基本使用说明

1. 环境准备
   
    a. 确保已安装python。截至目前，本仓库所使用语法特性不超过3.8，但出于版本生命周期以及未来的持续开发考量，建议 python >= 3.11
   
    b. 安装poetry，截至2025.11.24，官方提供的安装指令：
   
        Linux, macOS, WSL:
   
        `curl -sSL https://install.python-poetry.org | python3 -`
   
        Windows (Powershell):
   
        `(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -`
   
    c. 拉取代码仓库并进入仓库根目录
   
        `git clone https://github.com/haberzero/icp-toolchain.git && cd icp-toolchain`
   
    d. 安装项目依赖
   
        `poetry install --no-root`
   
    e. 环境激活
   
        `poetry env activate`

3. 工程模板及目录准备
   
    a. 复制整个`./template_proj`至你所期望的路径下，并更改文件夹名称。请勿直接使用`template_proj`作为工程目录。
   
    b. 修改工程目录下的`requirements.md`, 向其中填写清晰完整的编程需求，其中的文本会作为最初的用户编程提示词使用
   
    c. 修改工程目录下的`.icp_proj_config/icp_api_config.json`, 填写`api-url`, `api-key`, `model` 等内容，目前仅使用`coder_handler`，建议模型`qwen3-coder-30b-a3b-instruct`。Embedding模型相对随意
   
    d. 修改工程目录下的`.icp_proj_config/icp_config.json`, 填写目标编程语言以及目标后缀名

5. 运行主命令行工具
   
    `poetry run ./src_main/main_cmd.py`

7. 自 `para_extract` 指令开始，按顺序执行后续所有指令直到 `code_gen`。指令执行时可直接使用缩写，如 `PE`, `CG`

8. 在生成过程中密切观察大模型的输出，并按需随时介入最新生成的文件以进行精细化调整（具体介入思路以及各中间文件的具体职责说明手册会在未来提供）

9. 生成最终目标代码后，阅读代码并自行调试。调试时可考虑直接修改生成的代码文件，也可考虑修改相关 `.ibc` 文件后重新生成目标代码（暂译意图行为描述代码）

## 作者留言

作者本职工作为电子工程及嵌入式C，非专业软件开发者，开发工作全凭个人热情以及下班后的休息时间。如在仓库结构/代码结构/自动化工具使用/文档 等层面出现严重疏漏或错误，还请多包容并礼貌指出，会尽力处理。

工程中的大部分代码都直接或间接地由AI参与生成，一切以功能的快速实现为重。会定期review及重构，以避免vibe代码的多次迭代自我污染。故代码结构本身并不保证绝对稳定，只会尽可能保护常用的方法和功能的一致性。

直到ICP的稳定版出现前，初学者都切勿直接以当前代码作为学习范例。相关类似问题在此提前致歉。

此为长期项目，作者精力有限且必须长期稳定地把握主要开发方向和目标，故暂无力顾及过多与未来主线无关的“愿望功能清单”。

欢迎志同道合者的加入。任何时候请保持礼貌交流。
