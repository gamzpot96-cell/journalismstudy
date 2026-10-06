import os

import psycopg
from dotenv import load_dotenv


# .env 파일 불러오기
load_dotenv()


def get_database_connection():
    """
    Supabase PostgreSQL 데이터베이스에 연결합니다.
    """

    connection = psycopg.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DATABASE"),
        sslmode=os.getenv("POSTGRES_SSLMODE", "require")
    )

    return connection


def save_traffic_information_list(traffic_information_list):
    """
    ITS에서 받은 여러 개의 교통정보를
    Supabase에 저장합니다.
    """

    connection = get_database_connection()
    cursor = connection.cursor()

    # 한 번에 처리할 데이터 개수
    batch_size = 500

    for start_index in range(0, len(traffic_information_list), batch_size):

        end_index = start_index + batch_size

        batch_data = traffic_information_list[
            start_index:end_index
        ]

        value_placeholders = []

        query_parameters = []

        for traffic_information in batch_data:

            value_placeholders.append(
                "(%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            )

            query_parameters.extend(
                traffic_information
            )

        sql = f"""
            INSERT INTO traffic_information (
                road_name,
                road_type,
                link_id,
                speed,
                travel_time,
                traffic_status,
                latitude,
                longitude,
                collected_at
            )
            VALUES
                {", ".join(value_placeholders)}
            ON CONFLICT (link_id, collected_at)
            DO UPDATE SET
                road_name = EXCLUDED.road_name,
                road_type = EXCLUDED.road_type,
                speed = EXCLUDED.speed,
                travel_time = EXCLUDED.travel_time,
                traffic_status = EXCLUDED.traffic_status,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude
        """

        cursor.execute(
            sql,
            query_parameters
        )

        print(
            f"{min(end_index, len(traffic_information_list))}"
            f"/{len(traffic_information_list)}건 처리"
        )

    connection.commit()

    cursor.close()
    connection.close()

    print(
        f"{len(traffic_information_list)}건의 교통정보를 저장했습니다."
    )