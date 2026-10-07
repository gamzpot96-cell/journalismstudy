# app/its_api.py
import logging
import os

import httpx
from dotenv import load_dotenv

# 로그 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)

logger = logging.getLogger(__name__)

# .env 파일의 환경변수를 불러옵니다.
load_dotenv()

# ITS API 설정 (Vercel 접속 차단 및 타임아웃 방지를 위해 8081 포트 URL 적용)
ITS_API_KEY = os.getenv("ITS_API_KEY")
ITS_API_URL = "http://openapi.its.go.kr:8081/api/NTrafficInfo"


async def get_traffic_information(
    min_x: float,
    max_x: float,
    min_y: float,
    max_y: float
):
    """ITS 교통정보 API를 호출하고 응답을 반환합니다."""

    if not ITS_API_KEY:
        logger.error("ITS_API_KEY 존재 여부: False")
        raise ValueError("ITS_API_KEY가 설정되지 않았습니다.")

    logger.info("ITS_API_KEY 존재 여부: True")

    # ITS API 요청 파라미터
    request_parameters = {
        "apiKey": ITS_API_KEY,
        "type": "all",
        "drcType": "all",
        "minX": min_x,
        "maxX": max_x,
        "minY": min_y,
        "maxY": max_y,
        "getType": "json"
    }

    log_parameters = {
        key: value
        for key, value in request_parameters.items()
        if key != "apiKey"
    }

    logger.info("ITS API 요청 시작")
    logger.info("요청 주소: %s", ITS_API_URL)
    logger.info("요청 파라미터: %s", log_parameters)

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # connect 타임아웃을 5초로 명시적으로 세분화 설정
        timeout_config = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)

        async with httpx.AsyncClient(timeout=timeout_config, verify=False) as client:
            response = await client.get(
                ITS_API_URL,
                params=request_parameters,
                headers=headers
            )

        logger.info("HTTP 상태 코드: %s", response.status_code)
        logger.info("응답 Content-Type: %s", response.headers.get("content-type"))
        logger.info("응답 본문 길이: %s bytes", len(response.content))

        response.raise_for_status()

        try:
            traffic_data = response.json()
        except ValueError:
            logger.exception("ITS API 응답을 JSON으로 변환하지 못했습니다.")
            logger.info("응답 본문 미리보기: %s", response.text[:1000])
            raise

        if isinstance(traffic_data, dict):
            logger.info("JSON 최상위 키: %s", list(traffic_data.keys()))
        elif isinstance(traffic_data, list):
            logger.info("JSON 배열 데이터 개수: %s", len(traffic_data))

        logger.info("ITS API 요청 완료")
        return traffic_data

    except httpx.ConnectTimeout:
        logger.exception("ITS API 서버 커넥션 타임아웃 발생 (ConnectTimeout)")
        raise

    except httpx.ConnectError:
        logger.exception("ITS API 서버에 연결할 수 없습니다.")
        raise

    except httpx.TimeoutException:
        logger.exception("ITS API 서버 응답 시간이 초과되었습니다.")
        raise

    except Exception:
        logger.exception("ITS API 처리 중 예상하지 못한 오류가 발생했습니다.")
        raise