import os
import logging

import psycopg


logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Supabase PostgreSQL 연결
# ---------------------------------------------------------
def get_database_connection():

    """
    Supabase PostgreSQL 데이터베이스 연결을 생성합니다.
    """

    # Vercel에서는 Supabase Transaction Pooler 사용
    port = os.getenv(
        "POSTGRES_PORT",
        "6543"
    )


    connection = psycopg.connect(

        host=os.getenv(
            "POSTGRES_HOST"
        ),

        port=port,

        user=os.getenv(
            "POSTGRES_USER"
        ),

        password=os.getenv(
            "POSTGRES_PASSWORD"
        ),

        dbname=os.getenv(
            "POSTGRES_DB",
            "postgres"
        ),

        sslmode=os.getenv(
            "POSTGRES_SSLMODE",
            "require"
        ),

        connect_timeout=10

    )


    return connection


# ---------------------------------------------------------
# 교통정보 테이블 생성
# ---------------------------------------------------------
def create_traffic_table():

    """
    traffic_information 테이블이 없으면 생성합니다.
    """

    create_table_query = """

    CREATE TABLE IF NOT EXISTS traffic_information (

        traffic_id SERIAL PRIMARY KEY,

        road_name VARCHAR(100),

        road_type VARCHAR(50),

        link_id VARCHAR(100),

        speed NUMERIC,

        travel_time NUMERIC,

        traffic_status VARCHAR(20),

        latitude DECIMAL(10, 7),

        longitude DECIMAL(10, 7),

        collected_at TIMESTAMP WITH TIME ZONE
        DEFAULT CURRENT_TIMESTAMP

    );

    """


    try:

        with get_database_connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    create_table_query
                )

                connection.commit()


                logger.info(
                    "traffic_information 테이블 확인/생성 완료"
                )


    except psycopg.OperationalError as e:

        logger.error(
            "DB 연결 실패: %s",
            e
        )


    except Exception as e:

        logger.error(
            "테이블 생성 중 오류 발생: %s",
            e
        )


# ---------------------------------------------------------
# 교통정보 저장
# ---------------------------------------------------------
def save_traffic_information_list(
    traffic_list
):

    """
    ITS에서 받은 교통정보를
    Supabase PostgreSQL에 저장합니다.
    """


    if not traffic_list:

        logger.info(
            "저장할 교통정보가 없습니다."
        )

        return


    insert_query = """

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

    VALUES (

        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s

    );

    """


    try:

        with get_database_connection() as connection:

            with connection.cursor() as cursor:

                cursor.executemany(

                    insert_query,

                    traffic_list

                )


                connection.commit()


                logger.info(

                    "Supabase DB에 %d건의 "
                    "교통정보 저장 완료",

                    len(traffic_list)

                )


    except psycopg.OperationalError as e:

        logger.error(

            "DB 연결 실패: %s",

            e

        )


    except Exception as e:

        logger.error(

            "교통정보 DB 저장 중 오류 발생: %s",

            e

        )


# ---------------------------------------------------------
# DB에 저장된 교통정보 조회
# ---------------------------------------------------------
def get_recent_traffic_list(
    min_x=None,
    max_x=None,
    min_y=None,
    max_y=None,
    limit=200
):

    """
    Supabase에 저장된 교통정보를 조회합니다.

    주의:
    현재 ITS trafficInfo 데이터에는
    정확한 위도/경도 값이 없기 때문에

    latitude / longitude를 이용한
    정확한 위치 필터링은 하지 않습니다.
    """


    # -----------------------------------------------------
    # 좌표가 전달된 경우
    # -----------------------------------------------------

    if all(
        value is not None
        for value in [
            min_x,
            max_x,
            min_y,
            max_y
        ]
    ):

        logger.warning(

            "현재 DB 데이터에는 "
            "교통구간별 위도/경도가 없으므로 "
            "좌표 기반 DB 조회를 수행하지 않습니다."

        )

        return []


    # -----------------------------------------------------
    # 좌표가 없는 경우
    #
    # 가장 최근 데이터만 조회
    # -----------------------------------------------------

    select_query = """

    SELECT

        road_name,

        road_type,

        link_id,

        speed,

        travel_time,

        traffic_status,

        collected_at

    FROM traffic_information

    ORDER BY traffic_id DESC

    LIMIT %s;

    """


    traffic_items = []


    try:

        with get_database_connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(

                    select_query,

                    (limit,)

                )


                rows = cursor.fetchall()


                for row in rows:

                    traffic_item = {

                        "roadName":
                        row[0],

                        "roadDrcType":
                        row[1],

                        "linkId":
                        row[2],

                        "speed":
                        str(row[3])
                        if row[3] is not None
                        else "0",

                        "travelTime":
                        str(row[4])
                        if row[4] is not None
                        else "0",

                        "createdDate":
                        row[6].strftime(
                            "%Y%m%d%H%M%S"
                        )
                        if row[6]
                        else ""

                    }


                    traffic_items.append(
                        traffic_item
                    )


    except psycopg.OperationalError as e:

        logger.error(

            "DB 연결 실패: %s",

            e

        )


    except Exception as e:

        logger.error(

            "DB 교통정보 조회 중 오류 발생: %s",

            e

        )


    return traffic_items