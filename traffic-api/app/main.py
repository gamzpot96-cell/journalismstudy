import logging
import os
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse

from app.its_api import get_traffic_information
from app.database import (
    save_traffic_information_list,
    create_traffic_table
)


logger = logging.getLogger(__name__)


app = FastAPI(
    title="ITS 교통정보 API",
    description="FastAPI를 이용한 ITS 교통소통정보 API 예제",
    version="1.0.0"
)


# 카카오 REST API 키
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")


# ---------------------------------------------------------
# 서버 시작 시 데이터베이스 테이블 확인
# ---------------------------------------------------------
@app.on_event("startup")
async def startup_event():

    try:
        create_traffic_table()

    except Exception as e:
        logger.error("Startup DB 초기화 실패: %s", e)


# ---------------------------------------------------------
# 메인 페이지
# ---------------------------------------------------------
@app.get("/")
async def home():

    return FileResponse("static/index.html")


# ---------------------------------------------------------
# 지도 페이지
# ---------------------------------------------------------
@app.get("/map")
async def map_page():

    return FileResponse("static/map.html")


# ---------------------------------------------------------
# 교통정보 조회
# ---------------------------------------------------------
@app.get("/traffic")
async def traffic(

    background_tasks: BackgroundTasks,

    min_x: float = Query(
        ...,
        description="최소 경도"
    ),

    max_x: float = Query(
        ...,
        description="최대 경도"
    ),

    min_y: float = Query(
        ...,
        description="최소 위도"
    ),

    max_y: float = Query(
        ...,
        description="최대 위도"
    )
):

    logger.info(
        "교통정보 요청 BBOX: minX=%f, maxX=%f, minY=%f, maxY=%f",
        min_x,
        max_x,
        min_y,
        max_y
    )


    # -----------------------------------------------------
    # 1. ITS API 호출
    # -----------------------------------------------------
    try:

        traffic_data = await get_traffic_information(

            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y

        )

    except Exception as e:

        # -------------------------------------------------
        # 중요:
        # 기존에는 ITS API가 실패하면
        # Supabase의 과거 데이터를 반환했습니다.
        #
        # 이 때문에 다른 지역을 검색해도
        # 이전 지역의 데이터가 표시되었습니다.
        #
        # 이제는 잘못된 데이터를 보여주지 않고
        # 명확하게 오류를 반환합니다.
        # -------------------------------------------------

        logger.error(
            "ITS API 호출 실패: %s",
            e
        )

        raise HTTPException(

            status_code=502,

            detail={
                "message": "ITS 교통정보 API에 연결할 수 없습니다.",
                "reason": "현재 Vercel 서버에서 ITS API에 접근할 수 없습니다.",
                "requested_area": {
                    "min_x": min_x,
                    "max_x": max_x,
                    "min_y": min_y,
                    "max_y": max_y
                }
            }
        )


    # -----------------------------------------------------
    # 2. ITS API 응답에서 교통정보 가져오기
    # -----------------------------------------------------

    traffic_items = traffic_data.get(
        "body",
        {}
    ).get(
        "items",
        []
    )


    logger.info(
        "ITS에서 받은 교통정보 개수: %d",
        len(traffic_items)
    )


    # -----------------------------------------------------
    # 3. DB 저장용 데이터 만들기
    # -----------------------------------------------------

    traffic_information_list = []


    for traffic_item in traffic_items:

        # 도로 이름
        road_name = traffic_item.get(
            "roadName"
        )


        # 도로 진행 방향
        road_type = traffic_item.get(
            "roadDrcType"
        ) or "일반"


        # ITS 링크 ID
        link_id = traffic_item.get(
            "linkId"
        )


        # 평균 속도
        speed = int(
            float(
                traffic_item.get(
                    "speed",
                    0
                )
            )
        )


        # 통행 시간
        travel_time = float(
            traffic_item.get(
                "travelTime",
                0
            )
        )


        # -------------------------------------------------
        # 속도에 따른 교통상태 판단
        # -------------------------------------------------

        if speed >= 60:

            traffic_status = "원활"

        elif speed >= 30:

            traffic_status = "서행"

        else:

            traffic_status = "정체"


        # -------------------------------------------------
        # ITS의 createdDate를 datetime으로 변환
        # -------------------------------------------------

        created_date = traffic_item.get(
            "createdDate"
        )


        if created_date:

            try:

                collected_at = datetime.strptime(
                    created_date,
                    "%Y%m%d%H%M%S"
                )

            except ValueError:

                collected_at = None

        else:

            collected_at = None


        # -------------------------------------------------
        # DB 저장 데이터
        #
        # 현재 ITS trafficInfo 응답에는
        # 위도/경도 정보가 없기 때문에
        # latitude / longitude는 NULL로 저장합니다.
        # -------------------------------------------------

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


    # -----------------------------------------------------
    # 4. 교통정보가 있다면 Supabase에 저장
    # -----------------------------------------------------

    if traffic_information_list:

        background_tasks.add_task(

            save_traffic_information_list,

            traffic_information_list

        )


    # -----------------------------------------------------
    # 5. 현재 ITS API 응답을 그대로 반환
    # -----------------------------------------------------

    return traffic_data


# ---------------------------------------------------------
# 동네 이름으로 교통정보 검색
# ---------------------------------------------------------
@app.get("/traffic/search")
async def search_traffic_by_location(

    background_tasks: BackgroundTasks,

    location: str = Query(
        ...,
        description="검색할 동네 이름 (예: 인사동, 종로구, 혜화동)"
    )

):

    # -----------------------------------------------------
    # 1. 카카오 API 키 확인
    # -----------------------------------------------------

    if not KAKAO_REST_API_KEY:

        raise HTTPException(

            status_code=500,

            detail="KAKAO_REST_API_KEY 환경변수가 설정되지 않았습니다."

        )


    # -----------------------------------------------------
    # 2. 카카오 API 요청 헤더
    # -----------------------------------------------------

    headers = {

        "Authorization":
        f"KakaoAK {KAKAO_REST_API_KEY.strip()}"

    }


    # -----------------------------------------------------
    # 3. 카카오 장소 검색 API 호출
    # -----------------------------------------------------

    async with httpx.AsyncClient() as client:

        try:

            response = await client.get(

                "https://dapi.kakao.com/v2/local/search/keyword.json",

                params={
                    "query": location
                },

                headers=headers,

                timeout=5.0

            )


            response.raise_for_status()


            data = response.json()


        except httpx.HTTPStatusError as e:

            logger.error(

                "카카오 API HTTP Error (%d): %s",

                e.response.status_code,

                e.response.text

            )


            raise HTTPException(

                status_code=e.response.status_code,

                detail=(
                    f"카카오 API 오류 "
                    f"({e.response.status_code}): "
                    "API Key를 확인해주세요."
                )

            )


        except Exception as e:

            logger.error(
                "카카오 위치 검색 실패: %s",
                e
            )


            raise HTTPException(

                status_code=500,

                detail="동네 위치 정보를 가져오는데 실패했습니다."

            )


    # -----------------------------------------------------
    # 4. 카카오 검색 결과 확인
    # -----------------------------------------------------

    documents = data.get(
        "documents",
        []
    )


    if not documents:

        raise HTTPException(

            status_code=404,

            detail=(
                f"'{location}'에 해당하는 "
                "위치를 찾을 수 없습니다."
            )

        )


    # -----------------------------------------------------
    # 5. 검색된 위치의 중심 좌표
    #
    # x = 경도
    # y = 위도
    # -----------------------------------------------------

    center_x = float(
        documents[0]["x"]
    )


    center_y = float(
        documents[0]["y"]
    )


    # -----------------------------------------------------
    # 6. 검색 위치 주변 1.5km 정도의 범위 설정
    # -----------------------------------------------------

    offset = 0.015


    min_x = round(
        center_x - offset,
        5
    )


    max_x = round(
        center_x + offset,
        5
    )


    min_y = round(
        center_y - offset,
        5
    )


    max_y = round(
        center_y + offset,
        5
    )


    logger.info(

        "카카오 검색 [%s] -> "
        "중심:(%f, %f), "
        "BBOX:[minX=%f, maxX=%f, minY=%f, maxY=%f]",

        location,

        center_x,

        center_y,

        min_x,

        max_x,

        min_y,

        max_y

    )


    # -----------------------------------------------------
    # 7. 계산된 좌표를 이용해서 ITS 교통정보 조회
    # -----------------------------------------------------

    return await traffic(

        background_tasks=background_tasks,

        min_x=min_x,

        max_x=max_x,

        min_y=min_y,

        max_y=max_y

    )