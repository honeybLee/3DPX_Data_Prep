# 이미지 분류 및 이름 변경 도구

이미지 파일명을 분석하여 규칙에 따라 분류하고 이름을 변경하여 저장하는 Streamlit 애플리케이션입니다.

## 기능

1. **파일명 파싱**: `숫자-Layer Shot_숫자-trigger_count` 형식의 파일명을 분석
2. **누락 값 탐지**: 최대값을 기준으로 누락된 숫자 탐지
3. **그룹 분석**: 앞 숫자를 기준으로 그룹핑하여 비정상 그룹 탐지
4. **자동 분류 및 저장**: 그룹 개수에 따라 다른 폴더에 자동 분류
5. **로그 생성**: 비정상 그룹 및 처리 내역 로그 파일 생성

## 설치 방법

```bash
pip install -r requirements.txt
```

## 실행 방법

```bash
streamlit run app.py
```

## 사용 방법

1. 앱을 실행하면 웹 브라우저가 자동으로 열립니다.
2. **입력 폴더 경로**에 처리할 이미지가 들어있는 폴더 경로를 입력합니다.
3. **출력 폴더 경로**에 분류된 이미지를 저장할 폴더 경로를 입력합니다.
4. **처리 시작** 버튼을 클릭합니다.

## 파일명 규칙

### 입력 형식
- 형식: `숫자-Layer Shot_숫자-trigger_count.확장자`
- 예시: `90-Layer Shot_215-trigger_count.jpg`

### 출력 형식
- 형식: `숫자.확장자`
- 예시: `90.jpg`

## 분류 규칙

### 그룹 개수별 처리 방법

- **2개 (정상)**: 
  - 낮은 번호 → `Deposition` 폴더
  - 높은 번호 → `Scanning` 폴더

- **1개**:
  - `Unknown` 폴더에 저장

- **3개**:
  - 2번째로 높은 번호 → `Deposition` 폴더
  - 가장 높은 번호 → `Scanning` 폴더

- **4개**:
  - 2번째로 높은 번호 → `Deposition` 폴더
  - 가장 높은 번호 → `Scanning` 폴더

## 출력 구조

```
출력_폴더/
├── Deposition/
│   ├── 1.jpg
│   ├── 2.jpg
│   └── ...
├── Scanning/
│   ├── 1.jpg
│   ├── 2.jpg
│   └── ...
├── Unknown/
│   ├── 3.jpg
│   └── ...
├── abnormal_groups_log_YYYYMMDD_HHMMSS.txt
└── processing_log_YYYYMMDD_HHMMSS.txt
```

## 로그 파일

### abnormal_groups_log
개수가 2개가 아닌 그룹들의 정보를 포함합니다.

예시:
```
1개: 1, 3, 4, 5, 6
3개: 440, 442, 443
4개: 500, 502
```

### processing_log
각 파일이 어떻게 처리되었는지 상세 내역을 포함합니다.

예시:
```
[2개] 90: 90-Layer Shot_215-trigger_count.jpg -> Deposition/90.jpg, 90-Layer Shot_216-trigger_count.jpg -> Scanning/90.jpg
[1개] 3: 3-Layer Shot_100-trigger_count.jpg -> Unknown/3.jpg
[3개] 440: 440-Layer Shot_502-trigger_count.jpg -> Deposition/440.jpg, 440-Layer Shot_503-trigger_count.jpg -> Scanning/440.jpg (미사용: 440-Layer Shot_501-trigger_count.jpg)
```

## 지원 이미지 형식

- JPG/JPEG
- PNG
- BMP
- TIFF
- GIF

## 주의사항

- 입력 폴더의 원본 파일은 변경되지 않으며, 복사본이 출력 폴더에 저장됩니다.
- 출력 폴더가 없으면 자동으로 생성됩니다.
- 동일한 이름의 파일이 있으면 덮어씌워집니다.

