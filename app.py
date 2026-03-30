import base64
import io
import json
from copy import deepcopy
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw
from streamlit.components.v1 import html as components_html
from streamlit_image_coordinates import streamlit_image_coordinates

st.set_page_config(page_title="마트 전단지 블록 편집 / 시연", layout="wide")

PAGES = [
    {"name": "page1", "file": "data/page1.jpg"},
    {"name": "page2", "file": "data/page2.jpg"},
    {"name": "page3", "file": "data/page3.jpg"},
]

BLOCKS_FILE = Path("data/blocks.json")

# S23+ 세로 화면 기준으로 잡은 표시 박스 느낌
DISPLAY_MAX_W = 410
DISPLAY_MAX_H = 700

# 팝업 기본 배율 단계
ZOOM_LEVELS = [0.75, 1.0, 1.25, 1.5, 2.0, 3.0]


@st.cache_data
def load_default_blocks() -> dict:
    base = {page["name"]: [] for page in PAGES}
    if BLOCKS_FILE.exists():
        try:
            loaded = json.loads(BLOCKS_FILE.read_text(encoding="utf-8"))
            for page in base:
                if page in loaded and isinstance(loaded[page], list):
                    base[page] = loaded[page]
        except Exception:
            pass
    return base


@st.cache_data
def load_image_bytes(image_path: str) -> bytes:
    return Path(image_path).read_bytes()


@st.cache_data
def load_image_size(image_bytes: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(image_bytes)) as im:
        return im.size


def fit_size(orig_w: int, orig_h: int, max_w: int, max_h: int) -> tuple[int, int, float]:
    scale = min(max_w / orig_w, max_h / orig_h)
    scale = min(scale, 1.0)
    new_w = max(1, int(orig_w * scale))
    new_h = max(1, int(orig_h * scale))
    return new_w, new_h, scale


@st.cache_data
def render_display_image(image_bytes: bytes, blocks_json: str, max_w: int, max_h: int, line_width: int = 4) -> bytes:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    orig_w, orig_h = image.size
    disp_w, disp_h, scale = fit_size(orig_w, orig_h, max_w, max_h)

    if scale < 1.0:
        image = image.resize((disp_w, disp_h), Image.LANCZOS)

    draw = ImageDraw.Draw(image)
    blocks = json.loads(blocks_json)

    for block in blocks:
        x = int(block["x"] * scale)
        y = int(block["y"] * scale)
        w = max(1, int(block["w"] * scale))
        h = max(1, int(block["h"] * scale))

        draw.rectangle(
            [(x, y), (x + w, y + h)],
            outline=(255, 0, 0),
            width=line_width,
        )

    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


@st.cache_data
def crop_block_bytes(image_bytes: bytes, block_json: str, pad: int = 24) -> bytes:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    block = json.loads(block_json)

    x, y, w, h = block["x"], block["y"], block["w"], block["h"]

    left = max(0, x - pad)
    top = max(0, y - pad)
    right = min(image.width, x + w + pad)
    bottom = min(image.height, y + h + pad)

    cropped = image.crop((left, top, right, bottom))

    buf = io.BytesIO()
    cropped.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def bytes_to_data_uri(image_bytes: bytes, mime: str = "image/jpeg") -> str:
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


if "page_idx" not in st.session_state:
    st.session_state.page_idx = 0

if "blocks" not in st.session_state:
    st.session_state.blocks = deepcopy(load_default_blocks())

# 최초 실행은 시연 모드
if "editor_mode" not in st.session_state:
    st.session_state.editor_mode = False

if "is_adding" not in st.session_state:
    st.session_state.is_adding = False

if "first_point" not in st.session_state:
    st.session_state.first_point = None

if "selected_block" not in st.session_state:
    st.session_state.selected_block = None

if "zoom_idx" not in st.session_state:
    st.session_state.zoom_idx = 1  # 1.0


def reset_adding_state():
    st.session_state.is_adding = False
    st.session_state.first_point = None


def go_prev():
    if st.session_state.page_idx > 0:
        st.session_state.page_idx -= 1
        reset_adding_state()
        st.session_state.selected_block = None


def go_next():
    if st.session_state.page_idx < len(PAGES) - 1:
        st.session_state.page_idx += 1
        reset_adding_state()
        st.session_state.selected_block = None


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


def get_json_text():
    return json.dumps(st.session_state.blocks, ensure_ascii=False, indent=2)


def find_block_by_point(blocks: list[dict], x: int, y: int):
    for block in reversed(blocks):
        bx, by, bw, bh = block["x"], block["y"], block["w"], block["h"]
        if bx <= x <= bx + bw and by <= y <= by + bh:
            return block
    return None


@st.dialog(" ", width="large")
def show_block_dialog():
    sel = st.session_state.selected_block
    if not sel:
        return

    page_name = sel["page_name"]
    block_id = sel["block_id"]

    page = next((p for p in PAGES if p["name"] == page_name), None)
    block = next((b for b in st.session_state.blocks[page_name] if b["id"] == block_id), None)

    if page is None or block is None:
        st.warning("블록 정보를 찾지 못했습니다.")
        return

    image_bytes = load_image_bytes(page["file"])
    cropped_bytes = crop_block_bytes(image_bytes, json.dumps(block, ensure_ascii=False), pad=24)
    data_uri = bytes_to_data_uri(cropped_bytes)

    z1, z2, z3, z4 = st.columns([1, 1, 1, 2])
    with z1:
        if st.button("－", width="stretch", key="zoom_out"):
            st.session_state.zoom_idx = max(0, st.session_state.zoom_idx - 1)
            st.rerun()
    with z2:
        if st.button("＋", width="stretch", key="zoom_in"):
            st.session_state.zoom_idx = min(len(ZOOM_LEVELS) - 1, st.session_state.zoom_idx + 1)
            st.rerun()
    with z3:
        if st.button("기본", width="stretch", key="zoom_reset"):
            st.session_state.zoom_idx = 1
            st.rerun()
    with z4:
        if st.button("닫기", width="stretch", key="close_dialog"):
            st.session_state.selected_block = None
            st.session_state.zoom_idx = 1
            st.rerun()

    zoom = ZOOM_LEVELS[st.session_state.zoom_idx]

    # 좌상단 기준(top-left) + 스크롤 박스
    # 처음엔 세로에 맞춰 보이게(height:100%), 확대하면 그 비율대로 커짐
    popup_html = f"""
    <div style="
        height: 44vh;
        min-height: 300px;
        max-height: 420px;
        overflow: auto;
        border: 1px solid #ddd;
        border-radius: 10px;
        background: #ffffff;
        padding: 0;
    ">
        <div style="
            height: 100%;
            width: max-content;
            min-width: 100%;
        ">
            <img
                src="{data_uri}"
                style="
                    height: calc(100% * {zoom});
                    width: auto;
                    max-width: none;
                    display: block;
                    transform-origin: top left;
                "
            />
        </div>
    </div>
    """
    components_html(popup_html, height=430, scrolling=False)


current_page = get_current_page()
page_name = current_page["name"]
image_path = Path(current_page["file"])

st.title("마트 전단지 블록 편집 / 시연")

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
        f"<div style='text-align:center; font-size:22px; font-weight:700;'>{page_name}</div>",
        unsafe_allow_html=True,
    )

with top3:
    st.button(
        "다음 페이지 ▶",
        on_click=go_next,
        width="stretch",
        disabled=(st.session_state.page_idx == len(PAGES) - 1),
    )

mode1, mode2, mode3 = st.columns([1, 1, 3])

with mode1:
    st.toggle("편집 모드", key="editor_mode")

with mode2:
    if st.button("기본값 재로드", width="stretch"):
        st.session_state.page_idx = 0
        st.session_state.blocks = deepcopy(load_default_blocks())
        st.session_state.editor_mode = False
        reset_adding_state()
        st.session_state.selected_block = None
        st.session_state.zoom_idx = 1
        st.rerun()

with mode3:
    if st.session_state.editor_mode:
        st.info("편집 모드")
    else:
        st.info("시연 모드")

if not image_path.exists():
    st.error(f"이미지 파일을 찾을 수 없습니다: {image_path}")
    st.stop()


@st.fragment
def interactive_panel():
    page = get_current_page()
    page_name_local = page["name"]
    blocks_for_page = st.session_state.blocks[page_name_local]

    image_bytes = load_image_bytes(page["file"])
    orig_w, orig_h = load_image_size(image_bytes)
    disp_w, disp_h, scale = fit_size(orig_w, orig_h, DISPLAY_MAX_W, DISPLAY_MAX_H)

    display_bytes = render_display_image(
        image_bytes,
        json.dumps(blocks_for_page, ensure_ascii=False, sort_keys=True),
        DISPLAY_MAX_W,
        DISPLAY_MAX_H,
        line_width=4,
    )
    display_image = Image.open(io.BytesIO(display_bytes))

    if st.session_state.editor_mode:
        c1, c2, c3, c4 = st.columns([1, 1, 1, 2])

        with c1:
            if st.button("추가 시작", width="stretch", key=f"add_{page_name_local}"):
                st.session_state.is_adding = True
                st.session_state.first_point = None
                st.session_state.selected_block = None

        with c2:
            if st.button("마지막 삭제", width="stretch", key=f"del_{page_name_local}"):
                remove_last_block(page_name_local)
                reset_adding_state()
                st.rerun()

        with c3:
            if st.button("추가 취소", width="stretch", key=f"cancel_{page_name_local}"):
                reset_adding_state()
                st.rerun()

        with c4:
            st.write(f"블록 수: **{len(blocks_for_page)}**")

        if st.session_state.is_adding and st.session_state.first_point is None:
            st.info("좌상단 클릭")
        elif st.session_state.is_adding and st.session_state.first_point is not None:
            st.info("우하단 클릭")

        clicked = streamlit_image_coordinates(
            display_image,
            key=f"edit_{page_name_local}_{len(blocks_for_page)}_{st.session_state.is_adding}_{st.session_state.first_point}",
        )

        if clicked and st.session_state.is_adding:
            # 표시 이미지 좌표 -> 원본 좌표 역변환
            x = int(round(clicked["x"] / scale))
            y = int(round(clicked["y"] / scale))

            x = min(max(x, 0), orig_w)
            y = min(max(y, 0), orig_h)

            if st.session_state.first_point is None:
                st.session_state.first_point = {"x": x, "y": y}
                st.rerun()
            else:
                x1 = st.session_state.first_point["x"]
                y1 = st.session_state.first_point["y"]
                add_block(page_name_local, x1, y1, x, y)
                reset_adding_state()
                st.rerun()

    else:
        clicked = streamlit_image_coordinates(
            display_image,
            key=f"demo_{page_name_local}_{len(blocks_for_page)}",
        )

        if clicked:
            x = int(round(clicked["x"] / scale))
            y = int(round(clicked["y"] / scale))

            x = min(max(x, 0), orig_w)
            y = min(max(y, 0), orig_h)

            matched = find_block_by_point(blocks_for_page, x, y)
            if matched is not None:
                st.session_state.selected_block = {
                    "page_name": page_name_local,
                    "block_id": matched["id"],
                }
                st.session_state.zoom_idx = 1
                show_block_dialog()

    # 아래 미리보기/데이터 출력 제거
    st.download_button(
        "blocks.json 다운로드",
        data=get_json_text(),
        file_name="blocks.json",
        mime="application/json",
        width="stretch",
    )


interactive_panel()

if st.session_state.selected_block is not None and not st.session_state.editor_mode:
    show_block_dialog()
