import os

import httpx
from dotenv import load_dotenv


# .env 파일에 저장된 환경변수를 불러옵니다.
load_dotenv()


# ITS API Key
ITS_API_KEY = os.getenv("ITS_API_KEY")


# ITS 교통소통정보 API 주소
ITS_API_URL = "https://openapi.its.go.kr:9443/trafficInfo"


async def get_traffic_information(
    min_x: float,
    max_x: float,
    min_y: float,
    max_y: float
):
    """
    ITS 교통소통정보 API를 호출합니다.
    """

    # API Key가 없는지 확인합니다.
    if not ITS_API_KEY:

        raise ValueError(
            "ITS_API_KEY가 .env 파일에 설정되지 않았습니다."
        )


    # ITS API에 전달할 파라미터
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


    # 비동기 HTTP 클라이언트를 생성합니다.
    async with httpx.AsyncClient(timeout=15.0) as client:

        # ITS API에 GET 요청을 보냅니다.
        response = await client.get(
            ITS_API_URL,
            params=request_parameters
        )


        # HTTP 오류가 발생했는지 확인합니다.
        response.raise_for_status()


        # JSON 데이터를 반환합니다.
        return response.json()