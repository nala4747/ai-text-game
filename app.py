import streamlit as st
from supabase import create_client, Client
import docx
import io
from openai import OpenAI
from PIL import Image

# ==========================================
# ⚠️ 这里填入你的 Supabase 项目信息
# ==========================================
SUPABASE_URL = "https://gytwfzambyjutiwqoriv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd5dHdmemFtYnlqdXRpd3Fvcml2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAxNDc2MDYsImV4cCI6MjEwNTcyMzYwNn0.54rzjB0Ht7VZUOEwbiUdaJk6y3ElMUGgFqaRJl6ZWxs"
# ==========================================

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

st.set_page_config(page_title="Lewuwu", page_icon="😋", layout="centered")
st.title("😋 Lewuwu")
st.caption("⚠️ 声明：个人非盈利开源项目，仅供学习交流。AI生成内容不代表作者观点，请遵守法律法规。")

# 👇 完美排版 CSS
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
    /* 2. AI 里的正文 */
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

# --- 初始化 Session State ---
if "user" not in st.session_state:
    st.session_state.user = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "conversations" not in st.session_state:
    st.session_state.conversations = {}
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_avatar" not in st.session_state:
    st.session_state.user_avatar = "👤"
if "ai_avatar" not in st.session_state:
    st.session_state.ai_avatar = "😋"
if "ai_name" not in st.session_state:
    st.session_state.ai_name = "贺行枢"

# --- 用户认证界面 ---
if st.session_state.user is None:
    st.subheader("欢迎来到 Lewuwu")
    auth_mode = st.radio("选择模式", ["登录", "注册"], horizontal=True)
    email = st.text_input("邮箱")
    password = st.text_input("密码", type="password")
    
    if st.button("提交"):
        try:
            if auth_mode == "注册":
                res = supabase.auth.sign_up({"email": email, "password": password})
                st.success("注册成功！请直接登录（如果提示验证，请去邮箱点确认链接）。")
            else:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.session_state.user_id = res.user.id
                st.rerun()
        except Exception as e:
            st.error(f"操作失败: {e}")
    st.stop() # 未登录时不显示后续内容

# --- 已登录界面 ---
if "conversations" not in st.session_state or not st.session_state.conversations:
    res = supabase.table("conversations").select("*").eq("user_id", st.session_state.user_id).order("created_at", desc=True).execute()
    st.session_state.conversations = {c['title']: c['id'] for c in res.data}

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 设定与接入")
    
    st.success(f"已登录: {st.session_state.user.email}")
    if st.button("退出登录"):
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()
        
    st.divider()
    
    api_provider = st.selectbox("选择 API 提供方", ["硅基流动", "DeepSeek", "智谱 AI", "自定义"])
    if api_provider == "硅基流动":
        base_url = "https://api.siliconflow.cn/v1"
        default_model = "deepseek-ai/DeepSeek-V3"
    elif api_provider == "DeepSeek":
        base_url = "https://api.deepseek.com/v1"
        default_model = "deepseek-chat"
    elif api_provider == "智谱 AI":
        base_url = "https://open.bigmodel.cn/api/paas/v4/"
        default_model = "glm-4-flash"
    else:
        base_url = st.text_input("自定义 Base URL")
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
    
    if st.session_state.conversations:
        conv_title = st.selectbox("选择历史对话", list(st.session_state.conversations.keys()))
        if st.button("切换到此对话"):
            st.session_state.current_conv_id = st.session_state.conversations[conv_title]
            st.session_state.current_conv_title = conv_title
            msgs = supabase.table("messages").select("*").eq("conversation_id", st.session_state.current_conv_id).order("created_at").execute()
            st.session_state.messages = [{"role": m["role"], "content": m["content"]} for m in msgs.data]
            st.rerun()
    
    new_conv_name = st.text_input("输入新窗口名称")
    if st.button("➕ 新建对话窗口"):
        if new_conv_name and new_conv_name not in st.session_state.conversations:
            res = supabase.table("conversations").insert({"user_id": st.session_state.user_id, "title": new_conv_name}).execute()
            new_id = res.data[0]['id']
            st.session_state.conversations[new_conv_name] = new_id
            st.session_state.current_conv_id = new_id
            st.session_state.current_conv_title = new_conv_name
            st.session_state.messages = []
            st.rerun()
        elif new_conv_name in st.session_state.conversations:
            st.warning("对话名称已存在")
            
    st.divider()
    st.subheader("📝 上传设定")
    uploaded_file = st.file_uploader("上传角色设定文档", type=["docx", "txt"])
    if uploaded_file is not None:
        if st.button("🚀 载入设定并开始游戏"):
            if uploaded_file.name.endswith(".docx"):
                doc = docx.Document(io.BytesIO(uploaded_file.getvalue()))
                doc_text = "\n".join([para.text for para in doc.paragraphs])
            else:
                doc_text = uploaded_file.getvalue().decode("utf-8")
            system_prompt = f"你是一个沉浸式互动小说引擎...\n【设定文档】：\n{doc_text}\n【排版格式】：动作直接写，说话用引号，禁止写玩家动作。"
            if "current_conv_id" in st.session_state:
                # 存系统提示到消息表
                supabase.table("messages").insert({"conversation_id": st.session_state.current_conv_id, "role": "system", "content": system_prompt}).execute()
                st.session_state.messages = [{"role": "system", "content": system_prompt}]
                st.success("✅ 设定已写入云端，游戏开始！")
            else:
                st.warning("请先新建一个对话窗口！")

# --- 主界面渲染 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    if message["role"] != "system":
        avatar_img = st.session_state.user_avatar if message["role"] == "user" else st.session_state.ai_avatar
        if message["role"] == "assistant":
            with st.chat_message("assistant", avatar=avatar_img):
                st.markdown(message["content"])
        else:
            with st.chat_message("user", avatar=avatar_img):
                st.markdown(message["content"])

# --- 底部输入框逻辑 ---
if prompt := st.chat_input("输入你的行动或对白..."):
    if not user_api_key:
        st.warning("⚠️ 请先在左侧栏输入你的 API Key！")
    elif "current_conv_id" not in st.session_state:
        st.warning("⚠️ 请先在左侧新建或选择一个对话窗口！")
    else:
        # 1. 存入数据库
        supabase.table("messages").insert({
            "conversation_id": st.session_state.current_conv_id,
            "role": "user",
            "content": prompt
        }).execute()
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=st.session_state.user_avatar):
            st.markdown(prompt)
        
        client = OpenAI(api_key=user_api_key, base_url=base_url)
        with st.chat_message("assistant", avatar=st.session_state.ai_avatar):
            message_placeholder = st.empty()
            full_response = ""
            try:
                recent = st.session_state.messages[:1] + st.session_state.messages[-6:]
                response = client.chat.completions.create(model=model_name, messages=recent, stream=True)
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                        message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
                # 2. AI回复也存入数据库
                supabase.table("messages").insert({
                    "conversation_id": st.session_state.current_conv_id,
                    "role": "assistant",
                    "content": full_response
                }).execute()
            except Exception as e:
                st.error(f"❌ 模型调用失败：{e}")
