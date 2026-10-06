import logging

logger = logging.getLogger(__name__)

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from app.its_api import get_traffic_information
from app.database import save_traffic_information_list

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
    try:
        # 1. ITS에서 교통정보 가져오기
        traffic_data = await get_traffic_information(
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y
        )

        # 2. ITS 데이터에서 교통정보 목록 가져오기
        traffic_items = traffic_data["body"]["items"]

        logger.info(
            "ITS에서 받은 교통정보 개수: %d",
            len(traffic_items)
        )

        # 3. Supabase에 저장할 데이터 만들기
        traffic_information_list = []

        for traffic_item in traffic_items:

            road_name = traffic_item.get("roadName")

            road_type = traffic_item.get("roadDrcType")

            link_id = traffic_item.get("linkId")

            speed = int(
                float(traffic_item.get("speed", 0))
            )

            travel_time = float(
                traffic_item.get("travelTime", 0)
            )

            # 속도를 기준으로 교통 상태 판단
            if speed >= 60:
                traffic_status = "원활"

            elif speed >= 30:
                traffic_status = "서행"

            else:
                traffic_status = "정체"

            # ITS 수집 시간
            created_date = traffic_item.get("createdDate")

            from datetime import datetime

            collected_at = datetime.strptime(
                created_date,
                "%Y%m%d%H%M%S"
            )

            traffic_information = (
                road_name,
                road_type,
                link_id,
                speed,
                travel_time,
                traffic_status,
                None,
                None,
                collected_at
            )

            traffic_information_list.append(
                traffic_information
            )

        # 4. Supabase에 전체 데이터 저장
        if len(traffic_information_list) > 0:

            save_traffic_information_list(
                traffic_information_list
            )

            logger.info(
                "Supabase 저장 완료: %d건",
                len(traffic_information_list)
            )

        # 5. 원래처럼 ITS 데이터를 웹페이지에 반환
        return traffic_data

    except ValueError as error:

        logger.exception("설정값 오류")

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    except Exception:

        logger.exception(
            "교통정보 조회 또는 데이터베이스 저장 중 오류 발생"
        )

        raise HTTPException(
            status_code=502,
            detail="교통정보 조회 또는 데이터베이스 저장 중 오류가 발생했습니다."
        )