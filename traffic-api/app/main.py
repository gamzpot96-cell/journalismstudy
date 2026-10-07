import logging
import socket
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

@app.get("/test-external")
async def test_external():

    import httpx

    test_url = "https://example.com"

    try:
        async with httpx.AsyncClient(
            timeout=20.0
        ) as client:

            response = await client.get(test_url)

        return {
            "success": True,
            "status_code": response.status_code,
            "response_length": len(response.content)
        }

    except Exception as error:

        return {
            "success": False,
            "error_type": type(error).__name__,
            "error": str(error)
        }


@app.get("/test-its-http")
async def test_its_http():

    import httpx

    test_url = "http://openapi.its.go.kr/trafficInfo"

    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True
        ) as client:

            response = await client.get(
                test_url,
                params={
                    "type": "all",
                    "drcType": "all",
                    "minX": 126.8,
                    "maxX": 127.0,
                    "minY": 37.4,
                    "maxY": 37.6,
                    "getType": "json"
                }
            )

        return {
            "success": True,
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type"),
            "response_length": len(response.content),
            "response_preview": response.text[:500]
        }

    except Exception as error:

        return {
            "success": False,
            "error_type": type(error).__name__,
            "error": str(error)
        }

@app.get("/test-its-connection")
async def test_its_connection():
    """
    Vercel 서버에서 ITS API 서버의
    9443 포트에 연결할 수 있는지 테스트합니다.
    """

    host = "openapi.its.go.kr"
    port = 9443

    try:
        ip_address = socket.gethostbyname(host)

        print("ITS 서버 IP:", ip_address)
        print("ITS 서버 포트:", port)

        connection = socket.create_connection(
            (host, port),
            timeout=10
        )

        connection.close()

        return {
            "success": True,
            "message": "ITS 서버의 9443 포트에 연결할 수 있습니다.",
            "host": host,
            "port": port
        }

    except Exception as error:
        print("ITS 서버 연결 테스트 실패:", error)

        return {
            "success": False,
            "message": "ITS 서버의 9443 포트에 연결할 수 없습니다.",
            "host": host,
            "port": port,
            "error": str(error)
        }

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