import streamlit as st
import docx
import io
from openai import OpenAI
from PIL import Image

st.set_page_config(page_title="Lewuwu", page_icon="😋", layout="centered")
st.title("😋 Lewuwu")
st.caption("⚠️ 声明：个人非盈利开源项目，仅供学习交流。AI生成内容不代表作者观点，请遵守法律法规。")

# 👇 终极排版 CSS，完美还原图中的“引文+竖线”风格
st.markdown("""
<style>
    /* 1. AI 左侧：透明背景 + 灰色竖线 */
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarAssistant"]) {
        background-color: transparent !important;
        border-left: 3px solid #888 !important; 
        border-radius: 0 !important;
        padding-left: 15px !important;
        padding-top: 0px !important;
        padding-bottom: 0px !important;
        margin-top: 20px !important;
        margin-bottom: 20px !important;
        margin-right: auto !important; 
        width: fit-content !important;
        max-width: 85% !important;
    }
    
    /* 2. AI 里的正文（包括动作和台词），字体颜色深一点，不要斜体 */
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarAssistant"]) p {
        font-size: 15px !important;
        color: #333 !important;
        font-style: normal !important;
        line-height: 1.6 !important;
        margin-bottom: 8px !important;
    }

    /* 3. 用户右侧：灰色圆角气泡 */
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) {
        background-color: #f0f2f6 !important;
        border-radius: 16px !important;
        padding: 12px 18px !important;
        margin-top: 15px !important;
        margin-bottom: 15px !important;
        margin-left: auto !important;
        width: fit-content !important;
        max-width: 85% !important;
    }
</style>
""", unsafe_allow_html=True)

# 初始化数据
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
        default_model = "deepseek-ai/DeepSeek-V3"  # 默认换成 V3 帮你省心
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
    model_name = st.text_input("模型名称", value=default_model)
    
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
            
            # 👇 核心：强制 AI 使用截图里的排版逻辑
            system_prompt = f"""你是一个沉浸式互动小说引擎，请严格遵循以下文档中的设定和规则。
【设定文档】：
{doc_text}

【极其严格的排版格式（违反将视为不合格！）】：
1. 严禁描写玩家（我）的动作、语言和心理活动！你只能描写NPC的反应和环境。
2. 环境、动作、神态、心理等描写，全部直接写，**禁止加任何星号或斜体**。写完一段要换行。
3. 说话内容的格式必须是：NPC名字 + 冒号 + 中文双引号包裹的话。例如：沈之燎：“在外叫沈检察官，在家叫知了哥。”
4. 禁止写流水账，严格按照上面要求的格式和换行来排版。
5. 正文结束后，使用```text代码块输出状态面板（好感度、心情、动向）。"""
            
            st.session_state.sessions[st.session_state.current_session] = [{"role": "system", "content": system_prompt}]
            st.session_state.uploader_key += 1
            st.success("✅ 文档载入成功！现在可以开始对话了。")
            st.rerun()

# 主界面渲染聊天记录
current_messages = st.session_state.sessions[st.session_state.current_session]

for message in current_messages:
    if message["role"] != "system":
        avatar_img = st.session_state.user_avatar if message["role"] == "user" else st.session_state.ai_avatar
        
        # 注意这里：由于AI自己会在文字里写名字，所以这里我们不再重复加名字，避免出现两个名字
        if message["role"] == "assistant":
            with st.chat_message("assistant", avatar=avatar_img):
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
        
        with st.chat_message("assistant", avatar=st.session_state.ai_avatar):
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
