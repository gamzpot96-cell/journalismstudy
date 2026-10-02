import logging

logger = logging.getLogger(__name__)

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from app.its_api import get_traffic_information


# FastAPI 애플리케이션 생성
app = FastAPI(
    title="ITS 교통정보 API",
    description="FastAPI를 이용한 ITS 교통소통정보 API 예제",
    version="1.0.0"
)


# --------------------------------------------------
# 메인 페이지
# --------------------------------------------------

@app.get("/")
async def home():
    """
    index.html을 보여줍니다.
    """

    return FileResponse("static/index.html")

@app.get("/map")
async def map_page():
    return FileResponse("static/map.html")

# --------------------------------------------------
# 교통정보 API
# --------------------------------------------------

@app.get("/traffic")
async def traffic(
    min_x: float = Query(..., description="최소 경도"),
    max_x: float = Query(..., description="최대 경도"),
    min_y: float = Query(..., description="최소 위도"),
    max_y: float = Query(..., description="최대 위도")
):
    """
    지정한 좌표 범위의 ITS 교통정보를 조회합니다.
    """

    try:

        # ITS API 호출
        traffic_data = await get_traffic_information(
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y
        )

        # ITS에서 받은 데이터를 그대로 반환
        return traffic_data

    except ValueError as error:
        logger.exception("설정값 오류")
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    except Exception:
        logger.exception("교통정보 조회 중 오류 발생")
        raise HTTPException(
            status_code=502,
            detail="ITS API 호출 중 오류가 발생했습니다."
        )