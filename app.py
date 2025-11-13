import streamlit as st
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from io import BytesIO

# tkinter는 로컬 환경에서만 사용 가능
try:
    import tkinter as tk
    from tkinter import filedialog
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False

st.set_page_config(page_title="이미지 분류 도구", page_icon="📁", layout="wide")

# 세션 상태 초기화
if 'input_folder' not in st.session_state:
    st.session_state.input_folder = ""
if 'output_folder' not in st.session_state:
    st.session_state.output_folder = ""

def select_folder(folder_type):
    """폴더 선택 대화상자 열기 (로컬 환경에서만 작동)"""
    if not TKINTER_AVAILABLE:
        st.warning("⚠️ 폴더 선택 기능은 로컬 환경에서만 사용 가능합니다. 경로를 직접 입력해주세요.")
        return None
    
    try:
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes('-topmost', 1)
        folder_path = filedialog.askdirectory(master=root)
        root.destroy()
        
        if folder_path:
            if folder_type == "input":
                st.session_state.input_folder = folder_path
            elif folder_type == "output":
                st.session_state.output_folder = folder_path
        return folder_path
    except Exception as e:
        st.error(f"❌ 폴더 선택 중 오류 발생: {str(e)}")
        return None

def parse_filename(filename):
    """
    파일명을 파싱하여 (앞_숫자, 뒤_숫자) 형태로 반환
    예: "90-Layer Shot_215-trigger_count.jpg" -> ("90", "215")
    """
    # 확장자 제거
    name_without_ext = os.path.splitext(filename)[0]
    
    # 패턴: 숫자-Layer Shot_숫자-trigger_count
    pattern = r'(\d+)-Layer Shot_(\d+)-trigger_count'
    match = re.match(pattern, name_without_ext)
    
    if match:
        first_num = match.group(1)
        second_num = match.group(2)
        return (int(first_num), int(second_num))
    return None

def get_image_files(folder_path):
    """이미지 폴더에서 이미지 파일만 가져오기"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif'}
    image_files = []
    
    for file in os.listdir(folder_path):
        if os.path.splitext(file)[1].lower() in image_extensions:
            image_files.append(file)
    
    return image_files

def find_missing_numbers(numbers):
    """최대값을 기준으로 누락된 숫자 찾기"""
    if not numbers:
        return []
    
    max_num = max(numbers)
    all_numbers = set(range(1, max_num + 1))
    existing_numbers = set(numbers)
    missing = sorted(all_numbers - existing_numbers)
    
    return missing

def group_by_first_number(parsed_files):
    """앞 숫자를 기준으로 그룹핑"""
    groups = defaultdict(list)
    
    for filename, (first_num, second_num) in parsed_files.items():
        groups[first_num].append((second_num, filename))
    
    # 각 그룹 내에서 두번째 숫자로 정렬
    for key in groups:
        groups[key].sort()
    
    return groups

def analyze_groups(groups):
    """그룹별 개수 분석"""
    group_analysis = {
        1: [],
        2: [],
        3: [],
        4: [],
        'other': []
    }
    
    for first_num, items in groups.items():
        count = len(items)
        if count in [1, 2, 3, 4]:
            group_analysis[count].append(first_num)
        else:
            group_analysis['other'].append(first_num)
    
    return group_analysis

def process_images(input_folder, output_folder, groups):
    """그룹별 규칙에 따라 이미지 처리"""
    # 출력 폴더 생성
    deposition_folder = os.path.join(output_folder, "Deposition")
    scanning_folder = os.path.join(output_folder, "Scanning")
    unknown_folder = os.path.join(output_folder, "Unknown")
    
    os.makedirs(deposition_folder, exist_ok=True)
    os.makedirs(scanning_folder, exist_ok=True)
    os.makedirs(unknown_folder, exist_ok=True)
    
    processing_log = []
    
    for first_num, items in groups.items():
        count = len(items)
        
        # 원본 파일의 확장자 가져오기
        sample_filename = items[0][1]
        ext = os.path.splitext(sample_filename)[1]
        new_filename = f"{first_num}{ext}"
        
        if count == 1:
            # Unknown 폴더에 저장
            src = os.path.join(input_folder, items[0][1])
            dst = os.path.join(unknown_folder, new_filename)
            shutil.copy2(src, dst)
            processing_log.append(f"[1개] {first_num}: {items[0][1]} -> Unknown/{new_filename}")
            
        elif count == 2:
            # 낮은 숫자 -> Deposition, 높은 숫자 -> Scanning
            src_dep = os.path.join(input_folder, items[0][1])
            dst_dep = os.path.join(deposition_folder, new_filename)
            shutil.copy2(src_dep, dst_dep)
            
            src_scan = os.path.join(input_folder, items[1][1])
            dst_scan = os.path.join(scanning_folder, new_filename)
            shutil.copy2(src_scan, dst_scan)
            
            processing_log.append(f"[2개] {first_num}: {items[0][1]} -> Deposition/{new_filename}, {items[1][1]} -> Scanning/{new_filename}")
            
        elif count == 3:
            # 2번째로 높은 숫자 -> Deposition, 가장 높은 숫자 -> Scanning
            src_dep = os.path.join(input_folder, items[1][1])
            dst_dep = os.path.join(deposition_folder, new_filename)
            shutil.copy2(src_dep, dst_dep)
            
            src_scan = os.path.join(input_folder, items[2][1])
            dst_scan = os.path.join(scanning_folder, new_filename)
            shutil.copy2(src_scan, dst_scan)
            
            processing_log.append(f"[3개] {first_num}: {items[1][1]} -> Deposition/{new_filename}, {items[2][1]} -> Scanning/{new_filename} (미사용: {items[0][1]})")
            
        elif count == 4:
            # 2번째로 높은 숫자 -> Deposition, 가장 높은 숫자 -> Scanning
            src_dep = os.path.join(input_folder, items[2][1])
            dst_dep = os.path.join(deposition_folder, new_filename)
            shutil.copy2(src_dep, dst_dep)
            
            src_scan = os.path.join(input_folder, items[3][1])
            dst_scan = os.path.join(scanning_folder, new_filename)
            shutil.copy2(src_scan, dst_scan)
            
            processing_log.append(f"[4개] {first_num}: {items[2][1]} -> Deposition/{new_filename}, {items[3][1]} -> Scanning/{new_filename} (미사용: {items[0][1]}, {items[1][1]})")
            
        else:
            # 5개 이상인 경우
            processing_log.append(f"[{count}개] {first_num}: 처리 규칙 없음 - {', '.join([item[1] for item in items])}")
    
    return processing_log

def save_log(log_content, output_folder, log_name):
    """로그 파일 저장"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{log_name}_{timestamp}.txt"
    log_path = os.path.join(output_folder, log_filename)
    
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(log_content))
    
    return log_path

def process_uploaded_files(uploaded_files):
    """업로드된 파일들을 처리"""
    # 임시 디렉토리 생성
    temp_input = tempfile.mkdtemp(prefix="input_")
    temp_output = tempfile.mkdtemp(prefix="output_")
    
    try:
        # 업로드된 파일을 임시 폴더에 저장
        for uploaded_file in uploaded_files:
            file_path = os.path.join(temp_input, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
        
        # 처리 로직 실행
        image_files = get_image_files(temp_input)
        
        if not image_files:
            return None, None, "업로드된 이미지 파일이 없습니다."
        
        # 파일명 파싱
        parsed_files = {}
        failed_files = []
        
        for filename in image_files:
            result = parse_filename(filename)
            if result:
                parsed_files[filename] = result
            else:
                failed_files.append(filename)
        
        if not parsed_files:
            return None, None, "규칙에 맞는 파일명이 없습니다."
        
        # 그룹핑 및 분석
        first_numbers = [first_num for first_num, _ in parsed_files.values()]
        missing_numbers = find_missing_numbers(first_numbers)
        groups = group_by_first_number(parsed_files)
        group_analysis = analyze_groups(groups)
        
        # 비정상 그룹 로그
        abnormal_log = []
        if group_analysis[1]:
            abnormal_log.append(f"1개: {', '.join(map(str, group_analysis[1]))}")
        if group_analysis[3]:
            abnormal_log.append(f"3개: {', '.join(map(str, group_analysis[3]))}")
        if group_analysis[4]:
            abnormal_log.append(f"4개: {', '.join(map(str, group_analysis[4]))}")
        
        # 이미지 처리
        processing_log = process_images(temp_input, temp_output, groups)
        
        # 로그 저장
        if abnormal_log:
            save_log(abnormal_log, temp_output, "abnormal_groups_log")
        save_log(processing_log, temp_output, "processing_log")
        
        # ZIP 파일 생성
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for root, dirs, files in os.walk(temp_output):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_output)
                    zip_file.write(file_path, arcname)
        
        zip_buffer.seek(0)
        
        return zip_buffer, {
            'parsed_files': parsed_files,
            'failed_files': failed_files,
            'missing_numbers': missing_numbers,
            'group_analysis': group_analysis,
            'abnormal_log': abnormal_log,
            'processing_log': processing_log
        }, None
        
    except Exception as e:
        return None, None, str(e)
    finally:
        # 임시 폴더 정리
        try:
            shutil.rmtree(temp_input)
            shutil.rmtree(temp_output)
        except:
            pass

# Streamlit UI
st.title("📁 HBNU M160 Vision Image 분류 Tool")
st.markdown("---")

# 모드 선택
mode = st.radio(
    "**처리 모드 선택**",
    ["📁 로컬 폴더 모드", "📤 파일 업로드 모드"],
    horizontal=True,
    help="로컬 모드: 컴퓨터의 폴더에서 직접 처리 | 업로드 모드: 파일을 업로드하여 처리 후 다운로드"
)

st.markdown("---")

if mode == "📁 로컬 폴더 모드":
    # 로컬 폴더 모드
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**🔍 입력 폴더 경로**")
        if TKINTER_AVAILABLE:
            col1_1, col1_2 = st.columns([3, 1])
            with col1_1:
                input_folder = st.text_input("입력 폴더", value=st.session_state.input_folder, placeholder="예: C:/images/input", label_visibility="collapsed", key="input_text")
            with col1_2:
                if st.button("📁 선택", key="input_btn", use_container_width=True):
                    select_folder("input")
                    st.rerun()
        else:
            input_folder = st.text_input("입력 폴더", value=st.session_state.input_folder, placeholder="예: C:/images/input", label_visibility="collapsed", key="input_text")
        # 텍스트 입력으로 변경된 경우 세션 상태 업데이트
        if input_folder != st.session_state.input_folder:
            st.session_state.input_folder = input_folder

    with col2:
        st.write("**💾 출력 폴더 경로**")
        if TKINTER_AVAILABLE:
            col2_1, col2_2 = st.columns([3, 1])
            with col2_1:
                output_folder = st.text_input("출력 폴더", value=st.session_state.output_folder, placeholder="예: C:/images/output", label_visibility="collapsed", key="output_text")
            with col2_2:
                if st.button("📁 선택", key="output_btn", use_container_width=True):
                    select_folder("output")
                    st.rerun()
        else:
            output_folder = st.text_input("출력 폴더", value=st.session_state.output_folder, placeholder="예: C:/images/output", label_visibility="collapsed", key="output_text")
        # 텍스트 입력으로 변경된 경우 세션 상태 업데이트
        if output_folder != st.session_state.output_folder:
            st.session_state.output_folder = output_folder

    st.markdown("---")

    if st.button("🚀 처리 시작", type="primary", use_container_width=True, key="process_local"):
        if not input_folder:
            st.error("❌ 입력 폴더 경로를 입력해주세요.")
        elif not os.path.exists(input_folder):
            st.error(f"❌ 입력 폴더를 찾을 수 없습니다: {input_folder}")
        elif not output_folder:
            st.error("❌ 출력 폴더 경로를 입력해주세요.")
        else:
            try:
                with st.spinner("처리 중..."):
                    # 1. 이미지 파일 가져오기
                    image_files = get_image_files(input_folder)
                    st.info(f"📊 총 {len(image_files)}개의 이미지 파일을 발견했습니다.")
                    
                    # 2. 파일명 파싱
                    parsed_files = {}
                    failed_files = []
                    
                    for filename in image_files:
                        result = parse_filename(filename)
                        if result:
                            parsed_files[filename] = result
                        else:
                            failed_files.append(filename)
                    
                    if failed_files:
                        st.warning(f"⚠️ {len(failed_files)}개의 파일은 파일명 규칙에 맞지 않아 제외되었습니다.")
                        with st.expander("제외된 파일 목록 보기"):
                            st.write(failed_files)
                    
                    # 3. 누락된 값 찾기
                    first_numbers = [first_num for first_num, _ in parsed_files.values()]
                    missing_numbers = find_missing_numbers(first_numbers)
                    
                    st.subheader("📋 누락된 숫자 분석")
                    if missing_numbers:
                        st.warning(f"누락된 숫자 ({len(missing_numbers)}개): {', '.join(map(str, missing_numbers[:50]))}")
                        if len(missing_numbers) > 50:
                            st.info(f"... 외 {len(missing_numbers) - 50}개 더")
                    else:
                        st.success("✅ 누락된 숫자가 없습니다.")
                    
                    # 4. 그룹핑 및 분석
                    groups = group_by_first_number(parsed_files)
                    group_analysis = analyze_groups(groups)
                    
                    st.subheader("📊 그룹별 분석")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("1개 그룹", len(group_analysis[1]))
                    with col2:
                        st.metric("2개 그룹 (정상)", len(group_analysis[2]))
                    with col3:
                        st.metric("3개 그룹", len(group_analysis[3]))
                    with col4:
                        st.metric("4개 그룹", len(group_analysis[4]))
                    
                    # 비정상 그룹 로그 생성
                    abnormal_log = []
                    if group_analysis[1]:
                        abnormal_log.append(f"1개: {', '.join(map(str, group_analysis[1]))}")
                    if group_analysis[3]:
                        abnormal_log.append(f"3개: {', '.join(map(str, group_analysis[3]))}")
                    if group_analysis[4]:
                        abnormal_log.append(f"4개: {', '.join(map(str, group_analysis[4]))}")
                    if group_analysis['other']:
                        for first_num in group_analysis['other']:
                            count = len(groups[first_num])
                            abnormal_log.append(f"{count}개: {first_num}")
                    
                    if abnormal_log:
                        st.warning("⚠️ 개수가 2개가 아닌 그룹이 발견되었습니다.")
                        with st.expander("비정상 그룹 상세 정보"):
                            st.text('\n'.join(abnormal_log))
                        
                        # 비정상 그룹 로그 저장
                        os.makedirs(output_folder, exist_ok=True)
                        abnormal_log_path = save_log(abnormal_log, output_folder, "abnormal_groups_log")
                        st.info(f"📝 비정상 그룹 로그 저장: {abnormal_log_path}")
                    
                    # 5. 이미지 처리
                    status_placeholder = st.empty()
                    status_placeholder.subheader("🔄 이미지 처리 중...")
                    processing_log = process_images(input_folder, output_folder, groups)
                    status_placeholder.subheader("✅ 이미지 처리 완료")
                    
                    # 6. 처리 로그 저장
                    processing_log_path = save_log(processing_log, output_folder, "processing_log")
                    
                    st.success("✅ 모든 처리가 완료되었습니다!")
                    st.info(f"📝 처리 로그 저장: {processing_log_path}")
                    
                    # 처리 결과 요약
                    st.subheader("📈 처리 결과 요약")
                    deposition_count = len(group_analysis[2]) + len(group_analysis[3]) + len(group_analysis[4])
                    scanning_count = len(group_analysis[2]) + len(group_analysis[3]) + len(group_analysis[4])
                    unknown_count = len(group_analysis[1])
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Deposition 폴더", f"{deposition_count}개")
                    with col2:
                        st.metric("Scanning 폴더", f"{scanning_count}개")
                    with col3:
                        st.metric("Unknown 폴더", f"{unknown_count}개")
                    
                    with st.expander("처리 로그 보기"):
                        for log in processing_log[:100]:
                            st.text(log)
                        if len(processing_log) > 100:
                            st.info(f"... 외 {len(processing_log) - 100}개 더 (전체 로그는 파일을 확인하세요)")
                            
            except Exception as e:
                st.error(f"❌ 오류가 발생했습니다: {str(e)}")
                st.exception(e)

else:
    # 파일 업로드 모드
    st.write("**📤 이미지 파일 업로드**")
    uploaded_files = st.file_uploader(
        "이미지 파일들을 선택하세요 (여러 파일 선택 가능)",
        type=['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'gif'],
        accept_multiple_files=True,
        help="Ctrl 또는 Shift를 눌러 여러 파일을 선택할 수 있습니다."
    )
    
    if uploaded_files:
        st.info(f"📊 {len(uploaded_files)}개의 파일이 업로드되었습니다.")
    
    st.markdown("---")
    
    if st.button("🚀 처리 시작", type="primary", use_container_width=True, key="process_upload"):
        if not uploaded_files:
            st.error("❌ 파일을 업로드해주세요.")
        else:
            with st.spinner("처리 중..."):
                zip_buffer, results, error = process_uploaded_files(uploaded_files)
                
                if error:
                    st.error(f"❌ 오류가 발생했습니다: {error}")
                elif zip_buffer and results:
                    # 결과 표시
                    parsed_files = results['parsed_files']
                    failed_files = results['failed_files']
                    missing_numbers = results['missing_numbers']
                    group_analysis = results['group_analysis']
                    abnormal_log = results['abnormal_log']
                    processing_log = results['processing_log']
                    
                    if failed_files:
                        st.warning(f"⚠️ {len(failed_files)}개의 파일은 파일명 규칙에 맞지 않아 제외되었습니다.")
                        with st.expander("제외된 파일 목록 보기"):
                            st.write(failed_files)
                    
                    st.subheader("📋 누락된 숫자 분석")
                    if missing_numbers:
                        st.warning(f"누락된 숫자 ({len(missing_numbers)}개): {', '.join(map(str, missing_numbers[:50]))}")
                        if len(missing_numbers) > 50:
                            st.info(f"... 외 {len(missing_numbers) - 50}개 더")
                    else:
                        st.success("✅ 누락된 숫자가 없습니다.")
                    
                    st.subheader("📊 그룹별 분석")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("1개 그룹", len(group_analysis[1]))
                    with col2:
                        st.metric("2개 그룹 (정상)", len(group_analysis[2]))
                    with col3:
                        st.metric("3개 그룹", len(group_analysis[3]))
                    with col4:
                        st.metric("4개 그룹", len(group_analysis[4]))
                    
                    if abnormal_log:
                        st.warning("⚠️ 개수가 2개가 아닌 그룹이 발견되었습니다.")
                        with st.expander("비정상 그룹 상세 정보"):
                            st.text('\n'.join(abnormal_log))
                    
                    st.success("✅ 모든 처리가 완료되었습니다!")
                    
                    # 처리 결과 요약
                    st.subheader("📈 처리 결과 요약")
                    deposition_count = len(group_analysis[2]) + len(group_analysis[3]) + len(group_analysis[4])
                    scanning_count = len(group_analysis[2]) + len(group_analysis[3]) + len(group_analysis[4])
                    unknown_count = len(group_analysis[1])
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Deposition 폴더", f"{deposition_count}개")
                    with col2:
                        st.metric("Scanning 폴더", f"{scanning_count}개")
                    with col3:
                        st.metric("Unknown 폴더", f"{unknown_count}개")
                    
                    # 다운로드 버튼
                    st.markdown("---")
                    st.download_button(
                        label="📥 처리된 파일 다운로드 (ZIP)",
                        data=zip_buffer,
                        file_name=f"processed_images_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
                    
                    with st.expander("처리 로그 보기"):
                        for log in processing_log[:100]:
                            st.text(log)
                        if len(processing_log) > 100:
                            st.info(f"... 외 {len(processing_log) - 100}개 더")

st.markdown("---")
st.markdown("""
### 📖 사용 방법

#### 📁 로컬 폴더 모드 (로컬 환경 권장)
1. **입력 폴더 경로**: 처리할 이미지가 들어있는 폴더 경로를 입력하거나 선택하세요.
2. **출력 폴더 경로**: 분류된 이미지를 저장할 폴더 경로를 입력하거나 선택하세요.
3. **처리 시작** 버튼을 클릭하여 처리를 시작합니다.

#### 📤 파일 업로드 모드 (배포 환경 권장)
1. **이미지 파일 업로드**: 처리할 이미지 파일들을 선택하세요 (여러 파일 선택 가능).
2. **처리 시작** 버튼을 클릭하여 처리를 시작합니다.
3. 처리가 완료되면 **다운로드 버튼**을 클릭하여 결과 파일을 다운로드하세요.

### 📝 파일명 규칙
- 입력 형식: `숫자-Layer Shot_숫자-trigger_count.확장자`
- 예: `90-Layer Shot_215-trigger_count.jpg`

### 📂 출력 폴더 구조
- **Deposition**: 각 그룹의 낮은 번호 또는 2번째로 높은 번호 이미지
- **Scanning**: 각 그룹의 높은 번호 이미지
- **Unknown**: 그룹 내 개수가 1개인 이미지
""")
