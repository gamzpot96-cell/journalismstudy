import logging
import os
import httpx

logger = logging.getLogger(__name__)

ITS_API_KEY = os.getenv("ITS_API_KEY")
ITS_BASE_URL = "https://openapi.its.go.kr:9443/trafficInfo"


async def get_traffic_information(
    min_x: float,
    max_x: float,
    min_y: float,
    max_y: float,
    type_val: str = "all"
):
    if not ITS_API_KEY:
        logger.error("ITS_API_KEY 환경변수가 설정되지 않았습니다.")
        raise ValueError("ITS_API_KEY가 존재하지 않습니다.")

    # ITS Open API 필수 파라미터 매핑
    params = {
        "apiKey": ITS_API_KEY.strip(),
        "type": type_val,
        "getType": "json",
        "minX": str(min_x),
        "maxX": str(max_x),
        "minY": str(min_y),
        "maxY": str(max_y)
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                ITS_BASE_URL,
                params=params,
                timeout=5.0
            )
            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException:
            logger.warning("ITS API 호출 시간 초과 (Timeout)")
            raise Exception("ITS API 요청 타임아웃 발생")

        except httpx.HTTPStatusError as exc:
            logger.error("ITS API HTTP 에러 발생: %s", exc.response.status_code)
            raise Exception(f"ITS API HTTP 에러: {exc.response.status_code}")

        except Exception as exc:
            logger.error("ITS API 호출 중 예외 발생: %s", exc)
            raise exc