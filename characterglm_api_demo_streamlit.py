"""
一个简单的demo，调用CharacterGLM实现角色扮演，调用CogView生成图片，调用ChatGLM生成CogView所需的prompt。

依赖：
pyjwt
requests
streamlit
zhipuai
python-dotenv

运行方式：
```bash
streamlit run characterglm_api_demo_streamlit.py
"""
from data_types import TextMsg, ImageMsg, filter_text_msg
from api import generate_chat_scene_prompt, generate_role_appearance, get_characterglm_response, generate_cogview_image
import api
import os
import itertools
from typing import Iterator, Optional

import streamlit as st
from dotenv import load_dotenv
# 通过.env文件设置环境变量
# reference: https://github.com/theskumar/python-dotenv
load_dotenv()


st.set_page_config(page_title="CharacterGLM API Demo", page_icon="🤖", layout="wide")
debug = os.getenv("DEBUG", "").lower() in ("1", "yes", "y", "true", "t", "on")


def update_api_key(key: Optional[str] = None):
    if debug:
        print(f'update_api_key. st.session_state["API_KEY"] = {st.session_state["API_KEY"]}, key = {key}')
    key = key or st.session_state["API_KEY"]
    if key:
        api.API_KEY = key


# 设置API KEY
api_key = st.sidebar.text_input("API_KEY", value=os.getenv("ZHIPUAI_API_KEY", ""), key="API_KEY", type="password", on_change=update_api_key)
update_api_key(api_key)


# 初始化
if "history" not in st.session_state:
    st.session_state["history"] = []
if "meta" not in st.session_state:
    st.session_state["meta"] = {
        "user_info": "",
        "bot_info": "",
        "bot_name": "",
        "user_name": ""
    }


def init_session():
    st.session_state["history"] = []


# 4个输入框，设置meta的4个字段
meta_labels = {
    "bot_name": "角色名",
    "user_name": "用户名",
    "bot_info": "角色人设",
    "user_info": "用户人设"
}

# 2x2 layout
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        st.text_input(label="角色名", key="bot_name", on_change=lambda: st.session_state["meta"].update(bot_name=st.session_state["bot_name"]), help="模型所扮演的角色的名字，不可以为空")
        st.text_area(label="角色人设", key="bot_info", on_change=lambda: st.session_state["meta"].update(bot_info=st.session_state["bot_info"]), help="角色的详细人设信息，不可以为空")

    with col2:
        st.text_input(label="用户名", value="用户", key="user_name", on_change=lambda: st.session_state["meta"].update(user_name=st.session_state["user_name"]), help="用户的名字，默认为用户")
        st.text_area(label="用户人设", value="", key="user_info", on_change=lambda: st.session_state["meta"].update(user_info=st.session_state["user_info"]), help="用户的详细人设信息，可以为空")


def verify_meta() -> bool:
    # 检查`角色名`和`角色人设`是否空，若为空，则弹出提醒
    if st.session_state["meta"]["bot_name"] == "" or st.session_state["meta"]["bot_info"] == "":
        st.error("角色名和角色人设不能为空")
        return False
    else:
        return True


def draw_new_image():
    """生成一张图片，并展示在页面上"""
    if not verify_meta():
        return
    text_messages = filter_text_msg(st.session_state["history"])
    if text_messages:
        # 若有对话历史，则结合角色人设和对话历史生成图片
        image_prompt = "".join(
            generate_chat_scene_prompt(
                text_messages[-10:],
                meta=st.session_state["meta"]
            )
        )
    else:
        # 若没有对话历史，则根据角色人设生成图片
        image_prompt = "".join(generate_role_appearance(st.session_state["meta"]["bot_info"]))

    if not image_prompt:
        st.error("调用chatglm生成Cogview prompt出错")
        return

    # TODO: 加上风格选项
    image_prompt = '二次元风格。' + image_prompt.strip()

    print(f"image_prompt = {image_prompt}")
    n_retry = 3
    st.markdown("正在生成图片，请稍等...")
    for i in range(n_retry):
        try:
            img_url = generate_cogview_image(image_prompt)
        except Exception as e:
            if i < n_retry - 1:
                st.error("遇到了一点小问题，重试中...")
            else:
                st.error("又失败啦，点击【生成图片】按钮可再次重试")
                return
        else:
            break
    img_msg = ImageMsg({"role": "image", "image": img_url, "caption": image_prompt})
    # 若history的末尾有图片消息，则替换它，（重新生成）
    # 否则，append（新增）
    while st.session_state["history"] and st.session_state["history"][-1]["role"] == "image":
        st.session_state["history"].pop()
    st.session_state["history"].append(img_msg)
    st.rerun()


button_labels = {
    "clear_meta": "清空人设",
    "clear_history": "清空对话历史",
    "gen_picture": "生成图片",
    "start_dialogue": "开始对话",
    "save_dialogue": "保存对话记录"
}
if debug:
    button_labels.update({
        "show_api_key": "查看API_KEY",
        "show_meta": "查看meta",
        "show_history": "查看历史"
    })


def load_character_settings():
    """从markdown文件加载角色设定"""
    try:
        with open('character_setting.md', 'r', encoding='utf-8') as f:
            bot_info = f.read()
        with open('user_setting.md', 'r', encoding='utf-8') as f:
            user_info = f.read()
        return bot_info, user_info
    except Exception as e:
        st.error(f"读取角色设定文件失败: {str(e)}")
        return None, None


def save_dialogue_history():
    """保存对话记录到文件"""
    try:
        with open('dialogue_history.txt', 'w', encoding='utf-8') as f:
            for msg in st.session_state["history"]:
                if msg["role"] in ["user", "assistant"]:
                    speaker = "唐僧" if msg["role"] == "user" else "孙悟空"
                    f.write(f"{speaker}: {msg['content']}\n")
        st.success("对话记录已保存到 dialogue_history.txt")
    except Exception as e:
        st.error(f"保存对话记录失败: {str(e)}")


# 在同一行排列按钮
with st.container():
    n_button = len(button_labels)
    cols = st.columns(n_button)
    button_key_to_col = dict(zip(button_labels.keys(), cols))

    with button_key_to_col["clear_meta"]:
        clear_meta = st.button(button_labels["clear_meta"], key="clear_meta")
        if clear_meta:
            st.session_state["meta"] = {
                "user_info": "",
                "bot_info": "",
                "bot_name": "",
                "user_name": ""
            }
            st.rerun()

    with button_key_to_col["clear_history"]:
        clear_history = st.button(button_labels["clear_history"], key="clear_history")
        if clear_history:
            init_session()
            st.rerun()

    with button_key_to_col["gen_picture"]:
        gen_picture = st.button(button_labels["gen_picture"], key="gen_picture")

    if debug:
        with button_key_to_col["show_api_key"]:
            show_api_key = st.button(button_labels["show_api_key"], key="show_api_key")
            if show_api_key:
                print(f"API_KEY = {api.API_KEY}")

        with button_key_to_col["show_meta"]:
            show_meta = st.button(button_labels["show_meta"], key="show_meta")
            if show_meta:
                print(f"meta = {st.session_state['meta']}")

        with button_key_to_col["show_history"]:
            show_history = st.button(button_labels["show_history"], key="show_history")
            if show_history:
                print(f"history = {st.session_state['history']}")

    with button_key_to_col["start_dialogue"]:
        start_dialogue = st.button(button_labels["start_dialogue"])
        if start_dialogue:
            bot_info, user_info = load_character_settings()
            if bot_info and user_info:
                st.session_state["meta"].update({
                    "bot_name": "孙悟空",
                    "user_name": "唐僧",
                    "bot_info": bot_info,
                    "user_info": user_info
                })
                init_session()
                # 生成10轮对话
                for _ in range(10):
                    if len(st.session_state["history"]) == 0:
                        query = "悟空，我们又要经过一片妖怪出没的森林了，你要谨记佛祖教诲，不可轻易伤人。"
                    else:
                        response_stream = get_characterglm_response(
                            filter_text_msg(st.session_state["history"]),
                            meta=st.session_state["meta"]
                        )
                        query = "".join(response_stream)
                    st.session_state["history"].append(TextMsg({"role": "user", "content": query}))

                    response_stream = get_characterglm_response(
                        filter_text_msg(st.session_state["history"]),
                        meta=st.session_state["meta"]
                    )
                    bot_response = "".join(response_stream)
                    st.session_state["history"].append(TextMsg({"role": "assistant", "content": bot_response}))
                st.rerun()

    with button_key_to_col["save_dialogue"]:
        save_dialogue = st.button(button_labels["save_dialogue"])
        if save_dialogue:
            save_dialogue_history()


# 展示对话历史
for msg in st.session_state["history"]:
    if msg["role"] == "user":
        with st.chat_message(name="user", avatar="user"):
            st.markdown(msg["content"])
    elif msg["role"] == "assistant":
        with st.chat_message(name="assistant", avatar="assistant"):
            st.markdown(msg["content"])
    elif msg["role"] == "image":
        with st.chat_message(name="assistant", avatar="assistant"):
            st.image(msg["image"], caption=msg.get("caption", None))
    else:
        raise Exception("Invalid role")


if gen_picture:
    draw_new_image()


with st.chat_message(name="user", avatar="user"):
    input_placeholder = st.empty()
with st.chat_message(name="assistant", avatar="assistant"):
    message_placeholder = st.empty()


def output_stream_response(response_stream: Iterator[str], placeholder):
    content = ""
    for content in itertools.accumulate(response_stream):
        placeholder.markdown(content)
    return content


def start_chat():
    query = st.chat_input("开始对话吧")
    if not query:
        return
    else:
        if not verify_meta():
            return
        if not api.API_KEY:
            st.error("未设置API_KEY")

        input_placeholder.markdown(query)
        st.session_state["history"].append(TextMsg({"role": "user", "content": query}))

        response_stream = get_characterglm_response(filter_text_msg(st.session_state["history"]), meta=st.session_state["meta"])
        bot_response = output_stream_response(response_stream, message_placeholder)
        if not bot_response:
            message_placeholder.markdown("生成出错")
            st.session_state["history"].pop()
        else:
            st.session_state["history"].append(TextMsg({"role": "assistant", "content": bot_response}))


start_chat()
