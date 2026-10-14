# 🚗 ITS 실시간 교통정보 서비스 (Real-time Traffic Info Service)

ITS(국가교통정보센터) API와 카카오 Local API를 연동하여 전국 도로의 실시간 교통소통 상태를 조회하고, OpenLayers 지도로 시각화하는 FastAPI 웹 애플리케이션입니다.

---

## 📌 주요 기능 (Key Features)

* **동네 이름 기반 교통정보 검색**: 카카오 키워드 검색 API를 이용해 동네 이름(예: 인사동, 혜화동 등) 입력 시 해당 위치 중심의 실시간 도로 교통 데이터를 조회합니다.
* **좌표 범위(Bounding Box) 검색**: 특정 경도·위도 범위를 지정하여 해당 구역 내 도로들의 현재 속도, 통행시간, 정체 상태를 확인합니다.
* **인터랙티브 웹 지도 시각화**: OpenLayers 및 ITS WMTS 타일 레이어를 활용하여 실시간 지도 위에서 교통 흐름 상태를 직관적으로 파악할 수 있습니다.
* **Supabase DB 백업 및 데이터 누적**: 조회된 교통정보 데이터를 백그라운드 작업(Background Tasks)으로 Supabase PostgreSQL에 자동 저장하며, ITS API 장애/타임아웃 발생 시 DB에 저장된 최신 백업 데이터를 대체 반환합니다.
* **Vercel Serverless 배포 지원**: Vercel 환경에 최적화된 비동기 HTTP 요청 처리 및 타임아웃 예외 처리가 적용되어 있습니다.

---

## 🛠️ 기술 스택 (Tech Stack)

### Backend
* **Framework**: FastAPI (Python 3.10+)
* **HTTP Client**: HTTPX (Async)
* **Database**: Supabase (PostgreSQL)
* **ORM/Driver**: psycopg2-binary

### Frontend
* **HTML5 / CSS3 / JavaScript (Vanilla JS)**
* **Map Engine**: OpenLayers 6.x (OSM + ITS WMTS Layer)

### External APIs
* **ITS 국가교통정보센터 API**: 실시간 교통소통정보 조회
* **카카오 Local API**: 키워드 검색 기반 좌표(Geocoding) 변환

### Deployment
* **Platform**: Vercel (Serverless Function)

---

## 📁 프로젝트 구조 (Project Structure)

```text
├── app/
│   ├── database.py       # Supabase PostgreSQL DB 연동 및 CRUD 로직
│   └── its_api.py        # ITS 국가교통정보센터 Open API 호출 모듈
├── static/
│   ├── index.html        # 메인 교통정보 목록 및 동네/좌표 검색 UI
│   └── map.html          # OpenLayers 기반 실시간 교통 지도 페이지
├── main.py               # FastAPI 엔드포인트 및 카카오 API 연동 로직
├── requirements.txt      # 프로젝트 의존성 라이브러리 목록
├── vercel.json           # Vercel 배포 설정 파일
└── .env                  # 환경변수 설정 파일 (Git 미포함)