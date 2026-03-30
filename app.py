import json
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw
from streamlit_image_coordinates import streamlit_image_coordinates

st.set_page_config(page_title="마트 전단지 블록 설정", layout="wide")

PAGES = [
    {"name": "page1", "file": "data/page1.jpg"},
    {"name": "page2", "file": "data/page2.jpg"},
    {"name": "page3", "file": "data/page3.jpg"},
]

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


def reset_adding_state():
    st.session_state.is_adding = False
    st.session_state.first_point = None


def go_prev():
    if st.session_state.page_idx > 0:
        st.session_state.page_idx -= 1
        reset_adding_state()


def go_next():
    if st.session_state.page_idx < len(PAGES) - 1:
        st.session_state.page_idx += 1
        reset_adding_state()


def get_current_page():
    return PAGES[st.session_state.page_idx]


def add_block(page_name: str, x1: int, y1: int, x2: int, y2: int):
    x = min(x1, x2)
    y = min(y1, y2)
    w = abs(x2 - x1)
    h = abs(y2 - y1)

    if w < 5 or h < 5:
        return

    blocks = st.session_state.blocks[page_name]
    next_id = len(blocks) + 1
    blocks.append({
        "id": f"b{next_id}",
        "x": int(x),
        "y": int(y),
        "w": int(w),
        "h": int(h),
    })


def remove_last_block(page_name: str):
    if st.session_state.blocks[page_name]:
        st.session_state.blocks[page_name].pop()


def draw_blocks_preview(image_path: str, blocks: list[dict], line_width: int = 6):
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)

    for block in blocks:
        x, y, w, h = block["x"], block["y"], block["w"], block["h"]
        draw.rectangle(
            [(x, y), (x + w, y + h)],
            outline=(255, 0, 0),
            width=line_width,
        )
        draw.rectangle(
            [(x + 6, max(0, y - 28)), (x + 58, max(0, y - 4))],
            fill=(255, 255, 255),
        )
        draw.text((x + 10, max(0, y - 26)), block["id"], fill=(255, 0, 0))

    return image


def get_json_text():
    return json.dumps(st.session_state.blocks, ensure_ascii=False, indent=2)


current_page = get_current_page()
page_name = current_page["name"]
image_path = Path(current_page["file"])

st.title("마트 전단지 블록 설정")
st.caption(f"{st.session_state.page_idx + 1} / {len(PAGES)}")

top1, top2, top3 = st.columns([1, 2, 1])

with top1:
    st.button(
        "◀ 이전 페이지",
        on_click=go_prev,
        use_container_width=True,
        disabled=(st.session_state.page_idx == 0),
    )

with top2:
    st.markdown(
        f"<div style='text-align:center; font-size:24px; font-weight:700;'>{page_name}</div>",
        unsafe_allow_html=True,
    )

with top3:
    st.button(
        "다음 페이지 ▶",
        on_click=go_next,
        use_container_width=True,
        disabled=(st.session_state.page_idx == len(PAGES) - 1),
    )

c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 2])

with c1:
    st.toggle("블록 설정 모드", key="editor_mode")

with c2:
    if st.button("추가 시작", use_container_width=True, disabled=not st.session_state.editor_mode):
        st.session_state.is_adding = True
        st.session_state.first_point = None

with c3:
    if st.button("마지막 삭제", use_container_width=True):
        remove_last_block(page_name)
        reset_adding_state()
        st.rerun()

with c4:
    if st.button("추가 취소", use_container_width=True):
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

if not image_path.exists():
    st.error(f"이미지 파일을 찾을 수 없습니다: {image_path}")
    st.stop()

blocks_for_page = st.session_state.blocks[page_name]
preview_image = draw_blocks_preview(str(image_path), blocks_for_page)

clicked = streamlit_image_coordinates(
    preview_image,
    key=f"imgcoords_{page_name}_{len(blocks_for_page)}_{st.session_state.is_adding}_{st.session_state.first_point}",
)

st.write("clicked:", clicked)

if clicked and st.session_state.editor_mode and st.session_state.is_adding:
    x = int(clicked["x"])
    y = int(clicked["y"])

    if st.session_state.first_point is None:
        st.session_state.first_point = {"x": x, "y": y}
        st.rerun()
    else:
        x1 = st.session_state.first_point["x"]
        y1 = st.session_state.first_point["y"]
        add_block(page_name, x1, y1, x, y)
        reset_adding_state()
        st.rerun()

st.divider()

left, right = st.columns([3, 2])

with left:
    st.subheader("현재 페이지 미리보기")
    st.image(preview_image, use_container_width=True)

with right:
    st.subheader("현재 페이지 블록 데이터")
    st.code(
        json.dumps(st.session_state.blocks[page_name], ensure_ascii=False, indent=2),
        language="json",
    )

st.download_button(
    "전체 blocks.json 다운로드",
    data=get_json_text(),
    file_name="blocks.json",
    mime="application/json",
    use_container_width=True,
)
