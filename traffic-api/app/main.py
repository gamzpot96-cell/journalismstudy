import logging
import os
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ITS 교통정보 서비스",
    description="카카오 위치 검색 및 정적 웹페이지 서빙 전용 백엔드",
    version="2.0.0"
)

# Static 폴더 연결 (index.html, map.html 및 관련 assets 서빙)
app.mount("/static", StaticFiles(directory="static"), name="static")

KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")


# ---------------------------------------------------------
# 1. HTML 페이지 서빙 엔드포인트
# ---------------------------------------------------------
@app.get("/")
async def home():
    """메인 검색 페이지 반환"""
    return FileResponse("static/index.html")


@app.get("/map")
async def map_page():
    """교통정보 지도 표시 페이지 반환"""
    return FileResponse("static/map.html")


# ---------------------------------------------------------
# 2. 위치 검색 및 BBOX 좌표 변환 엔드포인트
# ---------------------------------------------------------
@app.get("/traffic/search")
async def search_location_bbox(
    location: str = Query(..., description="검색할 동네 이름 (예: 인사동, 혜화동)")
):
    """
    동네 이름을 입력받아 카카오 Local API로 위/경도를 조회하고,
    주변 약 1.5km 영역의 BBOX 범위 좌표를 반환합니다.
    """
    if not KAKAO_REST_API_KEY:
        logger.error("KAKAO_REST_API_KEY 환경변수가 설정되지 않았습니다.")
        raise HTTPException(
            status_code=500,
            detail="KAKAO_REST_API_KEY 환경변수가 설정되지 않았습니다."
        )

    headers = {
        "Authorization": f"KakaoAK {KAKAO_REST_API_KEY.strip()}"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://dapi.kakao.com/v2/local/search/keyword.json",
                params={"query": location},
                headers=headers,
                timeout=5.0
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.error("카카오 위치 검색 실패: %s", e)
            raise HTTPException(
                status_code=500,
                detail="동네 위치 정보를 가져오는데 실패했습니다."
            )

    documents = data.get("documents", [])
    if not documents:
        raise HTTPException(
            status_code=404,
            detail=f"'{location}'에 해당하는 위치를 찾을 수 없습니다."
        )

    # 검색된 첫 번째 장소의 좌표 수신
    center_x = float(documents[0]["x"])  # 경도 (Longitude)
    center_y = float(documents[0]["y"])  # 위도 (Latitude)

    # 검색 위치 중심 주변 약 1.5km 범위(Offset 0.015) BBOX 설정
    offset = 0.015
    min_x = round(center_x - offset, 5)
    max_x = round(center_x + offset, 5)
    min_y = round(center_y - offset, 5)
    max_y = round(center_y + offset, 5)

    logger.info("위치 검색 성공: %s -> 중심(%f, %f)", location, center_x, center_y)

    return {
        "location": location,
        "center": {"x": center_x, "y": center_y},
        "bbox": {
            "minX": min_x,
            "maxX": max_x,
            "minY": min_y,
            "maxY": max_y
        }
    }