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

load_dotenv()

ITS_API_KEY = os.getenv("ITS_API_KEY")
ITS_API_URL = "https://openapi.its.go.kr:9443/trafficInfo"


async def get_traffic_information(
    min_x: float,
    max_x: float,
    min_y: float,
    max_y: float
):
    """ITS 교통정보 API를 호출하고 응답을 반환합니다."""

    if not ITS_API_KEY:
        logger.error("ITS_API_KEY가 설정되지 않았습니다.")
        raise ValueError("ITS_API_KEY가 설정되지 않았습니다.")

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

    # API 키를 제외한 요청 정보만 기록
    log_parameters = {
        key: value
        for key, value in request_parameters.items()
        if key != "apiKey"
    }

    logger.info("ITS API 요청 시작")
    logger.info("요청 주소: %s", ITS_API_URL)
    logger.info("요청 파라미터: %s", log_parameters)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                ITS_API_URL,
                params=request_parameters
            )

            logger.info("HTTP 상태 코드: %s", response.status_code)
            logger.info(
                "응답 Content-Type: %s",
                response.headers.get("content-type")
            )
            logger.info(
                "응답 본문 길이: %s bytes",
                len(response.content)
            )

            # 응답 본문 일부 확인
            response_text = response.text

            logger.info(
                "응답 본문 미리보기: %s",
                response_text[:2000]
            )

            # HTTP 오류가 있으면 예외 발생
            response.raise_for_status()

            # JSON 변환
            try:
                traffic_data = response.json()
            except ValueError:
                logger.exception("응답을 JSON으로 변환하지 못했습니다.")
                raise

            # JSON의 최상위 구조 확인
            if isinstance(traffic_data, dict):
                logger.info(
                    "JSON 최상위 키: %s",
                    list(traffic_data.keys())
                )
            elif isinstance(traffic_data, list):
                logger.info(
                    "JSON 배열 데이터 개수: %s",
                    len(traffic_data)
                )
            else:
                logger.info(
                    "JSON 데이터 유형: %s",
                    type(traffic_data).__name__
                )

            logger.info("ITS API 요청 완료")

            return traffic_data

    except httpx.HTTPStatusError:
        logger.exception("ITS API에서 HTTP 오류가 반환되었습니다.")
        raise

    except httpx.RequestError:
        logger.exception("ITS API 서버에 요청하는 중 오류가 발생했습니다.")
        raise

    except Exception:
        logger.exception("ITS API 처리 중 예상하지 못한 오류가 발생했습니다.")
        raise