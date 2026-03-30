import base64
import hashlib
import io
import json
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw
from streamlit.components.v1 import html as components_html
from streamlit_image_coordinates import streamlit_image_coordinates

st.set_page_config(page_title="마트 전단지 블록 편집 / 시연", layout="wide")

DATA_DIR = Path("data")
BLOCKS_FILE = DATA_DIR / "blocks.json"

DISPLAY_MAX_W = 350
DISPLAY_MAX_H = 620


# -----------------------------
# 페이지 목록: data 폴더의 모든 jpg를 파일명순 정렬
# -----------------------------
def discover_pages():
    jpg_files = sorted(DATA_DIR.glob("*.jpg"), key=lambda p: p.name)
    return [{"name": p.stem, "file": str(p)} for p in jpg_files]


PAGES = discover_pages()

if not PAGES:
    st.error("data 폴더에 jpg 파일이 없습니다.")
    st.stop()


# -----------------------------
# blocks.json 자동 반영
# -----------------------------
def get_blocks_file_signature() -> str:
    if not BLOCKS_FILE.exists():
        return "missing"
    return hashlib.md5(BLOCKS_FILE.read_bytes()).hexdigest()


def read_blocks_from_disk() -> dict:
    base = {page["name"]: [] for page in PAGES}

    if not BLOCKS_FILE.exists():
        return base

    try:
        loaded = json.loads(BLOCKS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return base

    for page_name in base:
        if page_name in loaded and isinstance(loaded[page_name], list):
            base[page_name] = loaded[page_name]

    return base


# -----------------------------
# 캐시 함수(안씀)
# -----------------------------
#@st.cache_data
def load_image_bytes(image_path: str) -> bytes:
    return Path(image_path).read_bytes()


#@st.cache_data
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
def render_display_image(
    image_bytes: bytes,
    blocks_json: str,
    max_w: int,
    max_h: int,
    line_width: int = 4,
) -> bytes:
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


# -----------------------------
# Session state
# -----------------------------
current_sig = get_blocks_file_signature()

if "page_idx" not in st.session_state:
    st.session_state.page_idx = 0

if "blocks_file_sig" not in st.session_state:
    st.session_state.blocks_file_sig = current_sig

if "blocks" not in st.session_state:
    st.session_state.blocks = read_blocks_from_disk()
    st.session_state.blocks_file_sig = current_sig
elif st.session_state.blocks_file_sig != current_sig:
    st.session_state.blocks = read_blocks_from_disk()
    st.session_state.blocks_file_sig = current_sig

if "editor_mode" not in st.session_state:
    st.session_state.editor_mode = False  # 최초 실행은 시연 모드

if "prev_editor_mode" not in st.session_state:
    st.session_state.prev_editor_mode = st.session_state.editor_mode

if "is_adding" not in st.session_state:
    st.session_state.is_adding = False

if "first_point" not in st.session_state:
    st.session_state.first_point = None

if "selected_block" not in st.session_state:
    st.session_state.selected_block = None

if "page_nonce" not in st.session_state:
    st.session_state.page_nonce = 0


# -----------------------------
# Helpers
# -----------------------------
def reset_adding_state():
    st.session_state.is_adding = False
    st.session_state.first_point = None


def clear_popup_state():
    st.session_state.selected_block = None


def remount_viewer():
    st.session_state.page_nonce += 1


def get_current_page():
    if st.session_state.page_idx >= len(PAGES):
        st.session_state.page_idx = len(PAGES) - 1
    return PAGES[st.session_state.page_idx]


def go_prev():
    if st.session_state.page_idx > 0:
        st.session_state.page_idx -= 1
        reset_adding_state()
        clear_popup_state()
        remount_viewer()


def go_next():
    if st.session_state.page_idx < len(PAGES) - 1:
        st.session_state.page_idx += 1
        reset_adding_state()
        clear_popup_state()
        remount_viewer()


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


# -----------------------------
# Dialog
# -----------------------------
@st.dialog(" ", width="large")
def show_block_dialog():
    sel = st.session_state.selected_block
    if not sel:
        return

    page_name = sel["page_name"]
    block_id = sel["block_id"]

    page = next((p for p in PAGES if p["name"] == page_name), None)
    block = next((b for b in st.session_state.blocks.get(page_name, []) if b["id"] == block_id), None)

    if page is None or block is None:
        return

    image_bytes = load_image_bytes(page["file"])
    cropped_bytes = crop_block_bytes(image_bytes, json.dumps(block, ensure_ascii=False), pad=24)
    data_uri = bytes_to_data_uri(cropped_bytes)

    popup_html = f"""
    <!doctype html>
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
      <style>
        html, body {{
          margin: 0;
          padding: 0;
          background: white;
          overflow: hidden;
        }}
        #viewer {{
          width: 100vw;
          height: 60vh;
          min-height: 260px;
          max-height: 340px;
          overflow: hidden;
          position: relative;
          background: white;
          touch-action: none;
        }}
        #img {{
          position: absolute;
          left: 0;
          top: 0;
          transform-origin: 0 0;
          user-select: none;
          -webkit-user-drag: none;
          -webkit-user-select: none;
          max-width: none;
          max-height: none;
          will-change: transform;
        }}
      </style>
    </head>
    <body>
      <div id="viewer">
        <img id="img" src="{data_uri}" />
      </div>

      <script>
        const viewer = document.getElementById("viewer");
        const img = document.getElementById("img");

        let scale = 1;
        let minScale = 1;
        let maxScale = 5;
        let tx = 0;
        let ty = 0;

        let pointers = new Map();
        let startDist = 0;
        let startScale = 1;
        let lastX = 0;
        let lastY = 0;
        let dragging = false;

        function clamp(val, min, max) {{
          return Math.max(min, Math.min(max, val));
        }}

        function getDistance(a, b) {{
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          return Math.sqrt(dx * dx + dy * dy);
        }}

        function applyTransform() {{
          img.style.transform = `translate(${{tx}}px, ${{ty}}px) scale(${{scale}})`;
        }}

        function fitToHeight() {{
          const vh = viewer.clientHeight;
          const naturalW = img.naturalWidth;
          const naturalH = img.naturalHeight;

          minScale = vh / naturalH;
          scale = minScale;

          const scaledW = naturalW * scale;
          tx = 0;
          ty = 0;

          if (scaledW < viewer.clientWidth) {{
            tx = (viewer.clientWidth - scaledW) / 2;
          }}

          applyTransform();
        }}

        function zoomAround(cx, cy, newScale) {{
          newScale = clamp(newScale, minScale, maxScale);
          const worldX = (cx - tx) / scale;
          const worldY = (cy - ty) / scale;

          scale = newScale;
          tx = cx - worldX * scale;
          ty = cy - worldY * scale;

          applyTransform();
        }}

        img.onload = () => {{
          fitToHeight();
        }};

        viewer.addEventListener("wheel", (e) => {{
          e.preventDefault();
          const factor = e.deltaY < 0 ? 1.1 : 0.9;
          const rect = viewer.getBoundingClientRect();
          zoomAround(e.clientX - rect.left, e.clientY - rect.top, scale * factor);
        }}, {{ passive: false }});

        viewer.addEventListener("pointerdown", (e) => {{
          viewer.setPointerCapture(e.pointerId);
          pointers.set(e.pointerId, {{ x: e.clientX, y: e.clientY }});

          if (pointers.size === 1) {{
            dragging = true;
            lastX = e.clientX;
            lastY = e.clientY;
          }} else if (pointers.size === 2) {{
            dragging = false;
            const pts = Array.from(pointers.values());
            startDist = getDistance(pts[0], pts[1]);
            startScale = scale;
          }}
        }});

        viewer.addEventListener("pointermove", (e) => {{
          if (!pointers.has(e.pointerId)) return;

          pointers.set(e.pointerId, {{ x: e.clientX, y: e.clientY }});

          if (pointers.size === 1 && dragging) {{
            const dx = e.clientX - lastX;
            const dy = e.clientY - lastY;
            tx += dx;
            ty += dy;
            lastX = e.clientX;
            lastY = e.clientY;
            applyTransform();
          }} else if (pointers.size === 2) {{
            const pts = Array.from(pointers.values());
            const dist = getDistance(pts[0], pts[1]);
            if (startDist > 0) {{
              const rect = viewer.getBoundingClientRect();
              const cx = ((pts[0].x + pts[1].x) / 2) - rect.left;
              const cy = ((pts[0].y + pts[1].y) / 2) - rect.top;
              zoomAround(cx, cy, startScale * (dist / startDist));
            }}
          }}
        }});

        function endPointer(e) {{
          pointers.delete(e.pointerId);
          if (pointers.size < 2) startDist = 0;
          if (pointers.size === 0) dragging = false;
        }}

        viewer.addEventListener("pointerup", endPointer);
        viewer.addEventListener("pointercancel", endPointer);
        viewer.addEventListener("pointerleave", endPointer);

        window.addEventListener("resize", fitToHeight);
      </script>
    </body>
    </html>
    """

    components_html(popup_html, height=360, scrolling=False)


# -----------------------------
# UI
# -----------------------------
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

mode1, mode2 = st.columns([1, 3])

with mode1:
    st.toggle("편집 모드", key="editor_mode")

with mode2:
    st.info("편집 모드" if st.session_state.editor_mode else "시연 모드")
# 토글 변화시에만 remount
if st.session_state.editor_mode != st.session_state.prev_editor_mode:
    st.session_state.prev_editor_mode = st.session_state.editor_mode
    reset_adding_state()
    clear_popup_state()
    remount_viewer()
    st.rerun()

if not image_path.exists():
    st.error(f"이미지 파일을 찾을 수 없습니다: {image_path}")
    st.stop()


# -----------------------------
# 메인 뷰어
# -----------------------------
page_name_local = current_page["name"]
blocks_for_page = st.session_state.blocks.get(page_name_local, [])

image_bytes = load_image_bytes(current_page["file"])
orig_w, orig_h = load_image_size(image_bytes)
_, _, scale = fit_size(orig_w, orig_h, DISPLAY_MAX_W, DISPLAY_MAX_H)

display_bytes = render_display_image(
    image_bytes,
    json.dumps(blocks_for_page, ensure_ascii=False, sort_keys=True),
    DISPLAY_MAX_W,
    DISPLAY_MAX_H,
    line_width=4,
)
display_image = Image.open(io.BytesIO(display_bytes))

viewer_key = (
    f"viewer_"
    f"{page_name_local}_"
    f"{st.session_state.page_nonce}_"
    f"{'edit' if st.session_state.editor_mode else 'demo'}_"
    f"{len(blocks_for_page)}_"
    f"{st.session_state.is_adding}"
)

if st.session_state.editor_mode:
    c1, c2, c3, c4 = st.columns([1, 1, 1, 2])

    with c1:
        if st.button("추가 시작", width="stretch", key=f"add_{page_name_local}"):
            st.session_state.is_adding = True
            st.session_state.first_point = None
            clear_popup_state()
            remount_viewer()
            st.rerun()

    with c2:
        if st.button("마지막 삭제", width="stretch", key=f"del_{page_name_local}"):
            remove_last_block(page_name_local)
            reset_adding_state()
            remount_viewer()
            st.rerun()

    with c3:
        if st.button("추가 취소", width="stretch", key=f"cancel_{page_name_local}"):
            reset_adding_state()
            remount_viewer()
            st.rerun()

    with c4:
        st.write(f"블록 수: **{len(blocks_for_page)}**")

    if st.session_state.is_adding and st.session_state.first_point is None:
        st.info("좌상단 클릭")
    elif st.session_state.is_adding and st.session_state.first_point is not None:
        st.info("우하단 클릭")

    clicked = streamlit_image_coordinates(display_image, key=viewer_key)

    if clicked and st.session_state.is_adding:
        x = int(round(clicked["x"] / scale))
        y = int(round(clicked["y"] / scale))

        x = min(max(x, 0), orig_w)
        y = min(max(y, 0), orig_h)

        if st.session_state.first_point is None:
            st.session_state.first_point = {"x": x, "y": y}
            remount_viewer()
            st.rerun()
        else:
            x1 = st.session_state.first_point["x"]
            y1 = st.session_state.first_point["y"]
            add_block(page_name_local, x1, y1, x, y)
            reset_adding_state()
            remount_viewer()
            st.rerun()

else:
    clicked = streamlit_image_coordinates(display_image, key=viewer_key)

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
            show_block_dialog()

st.download_button(
    "blocks.json 다운로드",
    data=get_json_text(),
    file_name="blocks.json",
    mime="application/json",
    width="stretch",
)
