import json
import os
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw

st.set_page_config(page_title="마트 전단지 뷰어", layout="wide")

# -----------------------------
# 기본 설정
# -----------------------------
PAGES = [
    {"name": "page1", "file": "data/page1.jpg"},
    {"name": "page2", "file": "data/page2.jpg"},
    {"name": "page3", "file": "data/page3.jpg"},
]

COMPONENT_DIR = os.path.join(
    os.path.dirname(__file__),
    "components",
    "image_block_editor"
)

image_block_editor = components.declare_component(
    "image_block_editor",
    path=COMPONENT_DIR
)

# -----------------------------
# 세션 상태 초기화
# -----------------------------
if "page_idx" not in st.session_state:
    st.session_state.page_idx = 0

if "blocks" not in st.session_state:
    st.session_state.blocks = {
        "page1": [],
        "page2": [],
        "page3": [],
    }

if "editor_mode" not in st.session_state:
    st.session_state.editor_mode = False

if "is_adding" not in st.session_state:
    st.session_state.is_adding = False

if "first_point" not in st.session_state:
    st.session_state.first_point = None


# -----------------------------
# 유틸
# -----------------------------
def go_prev():
    if st.session_state.page_idx > 0:
        st.session_state.page_idx -= 1
        reset_adding_state()


def go_next():
    if st.session_state.page_idx < len(PAGES) - 1:
        st.session_state.page_idx += 1
        reset_adding_state()


def reset_adding_state():
    st.session_state.is_adding = False
    st.session_state.first_point = None


def get_current_page():
    return PAGES[st.session_state.page_idx]


def add_block(page_name: str, x1: int, y1: int, x2: int, y2: int):
    x = min(x1, x2)
    y = min(y1, y2)
    w = abs(x2 - x1)
    h = abs(y2 - y1)

    if w < 5 or h < 5:
        return

    existing = st.session_state.blocks[page_name]
    next_id = len(existing) + 1
    existing.append({
        "id": f"b{next_id}",
        "x": int(x),
        "y": int(y),
        "w": int(w),
        "h": int(h),
    })


def remove_last_block(page_name: str):
    if st.session_state.blocks[page_name]:
        st.session_state.blocks[page_name].pop()


def draw_blocks_preview(image_path: str, blocks: list[dict], line_width: int = 5):
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)

    for block in blocks:
        x, y, w, h = block["x"], block["y"], block["w"], block["h"]
        draw.rectangle(
            [(x, y), (x + w, y + h)],
            outline=(255, 0, 0),
            width=line_width
        )
        draw.rectangle(
            [(x + 6, max(0, y - 28)), (x + 58, max(0, y - 4))],
            fill=(255, 255, 255)
        )
        draw.text((x + 10, max(0, y - 26)), block["id"], fill=(255, 0, 0))

    return image


def get_json_text():
    return json.dumps(st.session_state.blocks, ensure_ascii=False, indent=2)


# -----------------------------
# 화면 상단
# -----------------------------
current_page = get_current_page()
page_name = current_page["name"]
image_path = Path(current_page["file"])

st.title("마트 전단지 블록 설정")

top1, top2, top3 = st.columns([1, 2, 1])

with top1:
    st.button(
        "◀ 이전 페이지",
        on_click=go_prev,
        width="stretch",
        disabled=(st.session_state.page_idx == 0),
    )

with top2:
    st.markdown(
        f"<div style='text-align:center; font-size:24px; font-weight:700;'>{page_name}</div>",
        unsafe_allow_html=True
    )

with top3:
    st.button(
        "다음 페이지 ▶",
        on_click=go_next,
        width="stretch",
        disabled=(st.session_state.page_idx == len(PAGES) - 1),
    )

st.caption(f"{st.session_state.page_idx + 1} / {len(PAGES)}")

# -----------------------------
# 컨트롤
# -----------------------------
c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 2])

with c1:
    st.toggle("블록 설정 모드", key="editor_mode")

with c2:
    if st.button("추가 시작", width="stretch", disabled=not st.session_state.editor_mode):
        st.session_state.is_adding = True
        st.session_state.first_point = None

with c3:
    if st.button("마지막 삭제", width="stretch"):
        remove_last_block(page_name)
        reset_adding_state()
        st.rerun()

with c4:
    if st.button("추가 취소", width="stretch"):
        reset_adding_state()
        st.rerun()

with c5:
    st.write(f"현재 블록 수: **{len(st.session_state.blocks[page_name])}**")

if st.session_state.editor_mode:
    if st.session_state.is_adding and st.session_state.first_point is None:
        st.info("좌상단 점을 클릭하세요.")
    elif st.session_state.is_adding and st.session_state.first_point is not None:
        st.info("우하단 점을 클릭하세요.")
    else:
        st.info("‘추가 시작’을 누르면 블록을 새로 만들 수 있습니다.")
else:
    st.info("블록 설정 모드를 켜면 추가 기능을 사용할 수 있습니다.")

st.divider()

# -----------------------------
# 이미지 표시 + 클릭 좌표 수신
# -----------------------------
if not image_path.exists():
    st.error(f"이미지 파일을 찾을 수 없습니다: {image_path}")
    st.stop()

blocks_for_page = st.session_state.blocks[page_name]
image = Image.open(image_path)
img_width, img_height = image.size

# 파일을 base64로 넘기지 않고, 정적 파일 경로를 그대로 사용
# 컴포넌트 쪽에서 상대경로 해석 문제를 피하려고 file URL 대신
# Streamlit이 직접 못 읽는 경우가 있으므로 여기서는 data URI로 넘김
import base64
with open(image_path, "rb") as f:
    encoded = base64.b64encode(f.read()).decode("utf-8")
image_src = f"data:image/{image_path.suffix.replace('.', '')};base64,{encoded}"

clicked = image_block_editor(
    image_src=image_src,
    image_width=img_width,
    image_height=img_height,
    blocks=blocks_for_page,
    editor_mode=st.session_state.editor_mode,
    adding=st.session_state.is_adding,
    first_point=st.session_state.first_point,
    key=f"editor_{page_name}"
)

# -----------------------------
# 클릭 처리
# -----------------------------
if clicked is not None and isinstance(clicked, dict):
    if clicked.get("type") == "point":
        x = int(clicked["x"])
        y = int(clicked["y"])

        if st.session_state.editor_mode and st.session_state.is_adding:
            if st.session_state.first_point is None:
                st.session_state.first_point = {"x": x, "y": y}
                st.rerun()
            else:
                x1 = st.session_state.first_point["x"]
                y1 = st.session_state.first_point["y"]
                add_block(page_name, x1, y1, x, y)
                reset_adding_state()
                st.rerun()
st.write("clicked:", clicked)
st.divider()

preview_col1, preview_col2 = st.columns([3, 2])

with preview_col1:
    st.subheader("미리보기")
    rendered = draw_blocks_preview(str(image_path), st.session_state.blocks[page_name])
    st.image(rendered, width="stretch")

with preview_col2:
    st.subheader("현재 페이지 블록 데이터")
    st.code(json.dumps(st.session_state.blocks[page_name], ensure_ascii=False, indent=2), language="json")

st.download_button(
    label="전체 blocks.json 다운로드",
    data=get_json_text(),
    file_name="blocks.json",
    mime="application/json",
    width="stretch"
)
