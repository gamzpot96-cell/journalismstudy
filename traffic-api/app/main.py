# app/main.py
import logging
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse

from app.its_api import get_traffic_information
from app.database import save_traffic_information_list, create_traffic_table

logger = logging.getLogger(__name__)

app = FastAPI(
    title="ITS 교통정보 API",
    description="FastAPI를 이용한 ITS 교통소통정보 API 예제",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """앱 시작 시 Supabase DB 테이블 확인 및 생성"""
    try:
        create_traffic_table()
    except Exception as e:
        logger.error("Startup DB 초기화 실패: %s", e)


@app.get("/")
async def home():
    return FileResponse("static/index.html")


@app.get("/map")
async def map_page():
    return FileResponse("static/map.html")


@app.get("/traffic")
async def traffic(
    background_tasks: BackgroundTasks,
    min_x: float = Query(..., description="최소 경도"),
    max_x: float = Query(..., description="최대 경도"),
    min_y: float = Query(..., description="최소 위도"),
    max_y: float = Query(..., description="최대 위도")
):
    try:
        # 1. ITS API 조회
        traffic_data = await get_traffic_information(
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y
        )

# app/main.py 중 traffic 함수 내부

        # 2. DB 저장용 데이터 변환
        traffic_information_list = []
        for traffic_item in traffic_items:
            road_name = traffic_item.get("roadName")
            # roadDrcType이 None이거나 비어있을 경우 '일반' 또는 '미지정'으로 기본값 처리
            road_type = traffic_item.get("roadDrcType") or "일반"
            link_id = traffic_item.get("linkId")
            speed = int(float(traffic_item.get("speed", 0)))
            travel_time = float(traffic_item.get("travelTime", 0))

            if speed >= 60:
                traffic_status = "원활"
            elif speed >= 30:
                traffic_status = "서행"
            else:
                traffic_status = "정체"

            created_date = traffic_item.get("createdDate")
            collected_at = (
                datetime.strptime(created_date, "%Y%m%d%H%M%S")
                if created_date else None
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
            traffic_information_list.append(traffic_information)

        # 3. DB 저장을 백그라운드 작업으로 등록 (사용자 대기 시간 소요 방지)
        if traffic_information_list:
            background_tasks.add_task(
                save_traffic_information_list,
                traffic_information_list
            )

        # 4. 즉시 응답 반환
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
            detail="교통정보 조회 중 오류가 발생했습니다."
        )