from flask import Flask, render_template, request, jsonify
import json
import os
from openai import OpenAI

app = Flask(__name__)

# =========================
# 🔑 API KEY (安全版 - 智谱 GLM)
# =========================
# 从 Vercel 后台的环境变量中读取 Key，不要明文写在代码里！
# 注意：在 Vercel 环境变量里，Key 要写 GLM_API_KEY，Value 写你的智谱 API Key
GLM_API_KEY = os.environ.get("GLM_API_KEY", "")
client = OpenAI(
    api_key=GLM_API_KEY,
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)

# ⚠️【新增的关键修复】明确告诉 Vercel 顶层变量叫 app
app = app 
# =========================
# 🧠 洛天依人设
# =========================
SYSTEM_PROMPT = "你是一个正常聊天的少女，说话简短自然。"
# =========================
# 💾 记忆系统（Vercel 防崩溃修复版）
# =========================
MEMORY_FILE = "memory.json"

def load_memory():
    try:
        if not os.path.exists(MEMORY_FILE):
            return {
                "name": None,
                "history": [],
                "emotion_memory": {"affection": 0}
            }

        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 🧠 兼容旧版本
        if "history" not in data:
            data["history"] = []

        if "name" not in data:
            data["name"] = None

        # 🧠 情绪记忆补丁
        if "emotion_memory" not in data:
            data["emotion_memory"] = {"affection": 0}

        return data
    except Exception:
        # 如果读取失败（比如Vercel只读环境），返回一个空的默认记忆，防止程序崩溃
        return {
            "name": None,
            "history": [],
            "emotion_memory": {"affection": 0}
        }


def save_memory(memory):
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
    except Exception:
        # 如果写入失败（比如Vercel不能写文件），直接忽略，防止报 500 错误
        pass


# 初始化记忆
memory = load_memory()

# =========================
# 💙 情绪记忆系统（v3.6核心）
# =========================
def update_emotion(memory, user_text):

    emo = memory["emotion_memory"]

    positive_words = ["喜欢", "可爱", "谢谢", "厉害", "棒", "好听", "真好"]
    negative_words = ["讨厌", "烦", "走开", "无聊", "差劲"]

    # 正向
    if any(w in user_text for w in positive_words):
        emo["affection"] += 1

    # 负向
    if any(w in user_text for w in negative_words):
        emo["affection"] -= 2

    # 限制范围
    emo["affection"] = max(-10, min(10, emo["affection"]))

    return emo


# =========================
# 🧠 AI核心函数（v3.6记忆+情绪版）
# =========================
def ask_ai(user_text):

    global memory

    try:
        # =========================
        # 💙 情绪更新
        # =========================
        update_emotion(memory, user_text)
        affection = memory["emotion_memory"]["affection"]

        # =========================
        # 🧠 构造 messages
        # =========================
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT +
                           f"\n\n用户信息：{json.dumps(memory, ensure_ascii=False)}" +
                           f"\n情绪好感度：{affection}"
            }
        ]

        # 加入历史（最多10轮）
        history = memory.get("history", [])[-10:]

        for item in history:
            if len(item) == 2:
                messages.append({"role": "user", "content": item[0]})
                messages.append({"role": "assistant", "content": item[1]})

        # 当前输入
        messages.append({"role": "user", "content": user_text})

        # =========================
        # 🚀 调用 GLM
        # =========================
        response = client.chat.completions.create(
            model="glm-4.5-air",
            messages=messages,
            temperature=0.8
        )

        # =========================
        # 🧾 取回复
        # =========================
        reply = response.choices[0].message.content

        if not reply:
            return "嗯……我好像有点不知道怎么回答呢。"

        # =========================
        # 💾 写入记忆
        # =========================
        memory["history"].append([user_text, reply])
        memory["history"] = memory["history"][-20:]

        # 名字记忆（简单版）
        if "我叫" in user_text:
            memory["name"] = user_text.replace("我叫", "").strip()

        save_memory(memory)

        return reply

    except Exception as e:
        # ⚠️ 关键：真实错误输出（方便你调试）
        print("ERROR:", e)
        return f"系统错误：{str(e)}"

# =========================
# 🌐 页面
# =========================
@app.route("/")
def index():
    return render_template("index.html")


# =========================
# 💬 聊天接口
# =========================
@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message")
    reply = ask_ai(user_message)
    return jsonify({"reply": reply})


# =========================
# 🚀 启动（Vercel 必须删掉 app.run，但保留 `app` 变量即可）
# =========================