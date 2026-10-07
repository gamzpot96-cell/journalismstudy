import logging
import os
import httpx

logger = logging.getLogger(__name__)

# ITS API Key 가져오기
ITS_API_KEY = os.getenv("ITS_API_KEY")
ITS_BASE_URL = "https://openapi.its.go.kr:9443/trafficInfo"


async def get_traffic_information(
    min_x: float,
    max_x: float,
    min_y: float,
    max_y: float,
    type_val: str = "all"
):
    """
    ITS 국가교통정보센터 API를 호출하여 해당 Bounding Box 범위 내의 교통소통정보를 가져옵니다.
    """
    if not ITS_API_KEY:
        logger.error("ITS_API_KEY 환경변수가 설정되지 않았습니다.")
        raise ValueError("ITS_API_KEY가 존재하지 않습니다.")

    params = {
        "apiKey": ITS_API_KEY,
        "type": type_val,
        "getType": "json",
        "minX": min_x,
        "maxX": max_x,
        "minY": min_y,
        "maxY": max_y
    }

    # Vercel 서버리스 타임아웃 방지를 위해 timeout을 5초로 설정
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
            logger.error("ITS API호출 중 예외 발생: %s", exc)
            raise exc