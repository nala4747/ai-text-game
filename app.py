import streamlit as st
import docx
import io
from openai import OpenAI
from PIL import Image

st.set_page_config(page_title="Lewuwu", page_icon="😋", layout="centered")
st.title("😋 Lewuwu")
st.caption("⚠️ 声明：个人非盈利开源项目，仅供学习交流。AI生成内容不代表作者观点，请遵守法律法规。")

# 注入自定义 CSS，修复左右排版 + 高级聊天体验
st.markdown("""
<style>
    /* 1. AI 气泡（左侧）：透明背景 + 左侧竖线 */
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarAssistant"]) {
        background-color: transparent !important;
        border-left: 3px solid #777 !important; 
        border-radius: 0 !important;
        padding-left: 15px !important;
        padding-top: 5px !important;
        padding-bottom: 5px !important;
        margin-top: 15px !important;
        margin-bottom: 15px !important;
        margin-right: auto !important;
        width: fit-content !important;
        max-width: 90% !important;
    }
    
    /* 2. AI 气泡里的【动作/神态/心理】用小字、灰色斜体显示 */
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarAssistant"]) em {
        font-size: 13px !important;
        color: #888 !important;
        font-style: italic !important;
        display: block !important;
        margin-bottom: 5px !important;
    }

    /* 3. AI 气泡里的【对话内容】用正常大小、加粗显示，带引号 */
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarAssistant"]) p {
        font-size: 16px !important;
        color: #222 !important;
        font-weight: 500 !important;
        margin-bottom: 5px !important;
    }

    /* 4. 用户气泡（右侧）浅灰色 + 强制靠右 */
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) {
        background-color: #f0f2f6 !important;
        border-radius: 18px !important;
        padding: 10px 15px !important;
        margin-top: 10px !important;
        margin-bottom: 10px !important;
        margin-left: auto !important;
        width: fit-content !important;
        max-width: 90% !important;
    }
</style>
""", unsafe_allow_html=True)

# 初始化多会话数据
if "sessions" not in st.session_state:
    st.session_state.sessions = {"默认对话": []}
if "current_session" not in st.session_state:
    st.session_state.current_session = "默认对话"
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
if "user_avatar" not in st.session_state:
    st.session_state.user_avatar = "👤"
if "ai_avatar" not in st.session_state:
    st.session_state.ai_avatar = "😋"
if "ai_name" not in st.session_state:
    st.session_state.ai_name = "贺行枢"

# 侧边栏
with st.sidebar:
    st.header("⚙️ 设定与接入")
    
    api_provider = st.selectbox("选择 API 提供方", ["硅基流动", "DeepSeek", "智谱 AI", "自定义"])
    
    if api_provider == "硅基流动":
        base_url = "https://api.siliconflow.cn/v1"
        default_model = "Qwen/Qwen2.5-7B-Instruct"
    elif api_provider == "DeepSeek":
        base_url = "https://api.deepseek.com/v1"
        default_model = "deepseek-chat"
    elif api_provider == "智谱 AI":
        base_url = "https://open.bigmodel.cn/api/paas/v4/"
        default_model = "glm-4-flash"
    else:
        base_url = st.text_input("自定义 Base URL（例如 https://api.openai.com/v1）")
        default_model = ""

    user_api_key = st.text_input("请输入你的 API Key", type="password")
    model_name = st.text_input("模型名称（选好平台后会自动填好）", value=default_model)
    
    st.divider()
    st.subheader("🖼️ 头像与名字设置")
    
    st.session_state.ai_name = st.text_input("AI 角色名字", value=st.session_state.ai_name)
    
    upload_user_avatar = st.file_uploader("上传你的头像（可选）", type=["png", "jpg", "jpeg"])
    upload_ai_avatar = st.file_uploader("上传AI头像（可选）", type=["png", "jpg", "jpeg"])
    
    if upload_user_avatar is not None:
        st.session_state.user_avatar = Image.open(io.BytesIO(upload_user_avatar.getvalue()))
    if upload_ai_avatar is not None:
        st.session_state.ai_avatar = Image.open(io.BytesIO(upload_ai_avatar.getvalue()))

    st.divider()
    st.subheader("📂 对话管理")
    
    custom_window_name = st.text_input("输入新窗口名称（可选）", key="new_window_name_input")
    
    if st.button("➕ 新建对话窗口"):
        if custom_window_name.strip() == "":
            new_name = f"新对话 {len(st.session_state.sessions) + 1}"
        else:
            new_name = custom_window_name.strip()
            
        base_name = new_name
        counter = 1
        while new_name in st.session_state.sessions:
            new_name = f"{base_name} ({counter})"
            counter += 1
            
        st.session_state.sessions[new_name] = []
        st.session_state.current_session = new_name
        st.rerun()
        
    session_names = list(st.session_state.sessions.keys())
    current_index = session_names.index(st.session_state.current_session)
    selected = st.selectbox("选择历史对话", session_names, index=current_index)
    if selected != st.session_state.current_session:
        st.session_state.current_session = selected
        st.rerun()
        
    if st.button("🗑️ 删除当前对话"):
        if len(st.session_state.sessions) > 1:
            del st.session_state.sessions[st.session_state.current_session]
            st.session_state.current_session = list(st.session_state.sessions.keys())[0]
            st.rerun()
        else:
            st.warning("至少保留一个对话窗口")

    st.divider()
    st.subheader("📝 上传设定")
    
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

【输出排版格式（极其重要！必须严格遵守！）】：
1. 描写人物动作、神态、心理、环境时，请使用星号*包裹（例如：*他垂着眼，手指轻轻敲了敲桌面，没有看你。*），不要加引号。
2. 人物说话的内容，请放在动作描写的后面，使用英文双引号""括起来（例如："嗯，我知道了。"），不要用星号。
3. 动作描写和对话要分开换行，禁止混在同一行。
4. 正文结束后，使用```text代码块输出状态面板（好感度、心情、动向）。"""
            
            st.session_state.sessions[st.session_state.current_session] = [{"role": "system", "content": system_prompt}]
            st.session_state.uploader_key += 1
            st.success("✅ 文档载入成功！现在可以开始对话了。")
            st.rerun()

# 主界面渲染聊天记录
current_messages = st.session_state.sessions[st.session_state.current_session]

for message in current_messages:
    if message["role"] != "system":
        avatar_img = st.session_state.user_avatar if message["role"] == "user" else st.session_state.ai_avatar
        
        if message["role"] == "assistant":
            # 👇 修复报错：去掉不兼容的 name= 参数，直接用HTML把名字写在头顶
            with st.chat_message("assistant", avatar=avatar_img):
                st.markdown(f"<div style='font-size:13px; color:#555; font-weight:bold; margin-bottom:5px;'>{st.session_state.ai_name}</div>", unsafe_allow_html=True)
                st.markdown(message["content"])
        else:
            with st.chat_message("user", avatar=avatar_img):
                st.markdown(message["content"])

# 底部输入框逻辑
if prompt := st.chat_input("输入你的行动或对白..."):
    if not user_api_key:
        st.warning("⚠️ 请先在左侧栏输入你的 API Key！")
    elif not base_url:
        st.warning("⚠️ 请先填写正确的 Base URL！")
    else:
        st.session_state.sessions[st.session_state.current_session].append({"role": "user", "content": prompt})
        
        with st.chat_message("user", avatar=st.session_state.user_avatar):
            st.markdown(prompt)
        
        client = OpenAI(api_key=user_api_key, base_url=base_url)
        
        # 👇 修复报错：同样在流式输出时去掉不兼容的 name= 参数
        with st.chat_message("assistant", avatar=st.session_state.ai_avatar):
            st.markdown(f"<div style='font-size:13px; color:#555; font-weight:bold; margin-bottom:5px;'>{st.session_state.ai_name}</div>", unsafe_allow_html=True)
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                recent_messages = st.session_state.sessions[st.session_state.current_session][:1] + st.session_state.sessions[st.session_state.current_session][-6:]
                
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
                
                st.session_state.sessions[st.session_state.current_session].append({"role": "assistant", "content": full_response})
            except Exception as e:
                st.error(f"❌ 模型调用失败：{e}")
