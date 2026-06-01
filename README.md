# AI 应用开发作品集

包含两个完整的 AI 应用项目。

## 项目一：企业文档问答助手（RAG）
位置：`rag_qa_demo/rag_app.py`

功能：上传文档（txt/pdf/docx/md）、自动切分、向量化检索、LLM相关性过滤

运行方式：
cd rag_qa_demo
pip install -r requirements.txt
streamlit run rag_app.py

## 项目二：全流程 AI 视频助手（Agent）
位置：`agent_demo/agent_app.py`

功能：根据需求生成脚本、任务持久化、执行日志、发布前确认

运行方式：
cd agent_demo
streamlit run agent_app.py

## 环境配置
安装依赖：pip install -r requirements.txt
配置API Key：替换代码中的"你的apikey"

## 技术栈
Python + Streamlit + LangChain + 通义千问 + Chroma

## 联系方式
GitHub: EverythingBreaker
