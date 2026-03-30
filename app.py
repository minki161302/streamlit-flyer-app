import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="마트 전단지 뷰어",
    layout="wide"
)

# 페이지 정보
PAGES = [
    {"name": "page1", "file": "data/page1.jpg"},
    {"name": "page2", "file": "data/page2.jpg"},
    {"name": "page3", "file": "data/page3.jpg"},
]

# 현재 페이지 상태
if "page_idx" not in st.session_state:
    st.session_state.page_idx = 0


def go_prev():
    if st.session_state.page_idx > 0:
        st.session_state.page_idx -= 1


def go_next():
    if st.session_state.page_idx < len(PAGES) - 1:
        st.session_state.page_idx += 1


current_page = PAGES[st.session_state.page_idx]
image_path = Path(current_page["file"])

st.title("마트 전단지 뷰어")
st.caption(f"{st.session_state.page_idx + 1} / {len(PAGES)}")

# 상단 이동 버튼
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    st.button(
        "◀ 이전 페이지",
        on_click=go_prev,
        use_container_width=True,
        disabled=(st.session_state.page_idx == 0),
    )

with col2:
    st.markdown(
        f"<div style='text-align:center; font-size:20px; font-weight:600;'>{current_page['name']}</div>",
        unsafe_allow_html=True
    )

with col3:
    st.button(
        "다음 페이지 ▶",
        on_click=go_next,
        use_container_width=True,
        disabled=(st.session_state.page_idx == len(PAGES) - 1),
    )

st.divider()

# 이미지 표시
if image_path.exists():
    st.image(str(image_path), use_container_width=True)
else:
    st.error(f"이미지 파일을 찾을 수 없습니다: {image_path}")

st.divider()

# 하단 이동 버튼도 하나 더
col4, col5, col6 = st.columns([1, 2, 1])

with col4:
    st.button(
        "◀ 이전",
        key="bottom_prev",
        on_click=go_prev,
        use_container_width=True,
        disabled=(st.session_state.page_idx == 0),
    )

with col5:
    st.markdown(
        f"<div style='text-align:center;'>현재 페이지: {current_page['name']}</div>",
        unsafe_allow_html=True
    )

with col6:
    st.button(
        "다음 ▶",
        key="bottom_next",
        on_click=go_next,
        use_container_width=True,
        disabled=(st.session_state.page_idx == len(PAGES) - 1),
    )