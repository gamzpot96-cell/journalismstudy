from datetime import datetime

from app.database import save_traffic_information_list
from app.its_api import get_traffic_information


async def test_its_to_database():
    """
    ITS에서 교통정보를 가져와
    전체 데이터를 Supabase에 저장합니다.
    """

    print("ITS 교통정보를 가져오는 중입니다.")

    traffic_data = await get_traffic_information(
        min_x=126.8,
        max_x=127.0,
        min_y=37.4,
        max_y=37.6
    )

    traffic_items = traffic_data["body"]["items"]

    print("ITS 교통정보 개수:", len(traffic_items))

    if len(traffic_items) == 0:
        print("저장할 교통정보가 없습니다.")
        return

    traffic_information_list = []

    for traffic_item in traffic_items:

        # 도로 이름
        road_name = traffic_item.get("roadName")

        # 도로 방향 정보
        road_type = traffic_item.get("roadDrcType")

        # ITS 도로 구간 ID
        link_id = traffic_item.get("linkId")

        # 속도
        speed = int(
            float(traffic_item.get("speed", 0))
        )

        # 통행 시간
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

        collected_at = datetime.strptime(
            created_date,
            "%Y%m%d%H%M%S"
        )

        # 데이터베이스에 저장할 데이터
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

    print(
        "Supabase에 저장할 데이터:",
        len(traffic_information_list)
    )

    # 전체 데이터를 Supabase에 저장
    save_traffic_information_list(
        traffic_information_list
    )

    print("ITS 교통정보 전체 저장이 완료되었습니다.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_its_to_database())