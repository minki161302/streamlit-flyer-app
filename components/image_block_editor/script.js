const Streamlit = window.Streamlit
const RenderEvent = Streamlit.RENDER_EVENT

function draw(args) {
  const imageSrc = args.image_src
  const imageWidth = args.image_width
  const imageHeight = args.image_height
  const blocks = args.blocks || []
  const editorMode = !!args.editor_mode
  const adding = !!args.adding
  const firstPoint = args.first_point

  const img = document.getElementById("mainImage")
  const svg = document.getElementById("overlay")
  const stage = document.getElementById("stage")
  const hint = document.getElementById("hint")

  img.src = imageSrc
  svg.setAttribute("viewBox", `0 0 ${imageWidth} ${imageHeight}`)
  svg.innerHTML = ""

  hint.textContent = editorMode
    ? (adding
        ? (firstPoint ? "우하단 점 클릭" : "좌상단 점 클릭")
        : "블록 설정 모드")
    : "보기 모드"

  blocks.forEach((block) => {
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect")
    rect.setAttribute("x", block.x)
    rect.setAttribute("y", block.y)
    rect.setAttribute("width", block.w)
    rect.setAttribute("height", block.h)
    rect.setAttribute("fill", "rgba(255,0,0,0.08)")
    rect.setAttribute("stroke", "red")
    rect.setAttribute("stroke-width", "4")
    svg.appendChild(rect)

    const textBg = document.createElementNS("http://www.w3.org/2000/svg", "rect")
    textBg.setAttribute("x", block.x + 6)
    textBg.setAttribute("y", Math.max(0, block.y - 26))
    textBg.setAttribute("width", 42)
    textBg.setAttribute("height", 20)
    textBg.setAttribute("fill", "white")
    svg.appendChild(textBg)

    const text = document.createElementNS("http://www.w3.org/2000/svg", "text")
    text.setAttribute("x", block.x + 10)
    text.setAttribute("y", Math.max(14, block.y - 10))
    text.setAttribute("fill", "red")
    text.setAttribute("font-size", "14")
    text.setAttribute("font-weight", "700")
    text.textContent = block.id
    svg.appendChild(text)
  })

  if (firstPoint) {
    const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle")
    dot.setAttribute("cx", firstPoint.x)
    dot.setAttribute("cy", firstPoint.y)
    dot.setAttribute("r", "8")
    dot.setAttribute("fill", "blue")
    svg.appendChild(dot)
  }

  svg.onclick = function (e) {
    const rect = svg.getBoundingClientRect()
    const scaleX = imageWidth / rect.width
    const scaleY = imageHeight / rect.height

    const x = Math.round((e.clientX - rect.left) * scaleX)
    const y = Math.round((e.clientY - rect.top) * scaleY)

    Streamlit.setComponentValue({
      type: "point",
      x: x,
      y: y,
    })
  }

  // 이미지 로드 후 높이 재계산
  const updateHeight = () => {
    Streamlit.setFrameHeight(stage.offsetHeight + 32)
  }

  if (img.complete) {
    updateHeight()
  } else {
    img.onload = updateHeight
  }
}

function onRender(event) {
  const args = event.detail.args
  draw(args)
}

Streamlit.events.addEventListener(RenderEvent, onRender)
Streamlit.setComponentReady()
Streamlit.setFrameHeight(300)
