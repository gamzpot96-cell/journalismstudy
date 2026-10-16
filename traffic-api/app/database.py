import os
import logging
import psycopg

logger = logging.getLogger(__name__)


def get_database_connection():
    """
    Supabase PostgreSQL 데이터베이스 커넥션을 생성하여 반환합니다.
    """
    # Vercel Serverless 환경 대응을 위해 Transaction Pooler 포트(6543) 사용
    port = os.getenv("POSTGRES_PORT", "6543")
    
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=port,
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DB", "postgres"),
        sslmode=os.getenv("POSTGRES_SSLMODE", "require"),
        connect_timeout=10
    )


def create_traffic_table():
    """
    traffic_information 테이블이 없을 경우 생성합니다.
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
        collected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    try:
        with get_database_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(create_table_query)
                conn.commit()
                logger.info("traffic_information 테이블 확인/생성 완료")
    except psycopg.OperationalError as e:
        logger.error("DB 연결 실패 (호스트 또는 네트워크 설정 점검 필요): %s", e)
    except Exception as e:
        logger.error("테이블 생성 중 오류 발생: %s", e)


def save_traffic_information_list(traffic_list):
    """
    수집된 교통정보 리스트를 Supabase DB에 다량(Bulk)으로 저장합니다.
    """
    if not traffic_list:
        return

    insert_query = """
    INSERT INTO traffic_information (
        road_name, road_type, link_id, speed, travel_time,
        traffic_status, latitude, longitude, collected_at
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
    """

    try:
        with get_database_connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(insert_query, traffic_list)
                conn.commit()
                logger.info("Supabase DB에 %d건의 교통정보 저장 완료", len(traffic_list))
    except psycopg.OperationalError as e:
        logger.error("DB 연결 실패 - .env 호스트/비밀번호 정보 또는 인터넷 연결을 확인하세요: %s", e)
    except Exception as e:
        logger.error("교통정보 DB 저장 중 오류 발생: %s", e)


def get_recent_traffic_list(min_x: float = None, max_x: float = None, min_y: float = None, max_y: float = None, limit: int = 200):
    """
    ITS API 타임아웃 발생 시 백업용으로 Supabase DB에서
    해당 좌표 범위 내의 최신 교통정보 데이터를 조회합니다.
    """
    # 좌표 조건이 모두 전달된 경우 범위 쿼리 적용, 없으면 전체 최신 쿼리 적용
    if all(v is not None for v in [min_x, max_x, min_y, max_y]):
        select_query = """
        SELECT road_name, road_type, link_id, speed, travel_time, traffic_status, collected_at
        FROM traffic_information
        WHERE (longitude BETWEEN %s AND %s AND latitude BETWEEN %s AND %s)
           OR (longitude IS NULL OR latitude IS NULL)  -- 좌표가 없는 과거 데이터 호환성 보장
        ORDER BY traffic_id DESC
        LIMIT %s;
        """
        params = (min_x, max_x, min_y, max_y, limit)
    else:
        select_query = """
        SELECT road_name, road_type, link_id, speed, travel_time, traffic_status, collected_at
        FROM traffic_information
        ORDER BY traffic_id DESC
        LIMIT %s;
        """
        params = (limit,)

    traffic_items = []
    try:
        with get_database_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(select_query, params)
                rows = cur.fetchall()
                for row in rows:
                    traffic_items.append({
                        "roadName": row[0],
                        "roadDrcType": row[1],
                        "linkId": row[2],
                        "speed": str(row[3]) if row[3] is not None else "0",
                        "travelTime": str(row[4]) if row[4] is not None else "0",
                        "createdDate": row[6].strftime("%Y%m%d%H%M%S") if row[6] else ""
                    })
    except Exception as e:
        logger.error("DB 교통정보 조회 중 오류 발생: %s", e)
    
    return traffic_items