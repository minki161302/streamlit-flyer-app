import streamlit as st
from pathlib import Path
from PIL import Image, ImageDraw

st.set_page_config(
    page_title="마트 전단지 뷰어",
    layout="wide"
)

# -----------------------------
# 1) 페이지 파일 목록
# -----------------------------
PAGES = [
    {"name": "page1", "file": "data/page1.jpg"},
    {"name": "page2", "file": "data/page2.jpg"},
    {"name": "page3", "file": "data/page3.jpg"},
]

# -----------------------------
# 2) 블록 좌표 예시
#    x, y, w, h 는 원본 이미지 기준 픽셀
#    여기 숫자는 예시니까 네 이미지에 맞게 바꿔야 함
# -----------------------------
BLOCKS = {
    "page1": [
        {"id": "b1", "x": 120, "y": 180, "w": 500, "h": 380},
        {"id": "b2", "x": 700, "y": 180, "w": 480, "h": 380},
        {"id": "b3", "x": 120, "y": 620, "w": 1060, "h": 320},
    ],
    "page2": [
        {"id": "b1", "x": 100, "y": 150, "w": 420, "h": 360},
        {"id": "b2", "x": 560, "y": 150, "w": 420, "h": 360},
        {"id": "b3", "x": 1020, "y": 150, "w": 420, "h": 360},
    ],
    "page3": [
        {"id": "b1", "x": 140, "y": 200, "w": 540, "h": 420},
        {"id": "b2", "x": 720, "y": 200, "w": 540, "h": 420},
    ],
}

# -----------------------------
# 3) 상태 초기화
# -----------------------------
if "page_idx" not in st.session_state:
    st.session_state.page_idx = 0

if "show_blocks" not in st.session_state:
    st.session_state.show_blocks = True


def go_prev():
    if st.session_state.page_idx > 0:
        st.session_state.page_idx -= 1


def go_next():
    if st.session_state.page_idx < len(PAGES) - 1:
        st.session_state.page_idx += 1


def draw_blocks(image_path: str, blocks: list[dict], line_width: int = 6) -> Image.Image:
    """
    원본 이미지 위에 블록 테두리를 그려서 새 이미지 반환
    """
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)

    for block in blocks:
        x = block["x"]
        y = block["y"]
        w = block["w"]
        h = block["h"]

        # 빨간 테두리
        draw.rectangle(
            [(x, y), (x + w, y + h)],
            outline=(255, 0, 0),
            width=line_width
        )

        # 좌상단에 블록 id 표시
        label = block["id"]
        text_x = x + 10
        text_y = max(0, y - 28)

        # 가독성용 흰 배경
        draw.rectangle(
            [(text_x - 4, text_y - 4), (text_x + 60, text_y + 20)],
            fill=(255, 255, 255)
        )
        draw.text((text_x, text_y), label, fill=(255, 0, 0))

    return image


current_page = PAGES[st.session_state.page_idx]
page_name = current_page["name"]
image_path = Path(current_page["file"])

st.title("마트 전단지 뷰어")
st.caption(f"{st.session_state.page_idx + 1} / {len(PAGES)}")

top_left, top_mid, top_right = st.columns([1, 2, 1])

with top_left:
    st.button(
        "◀ 이전 페이지",
        on_click=go_prev,
        width="stretch",
        disabled=(st.session_state.page_idx == 0),
    )

with top_mid:
    st.markdown(
        f"<div style='text-align:center; font-size:22px; font-weight:700;'>{page_name}</div>",
        unsafe_allow_html=True
    )

with top_right:
    st.button(
        "다음 페이지 ▶",
        on_click=go_next,
        width="stretch",
        disabled=(st.session_state.page_idx == len(PAGES) - 1),
    )

st.divider()

tool_col1, tool_col2, tool_col3 = st.columns([1, 1, 3])

with tool_col1:
    st.toggle("블록 테두리 표시", key="show_blocks")

with tool_col2:
    st.write(f"블록 수: {len(BLOCKS.get(page_name, []))}")

if image_path.exists():
    if st.session_state.show_blocks:
        rendered = draw_blocks(str(image_path), BLOCKS.get(page_name, []))
        st.image(rendered, width="stretch")
    else:
        st.image(str(image_path), width="stretch")
else:
    st.error(f"이미지 파일을 찾을 수 없습니다: {image_path}")

st.divider()

bottom_left, bottom_mid, bottom_right = st.columns([1, 2, 1])

with bottom_left:
    st.button(
        "◀ 이전",
        key="bottom_prev",
        on_click=go_prev,
        width="stretch",
        disabled=(st.session_state.page_idx == 0),
    )

with bottom_mid:
    st.markdown(
        f"<div style='text-align:center;'>현재 페이지: <b>{page_name}</b></div>",
        unsafe_allow_html=True
    )

with bottom_right:
    st.button(
        "다음 ▶",
        key="bottom_next",
        on_click=go_next,
        width="stretch",
        disabled=(st.session_state.page_idx == len(PAGES) - 1),
    )

with st.expander("현재 페이지 블록 좌표 보기"):
    st.code(BLOCKS.get(page_name, []), language="python")
