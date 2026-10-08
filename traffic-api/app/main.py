import logging
import os
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse

from app.its_api import get_traffic_information
from app.database import (
    save_traffic_information_list,
    create_traffic_table,
    get_recent_traffic_list
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="ITS 교통정보 API",
    description="FastAPI를 이용한 ITS 교통소통정보 API 예제",
    version="1.0.0"
)

# 카카오 REST API 키
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")

@app.on_event("startup")
async def startup_event():
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
        traffic_data = await get_traffic_information(
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y
        )

        traffic_items = traffic_data.get("body", {}).get("items", [])
        logger.info("ITS에서 받은 교통정보 개수: %d", len(traffic_items))

        traffic_information_list = []
        for traffic_item in traffic_items:
            road_name = traffic_item.get("roadName")
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

        if traffic_information_list:
            background_tasks.add_task(
                save_traffic_information_list,
                traffic_information_list
            )

        return traffic_data

    except Exception as e:
        logger.warning("ITS API 호출 실패 -> DB 해당 위치 백업 데이터 반환: %s", e)
        
        db_items = get_recent_traffic_list(
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y,
            limit=200
        )
        
        return {
            "header": {
                "resultCode": "00",
                "resultMsg": "Supabase DB 백업 데이터 반환"
            },
            "body": {
                "items": db_items
            }
        }


@app.get("/traffic/search")
async def search_traffic_by_location(
    background_tasks: BackgroundTasks,
    location: str = Query(..., description="검색할 동네 이름 (예: 인사동, 종로구, 혜화동)")
):
    if not KAKAO_REST_API_KEY:
        raise HTTPException(
            status_code=500, 
            detail="KAKAO_REST_API_KEY 환경변수가 설정되지 않았습니다."
        )

    # 1. 카카오 API 헤더 설정 (KakaoAK 공백 주의)
    headers = {
        "Authorization": f"KakaoAK {KAKAO_REST_API_KEY.strip()}"
    }

    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(
                "https://dapi.kakao.com/v2/local/search/keyword.json",
                params={"query": location},
                headers=headers,
                timeout=5.0
            )
            res.raise_for_status()
            data = res.json()
        except httpx.HTTPStatusError as exc:
            logger.error("카카오 API HTTP Error (%d): %s", exc.response.status_code, exc.response.text)
            raise HTTPException(status_code=exc.response.status_code, detail=f"카카오 API 오류 ({exc.response.status_code}): Key를 확인해주세요.")
        except Exception as e:
            logger.error("카카오 위치 검색 실패: %s", e)
            raise HTTPException(status_code=500, detail="동네 위치 정보를 가져오는데 실패했습니다.")

    documents = data.get("documents", [])
    if not documents:
        raise HTTPException(status_code=404, detail=f"'{location}'에 해당하는 위치를 찾을 수 없습니다.")

    # 2. 중심 좌표 (x: 경도, y: 위도)
    center_x = float(documents[0]["x"])
    center_y = float(documents[0]["y"])

    # 3. 반경 1.5km 범위 오프셋 계산 (ITS API 호환을 위해 명확한 범위 지정)
    offset = 0.015
    min_x = round(center_x - offset, 5)
    max_x = round(center_x + offset, 5)
    min_y = round(center_y - offset, 5)
    max_y = round(center_y + offset, 5)

    logger.info("카카오 검색 [%s] -> 중심:(%f, %f), BBOX:[minX=%f, maxX=%f, minY=%f, maxY=%f]",
                location, center_x, center_y, min_x, max_x, min_y, max_y)

    return await traffic(
        background_tasks=background_tasks,
        min_x=min_x,
        max_x=max_x,
        min_y=min_y,
        max_y=max_y
    )