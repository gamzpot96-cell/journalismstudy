import os

import mysql.connector
from dotenv import load_dotenv


# .env 파일 불러오기
load_dotenv()


def get_database_connection():
    """
    MySQL 데이터베이스에 연결합니다.
    """

    connection = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )

    return connection