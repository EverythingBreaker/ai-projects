"""
项目二:Agent 全流程自动化（模拟 + 日志 + 任务持久化）

功能：
- 根据用户需求自动生成视频脚本
- 支持任务持久化（关闭网页后恢复）
- 支持执行日志（调试 / 面试展示）
- 发布前需要人工确认
"""

import streamlit as st
import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from langchain_community.chat_models import ChatTongyi

# ==================== 配置 ====================
# TODO: 请在这里填入你的 API Key
os.environ["DASHSCOPE_API_KEY"] = "你的API_KEY"

# 日志配置
LOG_FILE = "agent_execution.log"
TASK_FILE = "agent_tasks.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== 数据模型 ====================
@dataclass
class AgentTask:
    """任务持久化数据结构"""
    task_id: str
    user_input: str
    topic: Optional[str]
    script: Optional[str]
    status: str  # pending / approved / published / cancelled
    created_at: str
    updated_at: str

# ==================== 工具函数 ====================
def save_task(task: AgentTask):
    """保存任务到本地文件"""
    tasks = []
    if os.path.exists(TASK_FILE):
        with open(TASK_FILE, "r", encoding="utf-8") as f:
            tasks = json.load(f)
    
    task_dict = asdict(task)
    # 更新或新增
    for i, t in enumerate(tasks):
        if t["task_id"] == task.task_id:
            tasks[i] = task_dict
            break
    else:
        tasks.append(task_dict)
    
    with open(TASK_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


def load_task(task_id: str) -> Optional[AgentTask]:
    """加载指定任务"""
    if not os.path.exists(TASK_FILE):
        return None
    with open(TASK_FILE, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    for t in tasks:
        if t["task_id"] == task_id:
            return AgentTask(**t)
    return None


def log_execution(step: str, details: str, level: str = "info"):
    """统一日志记录"""
    if level == "info":
        logger.info(f"[{step}] {details}")
    elif level == "error":
        logger.error(f"[{step}] {details}")
    elif level == "warning":
        logger.warning(f"[{step}] {details}")


def generate_task_id():
    """生成唯一任务ID"""
    return datetime.now().strftime("%Y%m%d%H%M%S%f")

# ==================== 模拟工具 ====================
def get_trending_topics() -> str:
    """获取热门话题（模拟）"""
    log_execution("get_trending_topics", "调用模拟热搜")
    return """1. #上下五千年历史
2. #编程语言学习趋势
3. #积木搭建挑战
4. #AI改变生活
5. #科技圈最新动态"""


def generate_script(topic: str) -> str:
    """生成视频脚本（模拟）"""
    log_execution("generate_script", f"为话题生成脚本: {topic}")
    return f"""【视频标题】{topic}的深度解析

【开场白】
大家好！今天我们来聊一个超火的话题：{topic}

【核心内容】
1. 什么是{topic}？为什么它这么重要？
2. 实际应用场景和案例分析
3. 学习/实践路径推荐
4. 常见误区与避坑指南

【互动话题】
你觉得{topic}对你的帮助大吗？欢迎在评论区留言讨论！

【结尾】
点赞收藏，下期带来更多干货！#知乎 #热点讨论 #{topic.replace('#', '')}"""


def post_to_zhihu(title: str, content: str) -> str:
    """模拟发布"""
    log_execution("post_to_zhihu", f"发布视频: {title}")
    return f"✅ 已成功发布到知乎！\n标题：{title}\n发布时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

# ==================== Agent 核心 ====================
def run_agent(user_input: str, task_id: str = None):
    """执行 Agent 主流程"""
    if not task_id:
        task_id = generate_task_id()
        log_execution("agent_start", f"新任务 ID: {task_id} | 用户需求: {user_input}")
    
    # 加载已有任务（如果存在）
    existing_task = load_task(task_id)
    if existing_task and existing_task.status == "approved":
        log_execution("agent_reuse", f"复用已批准任务: {task_id}")
        return existing_task.script, task_id, existing_task
    
    # 1. 获取热门话题
    topics_str = get_trending_topics()
    log_execution("step1", "获取话题成功")
    
    # 2. 提取第一个话题作为示例（实际可让用户选择）
    first_topic = topics_str.split("\n")[0].split(". ")[1]
    
    # 3. 生成脚本
    script = generate_script(first_topic)
    log_execution("step2", "脚本生成完成")
    
    # 4. 持久化当前任务
    task = AgentTask(
        task_id=task_id,
        user_input=user_input,
        topic=first_topic,
        script=script,
        status="pending",
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    save_task(task)
    
    return script, task_id, task

# ==================== Streamlit UI ====================
st.set_page_config(page_title="AI 视频助手", page_icon="🤖")
st.title("🤖 全流程 AI 视频助手")
st.caption("支持任务持久化 | 执行日志 | 发布前确认")

# 初始化 session
if "task_id" not in st.session_state:
    st.session_state.task_id = None
if "script" not in st.session_state:
    st.session_state.script = None
if "pending_post" not in st.session_state:
    st.session_state.pending_post = None

# 侧边栏：任务恢复
with st.sidebar:
    st.header("📋 历史任务")
    if os.path.exists(TASK_FILE):
        with open(TASK_FILE, "r", encoding="utf-8") as f:
            tasks = json.load(f)
        if tasks:
            task_options = {t["task_id"]: t["user_input"][:30] + "..." for t in tasks}
            selected_task_id = st.selectbox(
                "选择历史任务",
                options=list(task_options.keys()),
                format_func=lambda x: task_options[x]
            )
            if st.button("恢复任务"):
                task = load_task(selected_task_id)
                if task and task.script:
                    st.session_state.task_id = task.task_id
                    st.session_state.script = task.script
                    st.success(f"已恢复任务: {task.user_input}")
                    st.rerun()
    
    st.divider()
    st.caption(f"📄 日志文件: {LOG_FILE}")

# 主界面
user_input = st.chat_input("请输入需求，例如：帮我制作一个编程语言的视频发布到知乎")

if user_input:
    with st.spinner("🤖 Agent 工作中..."):
        script, task_id, task = run_agent(user_input, st.session_state.task_id)
        st.session_state.script = script
        st.session_state.task_id = task_id
        st.session_state.pending_post = {
            "title": f"AI 生成的视频：{task.topic}",
            "content": script
        }
        st.rerun()

# 显示脚本预览
if st.session_state.script:
    st.subheader("📝 生成的视频脚本")
    st.markdown(st.session_state.script)

# 发布确认区
if st.session_state.pending_post:
    st.divider()
    st.warning("⚠️ 请确认是否发布")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ 确认发布", use_container_width=True):
            result = post_to_zhihu(
                st.session_state.pending_post["title"],
                st.session_state.pending_post["content"]
            )
            # 更新任务状态
            task = load_task(st.session_state.task_id)
            if task:
                task.status = "published"
                save_task(task)
            st.success(result)
            st.session_state.pending_post = None
            st.rerun()
    with col2:
        if st.button("❌ 取消发布", use_container_width=True):
            st.session_state.pending_post = None
            st.rerun()

# 显示执行日志（可选）
with st.expander("📜 查看执行日志（调试用）"):
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            st.code(f.read()[-2000:])  # 只显示最后2000字符
    else:
        st.info("暂无日志")