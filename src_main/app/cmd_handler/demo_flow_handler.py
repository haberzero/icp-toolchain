import asyncio
import os
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable, List, Tuple
from dataclasses import dataclass, field

from typedef.cmd_data_types import Colors, CommandInfo
from app.cmd_handler.base_cmd_handler import BaseCmdHandler
from utils.icp_ai_utils.icp_chat_inst import ICPChatInsts
from data_store.sys_prompt_manager import get_instance as get_sys_prompt_manager
from data_store.user_prompt_manager import get_instance as get_user_prompt_manager
from run_time_cfg.proj_run_time_cfg import get_instance as get_proj_run_time_cfg

# 暂时直接由ai生成，后续考虑是否要作为一个模板范例来指导cmd_handler的重构

# =================================================================================================
# 1. 核心基础设施 (Infrastructure)
# =================================================================================================

class ResourceManager:
    """资源管理器：封装繁琐的文件路径拼接和读写操作"""
    def __init__(self, work_dir: str):
        self.work_dir = work_dir
        self.data_dir = os.path.join(work_dir, 'icp_proj_data')
        self.staging_dir = os.path.join(work_dir, 'src_staging')
        self.ibc_dir = os.path.join(work_dir, 'src_ibc')
        # 确保目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.staging_dir, exist_ok=True)
        os.makedirs(self.ibc_dir, exist_ok=True)

    def read_text(self, path: str) -> str:
        """读取文本文件，自动处理异常"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"{Colors.WARNING}读取文件失败 {path}: {e}{Colors.ENDC}")
            return ""

    def save_text(self, path: str, content: str):
        """保存文本文件"""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print(f"{Colors.FAIL}保存文件失败 {path}: {e}{Colors.ENDC}")

    def get_depend_analysis_json(self) -> Dict[str, Any]:
        """特化方法：获取依赖分析结果"""
        path = os.path.join(self.data_dir, 'icp_dir_content_with_depend.json')
        content = self.read_text(path)
        return json.loads(content) if content else {}

    def get_one_file_req(self, file_path: str) -> str:
        """特化方法：获取单个文件的需求"""
        # 注意：这里假设 file_path 是相对路径，需要拼接到 staging 目录
        # 实际逻辑可能需要根据项目结构调整
        fname = f"{file_path}_one_file_req.txt"
        return self.read_text(os.path.join(self.staging_dir, fname))


@dataclass
class FlowContext:
    """流上下文：在状态机节点间传递的唯一对象"""
    # 基础设施
    rm: ResourceManager
    chat_handler: Any
    sys_prompt_manager: Any
    user_prompt_manager: Any
    
    # 全局数据 (只读)
    global_data: Dict[str, Any] = field(default_factory=dict)
    
    # 运行时状态 (可变)
    current_file_path: str = ""
    current_attempt: int = 0
    max_attempts: int = 3
    
    # 过程产物 (Artifacts)
    last_generated_content: Optional[str] = None
    last_sys_prompt: str = ""
    last_user_prompt: str = ""
    issues: List[str] = field(default_factory=list)
    fix_suggestion: str = ""
    
    # 流程控制
    should_terminate: bool = False

    def reset_per_file(self, file_path: str):
        """处理新文件时重置状态"""
        self.current_file_path = file_path
        self.current_attempt = 0
        self.last_generated_content = None
        self.last_sys_prompt = ""
        self.last_user_prompt = ""
        self.issues = []
        self.fix_suggestion = ""
        self.should_terminate = False


class FlowState(ABC):
    """状态基类"""
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def execute(self, ctx: FlowContext) -> str:
        """执行状态逻辑，返回下一个状态的名称"""
        pass


class FlowEngine:
    """流程引擎：驱动状态机运行"""
    def __init__(self, context: FlowContext):
        self.ctx = context
        self.states: Dict[str, FlowState] = {}
        self.start_state_name: str = ""

    def add_state(self, state: FlowState):
        self.states[state.name] = state
        return self # 链式调用

    def set_start(self, name: str):
        self.start_state_name = name
        return self

    async def run(self):
        current_name = self.start_state_name
        print(f"{Colors.OKBLUE}流程开始，起始状态: {current_name}{Colors.ENDC}")
        
        while current_name and current_name != "__END__":
            if self.ctx.should_terminate:
                print(f"{Colors.WARNING}流程被标记为终止。{Colors.ENDC}")
                break
                
            state = self.states.get(current_name)
            if not state:
                print(f"{Colors.FAIL}找不到状态: {current_name}{Colors.ENDC}")
                break
                
            # print(f"  -> 进入状态: {state.name}")
            try:
                next_name = await state.execute(self.ctx)
                current_name = next_name
            except Exception as e:
                print(f"{Colors.FAIL}状态 {state.name} 执行异常: {e}{Colors.ENDC}")
                import traceback
                traceback.print_exc()
                break
        
        print(f"{Colors.OKBLUE}流程结束。{Colors.ENDC}")


# =================================================================================================
# 2. 通用状态节点 (Generic States)
# =================================================================================================

class LLMGenerateState(FlowState):
    """通用的 LLM 生成状态"""
    def __init__(self, name: str, role_name: str, sys_template_key: str, user_template_key: str, 
                 next_state: str, retry_state: str = None):
        super().__init__(name)
        self.role_name = role_name
        self.sys_template_key = sys_template_key
        self.user_template_key = user_template_key
        self.next_state = next_state
        # 如果生成过程本身出错（如API挂了），可以跳转到 retry_state 或者直接失败
        self.retry_state = retry_state or "__END__"

    async def execute(self, ctx: FlowContext) -> str:
        print(f"    [AI生成] 正在调用角色 {self.role_name}...")
        
        # 1. 准备 Mapping
        mapping = self.prepare_mapping(ctx)
        
        # 2. 构建 Prompt
        # 如果 sys_template_key 是具体内容而不是key，需要适配逻辑。这里假设都是 key。
        # 为了灵活性，这里做一个简单的判断：如果 key 包含空格或很长，可能就是内容本身
        if " " in self.sys_template_key or len(self.sys_template_key) > 50:
            sys_prompt = self.sys_template_key
        else:
            sys_prompt = ctx.sys_prompt_manager.get_prompt(self.sys_template_key)
            
        user_prompt = ctx.user_prompt_manager.build_prompt_from_template(
            self.user_template_key, mapping
        )
        
        # 3. 记录上下文 (用于重试)
        ctx.last_sys_prompt = sys_prompt
        ctx.last_user_prompt = user_prompt
        
        # 4. 调用 API
        response, success = await ctx.chat_handler.get_role_response(
            role_name=self.role_name,
            sys_prompt=sys_prompt,
            user_prompt=user_prompt
        )
        
        if not success:
            print(f"    {Colors.WARNING}AI调用失败{Colors.ENDC}")
            return self.retry_state
            
        # 5. 清理结果并存入上下文
        from libs.text_funcs import ChatResponseCleaner
        cleaned_content = ChatResponseCleaner.clean_code_block_markers(response)
        ctx.last_generated_content = cleaned_content
        
        return self.next_state

    def prepare_mapping(self, ctx: FlowContext) -> Dict[str, str]:
        """子类可重写此方法以注入特定变量"""
        return {}


class ValidationState(FlowState):
    """通用的验证状态"""
    def __init__(self, name: str, success_state: str, fail_state: str, max_retry_fail_state: str):
        super().__init__(name)
        self.success_state = success_state
        self.fail_state = fail_state
        self.max_retry_fail_state = max_retry_fail_state

    async def execute(self, ctx: FlowContext) -> str:
        print(f"    [验证] 正在检查生成结果 (尝试 {ctx.current_attempt + 1}/{ctx.max_attempts})...")
        
        is_valid, issues = self.validate(ctx)
        
        if is_valid:
            print(f"    {Colors.OKGREEN}验证通过{Colors.ENDC}")
            return self.success_state
        else:
            print(f"    {Colors.WARNING}验证失败，发现 {len(issues)} 个问题{Colors.ENDC}")
            ctx.issues = issues
            
            ctx.current_attempt += 1
            if ctx.current_attempt >= ctx.max_attempts:
                print(f"    {Colors.FAIL}达到最大重试次数，放弃当前文件{Colors.ENDC}")
                return self.max_retry_fail_state
            else:
                return self.fail_state

    def validate(self, ctx: FlowContext) -> Tuple[bool, List[str]]:
        """子类必须实现：返回 (是否通过, 问题列表)"""
        return True, []


class AnalysisAndFixState(FlowState):
    """诊断与修复准备状态：通过 AI 分析问题并准备下一次的 Prompt"""
    def __init__(self, name: str, next_state: str):
        super().__init__(name)
        self.next_state = next_state

    async def execute(self, ctx: FlowContext) -> str:
        print(f"    [诊断修复] 正在分析失败原因并生成修复建议...")
        
        # 1. 构造诊断 Prompt (利用 PromptManager 的标准模板)
        issues_text = "\n".join(ctx.issues)
        
        analysis_mapping = {
            "PREVIOUS_SYS_PROMPT_PLACEHOLDER": ctx.last_sys_prompt or "(无)",
            "PREVIOUS_USER_PROMPT_PLACEHOLDER": ctx.last_user_prompt or "(无)",
            "PREVIOUS_CONTENT_PLACEHOLDER": ctx.last_generated_content or "(无输出)",
            "ISSUES_LIST_PLACEHOLDER": issues_text or "(未检测到问题描述)"
        }
        
        # 注意：这里直接硬编码了模板名称，实际使用时可以通过 init 参数传入
        analysis_sys_prompt = ctx.sys_prompt_manager.get_prompt("retry_analysis_sys_prompt")
        analysis_user_prompt = ctx.user_prompt_manager.build_prompt_from_template(
            "retry_analysis_prompt_template", analysis_mapping
        )
        
        # 2. 调用 AI 获取修复建议
        fix_suggestion_raw, success = await ctx.chat_handler.get_role_response(
            role_name="5_depend_analyzer", # 暂时借用一个角色，或者传入
            sys_prompt=analysis_sys_prompt,
            user_prompt=analysis_user_prompt
        )
        
        if success:
            ctx.fix_suggestion = fix_suggestion_raw
            print(f"    [诊断修复] 获得修复建议: {fix_suggestion_raw[:50]}...")
        else:
            print(f"    {Colors.WARNING}[诊断修复] 获取建议失败，将尝试盲修{Colors.ENDC}")
            ctx.fix_suggestion = "请根据上述问题列表修复代码。"
            
        return self.next_state


class RetryPromptBuildState(FlowState):
    """重试 Prompt 构建状态：将修复建议拼接到 User Prompt"""
    def __init__(self, name: str, next_state: str, code_block_type: str = "json"):
        super().__init__(name)
        self.next_state = next_state
        self.code_block_type = code_block_type

    async def execute(self, ctx: FlowContext) -> str:
        # 这里演示的是“更新上下文中的 User Prompt，然后跳回生成状态”
        # 但生成状态通常会重新从 Template 构建 Prompt。
        # 为了配合 Flow，我们需要让 LLMGenerateState 能够感知它是处于“重试模式”还是“初始模式”。
        # 或者，我们在这里直接构建好 prompt，并让 LLMGenerateState 有能力直接使用 ctx.user_prompt_override
        
        # 更好的做法：使用特定的 retry_template 构建一个新的 prompt，并覆盖 ctx 的某个临时变量
        # 简化起见，我们直接在这里构建完整的 Prompt 逻辑，并使用一个特殊的 "ApplyFixState" 
        # 或者，我们简单地修改 ctx.last_user_prompt (但这可能不够，因为我们需要 sys_prompt 也能配合)
        
        # 让我们采用最直观的方案：本状态负责构建 Prompt，并直接调用 AI，或者把 Prompt 存入 ctx，
        # 然后跳转到一个通用的 "ExecuteAIState"。
        
        # 这里为了演示方便，我们构建出重试专用的 Prompt，然后跳转回 LLMGenerateState 的变体，或者复用。
        # 鉴于 LLMGenerateState 封装了 build_from_template，我们可以继承它实现一个 LLMRetryState。
        
        pass # 此类仅为占位，实际逻辑合并到下面的 Specialized State 中


class LLMRetryExecutionState(FlowState):
    """执行修复生成的 AI 调用状态"""
    def __init__(self, name: str, role_name: str, next_state: str, code_block_type: str = ""):
        super().__init__(name)
        self.role_name = role_name
        self.next_state = next_state
        self.code_block_type = code_block_type

    async def execute(self, ctx: FlowContext) -> str:
        print(f"    [重试执行] 根据修复建议重新生成...")
        
        # 1. 构建重试 Prompt
        issues_text = "\n".join(ctx.issues)
        formatted_content = f"```{self.code_block_type}\n{ctx.last_generated_content}\n```"
        
        retry_mapping = {
            "PREVIOUS_CONTENT_PLACEHOLDER": formatted_content,
            "ISSUES_LIST_PLACEHOLDER": issues_text
        }
        
        # 使用 retry_prompt_template
        retry_user_prompt = ctx.user_prompt_manager.build_prompt_from_template(
            "retry_prompt_template", retry_mapping
        )
        
        retry_user_prompt += f"\n\n【修复建议】\n{ctx.fix_suggestion}"
        
        # 组合：Base Prompt + Retry Part
        # 这里有个问题：Base Prompt 怎么来？
        # 方案：我们在 Context 里存了 initial_user_prompt_base 吗？没有。
        # 改进：Context 应该在首次生成时保存 base prompt。
        # 假设 ctx.last_user_prompt 在第一次尝试时就是 base prompt (因为还没加 retry part)
        # 但如果已经是第2次重试，last_user_prompt 包含了上次的 retry part。
        # 所以我们需要一个 ctx.base_user_prompt。
        
        base_user_prompt = getattr(ctx, 'base_user_prompt', ctx.last_user_prompt)
        base_sys_prompt = getattr(ctx, 'base_sys_prompt', ctx.last_sys_prompt)
        
        final_user_prompt = base_user_prompt + "\n\n" + retry_user_prompt
        final_sys_prompt = base_sys_prompt + "\n\n" + ctx.sys_prompt_manager.get_prompt("retry_sys_prompt")
        
        # 更新上下文
        ctx.last_user_prompt = final_user_prompt
        ctx.last_sys_prompt = final_sys_prompt
        
        # 2. 调用 AI
        response, success = await ctx.chat_handler.get_role_response(
            role_name=self.role_name,
            sys_prompt=final_sys_prompt,
            user_prompt=final_user_prompt
        )
        
        if not success:
            return "__END__" # 简化处理
            
        from libs.text_funcs import ChatResponseCleaner
        ctx.last_generated_content = ChatResponseCleaner.clean_code_block_markers(response)
        
        return self.next_state


# =================================================================================================
# 3. 业务相关实现 (Business Specific Implementation) - 以 IBC Gen 为例
# =================================================================================================

class IBCGenState(LLMGenerateState):
    """IBC 专用的初始生成状态"""
    def prepare_mapping(self, ctx: FlowContext) -> Dict[str, str]:
        # 这里放置复杂的“从 Context 获取数据并填入 Mapping”的逻辑
        # 比如读取需求、提取参数、构建依赖列表等
        # 这些逻辑以前散落在 execute 方法中，现在被隔离在这里
        
        file_path = ctx.current_file_path
        
        # 模拟：从 ctx.rm 获取数据
        req_content = ctx.rm.get_one_file_req(file_path)
        
        # 为了演示，只做简单映射。实际代码会调用 helper 函数处理那些 class/func 提取
        return {
            "CLASS_CONTENT_PLACEHOLDER": "Class Placeholder for " + file_path,
            "FUNC_CONTENT_PLACEHOLDER": "Func Placeholder",
            # ... 其他占位符
            "AVAILABLE_SYMBOLS_PLACEHOLDER": "No symbols (demo)",
            "MODULE_DEPENDENCIES_PLACEHOLDER": "No deps (demo)",
            "EXTRACTED_PARAMS_PLACEHOLDER": "No params"
        }
        
    async def execute(self, ctx: FlowContext) -> str:
        # 重写 execute 以保存 base prompt
        result_state = await super().execute(ctx)
        # 保存第一次生成的 Prompt 作为 Base，供重试使用
        ctx.base_user_prompt = ctx.last_user_prompt
        ctx.base_sys_prompt = ctx.last_sys_prompt
        return result_state


class IBCValidateState(ValidationState):
    """IBC 专用的验证状态"""
    def validate(self, ctx: FlowContext) -> Tuple[bool, List[str]]:
        content = ctx.last_generated_content
        issues = []
        
        if not content:
            return False, ["内容为空"]
            
        # 模拟验证逻辑
        if "error" in content:
            issues.append("第1行: 代码包含 error 关键字")
            
        # 实际逻辑会调用 analyze_ibc_content(content)
        # ast, symbols, metadata = analyze_ibc_content(content, ...)
        
        return len(issues) == 0, issues


class IBCSaveState(FlowState):
    """IBC 保存状态"""
    def __init__(self, name: str):
        super().__init__(name)

    async def execute(self, ctx: FlowContext) -> str:
        print(f"    {Colors.OKGREEN}[保存] 成功保存文件: {ctx.current_file_path}{Colors.ENDC}")
        # ctx.rm.save_ibc_file(...)
        return "__END__"


# =================================================================================================
# 4. 实验性 Handler 入口
# =================================================================================================

class CmdHandlerExperiment(BaseCmdHandler):
    """实验性：基于流程编排的 Handler"""
    
    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="experiment_flow",
            aliases=["exp"],
            description="实验性：基于状态机流程的生成演示",
            help_text="演示如何使用新的架构进行 IBC 代码生成",
        )
        
        self.sys_prompt_manager = get_sys_prompt_manager()
        self.user_prompt_manager = get_user_prompt_manager()
        self.chat_handler = ICPChatInsts.get_instance(handler_key='coder_handler')
        
        proj_cfg = get_proj_run_time_cfg()
        self.work_dir = proj_cfg.get_work_dir_path()

    def execute(self):
        """入口方法"""
        print(f"{Colors.HEADER}启动实验性流程引擎...{Colors.ENDC}")
        asyncio.run(self._run_async())

    async def _run_async(self):
        # 1. 初始化上下文
        rm = ResourceManager(self.work_dir)
        ctx = FlowContext(
            rm=rm,
            chat_handler=self.chat_handler,
            sys_prompt_manager=self.sys_prompt_manager,
            user_prompt_manager=self.user_prompt_manager,
            max_attempts=3
        )
        
        # 2. 获取待处理文件列表 (模拟)
        # 实际应从 depend_relation 获取
        files_to_process = ["demo/file_a", "demo/file_b"]
        
        # 3. 构建流程引擎 (The Blueprint)
        # 定义状态图：
        # Start -> Gen -> Validate -> Success -> Save -> End
        #                  |
        #                  v (Fail)
        #               Analyze -> Fix -> RetryExec -> Validate
        
        engine = FlowEngine(ctx)
        
        # 注册状态节点
        engine.add_state(IBCGenState(
            name="generate",
            role_name="7_intent_behavior_code_gen",
            sys_template_key="7_intent_behavior_code_gen", # 假设 key 存在
            user_template_key="intent_code_behavior_gen_user", # 假设 key 存在
            next_state="validate",
            retry_state="__END__"
        ))
        
        engine.add_state(IBCValidateState(
            name="validate",
            success_state="save",
            fail_state="analyze",
            max_retry_fail_state="__END__"
        ))
        
        engine.add_state(AnalysisAndFixState(
            name="analyze",
            next_state="retry_exec"
        ))
        
        engine.add_state(LLMRetryExecutionState(
            name="retry_exec",
            role_name="7_intent_behavior_code_gen",
            next_state="validate",
            code_block_type="intent_behavior_code"
        ))
        
        engine.add_state(IBCSaveState(
            name="save"
        ))
        
        engine.set_start("generate")
        
        # 4. 循环处理每个文件
        for file_path in files_to_process:
            print(f"\n{Colors.BOLD}=== 处理文件: {file_path} ==={Colors.ENDC}")
            ctx.reset_per_file(file_path)
            await engine.run()
            
