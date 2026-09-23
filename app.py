import streamlit as st
import docx
import io
from openai import OpenAI

st.set_page_config(page_title="开源文游平台", page_icon="🎭", layout="centered")
st.title("🎭 开源文字游戏")
st.caption("上传文档，即刻开演。")

# 初始化多会话数据
if "sessions" not in st.session_state:
    # 默认开一个初始窗口
    st.session_state.sessions = {"默认对话": []}
if "current_session" not in st.session_state:
    st.session_state.current_session = "默认对话"
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# 侧边栏
with st.sidebar:
    st.header("⚙️ 设定与接入")
    
    # API Key 配置
    user_api_key = st.text_input("请输入你的硅基流动 API Key", type="password")
    base_url = "https://api.siliconflow.cn/v1"
    model_name = "Qwen/Qwen2.5-7B-Instruct"
    
    st.divider()
    st.subheader("📂 对话管理")
    
    # 1. 新建对话按钮
    if st.button("➕ 新建对话窗口"):
        new_name = f"新对话 {len(st.session_state.sessions) + 1}"
        st.session_state.sessions[new_name] = []
        st.session_state.current_session = new_name
        st.rerun()
        
    # 2. 切换历史对话
    session_names = list(st.session_state.sessions.keys())
    # 找到当前对话在列表里的位置
    current_index = session_names.index(st.session_state.current_session)
    selected = st.selectbox("选择历史对话", session_names, index=current_index)
    if selected != st.session_state.current_session:
        st.session_state.current_session = selected
        st.rerun()
        
    # 3. 删除当前对话
    if st.button("🗑️ 删除当前对话"):
        if len(st.session_state.sessions) > 1:
            del st.session_state.sessions[st.session_state.current_session]
            st.session_state.current_session = list(st.session_state.sessions.keys())[0]
            st.rerun()
        else:
            st.warning("至少保留一个对话窗口")

    st.divider()
    st.subheader("📝 上传设定")
    
    # 上传文档（绑定到当前会话）
    uploaded_file = st.file_uploader(
        "上传角色设定文档（.docx 或 .txt）", 
        type=["docx", "txt"], 
        key=f"uploader_{st.session_state.uploader_key}"
    )
    
    if uploaded_file is not None:
        if st.button("🚀 载入设定并开始游戏"):
            if uploaded_file.name.endswith(".docx"):
                doc = docx.Document(io.BytesIO(uploaded_file.getvalue()))
                doc_text = "\n".join([para.text for para in doc.paragraphs])
            else:
                doc_text = uploaded_file.getvalue().decode("utf-8")
            
            system_prompt = f"""你是一个沉浸式互动小说引擎，目前正在进行创意写作。
请严格遵循以下文档中的设定、性格和规则，禁止说教，禁止跳出剧情。
【设定文档】：
{doc_text}
【输出规则】：
1. 全程使用第二人称“你”指代玩家。
2. 禁止替玩家做决定、做动作、做心理活动。
3. 正文结束后，使用```text代码块输出状态面板（好感度、心情、动向）。"""
            
            # 替换当前会话的上下文（第一条就是系统设定）
            st.session_state.sessions[st.session_state.current_session] = [{"role": "system", "content": system_prompt}]
            # 清空上传器，准备下一次
            st.session_state.uploader_key += 1
            st.success("✅ 文档载入成功！现在可以开始对话了。")
            st.rerun()

# 主界面：渲染当前对话记录
current_messages = st.session_state.sessions[st.session_state.current_session]

for message in current_messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# 输入框
if prompt := st.chat_input("输入你的行动或对白..."):
    if not user_api_key:
        st.warning("⚠️ 请先在左侧栏输入你的硅基流动 API Key！")
    else:
        # 1. 把用户输入加入当前会话
        current_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # 2. 准备请求模型
        client = OpenAI(api_key=user_api_key, base_url=base_url)
        
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                # 3. 只保留系统设定和最近6条对话记录（防卡顿）
                recent_messages = current_messages[:1] + current_messages[-6:]
                
                response = client.chat.completions.create(
                    model=model_name,
                    messages=recent_messages,
                    stream=True,
                )
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                        message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
                
                # 4. 把 AI 回复加入当前会话
                current_messages.append({"role": "assistant", "content": full_response})
            except Exception as e:
                st.error(f"❌ 模型调用失败：{e}")