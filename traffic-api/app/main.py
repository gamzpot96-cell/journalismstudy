import logging
import os
import math
from datetime import datetime
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import timezone, timedelta

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from app.its_api import get_traffic_information
from app.database import (
    save_traffic_information_list,
    create_traffic_table,
    get_recent_traffic_list
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await run_in_threadpool(create_traffic_table)
    except Exception as e:
        logger.error("Startup DB 초기화 실패: %s", e)
    yield

app = FastAPI(
    title="ITS 교통정보 API",
    description="FastAPI를 이용한 ITS 교통소통정보 API 예제",
    version="1.0.0",
    lifespan=lifespan
)

KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/map")
async def map_page():
    return FileResponse(STATIC_DIR / "map.html")


@app.get("/traffic")
async def traffic(
    min_x: float = Query(..., ge=-180, le=180, description="최소 경도"),
    max_x: float = Query(..., ge=-180, le=180, description="최대 경도"),
    min_y: float = Query(..., ge=-90, le=90, description="최소 위도"),
    max_y: float = Query(..., ge=-90, le=90, description="최대 위도")
):
    if min_x >= max_x or min_y >= max_y:
        raise HTTPException(status_code=422, detail="최소 좌표는 최대 좌표보다 작아야 합니다.")
    try:
        traffic_data = await get_traffic_information(
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y
        )

    except Exception as e:
        logger.warning("ITS API 호출 실패 (%s), 백업 조회", type(e).__name__)
        
        # ITS API 호출 실패 시 해당 좌표 영역(BBOX) 내의 DB 데이터를 조회
        try:
            db_items = await run_in_threadpool(get_recent_traffic_list,
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y,
            limit=200
            )
        except Exception as db_error:
            raise HTTPException(status_code=503, detail="ITS와 백업 DB 모두 사용할 수 없습니다.") from db_error
        
        return {
            "header": {
                "resultCode": "00",
                "resultMsg": "Supabase DB 백업 데이터 반환"
            },
            "body": {
                "items": db_items
            }
        }


    try:
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
                datetime.strptime(created_date, "%Y%m%d%H%M%S").replace(tzinfo=timezone(timedelta(hours=9)))
                if created_date else datetime.now(timezone.utc)
            )

            lat = float(traffic_item.get("coordY", 0)) if traffic_item.get("coordY") else None
            lng = float(traffic_item.get("coordX", 0)) if traffic_item.get("coordX") else None

            traffic_information = (
                road_name,
                road_type,
                link_id,
                speed,
                travel_time,
                traffic_status,
                lat,
                lng,
                collected_at
            )
            traffic_information_list.append(traffic_information)

        if traffic_information_list:
            saved_count = await run_in_threadpool(save_traffic_information_list, traffic_information_list)
            logger.info("ITS 교통정보 DB 저장 확인: %d건", saved_count)

        return traffic_data

    except Exception as e:
        logger.warning("교통정보 백업 저장 실패 (%s)", type(e).__name__)
        return traffic_data

@app.get("/traffic/search")
async def search_traffic_by_location(
    location: str = Query(..., min_length=1, max_length=100, description="검색할 동네 이름 (예: 인사동, 강남역, 혜화동)")
):
    location = location.strip()
    if not location:
        raise HTTPException(status_code=422, detail="검색어를 입력해주세요.")
    if not KAKAO_REST_API_KEY:
        raise HTTPException(
            status_code=500, 
            detail="KAKAO_REST_API_KEY 환경변수가 설정되지 않았습니다."
        )

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
            logger.warning("카카오 API HTTP 오류: %d", exc.response.status_code)
            raise HTTPException(status_code=502, detail="카카오 위치 검색 서비스 오류입니다.") from exc
        except Exception as e:
            logger.warning("카카오 위치 검색 실패 (%s)", type(e).__name__)
            raise HTTPException(status_code=502, detail="동네 위치 정보를 가져오는데 실패했습니다.") from e

    documents = data.get("documents") if isinstance(data, dict) else None
    if not isinstance(documents, list):
        raise HTTPException(status_code=502, detail="카카오 응답 형식이 올바르지 않습니다.")
    if not documents:
        raise HTTPException(status_code=404, detail=f"'{location}'에 해당하는 위치를 찾을 수 없습니다.")

    try:
        center_x = float(documents[0]["x"])
        center_y = float(documents[0]["y"])
        if not (math.isfinite(center_x) and math.isfinite(center_y) and -179.98 <= center_x <= 179.98 and -89.98 <= center_y <= 89.98):
            raise ValueError("Invalid coordinates")
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="카카오 위치 좌표가 올바르지 않습니다.") from exc

    # 반경 범위 설정
    offset = 0.02
    min_x = round(center_x - offset, 5)
    max_x = round(center_x + offset, 5)
    min_y = round(center_y - offset, 5)
    max_y = round(center_y + offset, 5)

    logger.info("카카오 검색 [%s] -> 중심:(%f, %f), BBOX:[minX=%f, maxX=%f, minY=%f, maxY=%f]",
                location, center_x, center_y, min_x, max_x, min_y, max_y)

    result = await traffic(
        min_x=min_x,
        max_x=max_x,
        min_y=min_y,
        max_y=max_y
    )
    return {**result, "location": {"name": location, "x": center_x, "y": center_y}}

@app.get("/test-its-connection")
async def test_its_connection():
    """ITS 서버의 DNS 및 IPv4/IPv6 주소별 TCP 연결을 진단합니다."""
    import asyncio
    import socket
    import time

    host = "openapi.its.go.kr"
    port = 9443
    timeout_seconds = 15.0

    try:
        addresses = await asyncio.wait_for(
            asyncio.to_thread(
                socket.getaddrinfo, host, port,
                family=socket.AF_UNSPEC, type=socket.SOCK_STREAM
            ),
            timeout=timeout_seconds
        )
    except (OSError, asyncio.TimeoutError) as exc:
        logger.warning("ITS DNS 조회 실패 (%s): %s", type(exc).__name__, exc)
        raise HTTPException(status_code=503, detail={
            "stage": "dns",
            "error_type": type(exc).__name__,
            "message": "ITS 서버 DNS 조회 실패"
        }) from exc

    # 중복된 IP 주소는 한 번만 테스트합니다.
    targets = []
    seen = set()
    for family, _, _, _, sockaddr in addresses:
        if family not in (socket.AF_INET, socket.AF_INET6):
            continue
        ip_address = sockaddr[0]
        key = (family, ip_address)
        if key not in seen:
            seen.add(key)
            targets.append((family, ip_address))

    async def check_address(family, ip_address):
        family_name = "IPv4" if family == socket.AF_INET else "IPv6"
        started = time.monotonic()
        writer = None
        try:
            # host 이름 대신 조회된 IP를 직접 지정하여 각 주소를 독립적으로 테스트합니다.
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(
                    host=ip_address, port=port, family=family
                ),
                timeout=timeout_seconds
            )
            return {
                "family": family_name,
                "ip": ip_address,
                "status": "success",
                "elapsed_ms": round((time.monotonic() - started) * 1000, 1)
            }
        except (OSError, asyncio.TimeoutError) as exc:
            logger.warning(
                "ITS %s TCP 연결 실패 (%s): %s",
                family_name, type(exc).__name__, exc
            )
            return {
                "family": family_name,
                "ip": ip_address,
                "status": "failed",
                "error_type": type(exc).__name__,
                "elapsed_ms": round((time.monotonic() - started) * 1000, 1)
            }
        finally:
            if writer is not None:
                writer.close()
                try:
                    await writer.wait_closed()
                except OSError:
                    pass

    results = await asyncio.gather(
        *(check_address(family, ip) for family, ip in targets)
    )
    connected = any(result["status"] == "success" for result in results)
    return {
        "status": "success" if connected else "failed",
        "host": host,
        "port": port,
        "timeout_seconds": timeout_seconds,
        "dns_resolved": bool(addresses),
        "results": results
    }
