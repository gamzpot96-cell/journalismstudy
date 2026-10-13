# ITS 실시간 교통정보 서비스

`traffic-api/`는 ITS 교통소통정보와 카카오 Local 키워드 검색을 연결하는 FastAPI 애플리케이션입니다. 목록 페이지와 OpenLayers 지도, Supabase PostgreSQL 백업을 제공합니다.

## 실행

Python 3.10 이상을 사용합니다. 아래 명령은 저장소 루트에서 시작합니다.

```sh
cd traffic-api
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
# PowerShell에서는 Copy-Item .env.example .env 사용 가능
python -m uvicorn app.main:app --reload
```

`.env`에 본인의 ITS API 키, 카카오 REST API 키, PostgreSQL 접속 정보를 입력하세요. `.env`는 Git에 커밋하지 않습니다. 환경변수는 `traffic-api/.env`에서 읽으며 이미 설정한 환경변수를 덮어쓰지 않습니다.

| 환경변수 | 용도 / 기본값 |
| --- | --- |
| ITS_API_KEY | ITS 교통소통정보 인증키 |
| KAKAO_REST_API_KEY | 카카오 Local 키워드 검색 REST 키 |
| POSTGRES_HOST | Supabase 또는 PostgreSQL 호스트 |
| POSTGRES_PORT | 포트, 기본 5432 |
| POSTGRES_USER | DB 사용자 |
| POSTGRES_PASSWORD | DB 비밀번호 |
| POSTGRES_DB | DB 이름, 기본 postgres |
| POSTGRES_SSLMODE | SSL 모드, 기본 require |

DB 드라이버는 **psycopg 3**입니다. 시작 시 테이블 생성을 시도합니다. 수동 초기화는 `sql/traffic_database.sql`을 PostgreSQL에서 실행하세요. 이 스크립트는 기존 테이블이나 데이터를 삭제하지 않습니다. 기존 테이블의 컬럼을 자동 마이그레이션하지는 않습니다.

## API와 화면

| 경로 | 기능 |
| --- | --- |
| `/` | 교통 목록, 동네 및 좌표 검색 |
| `/map` | OSM 지도, ITS 타일 표시 전환, 검색 위치 이동 |
| `/docs` | 대화형 API 문서 |
| `/traffic?min_x=126.8&max_x=127.0&min_y=37.4&max_y=37.6` | 지정 영역 조회 |
| `/traffic/search?location=서울역` | 검색 위치의 경도·위도 ±0.02도 영역 조회 |
| `/test-its-connection` | ITS 호스트 DNS 및 IPv4/IPv6 TCP 9443 연결 진단 |

경도는 -180~180, 위도는 -90~90이며 최소값이 최대값보다 작아야 합니다. 잘못된 좌표와 빈 검색어는 422를 반환합니다. 검색 결과가 없으면 404, 카카오 응답·통신 오류는 502, 카카오 키 미설정은 500입니다.

교통 응답은 `header`와 `body.items`를 유지합니다. 위치 검색은 지도 이동용 `location: {name, x, y}`도 반환합니다. 속도는 km/h, ITS `travelTime`은 초 단위입니다. 목록은 최대 50건을 표시하며 속도 60 이상은 원활, 30 이상은 서행, 그 미만은 정체로 표시합니다.

## 장애 및 저장 동작

- ITS HTTP/통신 오류, JSON 형식 오류, `header.resultCode` 오류 시 요청 영역에 해당하는 DB 백업을 최대 200건 반환합니다. 백업 응답의 `header.resultMsg`는 `Supabase DB 백업 데이터 반환`입니다.
- 백업 DB도 실패하면 503을 반환합니다. DB 조회가 성공했지만 데이터가 없으면 빈 목록을 반환합니다.
- ITS 조회가 성공하면 저장을 시도합니다. 데이터 변환 또는 DB 저장이 실패해도 정상 ITS 응답을 반환하고 실패를 로그에 남깁니다. DB 호출은 스레드에서 실행하되 완료를 기다립니다. 백그라운드 저장 방식은 아닙니다.
- ITS 수집 시간은 한국 시간(UTC+9)으로 해석하고, 누락 시 현재 시간을 저장합니다. 백업 응답 시간도 한국 시간으로 변환합니다.
- 좌표 없는 ITS 항목은 DB에 저장되더라도 영역별 백업 조회에서 제외됩니다. 백업은 누적 이력에서 최신 순으로 조회하며 링크별 중복 제거 또는 만료 필터를 적용하지 않습니다. 따라서 백업은 실시간 데이터로 간주하면 안 됩니다.

## 테스트

```sh
cd traffic-api
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

외부 HTTP 호출과 DB 연결을 모의하여 키 없이 테스트합니다. 정적 파일 경로, 좌표 검증, 정상 응답과 저장 실패, 영역별 백업과 동시 장애, ITS 오류 응답, 카카오 검색 응답 및 지도 중심 좌표, DB 시간·좌표 직렬화를 검증합니다. `app/test_database.py`는 실제 ITS와 DB를 사용하는 수동 실행 예제이며 자동 테스트 수집 대상이 아닙니다.

2026-10-13 검증: Python 3.12에서 자동 테스트 33건 통과. 실제 ITS·카카오 인증 요청, Supabase 연결, 지도 외부 타일 표시, Vercel 배포는 인증 정보나 배포 환경 없이 검증하지 않았습니다.

## 배포

Vercel 프로젝트의 Root Directory를 `traffic-api`로 설정하고 `.env.example`의 변수들을 배포 환경변수에 등록하세요. `vercel.json`은 `app/main.py`와 정적 파일을 라우팅합니다. ITS HTTP 제한시간은 30초, 카카오 검색은 5초, DB 접속은 10초입니다. 배포 함수의 실행 제한과 ITS 9443 포트 접근을 실제 환경에서 확인해야 합니다. 연결 진단은 TCP 연결만 확인하며 API 인증 성공을 보장하지 않습니다.

## 구조

```text
traffic-api/
├── app/main.py            # FastAPI 라우트 및 검색
├── app/its_api.py         # ITS 호출 및 응답 검증
├── app/database.py        # psycopg 3 기반 저장·백업 조회
├── app/test_database.py   # 실제 서비스 수동 테스트
├── static/               # 목록·지도 HTML
├── sql/traffic_database.sql
├── tests/test_traffic.py  # 외부 연결 없는 자동 테스트
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
├── .env.example
└── vercel.json
```

예제 설정에서 기존 비밀번호 형태의 값을 제거했습니다. 해당 값이 실제 사용된 인증 정보라면 Supabase에서 비밀번호를 변경하세요. 파일 수정으로 과거 Git 이력의 값이 삭제되지는 않습니다.
