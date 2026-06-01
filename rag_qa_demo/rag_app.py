"""
企业文档问答助手 - RAG系统
支持文档格式:txt, pdf, docx, md
"""

import streamlit as st
import tempfile
import os
from langchain_community.document_loaders import TextLoader, PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatTongyi

# ==================== 配置 ====================
os.environ["DASHSCOPE_API_KEY"] = "你的API_KEY"

# ==================== 初始化模型 ====================
@st.cache_resource
def init_models():
    embeddings = DashScopeEmbeddings(model="text-embedding-v4")
    llm = ChatTongyi(model="qwen-max")
    return embeddings, llm

embeddings, llm = init_models()

# ==================== Session 状态 ====================
if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = None
if "retriever" not in st.session_state:
    st.session_state.retriever = None

# ==================== 页面配置 ====================
st.set_page_config(page_title="企业文档问答助手", page_icon="📄")
st.title("📄 企业内部文档问答助手")

# ==================== 侧边栏：文档上传 ====================
with st.sidebar:
    st.header("📂 文档上传")
    st.caption("支持格式:txt / pdf / docx / md")
    
    uploaded_file = st.file_uploader(
        "选择文档",
        type=["txt", "pdf", "docx", "md"],
        help="上传后系统会自动切分并向量化"
    )
    
    if uploaded_file:
        try:
            file_extension = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
            
            if uploaded_file.name.endswith(".txt"):
                loader = TextLoader(tmp_path, encoding="utf-8")
            elif uploaded_file.name.endswith(".pdf"):
                loader = PyPDFLoader(tmp_path)
            elif uploaded_file.name.endswith(".docx"):
                loader = Docx2txtLoader(tmp_path)
            elif uploaded_file.name.endswith(".md"):
                loader = TextLoader(tmp_path, encoding="utf-8")
            else:
                st.error(f"不支持的文件格式：{file_extension}")
                st.stop()
            
            docs = loader.load()
            
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50
            )
            chunks = splitter.split_documents(docs)
            
            if not chunks:
                st.error("❌ 文档内容为空或无法切分，请检查文件")
                st.stop()
            
            st.session_state.vectorstore = Chroma.from_documents(chunks, embeddings)
            st.session_state.retriever = st.session_state.vectorstore.as_retriever(
                search_kwargs={"k": 10}
            )
            
            st.success(f"✅ 已加载 {len(chunks)} 个文档块")
            os.unlink(tmp_path)
            
        except Exception as e:
            st.error(f"❌ 处理文档时出错：{e}")

# ==================== Prompt 模板 ====================
prompt_template = ChatPromptTemplate([
    ("system", """你是一个基于参考资料的问答助手。请严格遵守以下规则:

1. **综合所有资料**：你必须综合**所有**提供的参考资料来回答问题，不能只根据第一块回答。
2. **逐块统计**：如果问题涉及"一共多少"、"总共几个"、"列举所有"，你必须**逐块阅读并统计**，不能只从一个块里找答案。
3. **冲突处理**：如果不同块中的信息有冲突或遗漏，你必须指出并尝试合并。
4. **引用来源**:回答结束后,在末尾另起一行加上(参考文档:第X、Y、Z块),X、Y、Z是你实际参考的文档块编号。

重要：你的回答中**不要出现"参考资料"、"参考文档"等字样**，这些只是给你看的，不要写进答案里。直接输出答案内容。

如果参考资料中没有相关信息，直接说"没有找到相关信息"，不用过多赘述其他。"""),
    ("human", "参考资料:\n{context}\n\n用户问题: {question}")
])

# ==================== 辅助函数 ====================
def filter_relevant_docs(question, docs):
    """严格判断哪些文档块与问题相关"""
    if not docs:
        return []
    
    relevant_docs = []
    for doc in docs:
        prompt = f"""判断以下文本块是否与用户问题**严格相关**。

用户问题: {question}

文本块内容:
{doc.page_content[:500]}

判断标准：
- 如果文本块直接回答了用户问题，或提供了回答问题必需的关键信息 → 回答"是"
- 如果文本块只是提到相关词汇但没有实质信息，或描述的是完全不同的内容 → 回答"否"

只回答"是"或"否":"""
        
        try:
            response = llm.invoke(prompt)
            if "是" in response.content:
                relevant_docs.append(doc)
        except Exception:
            # 出错时不保留，避免混入噪声
            pass
    
    return relevant_docs

# ==================== 主区域：问答 ====================
st.header("💬 提问")

question = st.text_input("请输入您的问题：", placeholder="例如：这份文档主要讲了什么内容？")

if st.session_state.retriever is None:
    st.info("👈 请先在左侧上传文档")
    
elif question:
    try:
        with st.spinner("正在处理您的问题..."):
            # ===== Step 1: 向量检索 =====
            raw_docs = st.session_state.retriever.invoke(question)
            
            # ===== Step 2: LLM严格相关性过滤 =====
            relevant_docs = filter_relevant_docs(question, raw_docs)
            
            if not relevant_docs:
                st.info("没有找到相关信息")
            else:
                # ===== Step 3: 构建上下文（只放内容，不加标记）=====
                context = "\n\n---\n\n".join([doc.page_content for doc in relevant_docs])
                
                # ===== Step 4: 调用模型生成答案 =====
                prompt = prompt_template.invoke({
                    "context": context,
                    "question": question
                })
                response = llm.invoke(prompt)
                answer = response.content
                
                # 显示答案
                st.markdown("### 🤖 回答")
                st.markdown(answer)
                
                # 在折叠区域展示**严格相关**的文档块
                with st.expander(f"📖 查看参考的文档块（共 {len(relevant_docs)} 块）"):
                    for i, doc in enumerate(relevant_docs, 1):
                        st.markdown(f"**参考块 {i}:**")
                        st.text(doc.page_content[:500] + ("..." if len(doc.page_content) > 500 else ""))
                        st.divider()
                            
    except Exception as e:
        st.error(f"❌ 生成回答时出错：{e}")

# ==================== 页脚 ====================
st.markdown("---")
st.caption("⚡ 支持 txt / pdf / docx / md 格式 | 智能检索 | LLM 相关性过滤")