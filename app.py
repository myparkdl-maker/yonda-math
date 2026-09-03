import streamlit as st
import os
from google import genai
from PIL import Image
from docx import Document
import io
import socket
import qrcode

API_KEY = "AQ.Ab8RN6JeD7GDknfM9jFK3SNq7eMlc0iKMp8pEAk9NZLgw17wzA"
client = genai.Client(api_key=API_KEY)

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def get_sort_key(file):
    name = os.path.splitext(file.name)[0]
    try:
        return int(name) 
    except ValueError:
        return name 

def analyze_math_image(image):
    prompt = """
    이 이미지에 있는 수학 문제를 처음부터 끝까지 빠짐없이 분석해줘.
    결과를 워드 파일 표나 깔끔한 구조로 넣을 거니까, 반드시 아래의 양식을 엄격하게 지켜서 작성해.
    문제 하나 분석이 끝날 때마다 반드시 '====' 기호를 넣어서 구분해줘.
    
    [Q] (여기에 수학 문제 번호 및 원문 내용 요약)
    [CONCEPT] (여기에 이 문제를 풀기 위해 알아야 하는 핵심 개념이나 공식)
    [STEP] (여기에 아이가 이해하기 쉽도록 단계별로 풀어주는 풀이 과정, 예: 1단계 ~~)
    [TIP] (여기에 아빠가 다정하게 들려주는 조언이나 자주 하는 실수 방지 팁)
    ====
    """
    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=[image, prompt],
    )
    return response.text

def parse_math_blocks(analyzed_blocks_list):
    parsed_data = []
    for blocks in analyzed_blocks_list:
        for block in blocks.split('===='):
            if not block.strip():
                continue
            
            q_text, concept_text, step_text, tip_text = "", "", "", ""
            
            for line in block.strip().split('\n'):
                line = line.strip()
                if line.startswith('[Q]'): q_text = line.replace('[Q]', '').strip()
                elif line.startswith('[CONCEPT]'): concept_text = line.replace('[CONCEPT]', '').strip()
                elif line.startswith('[STEP]'): step_text += line.replace('[STEP]', '').strip() + "\n"
                elif line.startswith('[TIP]'): tip_text = line.replace('[TIP]', '').strip()
            
            if q_text:
                parsed_data.append({
                    "q": q_text,
                    "concept": concept_text,
                    "step": step_text.strip(),
                    "tip": tip_text
                })
    return parsed_data

def create_math_word_document(parsed_data):
    doc = Document()
    doc.add_heading('🧮 아빠표 AI 수학 맞춤 해설서', 0)
    
    table = doc.add_table(rows=1, cols=2)
    table.style = 'Table Grid'
    
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = '문제 (Question)'
    hdr_cells[1].text = '친절한 단계별 풀이 (Step-by-Step)'
    
    for item in parsed_data:
        row_cells = table.add_row().cells
        row_cells[0].text = item['q']
        row_cells[1].text = f"[핵심 개념]\n{item['concept']}\n\n[단계별 풀이]\n{item['step']}\n\n[아빠의 꿀팁]\n{item['tip']}"
                
    doc_io = io.BytesIO()
    doc.save(doc_io)
    doc_io.seek(0)
    return doc_io

st.set_page_config(layout="wide")

with st.sidebar:
    st.markdown("### 📱 스마트폰으로 문제 찍기")
    local_ip = get_local_ip()
    local_url = f"http://{local_ip}:8501"
    
    qr = qrcode.make(local_url)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)
    
    st.image(buf, caption="스마트폰 카메라로 스캔하세요")

st.title("🧮 욘다를 위한 아빠표 AI 수학 선생님")

if 'math_data' not in st.session_state:
    st.session_state.math_data = None
if 'math_file' not in st.session_state:
    st.session_state.math_file = None

uploaded_files = st.file_uploader("수학 문제집 페이지 사진을 업로드하거나 스마트폰으로 찍어 올리세요. (여러 장 가능)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if uploaded_files:
    uploaded_files.sort(key=get_sort_key)
    st.info(f"총 {len(uploaded_files)}장의 수학 페이지가 업로드되었습니다. 분석을 시작합니다!")
    
    if st.button("수학 해설 및 워드 파일 생성"):
        all_analyzed_blocks = []
        
        for idx, file in enumerate(uploaded_files):
            with st.spinner(f"[{idx+1}/{len(uploaded_files)}] '{file.name}' 문제 풀이를 분석 중입니다..."):
                image = Image.open(file)
                analyzed_result = analyze_math_image(image)
                all_analyzed_blocks.append(analyzed_result)
        
        st.session_state.math_data = parse_math_blocks(all_analyzed_blocks)
        st.session_state.math_file = create_math_word_document(st.session_state.math_data)

if st.session_state.math_data:
    st.success("✅ 수학 해설서 생성이 완료되었습니다!")
    
    st.download_button(
        label="📥 맞춤형 수학 해설서(.docx) 다운로드",
        data=st.session_state.math_file,
        file_name="수학해설서.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    
    st.subheader("👀 해설 미리보기")
    for item in st.session_state.math_data:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**[문제]**\n{item['q']}")
        with col2:
            st.markdown(f"**[핵심 개념]** {item['concept']}")
            st.markdown(f"**[단계별 풀이]**\n{item['step']}")
            st.markdown(f"**[아빠의 꿀팁]** {item['tip']}")
        st.divider()
